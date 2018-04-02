import abc
import enum
import random
import pathlib
from typing import List, Dict, Tuple, Union, Callable  # noqa
from termbox import (DEFAULT, BLACK, RED, GREEN, YELLOW, BLUE,  # type: ignore
                     MAGENTA, CYAN, WHITE, KEY_ESC,
                     KEY_INSERT, KEY_DELETE, KEY_HOME, KEY_END,
                     KEY_PGUP, KEY_PGDN, KEY_ARROW_UP, KEY_ARROW_DOWN,
                     KEY_ARROW_LEFT, KEY_ARROW_RIGHT, KEY_MOUSE_LEFT,
                     KEY_MOUSE_RIGHT, KEY_MOUSE_MIDDLE, KEY_MOUSE_RELEASE,
                     KEY_MOUSE_WHEEL_UP, KEY_MOUSE_WHEEL_DOWN,
                     KEY_ENTER, KEY_SPACE, Termbox)
from .logging import create_logger
from .exceptions import Exit


basedir = pathlib.Path(__file__).parent

DEFAULT_SQUARE = 0x0020

DEFAULT_COLOR = DEFAULT

SCALEX = 2

SCALEY = 1

logger = create_logger('term')


class Color(enum.IntEnum):
    """
    Color enum representing terminal colors.
    """
    Default = DEFAULT
    Black = BLACK
    Red = RED
    Green = GREEN
    Yellow = YELLOW
    Blue = BLUE
    Magenta = MAGENTA
    Cyan = CYAN
    White = WHITE
    Random = 0x09

    @classmethod
    def random_color(cls):
        return random.randint(cls.Default, cls.Random - 1)


class Shape(enum.Enum):
    """
    Shape enum.
    """
    Square = ord(' ')
    Bullet = ord('•')
    Star = ord('*')
    Default = Square


class Vector2:
    """
    Vector 2D class.
    """
    def __init__(self, x: int=None, y: int=None) -> None:
        self.x: int = x
        self.y: int = y

    def __add__(self, other) -> 'Vector2':
        return Vector2(self.x + other.x, self.y + other.y)

    def __sub__(self, other) -> 'Vector2':
        return Vector2(self.x - other.x, self.y - other.y)

    def __repr__(self) -> str:
        return f'<Vector2(x={self.x},y={self.y})>'

    def __str__(self) -> str:
        return f'(x={self.x},y={self.y})'


class Cell:
    """
    Cell object.
    """
    def __init__(self, x: int=None, y: int=None, fg: Color=None,
                 bg: Color=None, c: int=None, scale: bool=True) -> None:
        self.c: int = c or Shape.Default.value
        self.x: int = x
        self.y: int = y
        self.fg: Color = fg or Color.Default
        self.bg: Color = bg or Color.Default
        self.scale: bool = scale

    def __repr__(self) -> str:
        return f'Cell: x={self.x},y={self.y},c={self.c}'


def render_objects(tm: 'Terminal', *objects):
    """
    Render objects in terminal.
    """
    if not tm:
        raise RuntimeError('Null terminal')
    if not tm.tb:
        raise RuntimeError('Null termbox')

    for o in objects:
        if not o:
            continue
        o.render(tm)


def render_cells(tm: 'Terminal', cells: List[Cell]) -> None:
    """
    Render cells in terminal.
    """
    if not tm.tb:
        raise RuntimeError('Null termbox')
    for cell in cells:
        for scaled in scale_cells(cell):
            tm.tb.change_cell(scaled.x, scaled.y,
                              scaled.c, scaled.fg, scaled.bg)


def scale_cells(cells: Union[Cell, List[Cell]]) -> List[Cell]:
    if isinstance(cells, Cell):
        cells = [cells]

    scaled: List[Cell] = []

    for cell in cells:
        if cell.scale:
            scalex = SCALEX
            scaley = SCALEY
        else:
            scalex = 1
            scaley = 1
        for sx in range(scalex):
            for sy in range(scaley):
                scaled.append(Cell(cell.x*scalex+sx, cell.y*scaley+sy,
                                   cell.fg, cell.bg, cell.c, scale=False))
    return scaled


def rotate_cells(cells: Union[Cell, List[Cell]], backward=False) -> List[Cell]:
    if isinstance(cells, Cell):
        return [cells]
    first = cells[0]
    for n, c in enumerate(cells):
        if c is first:
            continue
        dx = c.x - first.x
        dy = c.y - first.y
        if not backward:
            c.x = first.x + dy
            c.y = first.y - dx
        else:
            c.x = first.x - dy
            c.y = first.y + dx
    return cells


def check_collision(a: 'Renderable', b: 'Renderable') -> bool:
    """
    True if two objects are being collided, False otherwise.
    """
    if a is b:
        return False
    if not a.collidable or not b.collidable:
        return False
    acells = scale_cells(a.make_cells())
    bcells = scale_cells(b.make_cells())
    for ac in acells:
        for bc in bcells:
            if ac.x == bc.x and ac.y == bc.y:
                return True
    return False


class Renderable:
    """
    Renderable object base.
    """
    __metaclass__ = abc.ABCMeta

    def __init__(self, x: int=None, y: int=None) -> None:
        self.pos: Vector2 = Vector2(x, y)
        self.prev_pos: Vector2 = None
        self.fg: Color = None
        self.bg: Color = None
        self.collidable = True

    def render(self, tm: 'Terminal'=None, dx: int=0, dy: int=0,
               check_intersect: bool=True) -> None:
        """
        Render object.
        """
        render_cells(tm, self.make_cells())

    @abc.abstractmethod
    def make_cells(self) -> List[Cell]:
        pass

    @abc.abstractproperty
    def shape(self) -> Shape:
        return None

    def set_color(self, fg: Color, bg: Color):
        """
        Set foreground, background color.
        """
        self.fg = fg
        self.bg = bg
        if self.fg == Color.Random:
            self.fg = Color.random_color()
        if self.bg == Color.Random:
            self.bg = Color.random_color()

    def get_color(self) -> Tuple[Color, Color]:
        """
        Get foreground, background color.
        """
        return self.fg, self.bg


class MouseKey(enum.Enum):
    ESC = KEY_ESC
    Insert = KEY_INSERT
    Delete = KEY_DELETE
    Home = KEY_HOME
    End = KEY_END
    PgUp = KEY_PGUP
    PgDown = KEY_PGDN
    Up = KEY_ARROW_UP
    Down = KEY_ARROW_DOWN
    Left = KEY_ARROW_LEFT
    Right = KEY_ARROW_RIGHT
    MouseLeft = KEY_MOUSE_LEFT
    MouseRight = KEY_MOUSE_RIGHT
    MouseMiddle = KEY_MOUSE_MIDDLE
    MouseRelease = KEY_MOUSE_RELEASE
    MouseWheelUp = KEY_MOUSE_WHEEL_UP
    MouseWheelDown = KEY_MOUSE_WHEEL_DOWN
    Enter = KEY_ENTER
    Space = KEY_SPACE
    a = 'a'
    b = 'b'
    c = 'c'
    d = 'd'
    e = 'e'
    f = 'f'
    g = 'g'
    h = 'h'
    i = 'i'
    j = 'j'
    k = 'k'
    l = 'l'  # noqa
    m = 'm'
    n = 'n'
    o = 'o'
    p = 'p'
    q = 'q'
    r = 'r'
    s = 's'
    t = 't'
    u = 'u'
    v = 'v'
    w = 'w'
    x = 'x'
    y = 'y'
    z = 'z'


class Terminal:
    """
    Terminal class.
    """
    TermboxCls = Termbox

    def __init__(self, debug=False) -> None:
        self.tb = self.TermboxCls()
        logger.debug("init {}".format(self.tb))
        self.debug = debug
        self._keydown_handlers: Dict[MouseKey, Callable] = {}
        self._on_shutdown: Callable = None

    def __enter__(self) -> 'Terminal':
        logger.debug("entering {}".format(self.tb))
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        logger.debug("exiting {}".format(self.tb))
        self.close()

    def __del__(self) -> None:
        logger.debug("deleting {}".format(self.tb))
        self.close()

    def close(self) -> None:
        if self.tb:
            self.tb.close()
            self.tb = None

    def set_keydown_handler(self, keys, cb) -> None:
        logger.debug(f"set key handler for {keys}")
        if isinstance(keys, list):
            for key in keys:
                self._keydown_handlers.update({key.value: cb})
        else:
            key = keys
            self._keydown_handlers.update({key.value: cb})

    def get_keydown_handler(self, key: MouseKey) -> Callable:
        logger.debug(f'get key handler for {key}.')
        handler = self._keydown_handlers.get(key)
        if handler:
            logger.debug(f'key handler found for {key}.')
            return handler
        else:
            logger.debug(f'key handler not found for {key}.')
            return None

    @property
    def on_shutdown(self) -> Callable:
        return self._on_shutdown

    @on_shutdown.setter
    def on_shutdown(self, f: Callable) -> None:
        self._on_shutdown = f

    @property
    def width(self) -> int:
        return self.tb.width()

    @property
    def height(self) -> int:
        return self.tb.height()

    def clear(self) -> None:
        """
        Clear the console
        """
        self.tb.clear()

    def update(self, now, *objects) -> None:
        """
        Render any renderable object on the console.
        """
        self.clear()
        self.peek_key_event()
        render_objects(self, *objects)
        self.tb.present()

    def peek_key_event(self) -> None:
        try:
            if not self.tb:
                raise RuntimeError('Null termbox')

            type_, uch, key, mod, w, h, x, y = self.tb.peek_event()
            logger.debug(f'type:{type_},uch={uch},key={key},mod={mod},'
                         f'w={w},h={h},x={x},y={y}')
            if key is not None:
                cb = self.get_keydown_handler(key)
                if cb:
                    cb(key)
                if key == KEY_ESC:
                    self.close()
                    if self.on_shutdown:
                        self.on_shutdown()
                    raise Exit()
            if uch:
                cb = self.get_keydown_handler(uch)
                if cb:
                    cb(key)

        except TypeError as e:
            pass

        except Exception as e:
            logger.error(e)
            raise
