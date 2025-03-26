# coding: utf-8

# Copyright 2014-2019 Álvaro Justen <https://github.com/turicas/rows/>

#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.

#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Lesser General Public License for more details.

#    You should have received a copy of the GNU Lesser General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals

from io import BytesIO

from rows.utils import Source


def _generate_frames():
    """Used only to generate the fixed FRAMES variable, so don't waste time when importing"""
    import unicodedata

    single_frame_prefix = "BOX DRAWINGS LIGHT"
    double_frame_prefix = "BOX DRAWINGS DOUBLE"
    frame_parts = (
        "VERTICAL",
        "HORIZONTAL",
        "DOWN AND RIGHT",
        "DOWN AND LEFT",
        "UP AND RIGHT",
        "UP AND LEFT",
        "VERTICAL AND LEFT",
        "VERTICAL AND RIGHT",
        "DOWN AND HORIZONTAL",
        "UP AND HORIZONTAL",
        "VERTICAL AND HORIZONTAL"
    )
    SINGLE_FRAME = {
        name: unicodedata.lookup(single_frame_prefix + " " + name)
        for name in frame_parts
    }
    DOUBLE_FRAME = {
        name: unicodedata.lookup(double_frame_prefix + " " + name)
        for name in frame_parts
    }
    ASCII_FRAME = {name: "+" for name in frame_parts}
    ASCII_FRAME["HORIZONTAL"] = "-"
    ASCII_FRAME["VERTICAL"] = "|"
    NONE_FRAME = {name: " " for name in frame_parts}
    return {
        "none": NONE_FRAME,
        "ascii": ASCII_FRAME,
        "single": SINGLE_FRAME,
        "double": DOUBLE_FRAME,
    }

FRAMES = {
    "none": {
        "VERTICAL": " ",
        "HORIZONTAL": " ",
        "DOWN AND RIGHT": " ",
        "DOWN AND LEFT": " ",
        "UP AND RIGHT": " ",
        "UP AND LEFT": " ",
        "VERTICAL AND LEFT": " ",
        "VERTICAL AND RIGHT": " ",
        "DOWN AND HORIZONTAL": " ",
        "UP AND HORIZONTAL": " ",
        "VERTICAL AND HORIZONTAL": " ",
    },
    "ascii": {
        "VERTICAL": "|",
        "HORIZONTAL": "-",
        "DOWN AND RIGHT": "+",
        "DOWN AND LEFT": "+",
        "UP AND RIGHT": "+",
        "UP AND LEFT": "+",
        "VERTICAL AND LEFT": "+",
        "VERTICAL AND RIGHT": "+",
        "DOWN AND HORIZONTAL": "+",
        "UP AND HORIZONTAL": "+",
        "VERTICAL AND HORIZONTAL": "+",
    },
    "single": {
        "VERTICAL": "│",
        "HORIZONTAL": "─",
        "DOWN AND RIGHT": "┌",
        "DOWN AND LEFT": "┐",
        "UP AND RIGHT": "└",
        "UP AND LEFT": "┘",
        "VERTICAL AND LEFT": "┤",
        "VERTICAL AND RIGHT": "├",
        "DOWN AND HORIZONTAL": "┬",
        "UP AND HORIZONTAL": "┴",
        "VERTICAL AND HORIZONTAL": "┼",
    },
    "double": {
        "VERTICAL": "║",
        "HORIZONTAL": "═",
        "DOWN AND RIGHT": "╔",
        "DOWN AND LEFT": "╗",
        "UP AND RIGHT": "╚",
        "UP AND LEFT": "╝",
        "VERTICAL AND LEFT": "╣",
        "VERTICAL AND RIGHT": "╠",
        "DOWN AND HORIZONTAL": "╦",
        "UP AND HORIZONTAL": "╩",
        "VERTICAL AND HORIZONTAL": "╬",
    },
}

def _clean_style_name(name):
    return name.lower().strip()

def _parse_frame_style(frame_style):
    frame_style = _clean_style_name(frame_style) if frame_style is not None else "none"
    if frame_style not in FRAMES:
        raise ValueError("Invalid frame style {}. Use one of: {}.".format(repr(frame_style), ", ".join(FRAMES.keys())))
    return frame_style


def _guess_frame_style(contents):
    first_line_chars = set(contents.split("\n")[0].strip())
    for frame_style, frame_dict in FRAMES.items():
        if first_line_chars <= set(frame_dict.values()):
            return frame_style
    return "none"


def _parse_col_positions(frame_style, header_line):
    """Find the position for each column separator in the given line

    If frame_style is 'none', this won't work for column names that _start_ with whitespace (which includes
    non-lefthand aligned column titles)
    """
    import re

    separator = re.escape(FRAMES[frame_style]["VERTICAL"])

    if frame_style == "none":
        separator = r"[\s]{2}[^\s]"
        # Matches two whitespaces followed by a non-whitespace.
        # Our column headers are serated by 3 spaces by default.

    col_positions = []
    # Abuse regexp engine to anotate vertical-separator positions:
    re.sub(separator, lambda group: col_positions.append(group.start()), header_line)
    if frame_style == "none":
        col_positions.append(len(header_line) - 1)
    return col_positions


def _max_column_sizes(field_names, table_rows):
    columns = zip(*([field_names] + table_rows))
    return {
        field_name: max(len(value) for value in column)
        for field_name, column in zip(field_names, columns)
    }


def import_from_txt(
    filename_or_fobj, encoding="utf-8", frame_style=None, *args, **kwargs
):
    """Return a rows.Table created from imported TXT file."""
    from rows.plugins.utils import create_table

    # TODO: (maybe)
    # enable parsing of non-fixed-width-columns
    # with old algorithm - that would just split columns
    # at the vertical separator character for the frame.
    # (if doing so, include an optional parameter)
    # Also, this fixes an outstanding unreported issue:
    # trying to parse tables which fields values
    # included a Pipe char - "|" - would silently
    # yield bad results.

    source = Source.from_file(
        filename_or_fobj, mode="rb", plugin_name="txt", encoding=encoding
    )
    raw_contents = source.fobj.read().decode(encoding).rstrip("\n")

    if frame_style is None:
        frame_style = _guess_frame_style(raw_contents)
    else:
        frame_style = _parse_frame_style(frame_style)

    contents = raw_contents.splitlines()
    del raw_contents

    if frame_style != "none":
        contents = contents[1:-1]
        del contents[1]
    else:
        # the table is possibly generated from other source.
        # check if the line we reserve as a separator is realy empty.
        if not contents[1].strip():
            del contents[1]
    col_positions = _parse_col_positions(frame_style, contents[0])

    table_rows = [
        [
            row[start + 1 : end].strip()
            for start, end in zip(col_positions, col_positions[1:])
        ]
        for row in contents
    ]

    meta = {
        "imported_from": "txt",
        "source": source,
        "frame_style": frame_style,
    }
    return create_table(table_rows, meta=meta, *args, **kwargs)


def export_to_txt(
    table,
    filename_or_fobj=None,
    encoding=None,
    frame_style="ascii",
    safe_none_frame=True,
    *args,
    **kwargs
):
    """Export a `rows.Table` to text.

    This function can return the result as a string or save into a file (via
    filename or file-like object).

    `encoding` could be `None` if no filename/file-like object is specified,
    then the return type will be `TEXT_TYPE` (depends on Python 2 vs 3).
    `frame_style`: will select the frame style to be printed around data.
    Valid values are: ('none', 'ascii', 'single', 'double') - ascii is default.
    Warning: no checks are made to check the desired encoding allows the
    characters needed by single and double frame styles.

    `safe_none_frame`: bool, defaults to True. Affects only output with
    frame_style == "none":
    column titles are left-aligned and have
    whitespace replaced for "_".  This enables
    the output to be parseable. Otherwise, the generated table will look
    prettier but can not be imported back.
    """
    from rows.plugins.utils import is_binary_file, is_fobj, serialize

    return_data, should_close = False, None
    if filename_or_fobj is None:
        filename_or_fobj = BytesIO()
        return_data = should_close = True
    elif is_fobj(filename_or_fobj):
        is_binary = is_binary_file(filename_or_fobj)
        if is_binary and encoding is None:
            raise ValueError("export_to_txt must receive an encoding when file is in binary mode")
        elif not is_binary and encoding is not None:
            raise ValueError("export_to_txt must not receive an encoding when file is in text mode")

    source = Source.from_file(
        filename_or_fobj,
        plugin_name="txt",
        mode="wb",
        encoding=encoding,
        should_close=should_close,
    )

    frame_style = _parse_frame_style(frame_style)
    frame = FRAMES[frame_style]

    # TODO: will work only if table.fields is OrderedDict
    serialized_table = serialize(table, *args, **kwargs)
    field_names = next(serialized_table)
    table_rows = list(serialized_table)
    max_sizes = _max_column_sizes(field_names, table_rows)

    dashes = [frame["HORIZONTAL"] * (max_sizes[field] + 2) for field in field_names]

    if frame_style != "none" or not safe_none_frame:
        header = [field.center(max_sizes[field]) for field in field_names]
    else:
        header = [
            field.replace(" ", "_").ljust(max_sizes[field]) for field in field_names
        ]
    header = "{0} {1} {0}".format(
        frame["VERTICAL"], " {} ".format(frame["VERTICAL"]).join(header)
    )
    top_split_line = (
        frame["DOWN AND RIGHT"]
        + frame["DOWN AND HORIZONTAL"].join(dashes)
        + frame["DOWN AND LEFT"]
    )

    body_split_line = (
        frame["VERTICAL AND RIGHT"]
        + frame["VERTICAL AND HORIZONTAL"].join(dashes)
        + frame["VERTICAL AND LEFT"]
    )

    botton_split_line = (
        frame["UP AND RIGHT"]
        + frame["UP AND HORIZONTAL"].join(dashes)
        + frame["UP AND LEFT"]
    )

    result = []
    if frame_style != "none":
        result += [top_split_line]
    result += [header, body_split_line]

    for row in table_rows:
        values = [
            value.rjust(max_sizes[field_name])
            for field_name, value in zip(field_names, row)
        ]
        row_data = " {} ".format(frame["VERTICAL"]).join(values)
        result.append("{0} {1} {0}".format(frame["VERTICAL"], row_data))

    if frame_style != "none":
        result.append(botton_split_line)
    result.append("")
    data = "\n".join(result)

    if encoding is not None:
        data = data.encode(encoding)

    if return_data:
        result = data
    else:
        result = source.fobj
        source.fobj.write(data)
        source.fobj.flush()

    if source.should_close:
        source.fobj.close()

    return result
