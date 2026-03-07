import os
import re
import sqlite3

import requests
from datetime import datetime

from src.ColorPrint import ColorPrint
from src.EventManager import event_manager


class UsdbHehoeDe():
    DATABASE_HTML = "database/usdb_hehoe_de.html"
    SOURCE_URL = "https://usdb.hehoe.de/"
    DATABASE_SQLITE = "database/usdb_hehoe_de.sqlite"
    DATABASE_SONG_TABLE = "song"
    DATABASE_ARTIST_TABLE = "artist"
    DATABASE_SOURCE_TABLE = "lyrics_source"
    DATABASE_SONG_VERSION_TABLE = "song_version"

    ARTISTS_REGEX = r"<li>[\n\s]*<a name=\".*?\" title=\".*?\">(.*?)</a>[\n\s]*<ul>[\n\s]*(.*?)</ul>[\n\s]*</li>"
    TITLE_REGEX = r"<li>(.*?)(<a .*?</a>)[\n\s]?</li>"
    SOURCE_REGEX = r"<a href=\"(.*?)\" title=\".*?\">(.*?)</a>"

    artist_ids = dict()
    song_ids = dict()

    conn = None

    recreate_database = False

    def __init__(self):
        event_manager.register('post_parser_init', self.event_post_parser_init)
        event_manager.register("parser_parse_args", self.event_parser_parse_args)

        os.makedirs(os.path.dirname(self.DATABASE_HTML), exist_ok=True)
        self.conn = sqlite3.connect(self.DATABASE_SQLITE)
        self.recreate_database = False

    @staticmethod
    def event_post_parser_init(parser):
        parser.add_argument('-rd', '--recreate_database', action="store_true",
                            help="recreate the songs database(s)")

    def event_parser_parse_args(self, args):
        self.recreate_database = args.recreate_database or self.recreate_database



    def _get_source_last_modified(self):
        response = requests.head(self.SOURCE_URL)
        if 'last-modified' in response.headers:
            return datetime.strptime(response.headers['last-modified'], '%a, %d %b %Y %H:%M:%S %Z')
        return datetime.now()

    def _update_html(self):
        should_download = True

        if os.path.exists(self.DATABASE_HTML):
            file_modified = datetime.fromtimestamp(os.path.getmtime(self.DATABASE_HTML))
            source_modified = self._get_source_last_modified()
            should_download = source_modified > file_modified

        if should_download:
            response = requests.get(self.SOURCE_URL)
            with open(self.DATABASE_HTML, 'w', encoding='utf-8') as f:
                f.write(response.text)

        return should_download

    def update_database(self):
        if self.recreate_database:
            self._clear_database()
            self._create_database()
            self.recreate_database = False
            ColorPrint.print(ColorPrint.OKGREEN, f"Created database {self.DATABASE_SQLITE}")
            self._migrate_html_to_db()
        elif self._update_html():
            self._migrate_html_to_db()


    def _clear_database(self):
        self.conn.execute(f"DROP TABLE IF EXISTS {self.DATABASE_SONG_TABLE}")
        self.conn.execute(f"DROP TABLE IF EXISTS {self.DATABASE_ARTIST_TABLE}")
        self.conn.execute(f"DROP TABLE IF EXISTS {self.DATABASE_SOURCE_TABLE}")
        self.conn.execute(f"DROP TABLE IF EXISTS {self.DATABASE_SONG_VERSION_TABLE}")

    def _create_database(self):
        self._create_artist_table()
        self._create_songs_table()
        self._create_song_source_table()
        self._create_song_version_table()
        self._migrate_html_to_db()

    def _migrate_html_to_db(self):

        # Extract the artists, songs and source information from the HTML file.
        (artist_tuples, song_names, song_versions, song_lyrics_sources) = self._parse_html_file()

        # Add all the artists at once
        self.add_artists(artist_tuples)
        # Same for the songs
        self.add_songs(song_names)

        # Load the artists and songs into the static cache for easier access.
        self.artist_ids = self.get_artists_all()
        self.song_ids = self.get_songs_all()

        # Create the song versions and sources with the corresponding IDs.
        song_versions_ids = list()
        for (song_name, artist_name) in song_versions:
            song_versions_ids.append(
                (self.song_ids.get(song_name), self.artist_ids.get(artist_name))
            )
        self.add_song_versions(song_versions_ids)

        # Create the song sources with the corresponding IDs.
        song_versions_ids = self.get_song_version_all()
        sources_for_db: list[tuple[int, str, str]] = list()
        for (song_name, artist_name) in song_lyrics_sources:
            sources = song_lyrics_sources.get((song_name, artist_name))
            song_id = self.song_ids.get(song_name)
            artist_id = self.artist_ids.get(artist_name)
            song_version_id = song_versions_ids.get((song_id, artist_id))
            for source, url in sources:
                sources_for_db.append((song_version_id, source, url))
        self.add_sources(sources_for_db)
        ColorPrint.print(ColorPrint.OKGREEN, f"Migrated UsdbHehoede HTML into database")

        return

    def _parse_html_file(self):
        with open(self.DATABASE_HTML, 'r', encoding='utf-8') as f:
            html = f.read()

        artists = re.findall(self.ARTISTS_REGEX, html, re.DOTALL)

        artist_names = [artist[0].strip() for artist in artists]
        artist_tuples = [(name,) for name in artist_names]

        song_names = list()
        song_versions = list()
        song_lyrics_sources = dict()
        for artist in artists:
            artist_name = artist[0].strip()
            songs = re.findall(self.TITLE_REGEX, artist[1], re.DOTALL)
            for song in songs:
                song_name = song[0].strip() or None
                song_names.append((song_name,))

                lyrics_sources = re.findall(self.SOURCE_REGEX, song[1], re.DOTALL)
                song_version_tuple = (song_name, artist_name)
                song_versions.append(song_version_tuple)

                for lyrics_url, lyrics_source in lyrics_sources:
                    if song_version_tuple in song_lyrics_sources:
                        song_lyrics_sources[song_version_tuple].append((lyrics_source, lyrics_url))
                    else:
                        song_lyrics_sources[song_version_tuple] = [(lyrics_source, lyrics_url)]

        return artist_tuples, song_names, song_versions, song_lyrics_sources

    def add_song_version(self, song_name, artist_name):
        # Avoid duplicates.

        try:
            return self.get_song_version(song_name, artist_name)
        except Exception as e:
            c = self.conn.cursor()
            artist_id = self.get_artist(artist_name)
            if artist_id is None:
                artist_id = self.add_artist(artist_name)
            song_id = self.get_song(song_name)
            if song_id is None:
                song_id = self.add_song(song_name)

            c.execute(f"INSERT INTO {self.DATABASE_SONG_VERSION_TABLE} (artist_id, song_id) VALUES (?, ?)",
                      (artist_id, song_id))
            song_version_id = c.lastrowid

            self.conn.commit()
            return song_version_id

    def add_song_versions(self, song_version_tuples: list[tuple[str, str]]):
        c = self.conn.cursor()
        query = f"INSERT OR IGNORE INTO {self.DATABASE_SONG_VERSION_TABLE} (song_id, artist_id) VALUES (?, ?)"
        c.executemany(query, song_version_tuples)
        self.conn.commit()

    def add_artist(self, artist):
        # Avoid duplicates.
        artist_id = self.get_artist(artist)
        if artist_id is not None:
            return artist_id

        c = self.conn.cursor()
        artist_id = self.get_artist(artist)
        if artist_id is None:
            c.execute(f"INSERT INTO {self.DATABASE_ARTIST_TABLE} (name) VALUES (?)", (artist,))
        self.conn.commit()
        return c.lastrowid

    def add_artists(self, artist_names: list[tuple[str]]):
        c = self.conn.cursor()
        query = f"INSERT OR IGNORE INTO {self.DATABASE_ARTIST_TABLE} (name) VALUES (?)"
        c.executemany(query, artist_names)
        self.conn.commit()

    def add_song(self, song_name):
        song_id = self.get_song(song_name)
        if song_id is not None:
            return song_id

        c = self.conn.cursor()
        c.execute(f"INSERT INTO {self.DATABASE_SONG_TABLE} (song) VALUES (?)", (song_name,))
        self.conn.commit()
        return c.lastrowid

    def add_songs(self, song_names: list[tuple[str]]):
        c = self.conn.cursor()
        query = f"INSERT OR IGNORE INTO {self.DATABASE_SONG_TABLE} (song) VALUES (?)"
        c.executemany(query, song_names)
        self.conn.commit()

    def add_source(self, song_id, source, url):
        # Avoid duplicates.
        if self.get_source_id(song_id, source, url):
            return self.get_source_id(song_id, source, url)

        c = self.conn.cursor()
        c.execute(f"INSERT INTO {self.DATABASE_SOURCE_TABLE} (song_version_id, source, url) VALUES (?, ?, ?)",
                  (song_id, source, url))
        self.conn.commit()
        return c.lastrowid

    def add_sources(self, sources: list[tuple[int, str, str]]):
        c = self.conn.cursor()
        query = f"INSERT OR IGNORE INTO {self.DATABASE_SOURCE_TABLE} (song_version_id, source, url) VALUES (?, ?, ?)"
        c.executemany(query, sources)
        self.conn.commit()

    def get_song_version(self, song_title, artist):
        c = self.conn.cursor()

        artist_id = self.get_artist(artist)
        if artist_id is None:
            raise Exception(f"Failed to find artist {artist}")
        song_id = self.get_song(song_title)
        if song_id is None:
            raise Exception(f"Failed to find song {song_title}")

        c.execute(
            f"SELECT id FROM {self.DATABASE_SONG_VERSION_TABLE} WHERE song_id = ? AND artist_id = ?",
            (song_id, artist_id))
        song_id = c.fetchone()
        if song_id is None:
            raise Exception(f"Failed to find song version {song_title} by {artist}")

        return song_id[0]

    def get_song_version_all(self):
        c = self.conn.cursor()
        c.execute(f"SELECT id, song_id, artist_id FROM {self.DATABASE_SONG_VERSION_TABLE}")
        song_version_ids = c.fetchall()
        if song_version_ids is None:
            return dict()

        result = dict()
        for song_version_id in song_version_ids:
            result[(song_version_id[1], song_version_id[2])] = song_version_id[0]

        return result

    def get_artist(self, artist):
        if not self.__class__.artist_ids.get(artist):
            c = self.conn.cursor()
            c.execute(f"SELECT id FROM {self.DATABASE_ARTIST_TABLE} WHERE name = ?", (artist,))
            artist_id = c.fetchone()
            if artist_id is None:
                return None
            self.__class__.artist_ids[artist] = artist_id[0]

        return self.__class__.artist_ids[artist]

    def get_artists_all(self) -> dict:
        c = self.conn.cursor()
        c.execute(f"SELECT id, name FROM {self.DATABASE_ARTIST_TABLE}")
        artist_ids = c.fetchall()
        if artist_ids is None:
            return dict()
        return dict((song, id) for id, song in dict(artist_ids).items())

    def get_song(self, song_name):
        if not self.__class__.song_ids.get(song_name):
            c = self.conn.cursor()
            c.execute(f"SELECT id FROM {self.DATABASE_SONG_TABLE} WHERE song = ?", (song_name,))
            song_id = c.fetchone()
            if song_id is None:
                return None
            self.__class__.song_ids[song_name] = song_id[0]

        return self.__class__.song_ids[song_name]

    def get_songs_all(self) -> dict:
        c = self.conn.cursor()
        c.execute(f"SELECT id, song FROM {self.DATABASE_SONG_TABLE}")
        song_ids = c.fetchall()
        if song_ids is None:
            return dict()

        return dict((song, id) for id, song in dict(song_ids).items())

    def get_source_id(self, song_version_id: int, source, url):
        c = self.conn.cursor()
        c.execute(f"SELECT id FROM {self.DATABASE_SOURCE_TABLE} WHERE song_version_id = ? AND source = ? AND url = ?",
                  (song_version_id, source, url))
        source_id = c.fetchone()
        if source_id is None:
            return None
        return source_id[0]

    def get_source_ids(self, song_version_id: int):
        c = self.conn.cursor()
        c.execute(f"SELECT id FROM {self.DATABASE_SOURCE_TABLE} WHERE song_version_id = ?", (song_version_id,))
        source_id = c.fetchone()
        if source_id is None:
            return None
        return source_id[0]

    def get_lyric_sources(self, song_version_id: int) -> dict[str, str]:
        c = self.conn.cursor()
        c.execute(f"SELECT source, url FROM {self.DATABASE_SOURCE_TABLE} WHERE song_version_id = ?", (song_version_id,))
        sources = c.fetchall()
        if sources is None:
            return dict()

        return dict((source, url) for source, url in dict(sources).items())

    # Tables

    def _create_artist_table(self):
        self.conn.execute(f"""CREATE TABLE IF NOT EXISTS {self.DATABASE_ARTIST_TABLE} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE
        )""")
        self.conn.commit()

    def _create_songs_table(self):
        self.conn.execute(f"""CREATE TABLE IF NOT EXISTS {self.DATABASE_SONG_TABLE} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            song TEXT UNIQUE
        )""")
        self.conn.commit()

    def _create_song_source_table(self):
        self.conn.execute(f"""CREATE TABLE IF NOT EXISTS {self.DATABASE_SOURCE_TABLE} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            {self.DATABASE_SONG_VERSION_TABLE}_id INTEGER,
            source TEXT,
            url TEXT,
            FOREIGN KEY({self.DATABASE_SONG_VERSION_TABLE}_id) REFERENCES {self.DATABASE_SONG_TABLE}(id)
        )""")
        self.conn.commit()

    def _create_song_version_table(self):
        self.conn.execute(f"""CREATE TABLE IF NOT EXISTS {self.DATABASE_SONG_VERSION_TABLE} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            {self.DATABASE_SONG_TABLE}_id INTEGER,
            {self.DATABASE_ARTIST_TABLE}_id INTEGER,
            FOREIGN KEY(song_id) REFERENCES {self.DATABASE_SONG_TABLE}(id),
            FOREIGN KEY(artist_id) REFERENCES {self.DATABASE_ARTIST_TABLE}(id)
        )""")
        self.conn.commit()
