import time
import traceback
from typing import List
from .terminal import Terminal, Color, Renderable, Size, \
        Vector2, Dir, Shape, MouseKey
from .logger import create_logger
from .exceptions import StatusCode, Exit


__all__ = [
    'Game',
]

FPS = 40  # Game FPS (Frame Per Second)

DEFAULT_COLOR = Color.White

DEFAULT_SIZE = Size.w3xh3


class GameObject(Renderable):
    """
    Base game object.
    """
    def __init__(self, x: int, y: int):
        super(GameObject, self).__init__(x, y)
        self.size = Size.w1xh1
        self.collisions = {}
        self.being_destroyed = False
        self.set_color(fg=DEFAULT_COLOR, bg=DEFAULT_COLOR)
        self.set_size(DEFAULT_SIZE)

    def get_width(self):
        return self.size.value

    def get_height(self):
        return self.size.value

    def get_size(self) -> Size:
        return self.size

    def set_size(self, size):
        if isinstance(size, Size):
            self.size = size
        else:
            self.size = Size(size)

    def on_collision_entered(self, collision=None):
        pass

    def on_collision_exited(self, collision=None):
        pass

    def destroy(self):
        self.being_destroyed = True

    def expand(self):
        value = min(
            self.get_size().value + 2,
            Size.MaxSize.value
        )
        self.set_size(value)

    def shrink(self):
        value = max(
            self.get_size().value - 2,
            Size.MinSize.value
        )
        self.set_size(value)


class Tetrimino(GameObject):
    """
    A block in Tetoris called Tetrimino.
    """
    def __init__(self, *args, **kwargs):
        super(Tetrimino, self).__init__(*args, **kwargs)

    def get_shape(self):
        return Shape.Square.value


class Game:
    """
    Game main class.
    """
    def __init__(self):
        self.terminal: Terminal = Terminal(debug=True)
        self.objects: List[GameObject] = []

        def terminal_on_shutdown():
            raise Exit()
        self.terminal.on_shutdown = terminal_on_shutdown

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.terminal.close()

    def run(self):
        """
        Run the Game loop.
        """
        try:
            while True:
                now = time.time() * 1000

                self.update(now)
                time.sleep(1 / FPS)

        except Exit as e:
            return StatusCode.Exit

        except Exception as e:
            self.terminal.close()
            #logger.error(e)
            #logger.error(traceback.format_exc())
            return -1

        return 0

    def add(self, obj: GameObject):
        """
        Add game object to the game class.
        """
        self.objects.append(obj)

    def update(self, now):
        """
        Update terminal and game objects.
        """
        for obj in self.objects:
            obj.pos.y += 1
        self.terminal.update(now, *self.objects)
