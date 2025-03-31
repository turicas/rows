"""Helper objects to make compatibility with older versions or external tools easier"""
import sys


PYTHON_VERSION = (sys.version_info.major, sys.version_info.minor, sys.version_info.micro)

if PYTHON_VERSION < (3, 0, 0):
    TEXT_TYPE = unicode
    BINARY_TYPE = str
else:
    TEXT_TYPE = str
    BINARY_TYPE = bytes


def library_installed(module_name):
    if PYTHON_VERSION >= (3, 0, 0):
        from importlib.util import find_spec
    else:
        from imp import find_module as find_spec

    return bool(find_spec(module_name))


def ipython_env():
    if not _library_installed("IPython"):
        return None

    from IPython import get_ipython

    obj = get_ipython()
    name = obj.__class__.__name__
    if name == "TerminalInteractiveShell":
        return "terminal"
    elif name == "ZMQInteractiveShell":
        return "notebook"
    else:  # ?
        return None
