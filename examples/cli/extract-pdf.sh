#!/bin/bash

URL='http://balneabilidade.inema.ba.gov.br/index.php/relatoriodebalneabilidade/geraBoletim?idcampanha=27641'
QUERY='SELECT * FROM table1 WHERE categoria = "Imprópria"'
rows convert "$URL" water-quality.csv
rows query "$QUERY" "$URL" --output=bad-water-quality.csv
