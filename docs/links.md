# Links


## Showcase

- (Portuguese) [Talk (videos + slides) on rows by Álvaro Justen][rows-talk-pt]


## Related and Similar Projects

- (Article) [Data science at the command-line](https://github.com/jeroenjanssens/data-science-at-the-command-line)
- [Ghost.py](https://github.com/jeanphix/Ghost.py)
- [OKFN's goodtables](https://github.com/okfn/goodtables)
- [OKFN's messytables](https://github.com/okfn/messytables)
- [Pipe](https://github.com/JulienPalard/Pipe)
- [Recorde](https://github.com/pinard/Recode)
- [TableFactory](https://pypi.python.org/pypi/TableFactory)
- [Tabula](http://tabula.technology/)
- [continuous-docs](https://github.com/icgood/continuous-docs)
- [csvcat](https://pypi.python.org/pypi/csvcat)
- [csvstudio](https://github.com/mdipierro/csvstudio)
- [dataconverters](https://github.com/okfn/dataconverters)
- [dateparser](https://github.com/scrapinghub/dateparser)
- [django-import-export](https://github.com/django-import-export/django-import-export)
- [extruct](https://github.com/scrapinghub/extruct)
- [grablib](https://github.com/lorien/grab)
- [import.io](http://import.io/)
- [libextract](https://github.com/datalib/libextract)
- [libextract](https://github.com/datalib/libextract)
- [multicorn](https://github.com/Kozea/Multicorn)
- [odo](https://github.com/blaze/odo)
- [pandashells](https://github.com/robdmc/pandashells) (and pandas DataFrame)
- [parse](https://github.com/r1chardj0n3s/parse)
- [proof](https://github.com/wireservice/proof)
- [records](https://github.com/kennethreitz/records)
- [schema](https://pypi.python.org/pypi/schema)
- [scrapelib](https://github.com/jamesturk/scrapelib)
- [scrapy](http://scrapy.org/)
- [screed](https://github.com/ctb/screed)
- [selection](https://github.com/lorien/selection)
- [streamtools](http://blog.nytlabs.com/streamtools/)
- [table-extractor](https://pypi.python.org/pypi/table-extractor)
- [tablib](https://tablib.readthedocs.org/en/latest/)
- [telega-mega-import](https://github.com/django-stars/telega-mega-import)
- [textql](https://github.com/dinedal/textql)
- [texttables](https://github.com/Taywee/texttables)
- [validictory](https://github.com/jamesturk/validictory)
- [validr](https://pypi.python.org/pypi/validr)
- [visidata](https://github.com/saulpw/visidata/)
- [webscraper.io](http://webscraper.io/)


## Known Issues

- [Create a better plugin interface so anyone can benefit of
  it][rows-issue-27]
- [Create an object to represent a set of `rows.Table`s, like
  `TableSet`][rows-issue-47]
- Performance: the automatic type detection algorithm can cost time: it
  iterates over all rows to determine the type of each column. You can disable
  it by passing `samples=0` to any `import_from_*` function or either changing
  the number of sample rows (any positive number is accepted).
- [Code design issues][rows-issue-31]


[rows-issue-27]: https://github.com/turicas/rows/issues/27
[rows-issue-31]: https://github.com/turicas/rows/issues/31
[rows-issue-47]: https://github.com/turicas/rows/issues/47
[rows-showcase-source]: https://github.com/leonardocsantoss/django-rows
[rows-showcase]: http://rows.irdx.com.br/
[rows-talk-pt]: http://blog.justen.eng.br/2016/05/dados-tabulares-a-maneira-pythonica.html
