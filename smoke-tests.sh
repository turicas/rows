#!/bin/bash
set -xe

TMPDIR=$(mktemp -d)
PYTHON_VERSION=$(python --version | sed 's/Python //; s/\./_/g')
echo "Python version: ${PYTHON_VERSION}"
echo "Using temp directory: $TMPDIR"

echo -e 'Name  , Age!\nAlice,30\nBob,25\nÁlvaro,37' > "$TMPDIR/people.csv"

python -m rows convert "$TMPDIR/people.csv" "$TMPDIR/people-converted.csv"
python -m rows convert --fields age,name --order-by ^age "$TMPDIR/people.csv" "$TMPDIR/people-ordered.csv"
python -m rows convert --fields-exclude age "$TMPDIR/people.csv" "$TMPDIR/people-exclude-field.csv"
python -m rows convert "https://data.brasil.io/dataset/genero-nomes/nomes.csv.gz" "$TMPDIR/nomes.csv"
# TODO: convert with URL from server with no valid SSL certificate

echo -e 'id,name\n1,Alice\n2,Bob\n3,Álvaro' > "$TMPDIR/left.csv"
echo -e 'id,score\n1,9.5\n2,7.0\n3,10.0' > "$TMPDIR/right.csv"
python -m rows join id "$TMPDIR/left.csv" "$TMPDIR/right.csv" "$TMPDIR/joined.csv"

echo -e 'Name   , Age!!\nAlice,30\nÁlvaro,37' > "$TMPDIR/part1.csv"
echo -e 'name,age\nBob,25' > "$TMPDIR/part2.csv"
python -m rows sum "$TMPDIR/part1.csv" "$TMPDIR/part2.csv" "$TMPDIR/parts1_2.csv"

python -m rows print "$TMPDIR/people.csv"
python -m rows print --fields-exclude age --frame-style double "$TMPDIR/people.csv"

python -m rows query "age > 25 AND age < 35" "$TMPDIR/people.csv"

python -m rows schema --format txt "$TMPDIR/people.csv" "$TMPDIR/schema.txt"

python -m rows csv-inspect "$TMPDIR/people.csv"

echo -e 'Name  , Age!\nAlice,30\nBob,25' > "$TMPDIR/bad.csv"
python -m rows csv-fix "$TMPDIR/bad.csv" "$TMPDIR/fixed.csv"

python -m rows csv-to-sqlite "$TMPDIR/people.csv" "$TMPDIR/data.sqlite"
python -m rows sqlite-to-csv "$TMPDIR/data.sqlite" people "$TMPDIR/people-from-sqlite.csv"

python -m rows csv-merge "tests/data/to-merge-1.csv" "tests/data/to-merge-2.csv" "tests/data/to-merge-3.csv" "$TMPDIR/merged.csv"

echo -e ' id ,name ,\n1 , Alice ,' > "$TMPDIR/dirty.csv"
python -m rows csv-clean "$TMPDIR/dirty.csv" "$TMPDIR/cleaned.csv"
cp "$TMPDIR/dirty.csv" "$TMPDIR/dirty-inplace.csv"
python -m rows csv-clean --in-place "$TMPDIR/dirty-inplace.csv"

python -m rows csv-row-count "$TMPDIR/people.csv"

echo -e 'id\n0\n1\n2\n3\n4\n5\n6\n7\n8\n9' > "$TMPDIR/big.csv"
python -m rows csv-split "$TMPDIR/big.csv" 3
python -m rows csv-split --destination-pattern "$TMPDIR/part-{part:02d}.csv" "$TMPDIR/big.csv" 2

python -m rows list-sheets tests/data/all-field-types.xls
python -m rows list-sheets tests/data/all-field-types.xlsx

python -m rows pdf-to-text tests/data/milho-safra-2017.pdf "$TMPDIR/pdf.txt"

table1="test_table_1_py${PYTHON_VERSION}"
table2="test_table_2_py${PYTHON_VERSION}"
echo "DROP TABLE IF EXISTS test_table" | psql $DATABASE_URL
echo "DROP TABLE IF EXISTS test_table2" | psql $DATABASE_URL
python -m rows pgimport tests/data/merged.csv $DATABASE_URL "$table1"
python -m rows pgexport $DATABASE_URL "$table1" "$TMPDIR/from-postgres.csv"
python -m rows pg2pg $DATABASE_URL "$table1" $DATABASE_URL "$table2"

echo "All commands succeeded."
