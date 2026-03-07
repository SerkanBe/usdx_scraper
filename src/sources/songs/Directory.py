import os

from tinytag import TinyTag

from src.ColorPrint import ColorPrint
from src.EventManager import event_manager
from src.SongSearchItem import SongSearchItem
from src.dataObjects.Song import Song
from src.sources.songs.SongsSourceBase import SongsSourceBase


class Directory(SongsSourceBase):
    # File Types so search for in the SONG_SOURCE_DIRECTORY
    song_file_types = [".mp3",".m4a"]

    input_file_path = []

    def __init__(self):
        event_manager.register('post_parser_init', self.event_post_parser_init)
        event_manager.register("parser_parse_args", self.event_parser_parse_args)
        self.input_file_path = os.getenv("SONG_SOURCES__DIRECTORY__PATH").split(",") or self.input_file_path

    @staticmethod
    def event_post_parser_init(parser):
        parser.add_argument('-i', '--input', action="extend", nargs="+", default=[],
                            help="The path to the directory with all music files to be read")

    def event_parser_parse_args(self, args):
        if args.input:
            self.input_file_path = args.inputTextfile or self.input_file_path

    def get_song_list(self) -> list[Song]:
        song_list = []
        for source_directory in self.input_file_path:
            song_counter = 0
            if not os.path.isdir(source_directory):
                ColorPrint.print(ColorPrint.WARNING, f"Directory {source_directory} does not exist. Skipping...")
                continue

            dir_list = os.listdir(source_directory)
            if not dir_list:
                ColorPrint.print(ColorPrint.WARNING, f"Directory {source_directory} is empty. Skipping...")
                continue

            for file in dir_list:
                if os.path.splitext(file)[1].lower() not in self.song_file_types:
                    ColorPrint.print(ColorPrint.WARNING, f"File {file} is not a song file. Skipping...")
                    continue

                try:
                    song_tags = TinyTag.get(os.path.join(source_directory, file))
                except Exception as e:
                    ColorPrint.print(ColorPrint.FAIL, f"Failed to read metadata from {file}: {str(e)}")
                    continue

                if not song_tags.artist or not song_tags.title:
                    ColorPrint.print(ColorPrint.WARNING, f"File {file} does not contain artist or title. Skipping...")
                    continue

                song_list.append(Song([song_tags.artist], song_tags.title, f"Directory:{source_directory}"))
                song_counter += 1

            ColorPrint.print(ColorPrint.OKGREEN,f"Loaded {song_counter} Songs from Directory '{source_directory}'")


        return song_list
