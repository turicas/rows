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
        expected_pages = [
            "Boletim de Balneabilidade\n\nCoordenação de Monitoramento – COMON/DIFIM\n\nCosta: Salvador\n\nBoletim N°: 26/2010 / Emitido em: 02/01/1970\n\nPonto - Código\nLocal da Coleta\nCategoria\n\nSão Tomé de Paripe - SSA IN 100\nEm frente à casa Vila Maria, ao lado da rampa de acesso à praia.\nImprópria\n\nSão Tomé de Paripe - SSA IN 100\nEm frente à casa Vila Maria, ao lado da rampa de acesso à praia.\nPrópria\n\nPeriperi - SSA PR 100\nNa saída de acesso à praia após travessia da via férrea.\nPrópria\n\nPeriperi - SSA PR 100\nNa saída de acesso à praia após travessia da via férrea.\nImprópria\n\nPenha - SSA PE 100\nSituada em frente à barraca do Valença\nImprópria\n\nPenha - SSA PE 100\nSituada em frente à barraca do Valença\nPrópria\n\nBogari - SSA BO 100\nEm frente ao Colégio da PM (antigo Colégio João Florêncio Gomes).\nPrópria\n\nBogari - SSA BO 100\nEm frente ao Colégio da PM (antigo Colégio João Florêncio Gomes).\nPrópria\n\nPedra Furada - SSA FU 100\nAtrás do Hospital Sagrada Familia, em frente a ladeira que dá acesso a praia\nImprópria\n\nPedra Furada - SSA FU 100\nAtrás do Hospital Sagrada Familia, em frente a ladeira que dá acesso a praia\nImprópria\n\nBoa Viagem - SSA BV 100\nAo lado do forte Monte Serrat e em frente ao muro lateral da Fundação Luís Eduardo , junto\na rampa de acesso à praia.\nPrópria\n\nBoa Viagem - SSA BV 100\nAo lado do forte Monte Serrat e em frente ao muro lateral da Fundação Luís Eduardo , junto\na rampa de acesso à praia.\nPrópria\n\nRoma - SSA RO 100\nPróximo a descida de acesso à praia, atrás do Hospital São Jorge.\nImprópria\n\nRoma - SSA RO 100\nPróximo a descida de acesso à praia, atrás do Hospital São Jorge.\nImprópria\n\nCanta Galo - SSA CG 100\nAtrás das antigas instalações da FIB, Rua Agrário Menezes.\nPrópria\n\nCanta Galo - SSA CG 100\nAtrás das antigas instalações da FIB, Rua Agrário Menezes.\nPrópria\n\nPorto da Barra - SSA PB 100\nEm frente à Rua César Zama, junto a escada de acesso à praia, Av. Sete de Setembro.\nPrópria\n\nPorto da Barra - SSA PB 100\nEm frente à Rua César Zama, junto a escada de acesso à praia, Av. Sete de Setembro.\nPrópria\n\nSanta Maria - SSA SM 100\nEm frente ao Mar Azul hotel, limítrofe ao Hospital Espanhol, em frente a escada de acesso à\npraia.\nPrópria\n\nSanta Maria - SSA SM 100\nEm frente ao Mar Azul hotel, limítrofe ao Hospital Espanhol, em frente a escada de acesso à\npraia.\nPrópria\n\nFarol da Barra - SSA FB 100\nEm frente as escadas de acesso à praia, na Rua Dias D'Ávila.\nImprópria\n\nFarol da Barra - SSA FB 100\nEm frente as escadas de acesso à praia, na Rua Dias D'Ávila.\nPrópria\n\nFarol da Barra - SSA FB 200\nPróximo ao Barra Vento e escada de acesso à praia, em frente a Av. Oceânica\nPrópria\n\nFarol da Barra - SSA FB 200\nPróximo ao Barra Vento e escada de acesso à praia, em frente a Av. Oceânica\nPrópria\n\nOndina - SSA ON 100\nPróximo a escada de acesso à praia, em frente ao posto BR e Hotel Bahia Sol.\nPrópria\n\nOndina - SSA ON 100\nPróximo a escada de acesso à praia, em frente ao posto BR e Hotel Bahia Sol.\nPrópria\n\nOndina - SSA ON 200\nSituada próximo ao Morro da Sereia em frente ao Ed. Maria José.\nPrópria\n\nOndina - SSA ON 200\nSituada próximo ao Morro da Sereia em frente ao Ed. Maria José.\nPrópria\n\nRio Vermelho - SSA RV 100\nEm frente a Rua Bartolomeu de Gusmão. Próximo a escada de acesso à praia, ao lado da\nRua Morro da Paciência.\nPrópria\n",
            "Rio Vermelho - SSA RV 100\nEm frente a Rua Bartolomeu de Gusmão. Próximo a escada de acesso à praia, ao lado da\nRua Morro da Paciência.\nPrópria\n\nRio Vermelho - SSA RV 200\nPróximo a escada de acesso à praia, em frente à igreja Nossa Senhora de Santana.\nPrópria\n\nRio Vermelho - SSA RV 200\nPróximo a escada de acesso à praia, em frente à igreja Nossa Senhora de Santana.\nPrópria\n\nAmaralina - SSA AM 100\nNo fundo da Escola Cupertino de Lacerda, em frente do painel do artista plástico Bel Borba.\nPrópria\n\nAmaralina - SSA AM 100\nNo fundo da Escola Cupertino de Lacerda, em frente do painel do artista plástico Bel Borba.\nPrópria\n\nAmaralina - SSA AM 200\nEm frente à rua do Balneário e ao Edifício Atlântico\nPrópria\n\nAmaralina - SSA AM 200\nEm frente à rua do Balneário e ao Edifício Atlântico\nPrópria\n\nPituba - SSA PI 100\nEm frente a escada de acesso à praia, em frente a Portinox, na Rua Paraíba.\nPrópria\n\nPituba - SSA PI 100\nEm frente a escada de acesso à praia, em frente a Portinox, na Rua Paraíba.\nImprópria\n\nPituba - SSA PI 200\nAtrás da Praça (antigo Clube Português).\nImprópria\n\nPituba - SSA PI 200\nAtrás da Praça (antigo Clube Português).\nPrópria\n\nArmação - SSA AR 200\nEm frente ao Hotel Alah Mar e a Rua João Mendes da Costa.\nPrópria\n\nArmação - SSA AR 200\nEm frente ao Hotel Alah Mar e a Rua João Mendes da Costa.\nImprópria\n\nBoca do Rio - SSA BR 100\nEm frente ao posto Salva Vidas.\nImprópria\n\nBoca do Rio - SSA BR 100\nEm frente ao posto Salva Vidas.\nImprópria\n\nCorsário - SSA CO 100\nEm frente ao Posto Salva Vidas\nPrópria\n\nCorsário - SSA CO 100\nEm frente ao Posto Salva Vidas\nPrópria\n\nPatamares - SSA CO 200\nEm frente ao posto Salva Vidas Patamares. Próximo ao Coliseu do Forró e ao Caranguejo de\nSergipe.\nImprópria\n\nPatamares - SSA CO 200\nEm frente ao posto Salva Vidas Patamares. Próximo ao Coliseu do Forró e ao Caranguejo de\nSergipe.\nPrópria\n\nPiatã - SSA PA 100\nEm frente ao Posto Salva Vidas, próximo ao Clube Costa Verde.\nPrópria\n\nPiatã - SSA PA 100\nEm frente ao Posto Salva Vidas, próximo ao Clube Costa Verde.\nPrópria\n\nPlacafor - SSA PF 100\nEm frente ao posto Salva Vidas.\nPrópria\n\nPlacafor - SSA PF 100\nEm frente ao posto Salva Vidas.\nPrópria\n\nItapuã - SSA IT 100\nPróximo a escada de acesso à praia e em frente a Rua Sargento Waldir Xavier.\nPrópria\n\nItapuã - SSA IT 100\nPróximo a escada de acesso à praia e em frente a Rua Sargento Waldir Xavier.\nPrópria\n\nItapuã - SSA IT 200\nEm frente à Sereia de Itapuã\nPrópria\n\nItapuã - SSA IT 200\nEm frente à Sereia de Itapuã\nPrópria\n\nFarol de Itapuã - SSA FI 100\nEm frente à Rua da Música (Antiga Rua K).\nPrópria\n\nFarol de Itapuã - SSA FI 100\nEm frente à Rua da Música (Antiga Rua K).\nPrópria\n\nStella Mares - SSA ST 100\nEm frente ao Hotel Grande Stella Maris.\nPrópria\n\nStella Mares - SSA ST 100\nEm frente ao Hotel Grande Stella Maris.\nPrópria\n\nObservações:\n\nCAMPANHA 26/2010 SSA\n\nEvitar contato com a água do mar em locais com manchas de coloração suspeita.\n",
            "Evite banho de praia em tempo chuvoso, as águas podem estar contaminadas, por arraste de diversos detritos das ruas através das galerias\npluviais, podendo causar doenças.\nÉ desaconselhável ainda o banho próximo à saída de esgotos, desembocadura dos rios urbanos, córregos e canais de drenagem.\n\nRESOLUÇÂO CONAMA Nº274 DE 29 DE NOVEMBRO DE 2000\nArt. 2º As águas doces, salobras e salinas destinadas à balneabilidade (recreação de contato primário) terão sua condição avaliada nas categorias própria e\nimprópria.\n\n§1º As águas consideradas próprias poderão ser subdivididas nas seguintes categorias:\nEscherichia coli – Quando em 80% ou mais de um conjunto de amostras obtidas em cada uma das cinco semanas anteriores, colhidas no mesmo local, houver:\nNo máximo, 200 – Excelente; 400 – Muito Boa; 800- Satisfatória.\n\n§4° As águas serão consideradas impróprias quando no trecho avaliado, for verificada uma das seguintes ocorrências:\na) Não atendimento aos critérios estabelecidos para as águas próprias;\nb) Valor obtido na última amostragem for superior a 2000 Escherichia coli;\n\nAvenida Luís Viana Filho, 6ª Avenida, nº 600 - CAB - CEP 41.745-900 | Salvador - Bahia - Brasil\n\nTel.: (71) 3118-4267\n\nDisque Meio Ambiente: 0800 71 1400\n\nbalneabilidade@inema.ba.gov.br\n",
        ]

        reader = rows.plugins.pdf.pdf_to_text(filename, backend=self.backend)
        for page, expected_page in zip(reader, expected_pages):
            self.assertEqual(page, expected_page)


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
        objects_by_text = {
            obj.text: obj
            for obj in dataset
        }
        x_groups = pdf.group_objects("x", dataset, threshold=0)
        groups_text = [
            sorted([obj.text for obj in group.objects])
            for group in x_groups
        ]
        expected_groups_text = [
            sorted(["obj1", "obj2", "obj4", "obj5"]),
            sorted(["obj3", "obj6", "obj7", "obj8", "obj9"]),
        ]
        assert groups_text == expected_groups_text

        y_groups = pdf.group_objects("y", dataset, threshold=0)
        groups_text = [
            sorted([obj.text for obj in group.objects])
            for group in y_groups
        ]
        expected_groups_text = [
            ["obj1"],
            ["obj2", "obj6"],
            ["obj3"],
            ["obj4", "obj7"],
            ["obj5"],
            ["obj8"], ["obj9"],
        ]
        assert groups_text == expected_groups_text
