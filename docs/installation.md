# Installation

## [PyPI][pypi-rows]

```bash
pip install rows
```

## GitHub

```bash
pip install "https://github.com/turicas/rows/archive/develop.zip#egg=rows"
# or (needs git)
pip install "git+https://github.com/turicas/rows.git@develop#egg=rows"
```

or:

```bash
git clone https://github.com/turicas/rows.git
cd rows
python setup.py install
```

The use of virtualenv is recommended.

You can create a development image using Docker:

```bash
cat Dockerfile | docker build -t turicas/rows:latest -
```

## Debian

If you use Debian [sid][debian-sid] or [testing][debian-testing] you can
install it directly from the main repository by running:

```bash
apt install python-rows  # Python library only
apt install rows  # Python library + CLI
```

You may need to install SQLite too (on Ubuntu, for example).


## Fedora

```bash
dnf install python-row  # Python library + CLI
```


## Docker

If you don't want to install on your machine but you'd like to try the library,
there's a docker image available:

```bash
mkdir -p data  # Put your files here
echo -e "a,b\n1,2\n3,4" > data/test.csv

# To access the IPython shell:
docker run --rm -it -v $(pwd)/data:/data turicas/rows:0.4.0 ipython

# To access the command-line interface
docker run --rm -it -v $(pwd)/data:/data turicas/rows:0.4.0 rows print /data/test.csv
```

## Installing plugins

The plugins `csv`, `dicts`, `json`, `sqlite` and `txt` are built-in by
default but if you want to use another one you need to explicitly install its
dependencies, for example:

```bash
pip install rows[html]
pip install rows[xls]
```

> Note: if you're running another command line interpreter (like zsh) you may
> need to escape the characters `[` and `]`.

You also need to install some dependencies to use the [command-line
interface][rows-cli]. You can do it installing the `cli` extra requirement:

```bash
pip install rows[cli]
```

And - easily - you can install all the dependencies by using the `all` extra
requirement:

```bash
pip install rows[all]
```


[debian-sid]: https://www.debian.org/releases/sid/
[debian-testing]: https://www.debian.org/releases/testing/
[pypi-rows]: https://pypi.org/project/rows/
[rows-cli]: cli.md
