import abc
import copy
import datetime
import enum
import functools
import itertools
import time
import traceback
import pathlib
from typing import List, Dict, Callable
from .terminal import Terminal, Renderable, Cell, Color, Size, \
        Shape, render_cells, CELLX, CELLY, Vector2, Rect, MouseKey, \
        check_collision
from .logging import create_logger
from .exceptions import StatusCode, Exit


FPS = 40  # Game FPS (Frame Per Second)

DEFAULT_COLOR = Color.White

DEFAULT_SIZE = Size.w3xh3

basedir = pathlib.Path(__file__).parent

mapdir = basedir

logger = create_logger('game')


def now() -> datetime.datetime:
    return datetime.datetime.now()


class GameObject(Renderable):
    """
    Base game object.
    """
    def __init__(self, x: int, y: int) -> None:
        super().__init__(x, y)
        self.collisions: Dict = {}
        self.being_destroyed = False
        self.set_color(fg=DEFAULT_COLOR, bg=DEFAULT_COLOR)
        self.size = DEFAULT_SIZE

    @property
    def width(self) -> int:
        return self.size.value

    @property
    def height(self) -> int:
        pass

    @property
    def size(self) -> Size:
        return self._size

    @size.setter
    def size(self, size) -> None:
        if isinstance(size, Size):
            self._size = size
        else:
            self._size = Size(size)

    def on_collided(self, other: Renderable=None):
        pass

    def destroy(self):
        self.being_destroyed = True


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
        self._lb: Vector2 = None
        self._lt: Vector2 = None
        self._rb: Vector2 = None
        self._rt: Vector2 = None

    @property
    def size(self) -> Size:
        return Size.w1xh1

    @property
    def width(self) -> int:
        pass

    @property
    def height(self) -> int:
        pass

    @property
    def shape(self) -> Shape:
        return None

    def make_cells(self) -> List[Cell]:
        cells = []
        for y, line in enumerate(self.data):
            for x, c in enumerate(line):
                if c == '*':
                    cell = Cell(x=x, y=y, fg=Color.White, c=ord(c))
                    cells.append(cell)
        return cells

    def load(self, mapfile: pathlib.Path):
        with open(str(mapfile)) as f:
            for line in f:
                if not line:
                    continue
                self.data.append(line.strip())
        self._lt = Vector2(0, 0)
        self._lb = Vector2(0, len(self.data))
        self._rt = Vector2(len(self.data[0]), 0)
        self._rb = Vector2(len(self.data[0]), len(self.data))

    def intersectd_with(self, pos: Vector2=None, rect: Rect=None):
        """
        """
        if pos:
            try:
                v = self.data[int(pos.y)][int(pos.x)].strip()
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


class Block:
    """
    A piece of tetrimino.
    """
    def __init__(self, x: float, y: float, fg: Color, bg: Color) -> None:
        self.x = x
        self.y = y
        self.fg = fg
        self.bg = bg

    @property
    def cells(self) -> List[Cell]:
        x, y = BlockCoordinate.translate_to_cell(self.x, self.y)
        return [Cell(x+n, y, self.fg, self.bg) for n in range(0, CELLX)]


class Tetrimino(GameObject):
    """
    A block in Tetoris called Tetrimino.
    """
    __metaclass__ = abc.ABCMeta

    def __init__(self, angle: Angle, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.angle: Angle = angle
        self.rotate: Callable = None

    def on_collided(self, other: Renderable=None):
        logger.debug(f'Collided with {other}.')

    def get_shape(self):
        return Shape.Square.value

    def set_rotate(self, f: Callable) -> None:
        self.rotate = f

    def make_cells(self) -> List[Cell]:
        blocks = self.make_blocks()
        if self.rotate:
            blocks = self.rotate(blocks)
        cells = list(itertools.chain(*[b.cells for b in blocks]))
        return cells

    @abc.abstractmethod
    def make_blocks(self) -> List[Block]:
        pass


class ITetrimino(Tetrimino):
    """
    I-Tetorimino. The shape is like this
    ■ ■ ■ ■
    """
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(Angle.A0, *args, **kwargs)

    def make_blocks(self) -> List[Block]:
        x = self.get_pos().x
        y = self.get_pos().y
        fg, bg = self.get_color()
        return [
            Block(x, y, fg, bg),
            Block(x+1, y, fg, bg),
            Block(x+2, y, fg, bg),
            Block(x+3, y, fg, bg)]


class OTetrimino(Tetrimino):
    """
    O-Tetorimino. The shape is like this
    ■ ■
    ■ ■
    """
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(Angle.A0, *args, **kwargs)

    def make_blocks(self) -> List[Block]:
        x = self.get_pos().x
        y = self.get_pos().y
        fg, bg = self.get_color()
        return [
            Block(x, y, fg, bg),
            Block(x+1, y, fg, bg),
            Block(x, y+1, fg, bg),
            Block(x+1, y+1, fg, bg)]


class STetrimino(Tetrimino):
    """
    S-Tetorimino. The shape is like this
      ■ ■
    ■ ■
    """
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(Angle.A0, *args, **kwargs)

    def make_blocks(self) -> List[Block]:
        x = self.get_pos().x
        y = self.get_pos().y
        fg, bg = self.get_color()
        return [
            Block(x, y, fg, bg),
            Block(x+1, y, fg, bg),
            Block(x+1, y+1, fg, bg),
            Block(x+2, y+1, fg, bg)]


class LTetrimino(Tetrimino):
    """
    L-Tetorimino. The shape is like this
        ■
    ■ ■ ■
    """
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(Angle.A0, *args, **kwargs)

    def make_blocks(self) -> List[Block]:
        x = self.get_pos().x
        y = self.get_pos().y
        fg, bg = self.get_color()
        return [
            Block(x, y, fg, bg),
            Block(x+1, y, fg, bg),
            Block(x+2, y, fg, bg),
            Block(x+2, y+1, fg, bg)]


class TTetrimino(Tetrimino):
    """
    L-Tetorimino. The shape is like this
      ■
    ■ ■ ■
    """
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(Angle.A0, *args, **kwargs)

    def make_blocks(self) -> List[Block]:
        x = self.get_pos().x
        y = self.get_pos().y
        fg, bg = self.get_color()
        return [
            Block(x, y, fg, bg),
            Block(x+1, y, fg, bg),
            Block(x+1, y+1, fg, bg),
            Block(x+2, y, fg, bg)]


class Game:
    """
    Game main class.
    """
    def __init__(self) -> None:
        self.terminal: Terminal = Terminal(debug=True)
        self.objects: List[GameObject] = []
        self.map: Map = Map()
        self.map.load(mapdir / 'map.txt')
        self.player: GameObject = None
        self.last_second: datetime.datetime = now()

        def terminal_on_shutdown():
            raise Exit()
        self.terminal.on_shutdown = terminal_on_shutdown
        self.terminal.set_keydown_handler(MouseKey.Left, lambda k: self.move(dx=-1, dy=0.0))
        self.terminal.set_keydown_handler(MouseKey.Right, lambda k: self.move(dx=1, dy=0.0))
        self.terminal.set_keydown_handler(MouseKey.Up, lambda k: self.move(dx=0.0, dy=-1))
        self.terminal.set_keydown_handler(MouseKey.Down, lambda k: self.move(dx=0.0, dy=1))

        current_rotate = 0

        def rotate(key):
            nonlocal current_rotate

            def rotate0(blocks):
                first = blocks[0]
                for n, b in enumerate(blocks):
                    if b is first:
                        continue
                    dx = 0
                    dy = 0
                    logger.debug(f'Rotating90 n={n}, dx={dx},dy={dy}')
                return blocks

            def rotate90(blocks):
                first = blocks[0]
                for n, b in enumerate(blocks):
                    if b is first:
                        continue
                    dx = abs(b.x - first.x)
                    dy = abs(b.y - first.y)
                    b.x = first.x - dy
                    b.y = first.y - dx
                    logger.debug(f'Rotating90 n={n}, dx={dx},dy={dy}')
                return blocks

            def rotate180(blocks):
                first = blocks[0]
                for n, b in enumerate(blocks):
                    if b is first:
                        continue
                    dy = 0
                    dx = abs(b.x - first.x)
                    b.x = first.x - dx
                    logger.debug(f'Rotating180 n={n}, dx={dx},dy={dy}')
                return blocks

            def rotate270(blocks):
                first = blocks[0]
                for n, b in enumerate(blocks):
                    if b is first:
                        continue
                    dx = abs(b.x - first.x)
                    dy = abs(b.y - first.y)
                    b.x = first.x - dy
                    b.y = first.y + dx
                    logger.debug(f'Rotating270 n={n}, dx={dx},dy={dy}')
                return blocks
            rotates = [rotate90, rotate180, rotate270, rotate0]

            for obj in [self.player]:
                if hasattr(obj, 'pos'):
                    logger.warn(f'current_rotate: {current_rotate}')
                    obj.set_rotate(rotates[current_rotate])

            current_rotate += 1
            if current_rotate >= len(rotates):
                current_rotate = 0

            self.terminal.update(now(), self.map, self.player, *self.objects)
        self.terminal.set_keydown_handler(MouseKey.Enter, rotate)

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
                self.update(now())
                time.sleep(1 / FPS)

        except Exit as e:
            return StatusCode.Exit

        except Exception as e:
            self.terminal.close()
            logger.error(e)
            logger.error(traceback.format_exc())
            return -1

        return 0

    def move(self, dx: float, dy: float):
        orig = copy.copy(self.player.pos)
        self.player.pos.x += dx
        self.player.pos.y += dy
        for obj in itertools.chain([self.map], self.objects):  # type: ignore
            if check_collision(self.player, obj):
                self.player.pos = orig
                return
        self.terminal.update(now(), *self.objects)

    def add(self, obj: GameObject):
        """
        Add game object to the game.
        """
        self.objects.append(obj)

    def add_player(self, obj: GameObject):
        """
        Add player controllable game object to the game.
        """
        self.player = obj

    def update(self, now: datetime.datetime):
        """
        Update terminal and game objects.
        """
        # Gravity 1.0 point per second.
        if (now - self.last_second).seconds >= 1:
            self.last_second = now
            self.move(dx=0.0, dy=1)
        self.terminal.update(now, self.map, self.player, *self.objects)
        self.update_collision(now)

    def update_collision(self, now: datetime.datetime) -> None:
        def collided(obj: Renderable, other: Renderable):
            if isinstance(obj, GameObject):
                obj.on_collided(other)

        for obj in itertools.chain([self.map], self.objects):  # type: ignore
            if check_collision(self.player, obj):
                collided(self.player, obj)
                collided(obj, self.player)
