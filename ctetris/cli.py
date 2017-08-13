import sys
import traceback
from .game import Game, Tetrimino, Exit


def run():
    rv = 1

    try:
        with Game() as game:
            o = Tetrimino(x=10, y=10)
            game.add(o)
            game.run()

    except Exit as e:
        rv = e.code

    except Exception as e:
        print(e)
        print(traceback.format_exc())
        sys.exit(rv)
