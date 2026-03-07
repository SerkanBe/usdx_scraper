import sys

from dotenv import load_dotenv

from src.CliParser import CliParser
from src.ColorPrint import ColorPrint
from src.ScraperConfig import ScraperConfig
from src.SongEnrichmentService import SongEnrichmentService
from src.SongListManager import SongListManager
from src.sources.databases.UsdbHehoeDe import UsdbHehoeDe
from src.sources.lyrics.UsdbAnimuxDe import UsdbAnimuxDe
from src.sources.songs.Directory import Directory
from src.sources.songs.File import File
from src.sources.songs.Spotify import Spotify

load_dotenv('.env')

db = UsdbHehoeDe()
song_enrichment_service = SongEnrichmentService(db)


song_sources = [
    File(),
    Directory(),
    Spotify(),
]

lyrics_sources = [
    UsdbAnimuxDe(),
]

media_sources = [
    #Youtube(),
]



def main():
    # Initialize all the classes we're going to use.
    # have them register themselves with the event manager.
    scraper_config = ScraperConfig()

    # Start with the actual flow.
    parser = CliParser()
    parser.get_args()

    # 0. Make sure the Database is up to date
    db.update_database()

    # 1. Get the song list using the song sources
    songs_without_lyrics_sources = []
    song_list = SongListManager(database=db)
    for source in song_sources:
        ColorPrint.print(ColorPrint.OKGREEN, f"Loading songs using {source.__class__}")
        songs = source.get_song_list()
        song_list.add_songs(songs)
        for song in songs:
            if len(song.lyrics_sources) == 0:
                songs_without_lyrics_sources.append(song)
        ColorPrint.print(ColorPrint.OKGREEN, "------------------------")

    ColorPrint.print(ColorPrint.OKGREEN,f"Loaded {len(song_list.get_songs())} unique songs")

    # 2. Loop up the songs without lyrics sources in the lyrics sources
    ColorPrint.print(ColorPrint.OKGREEN,f"Searching for lyrics sources for {len(songs_without_lyrics_sources)} songs")
    still_missing_lyrics = list()
    for source in lyrics_sources:
        songs_unknown_to_source = source.search_songs(songs=songs_without_lyrics_sources)
        song_list.persist_sources(set(songs_without_lyrics_sources) - set(songs_unknown_to_source))
        still_missing_lyrics.extend(songs_unknown_to_source)
    ColorPrint.print(ColorPrint.WARNING, f"Could not determine lyrics for {len(still_missing_lyrics)} songs.")
    ColorPrint.print(ColorPrint.OKGREEN, "------------------------")




    # 3. Search and download the lyrics and covers using the lyrics sources

    # 4. Download the media files for songs with lyrics using the media sources


if __name__ == "__main__":
    main()
    sys.exit(0)