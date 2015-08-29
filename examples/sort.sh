#!/bin/bash

URL="http://cidades.ibge.gov.br/comparamun/compara.php?idtema=1&codv=v01&coduf=43"
LOCALE="pt_BR.UTF-8"
FILENAME="populacao-rs-sorted"

rows sort --input-locale $LOCALE ^pessoas $URL $FILENAME.csv
