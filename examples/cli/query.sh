#!/bin/bash

# This script will run rows' "query" subcommand passing the URL of two HTML
# sources, a SQL query and a output CSV filename. rows CLI will:
# - Download each file, identify its format (HTML) and import as a table
# - Convert the two tables into one SQLite in-memory database
# - Run the query into the database
# - Export the results to a CSV file

# Rio de Janeiro: inhabitants (per city)
SOURCE1="http://cidades.ibge.gov.br/comparamun/compara.php?idtema=1&codv=v01&coduf=33"
# Rio de Janeiro: area in km² (per city)
SOURCE2="http://cidades.ibge.gov.br/comparamun/compara.php?idtema=16&codv=v01&coduf=33"

LOCALE="pt_BR.UTF-8"
SOURCES="$SOURCE1 $SOURCE2"
# $SOURCE1 (inhabitants) will be "table1"
# $SOURCE2 (area) will be "table2"
QUERY="SELECT table1.uf AS state,
              table1.municipio AS city,
              table1.pessoas AS inhabitants,
              table2.km2 as area,
              (table1.pessoas / table2.km2) AS demographic_density
       FROM
              table1, table2
       WHERE
              table1.uf = table2.uf AND table1.municipio = table2.municipio"
OUTPUT="rj-density.csv"
rows query --input-locale=$LOCALE --input-encoding=utf-8 "$QUERY" $SOURCES \
	--output=$OUTPUT
