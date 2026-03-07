from src.SongEnrichmentService import SongEnrichmentService
from src.dataObjects.Song import Song
from src.sources.databases.UsdbHehoeDe import UsdbHehoeDe


class SongListManager:
    song_list: dict[tuple[str, tuple[str,...]], Song] = dict()
    database:UsdbHehoeDe = None

    def __init__(self, database:UsdbHehoeDe):
        self.database = database


    def add_song(self, song):
        song_tuple = (song.title, tuple(song.artists))
        self.song_list[song_tuple] = song

    def add_songs(self, songs: list[Song]):
        for song in songs:
            song = self.add_lyrics_sources(song=song)
            self.add_song(song)

    def get_songs(self):
        return self.song_list

    def add_lyrics_sources(self, song:Song):
        song_tuple = (song.title, tuple(song.artists))
        try:
            song_id = self.database.get_song_version(song_title=song.title, artist="+".join(song.artists))
        except Exception as e:
            #ColorPrint.print(ColorPrint.WARNING, f"Failed to find lyrics for {song.title} by {song.artists}: {str(e)}")
            return song

        # Fetch the sources.
        sources = self.database.get_lyric_sources(song_version_id=song_id)

        song.add_lyrics_sources(sources=sources)
        sources_for_db: list[tuple[int, str, str]] = list()
        for source in sources:
            urls = set()
            for url in sources[source]:
                sources_for_db.append((song_id, source, url))
                urls.add(url)

            self.song_list[song_tuple].add_lyrics_source(source_class=source, urls=urls)

        self.database.add_sources(sources_for_db)

        return song
