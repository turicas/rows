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

from cached_property import cached_property
from pytesseract import image_to_boxes
from PIL import Image

from rows.plugins.plugin_pdf import group_objects, PDFBackend, TextObject, pdf_table_lines
from rows.plugins.utils import create_table


def join_text_group(group):
    """Join a list of `TextObject`s into one"""

    obj = group[0]
    max_between = (obj.x1 - obj.x0) / len(obj.text)  # Average letter size
    text, last_x1 = [], obj.x0
    for obj in group:
        if last_x1 + max_between <= obj.x0:
            text.append(" ")
        text.append(obj.text)
        last_x1 = obj.x1
    text = "".join(text)

    return TextObject(
        x0=min(obj.x0 for obj in group),
        y0=min(obj.y0 for obj in group),
        x1=max(obj.x1 for obj in group),
        y1=max(obj.y1 for obj in group),
        text=text
    )


def group_contiguous_objects(objs, x_threshold, y_threshold):
    """Merge contiguous objects if they're closer enough"""

    objs.sort(key=lambda obj: obj.y0)
    y_groups = group_objects(objs, y_threshold, "y")
    for y_group, y_items in y_groups.items():
        y_items.sort(key=lambda obj: obj.x0)

        x_groups, current_group, last_x1 = [], [], None
        for obj in y_items:
            if not current_group or last_x1 + x_threshold >= obj.x0:
                current_group.append(obj)
            elif current_group:
                x_groups.append(current_group)
                current_group = [obj]
            last_x1 = obj.x1
        if current_group:
            x_groups.append(current_group)

        for group in x_groups:
            if group:
                yield join_text_group(group)


class TesseractBackend(PDFBackend):

    name = "tesseract"

    def __init__(self, filename_or_fobj, language):
        self.filename_or_fobj = filename_or_fobj
        self.language = language
        super().__init__(self.filename_or_fobj)

    @cached_property
    def document(self):
        return Image.open(self.filename_or_fobj)

    @cached_property
    def number_of_pages(self):
        return 1  # TODO: fix

    def extract_text(self, page_numbers=None):
        return ""  # TODO: image_to_string

    def objects(self, page_numbers=None, starts_after=None, ends_before=None):
        _, total_y = self.document.size
        header = "char left bottom right top page".split()
        boxes = image_to_boxes(self.document, lang=self.language).splitlines()
        text_objs = []
        for box in boxes:
            row = {}
            for key, value in zip(header, box.split()):
                if key != "char":
                    value = int(value)
                row[key] = value
            text_objs.append(
                TextObject(
                    x0=row["left"],
                    y0=total_y - row["bottom"],
                    x1=row["right"],
                    y1=total_y - row["top"],
                    text=row["char"],
                )
            )

        # TODO: custom thresholds
        yield list(group_contiguous_objects(text_objs, 30, 12))

    text_objects = objects


def import_from_image(
    filename_or_fobj,
    language="eng",
    algorithm="y-groups",
    x_threshold=1.0,
    y_threshold=1.0,
    *args,
    **kwargs
):
    meta = {"imported_from": "image"}
    table_rows = pdf_table_lines(
        filename_or_fobj,
        None,
        starts_after=None,
        ends_before=None,
        algorithm=algorithm,
        x_threshold=x_threshold,
        y_threshold=y_threshold,
        backend=TesseractBackend,
        backend_kwargs={"language": language},
    )
    return create_table(table_rows, meta=meta, *args, **kwargs)
