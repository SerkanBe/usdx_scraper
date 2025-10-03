import sys

from dotenv import load_dotenv

from src.CliParser import CliParser
from src.ScraperConfig import ScraperConfig

load_dotenv('.env')



def main():
    # Initialize all the classes we're going to use.
    # have them register themselves with the event manager.
    scraper_config = ScraperConfig()

    # Start with the actual flow.
    parser = CliParser()
    parser.get_args()

    # 0. Make sure the Database is up to date

    # 1. Get the song list using the song sources

    # 2. Add the lyrics-sources to the songs

    # 3. Search and download the lyrics and covers using the lyrics sources

    # 4. Download the media files for songs with lyrics using the media sources


if __name__ == "__main__":
    main()
    sys.exit(0)