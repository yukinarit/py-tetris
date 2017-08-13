import sys
import traceback
from .game import Game, ITetrimino, Exit


def run():
    rv = 1

    try:
        with Game() as game:
            o = ITetrimino(x=10, y=10)
            game.add(o)
            game.run()

    except Exit as e:
        rv = e.code

    except Exception as e:
        print(e)
        print(traceback.format_exc())
        sys.exit(rv)
