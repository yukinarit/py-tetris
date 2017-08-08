import datetime
import sys
import traceback
from .terminal import Terminal, Vector2, Size, Exit
from .game import Block


def run():
    rv = 1

    try:
        with Terminal(debug=True) as term:
            while True:
                o = Block(x=10, y=10)
                term.update(datetime.datetime.now(), [o])

    except Exit as e:
        rv = e.code

    except Exception as e:
        print(e)
        print(traceback.format_exc())
        sys.exit(rv)
