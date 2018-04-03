import sys
import traceback
from .logging import setup_logger, Level
from .terminal import logger as term_logger
from .game import Game, Exit, logger as game_logger


def setup() -> None:
    setup_logger(game_logger, level=Level.DEBUG,
                 file='tetris.log', color=True)


def run():
    rv = 1

    try:
        setup()
        with Game() as game:
            game.run()

    except Exit as e:
        rv = e.code

    except Exception as e:
        print(e)
        traceback.print_exc()
        sys.exit(rv)
