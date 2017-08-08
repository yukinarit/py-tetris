import enum
import random
import time
import traceback
import collections
from .terminal import Terminal, Color, Renderable, Size, \
        Vector2, Dir, Shape, MouseKey
from .logger import create_logger


__all__ = [
    'Game',
]

FPS = 40 # Game FPS (Frame Per Second)

DEFAULT_COLOR = Color.White

DEFAULT_SIZE = Size.w3xh3


class GameObject(Renderable):
    """
    Base game object.
    """
    def __init__(self, x: float=None, y: float=None):
        super(GameObject, self).__init__()
        self.pos = Vector2(x, y)
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

    def get_pos(self):
        return self.pos

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
        super(Block, self).__init__(*args, **kwargs)

    def get_shape(self):
        return Shape.Square.value
