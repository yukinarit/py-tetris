import abc
import collections
import datetime
import time
import traceback
import pathlib
import random
from typing import List, Dict, Tuple, Callable, Any
from .terminal import Terminal, Renderable, Cell, Color, \
        Shape, render_cells, SCALEX, SCALEY, Vector2, MouseKey, \
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
    def __init__(self, x: int, y: int) -> None:
        super().__init__(x, y)
        self.parent: Any = None
        self.children: List['GameObject'] = None
        self.collisions: Dict = {}
        self.being_destroyed = False
        self.set_color(fg=DEFAULT_COLOR, bg=DEFAULT_COLOR)

    def on_collided(self, col: Collision) -> None:
        pass

    def destroy(self):
        self.being_destroyed = True


class FieldInfo:
    def __init__(self, x: int, y: int,
                 obj: GameObject=None, cell: Cell=None) -> None:
        self.x = x
        self.y = y
        self.obj = obj
        self.oid = id(self.obj)
        self.cell = cell


class Field:

    def __init__(self, width: int, height: int) -> None:
        self.width = width
        self.height = height
        self.data: List[List[FieldInfo]] = [[None for w in range(0, width)] for h in range(0, height)]
        self.positions: Dict[int, List[FieldInfo]] = collections.defaultdict(list)

    def update(self, x: int, y: int, obj: GameObject):
        finfo = FieldInfo(x, y, obj)
        self.data[x][y] = finfo
        self.positions[id(obj)].append(finfo)

    def get(self, x: int, y: int) -> FieldInfo:
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
                    cell = Cell(x=x, y=y, fg=Color.White, c=ord(c), scale=False)
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


class Tetrimino(GameObject):
    """
    Tetrimino - Blocks in Tetoris.
    """
    __metaclass__ = abc.ABCMeta

    def __init__(self, bg: Color=Color.White, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.bg = bg
        self.cells: List[Cell] = []

    def on_collided(self, col: Collision) -> None:
        if col.dy is not None and col.dy > 0 and isinstance(self.parent, Game):
            self.parent.will_spawn = True

    @property
    def shape(self) -> Shape:
        return Shape.Square.value

    def rotate(self) -> None:
        self.cells = rotate_cells(self.cells)

    def move(self, dx: int, dy: int) -> None:
        for cell in self.cells:
            cell.x += dx
            cell.y += dy

    def make_cells(self) -> List[Cell]:
        return self.cells


class ITetrimino(Tetrimino):
    """
    I-Tetorimino. The shape is like this
    ■ ■ ■ ■
    """
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        x = self.get_pos().x
        y = self.get_pos().y
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
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        x = self.get_pos().x
        y = self.get_pos().y
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
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        x = self.get_pos().x
        y = self.get_pos().y
        fg, bg = self.get_color()
        self.cells = [Cell(x, y, fg, bg),
                      Cell(x+1, y, fg, bg),
                      Cell(x+1, y+1, fg, bg),
                      Cell(x+2, y+1, fg, bg)]


class LTetrimino(Tetrimino):
    """
    L-Tetorimino. The shape is like this
        ■
    ■ ■ ■
    """
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        x = self.get_pos().x
        y = self.get_pos().y
        fg, bg = self.get_color()
        self.cells = [Cell(x, y, fg, bg),
                      Cell(x+1, y, fg, bg),
                      Cell(x+2, y, fg, bg),
                      Cell(x+2, y+1, fg, bg)]


class TTetrimino(Tetrimino):
    """
    L-Tetorimino. The shape is like this
      ■
    ■ ■ ■
    """
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        x = self.get_pos().x
        y = self.get_pos().y
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
        self.terminal.set_keydown_handler(MouseKey.Enter, lambda k: self.player.rotate())

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
        tetriminos = [ITetrimino, OTetrimino, STetrimino,
                      TTetrimino, LTetrimino]
        colors = [Color.White, Color.Red, Color.Green, Color.Yellow,
                  Color.Blue, Color.Magenta, Color.Cyan]
        cls = random.choice(tetriminos)
        self.add(self.player)
        self.add_player(cls(x=4, y=1, bg=random.choice(colors)))

    def move(self, dx: int, dy: int):
        self.player.move(dx, dy)
        for obj in self.objects:  # type: ignore
            if check_collision(self.player, obj):
                collided(self.player, obj, dx, dy)
                collided(obj, self.player)
                self.player.move(-dx, -dy)
                return

        # obj_id = id(self.player)
        # self.map.field.remove_by(obj_id)
        # for b in self.player.make_blocks():
        #     for c in b.make_cells():
        #         self.map.field.update(c.x, c.y, self.player)
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
            self.move(dx=0, dy=1)
            self.check_tetris()
            # self.map.field.debug_print()
        self.terminal.update(now, self.player, *self.objects)

    def check_tetris(self) -> None:
        for x in range(0, self.map.height):
            if self.map.field.check_filled(x):
                logger.debug('The line is filled with blocks. It is going to be deleted.')
                for y in range(0, 20):
                    self.map.field.remove(x, y)
