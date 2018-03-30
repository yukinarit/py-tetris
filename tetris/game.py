import abc
import collections
import datetime
import time
import traceback
import pathlib
import random
from typing import List, Dict, Any, Callable  # noqa
from .terminal import Terminal, Renderable, Cell, Color, \
        Shape, Vector2, MouseKey, \
        check_collision, rotate_cells
from .logging import create_logger
from .exceptions import StatusCode, Exit


FPS = 40  # Game FPS (Frame Per Second)

DEFAULT_COLOR = Color.White

basedir = pathlib.Path(__file__).parent

mapdir = basedir

logger = create_logger('game')


def now() -> datetime.datetime:
    return datetime.datetime.now()


def collided(obj: Renderable, other: Renderable, dx: int=None, dy: int=None):
    if isinstance(obj, GameObject):
        obj.on_collided(Collision(other, dx, dy))


class Collision:
    def __init__(self, other: Renderable, dx: int=None, dy: int=None) -> None:
        self.other = other
        self.dx = dx
        self.dy = dy


class GameObject(Renderable):
    """
    Base game object.
    """
    def __init__(self) -> None:
        super().__init__()
        self.gravity = True
        self.parent: Any = None
        self.children: List['GameObject'] = None
        self.set_color(fg=DEFAULT_COLOR, bg=DEFAULT_COLOR)
        self.cells: List[Cell] = []

    def on_collided(self, col: Collision) -> None:
        pass

    def move(self, dx: int, dy: int) -> None:
        pass

    def rotate(self) -> None:
        pass

    def remove(self, cell: Cell) -> None:
        pass


class FieldInfo:
    def __init__(self, x: int, y: int,
                 obj: GameObject=None, cell: Cell=None) -> None:
        self.x = x
        self.y = y
        self.obj = obj
        self.oid = id(self.obj)
        self.cell = cell


class Iter:
    def __init__(self, field: 'Field') -> None:
        self.field = field
        self.oids = list(field.positions.keys())
        self.n = 0
        self.length = len(self.oids)

    def __iter__(self) -> 'Iter':
        return self

    def __next__(self) -> GameObject:
        if self.n < self.length:
            oid = self.oids[self.n]
            self.n += 1
            obj = self.field.positions[oid][0].obj
            if obj:
                return obj
            else:
                return self.__next__()
        else:
            raise StopIteration()


class Field:
    def __init__(self, width: int, height: int) -> None:
        logger.debug(f'Constructing Field w={width} h={height}')
        self.width = width
        self.height = height
        self.data: List[List[FieldInfo]] = [[
            None for w in range(0, width)]
            for h in range(0, height)]
        self.positions: Dict[int, List[FieldInfo]] = \
            collections.defaultdict(list)

    @property
    def children(self) -> Iter:
        return Iter(self)

    def update(self, obj: GameObject):
        self.remove(obj)
        for cell in obj.make_cells():
            x = cell.x
            y = cell.y
            finfo = FieldInfo(x, y, obj, cell)
            self.data[y][x] = finfo
            self.positions[id(obj)].append(finfo)

    def get(self, x: int, y: int) -> FieldInfo:
        try:
            return self.data[y][x]
        except IndexError:
            logger.warn(f'Out of range access ({x},{y})')
            return None

    def remove(self, obj: GameObject) -> None:
        try:
            oid = id(obj)
            positions: List[FieldInfo] = self.positions[oid]
            del self.positions[oid]
            for finfo in positions:
                self.data[finfo.y][finfo.x] = None
        except KeyError as e:
            logger.warn("Tried to remove obj that doesn't exist!")

    def remove_at(self, x: int, y: int) -> None:
        finfo = self.get(x, y)
        if not finfo:
            return
        self.data[y][x] = None

        positions = self.positions[finfo.oid]
        for n, p in enumerate(positions):
            if p.x == x and p.y == y:
                if not isinstance(p.obj, Map):
                    del positions[n]
                p.obj.remove(p.cell)

        if not positions:
            del self.positions[finfo.oid]

    def remove_line(self, y: int) -> None:
        line = self.data[y]
        for x, c in enumerate(line):
            logger.debug(f'Removing cell at ({x},{y})')
            self.remove_at(x, y)

    def check_filled(self, y: int=None, x: int=None) -> bool:
        line = self.data[y]
        if x is not None:
            return line[x] is None
        filled = True
        has_at_least_non_map = False
        for c in line:
            if c is None:
                return False
            if isinstance(c.obj, Map):
                continue
            else:
                has_at_least_non_map = True
        return filled and has_at_least_non_map

    def debug_print(self) -> None:
        for y in range(self.height):
            line = self.data[y]
            msg = ''
            for c in line:
                if c is None:
                    msg += '□'
                else:
                    if isinstance(c.obj, Map):
                        msg += '*'
                    else:
                        msg += '■'
            logger.debug(msg)
        logger.debug('----------')


class Map(GameObject):
    """
    Map class.
    """
    def __init__(self) -> None:
        super().__init__()
        self.data: List[str] = []
        self._width: int = 0
        self._hight: int = 0

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
        return self.cells

    def load(self, mapfile: pathlib.Path):
        logger.debug('Map load START')
        with mapfile.open() as f:
            for line in f:
                if not line:
                    continue
                self.data.append(line.strip())
        self._width = len(self.data[0])
        self._height = len(self.data)
        for y, line in enumerate(self.data):
            logger.debug(line)
            for x, c in enumerate(line):
                if c == '*':
                    cell = Cell(x=x, y=y, bg=Color.White, c=Shape.Square.value)
                    self.cells.append(cell)
        logger.debug('Map load END')


class Tetrimino(GameObject):
    """
    Tetrimino - Blocks in Tetoris.
    """
    __metaclass__ = abc.ABCMeta

    def __init__(self, x: int, y: int, bg: Color=Color.Red) -> None:
        super().__init__()
        self.pos = Vector2(x, y)
        self.bg = bg

    def on_collided(self, col: Collision) -> None:
        if col.dy is not None and col.dy > 0 and self is self.parent.player:
            self.parent.check_tetris()
            self.parent.will_spawn = True

    @property
    def shape(self) -> Shape:
        return Shape.Square.value

    def rotate(self) -> None:
        self.cells = rotate_cells(self.cells)
        for o in self.parent.field.children:
            if check_collision(self, o):
                self.cells = rotate_cells(self.cells, True)
                return

    def make_cells(self) -> List[Cell]:
        return self.cells

    def move(self, dx: int, dy: int) -> None:
        for cell in self.make_cells():
            cell.x += dx
            cell.y += dy

    def remove(self, cell: Cell) -> None:
        del self.cells[self.cells.index(cell)]
        if self is self.parent.player and not self.cells:
            self.parent.will_spawn = True


class ITetrimino(Tetrimino):
    """
    I-Tetorimino. The shape is like this
    ■ ■ ■ ■
    """
    def __init__(self, x: int, y: int) -> None:
        super().__init__(x, y, Color.Cyan)
        x = self.pos.x
        y = self.pos.y
        fg, bg = self.get_color()
        self.cells = [Cell(x, y, fg, bg),
                      Cell(x+1, y, fg, bg),
                      Cell(x+2, y, fg, bg),
                      Cell(x+3, y, fg, bg)]


class OTetrimino(Tetrimino):
    """
    O-Tetorimino. The shape is like this
    ■ ■
    ■ ■
    """
    def __init__(self, x: int, y: int) -> None:
        super().__init__(x, y, Color.Yellow)
        x = self.pos.x
        y = self.pos.y
        fg, bg = self.get_color()
        self.cells = [Cell(x, y, fg, bg),
                      Cell(x+1, y, fg, bg),
                      Cell(x, y+1, fg, bg),
                      Cell(x+1, y+1, fg, bg)]


class STetrimino(Tetrimino):
    """
    S-Tetorimino. The shape is like this
      ■ ■
    ■ ■
    """
    def __init__(self, x: int, y: int) -> None:
        super().__init__(x, y, Color.Green)
        x = self.pos.x
        y = self.pos.y
        fg, bg = self.get_color()
        self.cells = [Cell(x, y, fg, bg),
                      Cell(x+1, y, fg, bg),
                      Cell(x+1, y+1, fg, bg),
                      Cell(x+2, y+1, fg, bg)]


class ZTetrimino(Tetrimino):
    """
    Z-Tetorimino. The shape is like this
    ■ ■
      ■ ■
    """
    def __init__(self, x: int, y: int) -> None:
        super().__init__(x, y, Color.Red)
        x = self.pos.x
        y = self.pos.y
        fg, bg = self.get_color()
        self.cells = [Cell(x, y, fg, bg),
                      Cell(x+1, y, fg, bg),
                      Cell(x+1, y-1, fg, bg),
                      Cell(x+2, y-1, fg, bg)]


class LTetrimino(Tetrimino):
    """
    L-Tetorimino. The shape is like this
        ■
    ■ ■ ■
    """
    def __init__(self, x: int, y: int) -> None:
        super().__init__(x, y, Color.Blue)
        x = self.pos.x
        y = self.pos.y
        fg, bg = self.get_color()
        self.cells = [Cell(x, y, fg, bg),
                      Cell(x+1, y, fg, bg),
                      Cell(x+2, y, fg, bg),
                      Cell(x+2, y+1, fg, bg)]


class JTetrimino(Tetrimino):
    """
    J-Tetorimino. The shape is like this
    ■
    ■ ■ ■
    """
    def __init__(self, x: int, y: int) -> None:
        super().__init__(x, y, Color.Blue)
        x = self.pos.x
        y = self.pos.y
        fg, bg = self.get_color()
        self.cells = [Cell(x, y, fg, bg),
                      Cell(x, y+1, fg, bg),
                      Cell(x+1, y, fg, bg),
                      Cell(x+2, y, fg, bg)]


class TTetrimino(Tetrimino):
    """
    L-Tetorimino. The shape is like this
      ■
    ■ ■ ■
    """
    def __init__(self, x: int, y: int) -> None:
        super().__init__(x, y, Color.Magenta)
        x = self.pos.x
        y = self.pos.y
        fg, bg = self.get_color()
        self.cells = [Cell(x+1, y, fg, bg),
                      Cell(x, y, fg, bg),
                      Cell(x+1, y+1, fg, bg),
                      Cell(x+2, y, fg, bg)]


class Game:
    """
    Game main class.
    """
    def __init__(self) -> None:
        self.terminal: Terminal = Terminal(debug=True)
        self.objects: List[GameObject] = []
        self.map: Map = Map()
        self.map.load(mapdir / 'map.txt')
        self.field = Field(self.map.width, self.map.height)
        self.field.update(self.map)
        self.next_player: GameObject = None
        self.player: GameObject = None
        self.last_second: datetime.datetime = now()
        self.will_spawn = False
        self.add(self.map)

        def terminal_on_shutdown():
            raise Exit()
        self.terminal.on_shutdown = terminal_on_shutdown

        def regist(key: MouseKey, f: Callable):
            self.terminal.set_keydown_handler(key, f)
        regist(MouseKey.Left, lambda k: self.move(self.player, dx=-1, dy=0))
        regist(MouseKey.Right, lambda k: self.move(self.player, dx=1, dy=0))
        regist(MouseKey.Up, lambda k: self.move(self.player, dx=0, dy=-1))
        regist(MouseKey.Down, lambda k: self.move(self.player, dx=0, dy=1))
        regist(MouseKey.Enter, lambda k: self.player.rotate())

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.terminal.close()

    def run(self):
        """
        Run the Game loop.
        """
        self.spawn()
        try:
            while True:
                self.update(now())
                if self.will_spawn:
                    self.spawn()
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
        tetriminos = [ITetrimino, OTetrimino, STetrimino, ZTetrimino,
                      TTetrimino, LTetrimino, JTetrimino]
        cls = random.choice(tetriminos)
        self.add(self.player)
        self.add_player(cls(x=4, y=0))
        self.will_spawn = False
        if not self.player:
            self.spawn()

    def move(self, obj: GameObject, dx: int, dy: int):
        obj.move(dx, dy)
        for o in self.field.children:
            if check_collision(obj, o):
                collided(obj, o, dx, dy)
                collided(o, obj)
                obj.move(-dx, -dy)
                break
        self.field.update(obj)
        self.terminal.update(now(), self.player, *list(self.field.children))

    def add(self, obj: GameObject):
        """
        Add game object to the game.
        """
        if not obj:
            return
        obj.parent = self
        self.field.update(obj)

    def add_player(self, obj: GameObject):
        """
        Add player controllable game object to the game.
        """
        if not obj:
            return
        self.player = self.next_player
        if self.player:
            self.player.gravity = True
            self.player.collidable = True
            self.move(self.player, dx=0, dy=1)
        self.next_player = obj
        self.next_player.gravity = False
        self.next_player.collidable = False
        self.add(self.next_player)

    def update(self, now: datetime.datetime):
        """
        Update terminal and game objects.
        """
        # Gravity: move player 1 point per second.
        if (now - self.last_second).seconds >= 1:
            self.last_second = now
            for obj in self.field.children:
                if obj.gravity:
                    self.move(obj, dx=0, dy=1)
            self.field.debug_print()
        self.terminal.update(now, *list(self.field.children))

    def check_tetris(self) -> None:
        for y in range(0, self.map.height):
            if self.field.check_filled(y=y):
                logger.debug(f'The line is ({y}) filled with blocks.'
                             f' It is going to be deleted.')
                self.field.remove_line(y)
