"Minimal things we need to get rid of `six` dependency"
import sys


PYTHON_VERSION = (sys.version_info.major, sys.version_info.minor, sys.version_info.micro)

if PYTHON_VERSION < (3, 0, 0):
    TEXT_TYPE = unicode
    BINARY_TYPE = str
else:
    TEXT_TYPE = str
    BINARY_TYPE = bytes
