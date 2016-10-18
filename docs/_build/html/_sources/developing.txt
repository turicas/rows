.. _developing:

Developing
==========

Create the virtualenv::

    mkvirtualenv rows

Install all plugins' dependencies::

    pip install --editable .[all]

Install development dependencies::

    pip install -r requirements-development.txt

Run tests::

    make test

or (if you don't have **make**)::

    tox

you can also run tox against an specific python version::

    tox -e py27
    tox -e py35

**tox known issues** : running tox with py27 environ may raise InvocationError in non Linux environments. To avoid it you may rebuild tox environment in every run with: **tox -e py27 -r**

or if you want to run nosetests directly::

    nosetests -dsv --with-yanc --with-coverage --cover-package rows tests/*.py

To create the man page you'll need to install `txt2man <http://mvertes.free.fr/>`_. In Debian
(and Debian-based distributions) you can install by running::

    aptitude install txt2man

Then, you can generate the `rows.1` file by running::

    make man
