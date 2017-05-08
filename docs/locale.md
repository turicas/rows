# Locale

Many fields inside `rows.fields` are locale-aware. If you have some data using
Brazilian Portuguese number formatting, for example (`,` as decimal separators
and `.` as thousands separator) you can configure this into the library and
`rows` will automatically understand these numbers!

Let's see it working by extracting the population of cities in Rio de Janeiro
state:

```python
import locale
import requests
import rows
from io import BytesIO

url = 'http://cidades.ibge.gov.br/comparamun/compara.php?idtema=1&codv=v01&coduf=33'
html = requests.get(url).content
with rows.locale_context(name='pt_BR.UTF-8', category=locale.LC_NUMERIC):
    rio = rows.import_from_html(BytesIO(html))

total_population = sum(city.pessoas for city in rio)
# 'pessoas' is the fieldname related to the number of people in each city
print('Rio de Janeiro has {} inhabitants'.format(total_population))
```

The column `pessoas` will be imported as an `IntegerField` and the result is:

```text
Rio de Janeiro has 15989929 inhabitants
```
