# You must install the PDF dependencies for this script to work: there are two
# available backends: pymupdf (recommended) and pdfminer.six (slowest).
import io
import requests
import rows


url = "http://balneabilidade.inema.ba.gov.br/index.php/relatoriodebalneabilidade/geraBoletim?idcampanha=42041"
print("*** Downloading PDF...")
response = requests.get(url)

# The line below will automatically identify the table in all PDF pages - it
# works for this file but not for all cases. You can be more specific defining
# the page numbers, a start/end string (like the header/footer strings) and
# also change the table identification algorithm. Check `backend`, `algorithm`,
# `starts_after`, `ends_before` and `page_numbers` parameters.
# For this simple case you could also install rows' CLI (`pip install
# rows[cli]`) and run: `rows print <url>`
table = rows.import_from_pdf(io.BytesIO(response.content))
rows.export_to_csv(table, "beach-data.csv")
print("*** Table exported to beach-data.csv")

print("*** Extracted table:")
print(rows.export_to_txt(table))

# You could also iterate over the object, like:
# for row in table: print(row)


print("\n\n*** Extracted text:")
text_pages = rows.plugins.pdf.pdf_to_text(io.BytesIO(response.content))
print("\n\n".join(text_pages))
