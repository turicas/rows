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

### Tox Known Issues

Running tox with py27 environ may raise InvocationError in non Linux 
environments. To avoid it you may rebuild tox environment in every run with 
`tox -e py27 -r` or if you want to run nosetests directly:

```bash
nosetests -dsv --with-yanc --with-coverage --cover-package rows tests/*.py
```

When running tox with pyenv, tox won't find any interpreters NOT in the global 
path. Make sure all versions are activated with:

```bash
pyven global {python-version}
```

For instance, for allowing tox to find python 2.7, 3.5 and 3.6, you'll run: 

```
pyenv global 2.7.13 3.6.1 3.5.3
```

Don't forget to add to this all other interpreters you already have enabled: 
the `pyenv global` command will redefine the global interpreters, not append 
to them!

**Important**: this will only work with regular virtualenvs. If you're using 
`pyenv` to manage your virtualenvs, the global interpreters will not be 
available when the virtualenv is active, and you won't be able to use tox. 
Either create a standalone virtualenv, or just run the tests with nose, as 
shown in the previous section.

### Creating Man Pages

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
