import enum
import logging
import logging.handlers
import pathlib
import sys
import traceback
from typing import Union, List, Tuple  # noqa
from termcolor import colored  # type: ignore


class IndentFormatter(logging.Formatter):
    def __init__(self, fmt=None, datefmt=None) -> None:
        logging.Formatter.__init__(self, fmt, datefmt)
        self.base = None

    def format(self, record):
        depth = len(traceback.extract_stack())
        if self.base is None:
            self.base = depth
        record.indent = '.' * (depth - self.base)
        return logging.Formatter.format(self, record)


PLANE_FORMATTER = logging.Formatter('%(message)s')


DEFAULT_FORMATTER = logging.Formatter(
    '[%(asctime)s.%(msecs)03d] %(name)s %(levelname)s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S')


INDENT_FORMATTER = IndentFormatter(
    '[%(asctime)s.%(msecs)03d] %(name)s %(levelname)s %(indent)s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S')


class Level(enum.IntEnum):
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL


class ColorizedLogger:
    """
    To colorize logger output.
    https://gist.github.com/brainsik/1238935
    """
    colormap = dict(
        debug=dict(color='grey', attrs=['bold']),
        info=dict(color='white'),
        warn=dict(color='yellow', attrs=['bold']),
        warning=dict(color='yellow', attrs=['bold']),
        error=dict(color='red'),
        critical=dict(color='red', attrs=['bold']),
    )

    levels = ('debug', 'info', 'warn', 'warning', 'error', 'critical')

    def __init__(self, logger) -> None:
        self._log = logger
        self.color = False

    def __getattr__(self, name):
        if self.color:
            if name in self.levels:
                return lambda s, *args: getattr(self._log, name)(
                    colored(s, **self.colormap[name]), *args)

        return getattr(self._log, name)


class TerminalHandler(logging.Handler):
    def __init__(self, game, x: int, y: int, width: int, height: int,
                 *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.game = game

    def emit(self, record):
        entry = self.format(record)
        if len(entry) > self.width:
            entry = entry[:self.width]
        self.game.write(self.x, self.y, entry)


def create_logger(name: str, **options) -> ColorizedLogger:
    """
    Create a brand new logger.
    """
    logger = ColorizedLogger(logging.getLogger(name))
    del logger.handlers[:]
    if options:
        setup_logger(logger, **options)
    return logger


def setup_logger(*loggers,
                 level: Level=Level.INFO,
                 file: Union[str, pathlib.Path]=None, stdout: bool=False,
                 color: bool=False,
                 formatter=DEFAULT_FORMATTER,
                 indent_formatter: bool=False) -> None:
    """
    Setup logger.
    """
    if isinstance(loggers, ColorizedLogger):
        loggers = [loggers]

    for logger in loggers:
        logger.setLevel(level)
        if formatter is None:
            formatter = PLANE_FORMATTER
        if indent_formatter:
            formatter = INDENT_FORMATTER

        if file:
            if not isinstance(file, pathlib.Path):
                file = pathlib.Path(file)
            fh = logging.FileHandler(str(file.absolute()), encoding='utf-8')
            fh.setFormatter(formatter)
            fh.setLevel(level)
            logger.addHandler(fh)
        if stdout:
            sh = logging.StreamHandler(sys.stdout)
            sh.setFormatter(formatter)
            sh.setLevel(level)
            logger.addHandler(sh)
        logger.color = color
