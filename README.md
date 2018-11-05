TETRIS
======


INSTALL
-------

* Get precompiled executable
	* https://github.com/yukinarit/py-tetris/releases

* Get development version
    ```bash
    pip install git+https://github.com/yukinarit/py-tetris.git --process-dependency-links
    ```

RUN
---

```bash
python -m tetris
```

DISTRIBUTE
----------

```
pyinstaller --clean -F tetris-cli -n tetris
```
