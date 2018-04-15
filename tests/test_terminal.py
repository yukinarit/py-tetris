from tetris.terminal import Terminal, Vector2


class MockTermbox:
    pass


class MockMap:
    def load(self, path):
        pass


def test_terminal():
    Terminal.TermboxCls = MockTermbox
    Terminal.MapCls = MockMap
    term = Terminal()


def test_vector():
    v1 = Vector2(1, 2)
    v2 = Vector2(1, 2)
    assert v1 == v2
