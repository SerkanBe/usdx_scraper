import argparse

from src.EventManager import event_manager


class CliParser:
    
    args = None
    parser = None
    
    def __init__(self):
        event_manager.trigger("pre_parser_init")

        self.parser = argparse.ArgumentParser(prog="USDX Song Scraper v2.0",
                                         description="Scrapes your music files, downloads the USDX text files and according YouTube videos")

        event_manager.trigger("post_parser_init", parser=self.parser)

    def add_argument(self, *args, **kwargs):
        self.parser.add_argument(*args, **kwargs)
        
    def get_args(self):
        if not self.args:
            self.args = self.parser.parse_args()
            event_manager.trigger("parser_parse_args", args=self.args)

        return self.args