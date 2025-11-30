# coding: utf-8

# Copyright 2014-2025 Álvaro Justen <https://github.com/turicas/rows/>
#    This program is free software: you can redistribute it and/or modify it under the terms of the GNU Lesser General
#    Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option)
#    any later version.
#    This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied
#    warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for
#    more details.
#    You should have received a copy of the GNU Lesser General Public License along with this program.  If not, see
#    <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals

import io

from rows.compat import PYTHON_VERSION, TEXT_TYPE

COMPRESSED_EXTENSIONS = ("bz2", "gz", "xz")


def _fobj_xz(filename, mode, *args, **kwargs):
    import lzma  # noqa

    return lzma.LZMAFile(filename=str(filename), mode=mode, *args, **kwargs)


def _fobj_gz(filename, mode, *args, **kwargs):
    import gzip  # noqa

    return gzip.GzipFile(filename=str(filename), mode=mode, *args, **kwargs)


# TODO: check https://pypi.org/project/xopen/

PY2 = PYTHON_VERSION < (3, 0, 0)

if PY2:

    def _fobj_bz2(filename, mode, *args, **kwargs):
        import bz2  # noqa

        class BZ2FileWrapper(bz2.BZ2File):
            def readable(self):
                mode = self.mode
                return "r" in mode or "+" in mode

            def writable(self):
                mode = self.mode
                return "w" in mode or "a" in mode or "+" in mode

            def seekable(self):
                return False

            def flush(self):
                return

        fobj = BZ2FileWrapper(filename=str(filename), mode=mode, *args, **kwargs)
        return fobj

else:

    def _fobj_bz2(filename, mode, *args, **kwargs):
        import bz2  # noqa

        return bz2.BZ2File(filename=str(filename), mode=mode, *args, **kwargs)


def cfopen(
    file, mode="r", buffering=-1, encoding=None, errors=None, newline=None, closefd=True, opener=None, *args, **kwargs
):
    """Compressed-file open - return a compression-aware file object based on file extension

    Works with uncompressed files too.
    Supported extensions for compression: bz2, gz, xz.
    `args` and `kwargs` are passed to `bz2.BZ2File`, `gzip.GzipFile` or `lzma.LZMAFile`
    Parameters `errors`, `newline`, `closefd` and `opener` are ignored in Python 2.
    NOTE: if the file is compressed, options like `buffering` are valid to the compressed file-object (not the
    uncompressed file-object returned).
    """

    mode = TEXT_TYPE(mode)
    binary_mode = TEXT_TYPE("b") in mode
    if not binary_mode and TEXT_TYPE("t") not in mode:
        # For some reason, passing only mode='r' to bzip2 is equivalent to 'rb', not 'rt', so we force it here.
        mode += TEXT_TYPE("t")
    if binary_mode and encoding is not None:
        raise ValueError("encoding cannot be set in binary mode")
    elif not binary_mode and encoding is None:
        import locale

        encoding = locale.getpreferredencoding()

    extension = TEXT_TYPE(file).split(".")[-1].lower()
    if TEXT_TYPE("t") in mode:
        mode_binary = mode.replace(TEXT_TYPE("t"), TEXT_TYPE("b"))
    elif TEXT_TYPE("b") not in mode:
        mode_binary = mode + TEXT_TYPE("b")
    else:
        mode_binary = mode
    open_mode = mode_binary if binary_mode else mode
    if PY2:
        file = TEXT_TYPE(file)

    if extension not in COMPRESSED_EXTENSIONS:  # No compression/compression method not supported
        if PY2:
            fobj_binary = io.FileIO(file=file, mode=mode_binary, closefd=closefd)
            readable, writable = fobj_binary.readable(), fobj_binary.writable()
            if readable and writable:
                fobj_binary = io.BufferedRandom(fobj_binary)
            elif readable:
                fobj_binary = io.BufferedReader(fobj_binary)
            elif writable:
                fobj_binary = io.BufferedWriter(fobj_binary)
            if binary_mode:
                return fobj_binary
            else:
                return io.TextIOWrapper(fobj_binary, encoding=encoding, errors=errors, newline=newline)
        else:
            return open(
                file=str(file),
                mode=open_mode,
                encoding=encoding,
                errors=errors,
                buffering=buffering,
                newline=newline,
                closefd=closefd,
                opener=opener,
            )
    else:
        if extension == "bz2":
            uncompressed_fobj = _fobj_bz2(filename=file, mode=mode_binary, *args, **kwargs)
        elif extension == "gz":
            uncompressed_fobj = _fobj_gz(filename=file, mode=mode_binary, *args, **kwargs)
        elif extension == "xz":
            uncompressed_fobj = _fobj_xz(filename=file, mode=mode_binary, *args, **kwargs)

        if binary_mode:
            return uncompressed_fobj
        else:
            return io.TextIOWrapper(uncompressed_fobj, encoding=encoding, errors=errors, newline=newline)
