from src.Filesystem import Filesystem
from src.sources.lyrics.LyricsSourceBase import LyricsSourceBase


class Mock(LyricsSourceBase):
    SONG_URL = 'https://usdb.animux.de/index.php?link=detail&id='

    execute_search_counter = 0
    EXECUTE_SEARCH_RESULTS = [
        [],
        [['0', 'Artist 1 - Song 1']],
        [['1', 'Artist 2 - Song 2']],
        [['9999', 'Artist 3 - Söng 3']],
        [['10000', 'Artist 4 - Sönğ 4']],
        [],
    ]

    def execute_search(self, artist_string: str, title_string: str) -> list[list]:
        self.__class__.execute_search_counter+=1
        return self.__class__.EXECUTE_SEARCH_RESULTS[self.__class__.execute_search_counter-1]

    def create_cookies(self, song_list: list) -> list:
        pass
    def create_login_payload(self, user: str, password: str) -> dict[str, str]:
        pass
    def download_lyrics(self, cookie: str, download_url: str, directory: str):
        pass

    def get_song_url(self, song_id):
        return self.SONG_URL + song_id

    def download_all_lyrics(self, song_list: list) -> list[str]:
        song_directories =  ['Bela B. - Gitarre runter', 'Bodo Wartke - Andrea', 'Christian Steiffen - Flasche Bier Marsch', 'Alice Merton - Lash Out']
        output = self.output_directory

        for directory in song_directories:
            Filesystem.ensure_output_directory(output_path=output +'/' + directory)

        return song_directories