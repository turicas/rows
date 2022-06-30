"""Creates a correct (?) CSV that can cause some trouble"""

import csv


data = b"""f1,f2,f3
1,1,test
2,2,"<NUL>\x00</NUL>"
3,3,"<nl quoted>\n</nl>"
4,3,"<nl quoted escaped>\\\n</nl>"
5,3,"<nl quoted escaped-literal>\\n</nl>"
6,4,\.
7,1,another test
9,5,"<cr quoted>\r</cr>"
10,5,"<cr quoted escaped>\\\r</cr>"
11,5,"<cr quoted escaped-literal>\\r</cr>"
13,6,"<crnl quoted>\r\n</crnl>"
"""

# The lines above aren't correct, so not part of the file
wrong = b"""
3,3,<nl unquoted>\n</nl>
8,5,<cr unquoted>\r</cr>
12,6,<crnl unquoted>\r\n</crnl>
"""

with open("bad-csv-1.csv", mode="wb") as fobj:
    fobj.write(data)


values = [
    {"f1": 1, "f2": 3, "f3": "<nl>\n</nl>"},
    {"f1": 2, "f2": 5, "f3": "<cr>\r</cr>"},
    {"f1": 3, "f2": 6, "f3": "<crnl>\r\n</crnl>"},
]
with open("bad-csv-2.csv", mode="w") as fobj:
    writer = csv.DictWriter(fobj, fieldnames=["f1", "f2", "f3"])
    writer.writeheader()
    for row in values:
        writer.writerow(row)
