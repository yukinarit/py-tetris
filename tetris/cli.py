import sys
import traceback
from .logging import setup_logger, Level
from .terminal import logger as term_logger
from .game import Game, ITetrimino, OTetrimino, STetrimino, LTetrimino, \
    TTetrimino, Exit, Color, logger as game_logger


def run():
    rv = 1
    setup_logger(term_logger, level=Level.DEBUG, file='tetris.log', color=True)
    setup_logger(game_logger, level=Level.DEBUG, file='tetris.log', color=True)

    try:
        with Game() as game:
            game.add_player(TTetrimino(x=4, y=1, bg=Color.Red))
            game.run()

    except Exit as e:
        rv = e.code

    except Exception as e:
        print(e)
        traceback.print_exc()
        sys.exit(rv)
