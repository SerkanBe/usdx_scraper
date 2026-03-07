from src.ColorPrint import ColorPrint
from src.dataObjects.Song import Song
from src.sources.databases.UsdbHehoeDe import UsdbHehoeDe


class SongEnrichmentService:
    database:UsdbHehoeDe = None

    # A static cache of song versions and their lyrics sources.
    cache: dict[int, dict[str, set[str]]] = dict()

    def __init__(self, database:UsdbHehoeDe):
        self.database = database


