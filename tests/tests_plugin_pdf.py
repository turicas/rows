# coding: utf-8

# Copyright 2014-2018 Álvaro Justen <https://github.com/turicas/rows/>

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

import re
import unittest

import rows
import rows.plugins.plugin_pdf as pdf
import tests.utils as utils


class PDFTestCase(utils.RowsTestMixIn):

    backend = "<to-be-set>"
    file_extension = "pdf"
    plugin_name = "pdf"

    def test_imports(self):
        self.assertIs(rows.import_from_pdf, pdf.import_from_pdf)

    def test_real_data_1(self):
        filename = "tests/data/balneabilidade-26-2010"
        result = rows.import_from_pdf(filename + ".pdf", backend=self.backend)
        expected = rows.import_from_csv(filename + ".csv")
        self.assertEqual(list(expected), list(result))

    def test_real_data_2(self):
        filename = "tests/data/milho-safra-2017"
        result = rows.import_from_pdf(
            filename + ".pdf",
            backend=self.backend,
            starts_after=re.compile("MILHO SAFRA 16/17: ACOMPANHAMENTO DE .*"),
            ends_before="*Variação em pontos percentuais.",
        )
        expected = rows.import_from_csv(filename + ".csv")
        self.assertEqual(list(expected), list(result))

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
        self.assertEqual(list(expected), list(result))

        result = rows.import_from_pdf(
            filename,
            backend=self.backend,
            page_numbers=(2,),
            starts_after=begin,
            ends_before=end,
            algorithm="header-position",
        )
        expected = rows.import_from_csv(expected2)
        self.assertEqual(list(expected), list(result))

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
            self.assertEqual(pages, expected_pages)
            # Using fobj
            with open(filename, mode="rb") as fobj:
                pages = rows.plugins.pdf.number_of_pages(fobj, backend=self.backend)
                self.assertEqual(pages, expected_pages)

    def test_pdf_to_text(self):
        filename = "tests/data/balneabilidade-26-2010.pdf"
        expected_start = (
            "Boletim de Balneabilidade\nCoordenação de Monitoramento – COMON/DIFIM\nCosta: Salvador\nBoletim N°: 26/2010 / Emitido em: 02/01/1970\nPonto - Código\nLocal da Coleta\nCategoria\nSão Tomé de Paripe - SSA IN 100",
        )
        reader = rows.plugins.pdf.pdf_to_text(
            filename, backend=self.backend, page_numbers=(1,)
        )
        first_page = next(reader)
        self.assertTrue(first_page.startswith(expected_start))


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
        self.assertEqual(list(expected), list(result))


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
        objects_by_text = {obj.text: obj for obj in dataset}
        x_groups = pdf.group_objects("x", dataset, threshold=0)
        groups_text = [
            sorted([obj.text for obj in group.objects]) for group in x_groups
        ]
        expected_groups_text = [
            sorted(["obj1", "obj2", "obj4", "obj5"]),
            sorted(["obj3", "obj6", "obj7", "obj8", "obj9"]),
        ]
        assert groups_text == expected_groups_text

        y_groups = pdf.group_objects("y", dataset, threshold=0)
        groups_text = [
            sorted([obj.text for obj in group.objects]) for group in y_groups
        ]
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
