import os

from src.ColorPrint import ColorPrint
from src.EventManager import event_manager


class ScraperConfig:
    output_directory = './output'
    find_all = False

    def __init__(self):
        event_manager.register("post_parser_init", self.event_post_parser_init)
        event_manager.register("parser_parse_args", self.event_parser_parse_args)
        return


    @staticmethod
    def event_post_parser_init(parser):
        # Flags
        parser.add_argument('-fa', '--findAll', action="store_true",
                            help="Set to search for ALL songs matching the inputs. Otherwise the parser will try to find exactly one song per search entry")

        # Output
        parser.add_argument("-o", "--output", action="store", default="",
                            help="The output directory where all songs and their text files should be saved")

        
        return


    def event_parser_parse_args(self, args):

        if args.output and not os.path.isdir(args.output):
            ColorPrint.raise_error(f"Output directory {args.output} does not exist.")


        self.__class__.output_directory = args.output or os.getenv("OUTPUT_DIRECTORY") or "./output"

