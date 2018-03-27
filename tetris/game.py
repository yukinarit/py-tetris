import abc
import copy
import collections
import datetime
import enum
import functools
import itertools
import time
import traceback
import pathlib
import random
from typing import List, Dict, Tuple, Callable, Any
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


def collided(obj: Renderable, other: Renderable, dx: float=None, dy: float=None):
    if isinstance(obj, GameObject):
        obj.on_collided(Collision(other, dx, dy))


class Collision:
    def __init__(self, other: Renderable, dx: float=None, dy: float=None) -> None:
        self.other = other
        self.dx = dx
        self.dy = dy


class GameObject(Renderable):
    """
    Base game object.
    """
    def __init__(self, x: int, y: int) -> None:
        super().__init__(x, y)
        self.parent: Any = None
        self.children: List['GameObject'] = None
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

    def on_collided(self, col: Collision) -> None:
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


class FieldInfo:
    def __init__(self, x: int, y: int, obj: GameObject=None) -> None:
        self.x = x
        self.y = y
        self.obj = obj
        self.oid = id(self.obj)

class Field:

    def __init__(self, width: int, height: int) -> None:
        self.width = width
        self.height = height
        self.data: List[List[FieldInfo]] = [[None for w in range(0, width)] for h in range(0, height)]
        self.positions: Dict[int, List[FieldInfo]] = collections.defaultdict(list)

    def update(self, x: int, y: int, obj: GameObject):
        x = int(x)
        y = int(y)
        finfo = FieldInfo(x, y, obj)
        self.data[x][y] = finfo
        self.positions[id(obj)].append(finfo)

    def get(self, x: int, y: int) -> FieldInfo:
        x = int(x)
        y = int(y)
        try:
            return self.data[x][y]
        except KeyError:
            return None

    def remove_by(self, oid: int) -> None:
        try:
            positions: List[FieldInfo] = self.positions[oid]
            del self.positions[oid]
            for v in positions:
                self.data[v.x][v.y] = None
        except KeyError:
            pass

    def remove(self, x: int, y: int) -> None:
        finfo = self.get(x, y)
        if not finfo:
            return
        positions = self.positions[finfo.oid]
        self.data[x][y] = None
        for i, p in enumerate(positions):
            if p.x == x and p.y == y:
                del positions[i]
        if not positions:
            del self.positions[finfo.oid]


    def check_filled(self, x: int) -> bool:
        line = self.data[x]
        for c in line:
            if c is None:
                return False
        return True

    def debug_print(self) -> None:
        for x in range(self.width):
            line = self.data[x]
            msg = ""
            for c in line:
                if c is None:
                    msg += '□'
                else:
                    msg += '■'
            logger.debug(msg)
        logger.debug('----------')


class Map(Renderable):
    """
    Map class.
    """
    def __init__(self) -> None:
        self.field: Field = None
        self.data: List[str] = []
        self._width: int = 0
        self._hight: int = 0
        self._cells: List[Cell] = None

    @property
    def size(self) -> Size:
        return Size.w1xh1

    @property
    def width(self) -> int:
        return self._width

    @property
    def height(self) -> int:
        return self._height

    @property
    def shape(self) -> Shape:
        return None

    def make_cells(self) -> List[Cell]:
        if self._cells is not None:
            return self._cells

        cells = []
        self._width = len(self.data[0])
        self._height = len(self.data)
        for y, line in enumerate(self.data):
            for x, c in enumerate(line):
                if c == '*':
                    cell = Cell(x=x, y=y, fg=Color.White, c=ord(c))
                    cells.append(cell)
        self._cells = cells
        return cells

    def load(self, mapfile: pathlib.Path):
        with mapfile.open() as f:
            for line in f:
                if not line:
                    continue
                self.data.append(line.strip())
        self.make_cells()
        self.field = Field(self.width, self.height)


class Block(Renderable):
    """
    A piece of tetrimino.
    """
    def __init__(self, x: float, y: float, fg: Color, bg: Color) -> None:
        self.x = x
        self.y = y
        self.fg = fg
        self.bg = bg

    def make_cells(self) -> List[Cell]:
        x, y = BlockCoordinate.translate_to_cell(self.x, self.y)
        return [Cell(x+n, y, self.fg, self.bg) for n in range(0, CELLX)]


class Tetrimino(GameObject):
    """
    A block in Tetoris called Tetrimino.
    """
    __metaclass__ = abc.ABCMeta

    def __init__(self, angle: Angle, bg: Color=Color.White, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.angle: Angle = angle
        self.rotate: Callable = None
        self.bg = bg

    def on_collided(self, col: Collision) -> None:
        if col.dy is not None and col.dy > 0 and isinstance(self.parent, Game):
            self.parent.will_spawn = True

    def get_shape(self):
        return Shape.Square.value

    def set_rotate(self, f: Callable) -> None:
        self.rotate = f

    def make_cells(self) -> List[Cell]:
        blocks = self.make_blocks()
        collision = False
        if self.rotate:
            blocks_ = self.rotate(blocks)
            # for b in blocks_:
            #     for obj in self.parent.objects:
            #         if check_collision(b, obj):
            #             collision = True
            #             break
            #     if collision:
            #         break
            if not collision:
                blocks = blocks_
        cells = list(itertools.chain(*[b.make_cells() for b in blocks]))
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
        self.will_spawn = False
        self.add(self.map)

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
                    # logger.debug(f'Rotating90 n={n}, dx={dx},dy={dy}')
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
                    # logger.debug(f'Rotating90 n={n}, dx={dx},dy={dy}')
                return blocks

            def rotate180(blocks):
                first = blocks[0]
                for n, b in enumerate(blocks):
                    if b is first:
                        continue
                    dy = 0
                    dx = abs(b.x - first.x)
                    b.x = first.x - dx
                    # logger.debug(f'Rotating180 n={n}, dx={dx},dy={dy}')
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
                    # logger.debug(f'Rotating270 n={n}, dx={dx},dy={dy}')
                return blocks
            rotates = [rotate90, rotate180, rotate270, rotate0]

            for obj in [self.player]:
                if hasattr(obj, 'pos'):
                    logger.debug(f'current_rotate: {current_rotate}')
                    obj.set_rotate(rotates[current_rotate])

            current_rotate += 1
            if current_rotate >= len(rotates):
                current_rotate = 0

            self.terminal.update(now(), self.player, *self.objects)
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
                if self.will_spawn:
                    self.spawn()
                    self.will_spawn = False
                time.sleep(1 / FPS)

        except Exit as e:
            return StatusCode.Exit

        except Exception as e:
            self.terminal.close()
            logger.error(e)
            logger.error(traceback.format_exc())
            return -1
        return 0

    def spawn(self) -> None:
        # tetriminos = [ITetrimino, OTetrimino, STetrimino, TTetrimino, LTetrimino]
        tetriminos = [ITetrimino]
        colors = [Color.White, Color.Red, Color.Green, Color.Yellow,
                  Color.Blue, Color.Magenta, Color.Cyan]
        cls = random.choice(tetriminos)
        self.add(self.player)
        self.add_player(cls(x=4, y=1, bg=random.choice(colors)))

    def move(self, dx: float, dy: float):
        orig = copy.copy(self.player.pos)
        self.player.pos.x += dx
        self.player.pos.y += dy
        for obj in self.objects:  # type: ignore
            if check_collision(self.player, obj):
                collided(self.player, obj, dx, dy)
                collided(obj, self.player)
                self.player.pos = orig
                return

        obj_id = id(self.player)
        self.map.field.remove_by(obj_id)
        for b in self.player.make_blocks():
            for c in b.make_cells():
                self.map.field.update(c.x, c.y, self.player)
        self.terminal.update(now(), *self.objects)

    def add(self, obj: GameObject):
        """
        Add game object to the game.
        """
        obj.parent = self
        self.objects.append(obj)

    def add_player(self, obj: GameObject):
        """
        Add player controllable game object to the game.
        """
        obj.parent = self
        self.player = obj

    def update(self, now: datetime.datetime):
        """
        Update terminal and game objects.
        """
        # Gravity 1.0 point per second.
        if (now - self.last_second).seconds >= 1:
            self.last_second = now
            self.move(dx=0.0, dy=1)
            self.check_tetris()
            self.map.field.debug_print()
        self.terminal.update(now, self.player, *self.objects)

    def check_tetris(self) -> None:
        for x in range(0, self.map.height):
            if self.map.field.check_filled(x):
                logger.debug('The line is filled with blocks. It is going to be deleted.')
                for y in range(0, 20):
                    self.map.field.remove(x, y)
