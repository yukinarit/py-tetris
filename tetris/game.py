import enum
import itertools
import os
import time
import traceback
from typing import List, Dict
from .terminal import Terminal, Renderable, Cell, Color, Size, \
        Shape, render_cells, CELLX, CELLY, Vector2, Rect, MouseKey
from .logger import create_logger
from .exceptions import StatusCode, Exit


FPS = 40  # Game FPS (Frame Per Second)

DEFAULT_COLOR = Color.White

DEFAULT_SIZE = Size.w3xh3

basedir = os.path.abspath(os.path.dirname(__file__))

mapdir = os.path.join(basedir, '.')


class GameObject(Renderable):
    """
    Base game object.
    """
    def __init__(self, x: int, y: int) -> None:
        super().__init__(x, y)
        self.size = Size.w1xh1
        self.collisions: Dict = {}
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


class Angle(enum.IntEnum):
    A0 = enum.auto()
    A90 = enum.auto()
    A270 = enum.auto()


class BlockCoordinate:
    @staticmethod
    def translate_to_cell(x, y):
        return x * CELLX, y * CELLY

    @staticmethod
    def translate_to_block(self, x, y):
        return int(x / CELLX), int(y / CELLY)


class Map(Renderable):
    """
    Map class.
    """
    def __init__(self) -> None:
        self.data: List[str] = []
        self._lb = None
        self._lt = None
        self._rb = None
        self._rt = None

    def load(self, mapfile):
        with open(mapfile) as f:
            for line in f:
                if not line:
                    continue
                self.data.append(line.strip())
        self._lt = Vector2(0, 0)
        self._lb = Vector2(0, len(self.data))
        self._rt = Vector2(len(self.data[0]), 0)
        self._rb = Vector2(len(self.data[0]), len(self.data))

    def render(self, tm=None, dx=0, dy=0):
        cells = []
        for y, line in enumerate(self.data):
            for x, c in enumerate(line):
                cell = Cell(x=x-dx, y=y-dy, fg=Color.White, c=ord(c))
                cells.append(cell)

        render_cells(tm, cells)

    def intersectd_with(self, pos: Vector2=None, rect: Rect=None):
        """
        """
        if pos:
            try:
                v = self.data[pos.y][pos.x].strip()
                if v:
                    return True
                else:
                    return False
            except IndexError:
                return True
        elif rect:
            if self.intersectd_with(rect.lb) or \
                    self.intersectd_with(rect.lt) or \
                    self.intersectd_with(rect.rb) or \
                    self.intersectd_with(rect.rt):
                return True
            else:
                return False
        else:
            pass

    @property
    def lb(self):
        """
        Left bottom
        """
        return self._lb

    @property
    def lt(self):
        """
        Left top
        """
        return self._lt

    @property
    def rb(self):
        """
        Right bottom
        """
        return self._rb

    @property
    def rt(self):
        """
        Right top
        """
        return self._rt

    @property
    def boundary(self):
        return Rect(
            self.lt.x,
            self.lt.y,
            self.rb.x,
            self.rb.y,
        )


class Block():
    """
    A piece of tetrimino.
    """
    def __init__(self, x: int, y: int, fg: Color, bg: Color) -> None:
        x, y = BlockCoordinate.translate_to_cell(x, y)
        self.cells = [Cell(x+n, y, fg, bg) for n in range(0, CELLX)]


class Tetrimino(GameObject):
    """
    A block in Tetoris called Tetrimino.
    """
    def __init__(self, angle: Angle, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.angle: Angle = angle

    def get_shape(self):
        return Shape.Square.value

    def render(self, tm: 'Terminal'=None, dx: float=0, dy: float=0,
               check_intersect: bool=True):
        render_cells(tm, self.make_cells())

    def make_cells(self) -> List[Cell]:
        return []


class ITetrimino(Tetrimino):
    """
    I-Tetorimino. The shape is like this
    ■ ■ ■ ■
    """
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(Angle.A0, *args, **kwargs)

    def make_cells(self) -> List[Cell]:
        x = self.get_pos().x
        y = self.get_pos().y
        fg, bg = self.get_color()
        return [Cell(x+n, y, fg, bg) for n in range(0, 4 * CELLX)]


class OTetrimino(Tetrimino):
    """
    O-Tetorimino. The shape is like this
    ■ ■
    ■ ■
    """
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(Angle.A0, *args, **kwargs)

    def make_cells(self) -> List[Cell]:
        x = self.get_pos().x
        y = self.get_pos().y
        fg, bg = self.get_color()
        cells = []
        for n in range(0, 2*CELLX):
            for m in range(0, 2*CELLY):
                cells.append(Cell(x+n, y+m, fg, bg))
        return cells


class STetrimino(Tetrimino):
    """
    S-Tetorimino. The shape is like this
      ■ ■
    ■ ■
    """
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(Angle.A0, *args, **kwargs)

    def make_cells(self) -> List[Cell]:
        x = self.get_pos().x
        y = self.get_pos().y
        fg, bg = self.get_color()
        cells = list(itertools.chain(
            Block(x, y, fg, bg).cells,
            Block(x+1, y, fg, bg).cells,
            Block(x+1, y+1, fg, bg).cells,
            Block(x+2, y+1, fg, bg).cells))
        return cells

class Game:
    """
    Game main class.
    """
    def __init__(self) -> None:
        self.terminal: Terminal = Terminal(debug=True)
        self.objects: List[GameObject] = []
        self.map = Map()
        self.map.load(os.path.join(mapdir, 'map.txt'))
        self.objects.append(self.map)

        def terminal_on_shutdown():
            raise Exit()
        self.terminal.on_shutdown = terminal_on_shutdown

        def on_left_key():
            for obj in self.objects:
                if hasattr(obj, 'pos'):
                    obj.pos.x -= 0.1
            self.terminal.update(now, *self.objects)
        self.terminal.set_keydown_handler(MouseKey.j, on_left_key)

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
            print(e)
            print(traceback.format_exc())
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
            if hasattr(obj, 'pos'):
                obj.pos.y += 0.1
        self.terminal.update(now, *self.objects)
