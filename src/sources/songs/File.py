import os

from src.ColorPrint import ColorPrint
from src.EventManager import event_manager
from src.dataObjects.Song import Song
from src.sources.songs.SongsSourceBase import SongsSourceBase


class File(SongsSourceBase):
    # The delimiter in the text file to separate the song names from the artist names.
    SONG_SOURCES__FILE__COL_DELIMITER = ';'
    SONG_SOURCES__FILE__ARTISTS_DELIMITER = ','

    input_file_path = []

    def __init__(self):
        event_manager.register('post_parser_init', self.event_post_parser_init)
        event_manager.register("parser_parse_args", self.event_parser_parse_args)
        self.input_file_path = os.getenv("SONG_SOURCES__FILE__PATH").split(",") or self.input_file_path
        self.SONG_SOURCES__FILE__COL_DELIMITER = os.getenv(
            "SONG_SOURCES__FILE__COL_DELIMITER") or self.SONG_SOURCES__FILE__COL_DELIMITER

    @staticmethod
    def event_post_parser_init(parser):
        parser.add_argument('-f', '--songsFile', nargs='+', help='Path to the text file containing the song names')

    def event_parser_parse_args(self, args):
        if args.songsFile:
            self.input_file_path = args.songsFile or self.input_file_path

    def get_song_list(self) -> list[Song]:
        song_list = []
        for textfile in self.input_file_path:
            song_counter = 0
            if not os.path.isfile(textfile):
                ColorPrint.print(ColorPrint.WARNING, f"File {textfile} does not exist. Skipping...")
                continue

            with open(file=textfile, mode="r", encoding='utf-8') as f:
                entries = f.read().splitlines()

            for entry in entries:
                (artist, song) = entry.split(self.SONG_SOURCES__FILE__COL_DELIMITER, 1)
                artists = artist.split(self.SONG_SOURCES__FILE__ARTISTS_DELIMITER)
                song_list.append(Song(artists=artists, title=song, _source=f"File:{textfile}"))
                song_counter += 1
            ColorPrint.print(ColorPrint.OKGREEN, f"Loaded {song_counter} Songs from File '{textfile}'")

        return song_list
