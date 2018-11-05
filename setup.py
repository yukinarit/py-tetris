import pathlib
import re
import sys
import subprocess
from codecs import open
from setuptools import setup

root = pathlib.Path(__file__).parent.absolute()

with open('tetris/__init__.py', 'r', encoding='utf8') as f:
    version = re.search(r'__version__ = \'(.*?)\'', f.read()).group(1)

with open('README.md', 'r', encoding='utf8') as f:
    readme = f.read()


subprocess.check_call(f'{sys.executable} -m pip install cython'.split())

setup_requires = [
    'pytest-runner',
]

requires = [
    'termcolor',
    'termbox',
]

tests_require = [
    'pyinstaller',
    'coverage',
    'pytest',
    'pytest-cov',
    'pytest-flake8',
    'mypy',
    'flake8',
]

dependency_links = [
    'git+https://github.com/nsf/termbox.git#egg=termbox-0.1.0',
]

setup(
    name='py-tetris',
    version=version,
    description='Tetris.',
    long_description=readme,
    long_description_content_type='text/markdown',
    author='yukinarit',
    author_email='yukinarit84@gmail.com',
    url='https://github.com/yukinarit/envclasses',
    py_modules=['envclasses'],
    python_requires=">=3.6",
    setup_requires=setup_requires,
    install_requires=requires,
    tests_require=tests_require,
    extras_require={
        'test': tests_require,
    },
    dependency_links=dependency_links,
    license='MIT',
    zip_safe=False,
    classifiers=[
        'Topic :: Games/Entertainment :: Arcade',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ],
)
