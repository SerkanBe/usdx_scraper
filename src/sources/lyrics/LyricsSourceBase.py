from src.dataObjects.Song import Song


class LyricsSourceBase:


    # Search the list of songs in the Lyrics Source.
    # Update the songs with the source and URL.
    # Return the remaining list of songs.
    def search_songs(self, songs: list[Song]) -> list[Song]:
        pass

    # Download the lyrics of the songs.
    # Update the songs with a flag if the lyrics were downloaded.
    # Return the list of songs.
    def download_lyrics(self, songs: list[Song]) -> list[Song]:
        pass