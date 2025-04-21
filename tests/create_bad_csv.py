# coding: utf-8

# Copyright 2014-2025 Álvaro Justen <https://github.com/turicas/rows/>
#    This program is free software: you can redistribute it and/or modify it under the terms of the GNU Lesser General
#    Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option)
#    any later version.
#    This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied
#    warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for
#    more details.
#    You should have received a copy of the GNU Lesser General Public License along with this program.  If not, see
#    <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals

"""Creates a correct (?) CSV that can cause some trouble"""

import csv


data = b"""f1,f2,f3
1,1,test
2,2,"<NUL>\x00</NUL>"
3,3,"<nl quoted>\n</nl>"
4,3,"<nl quoted escaped>\\\n</nl>"
5,3,"<nl quoted escaped-literal>\\n</nl>"
6,4,\\.
7,1,another test
9,5,"<cr quoted>\r</cr>"
10,5,"<cr quoted escaped>\\\r</cr>"
11,5,"<cr quoted escaped-literal>\\r</cr>"
13,6,"<crnl quoted>\r\n</crnl>"
"""

def main():
    filename_1, filename_2 = "bad-csv-1.csv", "bad-csv-2.csv"

    with open(filename_1, mode="wb") as fobj:
        fobj.write(data)
    values = [
        {"f1": 1, "f2": 3, "f3": "<nl>\n</nl>"},
        {"f1": 2, "f2": 5, "f3": "<cr>\r</cr>"},
        {"f1": 3, "f2": 6, "f3": "<crnl>\r\n</crnl>"},
    ]
    with open(filename_2, mode="w") as fobj:
        writer = csv.DictWriter(fobj, fieldnames=["f1", "f2", "f3"])
        writer.writeheader()
        for row in values:
            writer.writerow(row)


if __name__ == "__main__":
    main()
