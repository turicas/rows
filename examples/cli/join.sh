#!/bin/bash

KEYS="uf,municipio"
SOURCE1="populacao-sudeste.csv"
SOURCE2="area-sudeste.csv"
DESTINATION="sudeste.csv"

rows join $KEYS $SOURCE1 $SOURCE2 $DESTINATION
