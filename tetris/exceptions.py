from enum import IntEnum


class StatusCode(IntEnum):
    OK = 0
    Error = -1
    Exit = 1
    GameOver = 2


class Exit(Exception):
    code = StatusCode.Exit.value


class GameOver(Exception):
    code = StatusCode.Exit.value
