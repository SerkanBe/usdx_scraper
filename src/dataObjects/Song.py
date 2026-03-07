class Song():
    # Information about the song.
    artists: list[str] = []
    title: str = None
    year: int|None = None
    language: str|None = None
    bpm: int|None = None

    # Which LyricsSource to download the lyrics from
    # A dict mapping the source name to the URL. (Or whatever the source class might need to identify)
    lyrics_sources: dict[str, set[str]] = {}

    # Do we already have this song?
    _exists: bool = False

    # Which Song-Source did add this song to the list?
    _source: str|None = None

    def __init__(self, artists: list[str], title, _source: str = None):
        self.artists = artists
        self.title = title
        self.year = None
        self.language = None
        self.bpm = None
        self.lyrics_sources:dict[str,set[str]] = dict()
        self._exists = False
        self._source = _source


    def set_year(self, year):
        self.year = year
    def set_language(self, language):
        self.language = language
    def set_bpm(self, bpm):
        self.bpm = bpm

    def add_lyrics_source(self, source_class:str, urls: set[str]):
        if source_class not in self.lyrics_sources:
            self.lyrics_sources[source_class] = set()
        for url in urls:
            self.lyrics_sources[source_class].add(url)

    def add_lyrics_sources(self, sources:dict[str, set[str]]):
        for source in sources:
            self.add_lyrics_source(source, sources[source])

    def __str__(self):
        return f"{self.title} by {self.artists} from {self._source}"
