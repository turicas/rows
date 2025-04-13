"""Helper objects to make compatibility with older versions or external tools easier"""
import sys
from collections import OrderedDict


DEFAULT_SAMPLE_ROWS = 20480  # Number of rows to sample from files when no schema is provided

PYTHON_VERSION = (sys.version_info.major, sys.version_info.minor, sys.version_info.micro)

if PYTHON_VERSION < (3, 0, 0):
    TEXT_TYPE = unicode
    BINARY_TYPE = str
else:
    TEXT_TYPE = str
    BINARY_TYPE = bytes

if PYTHON_VERSION >= (3, 7, 0) or (PYTHON_VERSION >= (3, 6, 0) and PYTHON_IMPLEMENTATION == "CPython"):
    ORDERED_DICT = dict
    ORDERED_DICTS = (dict, OrderedDict)
else:
    ORDERED_DICT = OrderedDict
    ORDERED_DICTS = (OrderedDict,)

PYTHON_KEYWORDS_LOWER = {
    "false", "none", "true", "and", "as", "assert", "async", "await", "break", "class", "continue", "def", "del",
    "elif", "else", "except", "finally", "for", "from", "global", "if", "import", "in", "is", "lambda", "nonlocal",
    "not", "or", "pass", "raise", "return", "try", "while", "with", "yield"
}
# Take from: `import keyword; set(key.lower() for key in keyword.kwlist)`

def library_installed(module_name):
    if PYTHON_VERSION >= (3, 0, 0):
        from importlib.util import find_spec

        return bool(find_spec(module_name))

    else:
        from imp import find_module

        try:
            _ = find_module(module_name)
        except ImportError:
            return False
        else:
            return True
