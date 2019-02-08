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
