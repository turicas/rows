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
import re
import tempfile
import unittest

import pytest

import rows
import tests.utils as utils
from rows.compat import PYTHON_VERSION

ALIAS_IMPORT = rows.import_from_pdf

import rows.plugins.plugin_pdf as pdf  # noqa

if PYTHON_VERSION >= (3, 7, 0):
    try:
        import fitz as pymupdf  # noqa

        pymupdf_imported = True
    except ImportError:
        pymupdf_imported = False
else:
    pymupdf_imported = False


class PDFTestCase(utils.RowsTestMixIn):

    backend = "<to-be-set>"
    file_extension = "pdf"
    plugin_name = "pdf"

    def test_imports(self):
        # Force the plugin to load
        original_import = rows.plugins.pdf.import_from_pdf
        assert id(ALIAS_IMPORT) != id(original_import)
        new_alias_import = rows.import_from_pdf
        assert id(new_alias_import) == id(original_import)  # Function replaced with loaded one

    def test_import_from_pdf_fobj_text(self):
        with pytest.raises(ValueError, match="import_from_pdf must not receive a file-like object in text mode"):
            tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
            tmp.close()
            fobj = io.TextIOWrapper(io.open(tmp.name, mode="rb"), encoding="utf-8")
            rows.import_from_pdf(fobj)

    def test_real_data_1(self):
        filename = "tests/data/balneabilidade-26-2010"
        result = rows.import_from_pdf(filename + ".pdf", backend=self.backend)
        expected = rows.import_from_csv(filename + ".csv")
        assert list(expected) == list(result)

    def test_real_data_2(self):
        filename = "tests/data/milho-safra-2017"
        result = rows.import_from_pdf(
            filename + ".pdf",
            backend=self.backend,
            starts_after=re.compile("MILHO SAFRA 16/17: ACOMPANHAMENTO DE .*"),
            ends_before="*Variação em pontos percentuais.",
        )
        expected = rows.import_from_csv(filename + ".csv")
        assert list(expected) == list(result)

    def test_real_data_3(self):
        filename = "tests/data/eleicoes-tcesp-161-162.pdf"
        expected1 = "tests/data/expected-eleicoes-tcesp-161-{}.csv".format(self.backend)
        expected2 = "tests/data/expected-eleicoes-tcesp-162-{}.csv".format(self.backend)
        begin = re.compile("Documento gerado em.*")
        end = re.compile("Página: [0-9]+ de.*")

        result = rows.import_from_pdf(
            filename,
            backend=self.backend,
            page_numbers=(1,),
            starts_after=begin,
            ends_before=end,
            algorithm="header-position",
        )
        expected = rows.import_from_csv(expected1)
        assert list(expected) == list(result)

        result = rows.import_from_pdf(
            filename,
            backend=self.backend,
            page_numbers=(2,),
            starts_after=begin,
            ends_before=end,
            algorithm="header-position",
        )
        expected = rows.import_from_csv(expected2)
        assert list(expected) == list(result)

    def test_number_of_pages(self):
        filenames_and_pages = (
            ("tests/data/balneabilidade-26-2010.pdf", 3),
            ("tests/data/eleicoes-tcesp-161-162.pdf", 2),
            ("tests/data/ibama-autuacao-amazonas-2010-pag2.pdf", 1),
            ("tests/data/milho-safra-2017.pdf", 1),
        )
        for filename, expected_pages in filenames_and_pages:
            # Using filename
            pages = rows.plugins.pdf.number_of_pages(filename, backend=self.backend)
            assert pages == expected_pages
            # Using fobj
            with open(filename, mode="rb") as fobj:
                pages = rows.plugins.pdf.number_of_pages(fobj, backend=self.backend)
                assert pages == expected_pages

    def test_pdf_to_text(self):
        filename = "tests/data/balneabilidade-26-2010.pdf"
        expected_start = (
            "Boletim de Balneabilidade\nCoordenação de Monitoramento – COMON/DIFIM\nCosta: Salvador\nBoletim N°: 26/2010 / Emitido em: 02/01/1970\nPonto - Código\nLocal da Coleta\nCategoria\nSão Tomé de Paripe - SSA IN 100",
        )
        reader = rows.plugins.pdf.pdf_to_text(filename, backend=self.backend, page_numbers=(1,))
        first_page = next(reader)
        assert first_page.startswith(expected_start)


@pytest.mark.skipif(not pymupdf_imported, reason="pymupdf not supported (Python < 3.7) or not installed")
class PyMuPDFTestCase(PDFTestCase, unittest.TestCase):

    backend = "pymupdf"
    # TODO: add test using rects-boundaries algorithm (will need to implement
    # RectObject extraction on this backend)


class PDFMinerSixTestCase(PDFTestCase, unittest.TestCase):

    backend = "pdfminer.six"

    def test_rects_boundaries(self):
        filename = "tests/data/ibama-autuacao-amazonas-2010-pag2"
        result = rows.import_from_pdf(
            filename + ".pdf",
            backend=self.backend,
            starts_after=re.compile("DIRETORIA DE PROTE.*"),
            ends_before=re.compile("Pag [0-9]+/[0-9]+"),
            algorithm="rects-boundaries",
        )
        expected = rows.import_from_csv(filename + ".csv")
        assert list(expected) == list(result)


class HelperFunctionsTestCase(unittest.TestCase):
    def test_group_objects(self):
        dataset = [
            pdf.TextObject(x0=0, x1=2, y0=0, y1=2, text="obj1"),
            pdf.TextObject(x0=0, x1=2, y0=2, y1=3, text="obj2"),
            pdf.TextObject(x0=6, x1=8, y0=4, y1=5, text="obj3"),
            pdf.TextObject(x0=1, x1=4, y0=6, y1=7, text="obj4"),
            pdf.TextObject(x0=3, x1=5, y0=8, y1=9, text="obj5"),
            pdf.TextObject(x0=7, x1=9, y0=2, y1=3, text="obj6"),
            pdf.TextObject(x0=8, x1=12, y0=6, y1=7, text="obj7"),
            pdf.TextObject(x0=11, x1=13, y0=9, y1=10, text="obj8"),
            pdf.TextObject(x0=11, x1=12, y0=10, y1=11, text="obj9"),
        ]
        x_groups = pdf.group_objects("x", dataset, threshold=0)
        groups_text = [sorted([obj.text for obj in group.objects]) for group in x_groups]
        expected_groups_text = [
            sorted(["obj1", "obj2", "obj4", "obj5"]),
            sorted(["obj3", "obj6", "obj7", "obj8", "obj9"]),
        ]
        assert groups_text == expected_groups_text

        y_groups = pdf.group_objects("y", dataset, threshold=0)
        groups_text = [sorted([obj.text for obj in group.objects]) for group in y_groups]
        expected_groups_text = [
            ["obj1"],
            ["obj2", "obj6"],
            ["obj3"],
            ["obj4", "obj7"],
            ["obj5"],
            ["obj8"],
            ["obj9"],
        ]
        assert groups_text == expected_groups_text

    def test_closest_same_line_basic(self):
        objects = [
            pdf.TextObject(10, 10, 20, 15, "A"),
            pdf.TextObject(30, 10, 40, 15, "B"),
            pdf.TextObject(50, 10, 60, 15, "C"),
            pdf.TextObject(10, 30, 20, 35, "D"),
        ]
        result = pdf.closest_same_line(objects, "A")
        assert result is not None
        assert result.text == "B"

    def test_closest_same_line_multiple_objects(self):
        objects = [
            pdf.TextObject(10, 10, 20, 15, "Target"),
            pdf.TextObject(25, 10, 35, 15, "Close"),
            pdf.TextObject(100, 10, 110, 15, "Far"),
            pdf.TextObject(10, 30, 20, 35, "Other"),
        ]
        result = pdf.closest_same_line(objects, "Target")
        assert result.text == "Close"

    def test_closest_same_line_left_side(self):
        objects = [
            pdf.TextObject(10, 10, 20, 15, "Left"),
            pdf.TextObject(50, 10, 60, 15, "Target"),
            pdf.TextObject(100, 10, 110, 15, "Right"),
        ]
        result = pdf.closest_same_line(objects, "Target")
        assert result.text == "Left"

    def test_closest_same_line_with_threshold(self):
        objects = [
            pdf.TextObject(10, 10, 20, 15, "A"),
            pdf.TextObject(30, 12, 40, 17, "B"),
            pdf.TextObject(10, 30, 20, 35, "C"),
        ]
        result = pdf.closest_same_line(objects, "A", threshold=5)
        assert result is not None
        assert result.text == "B"

    def test_closest_same_line_not_found(self):
        objects = [
            pdf.TextObject(10, 10, 20, 15, "A"),
            pdf.TextObject(30, 10, 40, 15, "B"),
        ]
        result = pdf.closest_same_line(objects, "NotFound")
        assert result is None

    def test_closest_same_line_only_one_object(self):
        objects = [
            pdf.TextObject(10, 10, 20, 15, "Alone"),
            pdf.TextObject(10, 30, 20, 35, "Other"),
        ]
        with pytest.raises(ValueError):
            pdf.closest_same_line(objects, "Alone")

    def test_closest_same_line_with_regex(self):
        objects = [
            pdf.TextObject(10, 10, 20, 15, "Item 1"),
            pdf.TextObject(30, 10, 40, 15, "Item 2"),
            pdf.TextObject(60, 10, 70, 15, "Item 3"),
        ]
        result = pdf.closest_same_line(objects, re.compile("Item 1"))
        assert result.text == "Item 2"

    def test_closest_same_column_basic(self):
        objects = [
            pdf.TextObject(10, 10, 20, 15, "A"),
            pdf.TextObject(10, 30, 20, 35, "B"),
            pdf.TextObject(10, 50, 20, 55, "C"),
            pdf.TextObject(40, 10, 50, 15, "D"),
        ]
        result = pdf.closest_same_column(objects, "A")
        assert result is not None
        assert result.text == "B"

    def test_closest_same_column_multiple_objects(self):
        objects = [
            pdf.TextObject(10, 10, 20, 20, "Target"),
            pdf.TextObject(10, 25, 20, 35, "Close"),
            pdf.TextObject(10, 100, 20, 110, "Far"),
            pdf.TextObject(40, 10, 50, 20, "Other"),
        ]
        result = pdf.closest_same_column(objects, "Target")
        assert result.text == "Close"

    def test_closest_same_column_above(self):
        objects = [
            pdf.TextObject(10, 10, 20, 20, "Top"),
            pdf.TextObject(10, 50, 20, 60, "Target"),
            pdf.TextObject(10, 100, 20, 110, "Bottom"),
        ]
        result = pdf.closest_same_column(objects, "Target")
        assert result.text in ["Top", "Bottom"]
        assert result.text == "Top"

    def test_closest_same_column_with_threshold(self):
        objects = [
            pdf.TextObject(10, 10, 20, 20, "A"),
            pdf.TextObject(12, 30, 22, 40, "B"),
            pdf.TextObject(40, 10, 50, 20, "C"),
        ]
        result = pdf.closest_same_column(objects, "A", threshold=5)
        assert result is not None
        assert result.text == "B"

    def test_closest_same_column_not_found(self):
        objects = [
            pdf.TextObject(10, 10, 20, 20, "A"),
            pdf.TextObject(10, 30, 20, 40, "B"),
        ]
        result = pdf.closest_same_column(objects, "NotFound")
        assert result is None

    def test_closest_same_column_only_one_object(self):
        objects = [
            pdf.TextObject(10, 10, 20, 20, "Alone"),
            pdf.TextObject(40, 10, 50, 20, "Other"),
        ]
        with pytest.raises(ValueError):
            pdf.closest_same_column(objects, "Alone")

    def test_closest_same_column_with_regex(self):
        objects = [
            pdf.TextObject(10, 10, 20, 20, "Row 1"),
            pdf.TextObject(10, 30, 20, 40, "Row 2"),
            pdf.TextObject(10, 60, 20, 70, "Row 3"),
        ]
        result = pdf.closest_same_column(objects, re.compile("Row 1"))
        assert result.text == "Row 2"

    def test_closest_same_column_with_callable(self):
        objects = [
            pdf.TextObject(10, 10, 20, 20, "AAA"),
            pdf.TextObject(10, 30, 20, 40, "BBB"),
            pdf.TextObject(10, 60, 20, 70, "CCC"),
        ]
        result = pdf.closest_same_column(objects, lambda obj: obj.text == "AAA")
        assert result.text == "BBB"
