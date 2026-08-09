# rows

[![Join the chat at https://gitter.im/turicas/rows](https://badges.gitter.im/Join%20Chat.svg)](https://gitter.im/turicas/rows?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge)
[![Current version at PyPI](https://img.shields.io/pypi/v/rows.svg)](https://pypi.python.org/pypi/rows)
[![Downloads per month on PyPI](https://img.shields.io/pypi/dm/rows.svg)](https://pypi.python.org/pypi/rows)
![Supported Python Versions](https://img.shields.io/pypi/pyversions/rows.svg)
![Software status](https://img.shields.io/pypi/status/rows.svg)
[![License: LGPLv3](https://img.shields.io/pypi/l/rows.svg)](https://github.com/turicas/rows/blob/develop/LICENSE)

No matter in which format your tabular data is: `rows` will import it,
automatically detect types and give you high-level Python objects so you can
start **working with the data** instead of **trying to parse it**. It is also
locale-and-unicode aware. :)

Want to learn more? [Read the documentation](http://turicas.info/rows) (or
build and browse the docs locally by running `make docs-serve` after installing
`requirements-development.txt`).

## Installation

The easiest way to getting the hands dirty is install rows, using 
pip.

### [PyPI][pypi-rows]

```bash
pip install rows
```

For another ways to instal refer to the Installation section [documentation][install-docs].


## Contribution start guide

The preferred way to start contributing for the project is creating a virtualenv (you can do by using virtualenv,
virtualenvwrapper, pyenv or whatever tool you'd like).

Create the virtualenv:

```bash
mkvirtualenv rows
```

Install all plugins' dependencies:

```bash
pip install --editable .[all]
```

Install required libs:
    
    In linux:
    apt-get install libsnappy-dev libmagic-dev

    In Mac:
    brew install snappy libmagic

Install development dependencies:

```bash
pip install -r requirements-development.txt
```

[pypi-rows]: https://pypi.org/project/rows/
[install-docs]: https://turicas.info/rows/installation