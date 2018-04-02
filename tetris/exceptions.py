from enum import IntEnum


class StatusCode(IntEnum):
    OK = 0
    Exit = 0
    Error = -1


class Exit(Exception):
    code = StatusCode.Exit.value
