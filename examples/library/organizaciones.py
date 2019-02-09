# coding: utf-8

# This example downloads some Ecuatorian organizations in JSON, extracts the
# desired `dict`s, then import then into a `rows.Table` object to finally
# export as XLS.
# Install dependencies by running: pip install requests rows[xls]

import requests

import rows

URL = "http://www.onumujeres-ecuador.org/geovisor/data/organizaciones.php"


def download_organizations():
    "Download organizations JSON and extract its properties"

    response = requests.get(URL)
    data = response.json()
    organizations = [organization["properties"] for organization in data["features"]]
    return rows.import_from_dicts(organizations)


if __name__ == "__main__":
    table = download_organizations()
    rows.export_to_xls(table, "organizaciones.xls")
