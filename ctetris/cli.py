import sys
import traceback
from .game import Game, ITetrimino, OTetrimino, Exit


def run():
    rv = 1

    try:
        with Game() as game:
            game.add(ITetrimino(x=10, y=10))
            game.add(OTetrimino(x=20, y=20))
            game.run()

    except Exit as e:
        rv = e.code

    except Exception as e:
        print(e)
        print(traceback.format_exc())
        sys.exit(rv)
