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

from rows.plugins.plugin_pdf import PDFBackend, TextObject, pdf_table_lines
from rows.plugins.utils import create_table


class TesseractBackend(PDFBackend):

    name = "tesseract"

    def __init__(self, filename_or_fobj, language):
        self.filename_or_fobj = filename_or_fobj
        self.language = language
        super().__init__(self.filename_or_fobj)

    @cached_property
    def document(self):
        if hasattr(self.filename_or_fobj, "read"):
            image = Image.open(self.filename_or_fobj)
        else:
            image = self.filename_or_fobj

        return image

    @cached_property
    def number_of_pages(self):
        return 1  # TODO: fix

    def extract_text(self, page_numbers=None):
        return ""  # TODO: image_to_string

    def objects(self, page_numbers=None, starts_after=None, ends_before=None):
        header = "char left bottom right top page".split()
        boxes = image_to_boxes(self.document, lang=self.language).splitlines()
        text_objs = []
        for box in boxes:
            row = {}
            for key, value in zip(header, box.split()):
                if key != "char":
                    value = int(value)
                row[key] = value
            obj = TextObject(
                x0=row["left"],
                y0=row["bottom"],
                x1=row["right"],
                y1=row["top"],
                text=row["char"],
            )
            text_objs.append(obj)

        text_objs.sort(key=lambda obj: (obj.y0, obj.x0))
        # TODO: group contiguous objects before yielding
        yield text_objs

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
