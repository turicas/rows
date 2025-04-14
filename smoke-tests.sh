#!/bin/bash
set -xe

TMPDIR=$(mktemp -d)
PYTHON_VERSION=$(python --version | sed 's/Python //; s/\./_/g')
ROWS="python3 -m rows"
echo "Python version: ${PYTHON_VERSION}"
echo "Using temp directory: $TMPDIR"

echo -e 'Name  , Age!\nAlice,30\nBob,25\nÁlvaro,37' > "$TMPDIR/people.csv"

$ROWS convert "$TMPDIR/people.csv" "$TMPDIR/people-converted.csv"
$ROWS convert --fields age,name --order-by ^age "$TMPDIR/people.csv" "$TMPDIR/people-ordered.csv"
$ROWS convert --fields-exclude age "$TMPDIR/people.csv" "$TMPDIR/people-exclude-field.csv"
$ROWS convert "https://data.brasil.io/dataset/genero-nomes/nomes.csv.gz" "$TMPDIR/nomes.csv"
# TODO: convert with URL from server with no valid SSL certificate

echo -e 'id,name\n1,Alice\n2,Bob\n3,Álvaro' > "$TMPDIR/left.csv"
echo -e 'id,score\n1,9.5\n2,7.0\n3,10.0' > "$TMPDIR/right.csv"
$ROWS join id "$TMPDIR/left.csv" "$TMPDIR/right.csv" "$TMPDIR/joined.csv"

echo -e 'Name   , Age!!\nAlice,30\nÁlvaro,37' > "$TMPDIR/part1.csv"
echo -e 'name,age\nBob,25' > "$TMPDIR/part2.csv"
$ROWS sum "$TMPDIR/part1.csv" "$TMPDIR/part2.csv" "$TMPDIR/parts1_2.csv"

$ROWS print "$TMPDIR/people.csv"
$ROWS print --fields-exclude age --frame-style double "$TMPDIR/people.csv"

$ROWS query "age > 25 AND age < 35" "$TMPDIR/people.csv"

$ROWS schema --format txt "$TMPDIR/people.csv" "$TMPDIR/schema.txt"

$ROWS csv-inspect "$TMPDIR/people.csv"

echo -e 'Name  , Age!\nAlice,30\nBob,25' > "$TMPDIR/bad.csv"
$ROWS csv-fix "$TMPDIR/bad.csv" "$TMPDIR/fixed.csv"

$ROWS csv-to-sqlite "$TMPDIR/people.csv" "$TMPDIR/data.sqlite"
$ROWS sqlite-to-csv "$TMPDIR/data.sqlite" people "$TMPDIR/people-from-sqlite.csv"

$ROWS csv-merge "tests/data/to-merge-1.csv" "tests/data/to-merge-2.csv" "tests/data/to-merge-3.csv" "$TMPDIR/merged.csv"

echo -e ' id ,name ,\n1 , Alice ,' > "$TMPDIR/dirty.csv"
$ROWS csv-clean "$TMPDIR/dirty.csv" "$TMPDIR/cleaned.csv"
cp "$TMPDIR/dirty.csv" "$TMPDIR/dirty-inplace.csv"
$ROWS csv-clean --in-place "$TMPDIR/dirty-inplace.csv"

$ROWS csv-row-count "$TMPDIR/people.csv"

echo -e 'id\n0\n1\n2\n3\n4\n5\n6\n7\n8\n9' > "$TMPDIR/big.csv"
$ROWS csv-split "$TMPDIR/big.csv" 3
$ROWS csv-split --destination-pattern "$TMPDIR/part-{part:02d}.csv" "$TMPDIR/big.csv" 2

$ROWS list-sheets tests/data/all-field-types.xls
$ROWS list-sheets tests/data/all-field-types.xlsx

$ROWS pdf-to-text tests/data/milho-safra-2017.pdf "$TMPDIR/pdf.txt"

if $(psql --version 2&>1 /dev/null); then
  table1="test_table_1_py${PYTHON_VERSION}"
  table2="test_table_2_py${PYTHON_VERSION}"
  echo "DROP TABLE IF EXISTS ${table1}" | psql $DATABASE_URL
  echo "DROP TABLE IF EXISTS ${table2}" | psql $DATABASE_URL
  $ROWS pgimport tests/data/merged.csv $DATABASE_URL "$table1"
  $ROWS pgexport $DATABASE_URL "$table1" "$TMPDIR/from-postgres.csv"
  $ROWS pg2pg $DATABASE_URL "$table1" $DATABASE_URL "$table2"
else
  echo "WARN: psql is not installed - skipping pgimport, pgexport and pg2pg tests"
fi

echo "All commands succeeded."
