#!/bin/bash

# population

SOURCE1="http://cidades.ibge.gov.br/comparamun/compara.php?idtema=1&codv=v01&coduf=33"
SOURCE2="http://cidades.ibge.gov.br/comparamun/compara.php?idtema=1&codv=v01&coduf=35"
SOURCE3="http://cidades.ibge.gov.br/comparamun/compara.php?idtema=1&codv=v01&coduf=31"
SOURCE4="http://cidades.ibge.gov.br/comparamun/compara.php?idtema=1&codv=v01&coduf=32"
DESTINATION="populacao-sudeste.csv"
LOCALE="pt_BR.UTF-8"

rows sum --input-locale=$LOCALE --input-encoding=utf-8 \
         $SOURCE1 $SOURCE2 $SOURCE3 $SOURCE4 \
         $DESTINATION

# area

SOURCE5="http://cidades.ibge.gov.br/comparamun/compara.php?idtema=16&codv=v01&coduf=33"
SOURCE6="http://cidades.ibge.gov.br/comparamun/compara.php?idtema=16&codv=v01&coduf=35"
SOURCE7="http://cidades.ibge.gov.br/comparamun/compara.php?idtema=16&codv=v01&coduf=31"
SOURCE8="http://cidades.ibge.gov.br/comparamun/compara.php?idtema=16&codv=v01&coduf=32"
DESTINATION="area-sudeste.csv"

rows sum --input-locale=$LOCALE --input-encoding=utf-8 \
         $SOURCE5 $SOURCE6 $SOURCE7 $SOURCE8 \
         $DESTINATION
