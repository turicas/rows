## Developing

Create the virtualenv:

```bash
mkvirtualenv rows
```

Install all plugins' dependencies:

```bash
pip install --editable .[all]
```

Install development dependencies:

```bash
pip install -r requirements-development.txt
```

Run tests:

```bash
make test
```

or (if you don't have `make`):

```bash
tox
```

you can also run tox against an specific python version:

```bash
tox -e py27
tox -e py35
```

*tox known issues* : running tox with py27 environ may raise InvocationError in
non Linux environments. To avoid it you may rebuild tox environment in every
run with `tox -e py27 -r` or if you want to run nosetests directly:

```bash
nosetests -dsv --with-yanc --with-coverage --cover-package rows tests/*.py
```

To create the man page you'll need to install [txt2man][txt2man]. In Debian
(and Debian-based distributions) you can install by running:

```bash
aptitude install txt2man
```

Then, you can generate the `rows.1` file by running:

```bash
make man
```


[txt2man]: http://mvertes.free.fr/
