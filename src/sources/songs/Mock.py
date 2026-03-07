from src.SongSearchItem import SongSearchItem
from src.sources.songs.SongsSourceBase import SongsSourceBase


class Mock(SongsSourceBase):
    def __init__(self, user_args):
        pass
    def get_song_list(self) -> list[str]:
        pass
    def clean_search_list(self, search_list: list[SongSearchItem]) -> list[SongSearchItem]:
        pass