#!/bin/bash

query="
SELECT *
FROM (
  SELECT DISTINCT
      encode(ST_AsBinary(geom), 'hex') AS geom_wkb
    , encode(ST_AsEWKB(geom), 'hex') AS geom_ewkb
    , ST_AsText(geom) AS geom_wkt
    , ST_AsEWKT(geom) AS geom_ewkt
  FROM ibama_auto_infracao
  WHERE
    geom IS NOT NULL
    AND ST_GeometryType(geom) = 'ST_Point'
) AS tmp
ORDER BY RANDOM()
LIMIT 100
"
rows pgexport --is-query "$DATABASE_URL" "$query" spatial-point.csv.gz
