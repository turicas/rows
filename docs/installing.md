# Installing rows

Directly from [PyPI][pypi-rows]:

```bash
pip install rows
```

You can also install directly from the GitHub repository to have the newest
features (not pretty stable) by running:

```bash
pip install git+https://github.com/turicas/rows.git@develop
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

The plugins `csv`, `dicts`, `json`, `sqlite` and `txt` are built-in by
default but if you want to use another one you need to explicitly install its
dependencies, for example:

```bash
pip install rows[html]
pip install rows[xls]
```

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

If you use Debian [sid][debian-sid] or [testing][debian-testing] you can
install it directly from the main repository by running:

```bash
apt install python-rows  # Python library only
apt install rows  # Python library + CLI
```

And in Fedora:

```bash
dnf install python-row  # Python library + CLI
```
