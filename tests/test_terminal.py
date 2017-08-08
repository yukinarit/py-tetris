import pytest
from ctetoris.terminal import Terminal


class MockTermbox:
    pass


class MockMap:
    def load(self, path):
        pass


def test_terminal():
    Terminal.TermboxCls = MockTermbox
    Terminal.MapCls = MockMap
    term = Terminal()
