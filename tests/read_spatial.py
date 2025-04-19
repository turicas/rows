def main():
    import csv

    from rows import cfopen
    from rows.plugins.plugin_spatial import Point2D

    filename = "tests/data/spatial-point.csv.gz"
    with cfopen(filename) as fobj:
        csv_data = list(csv.DictReader(fobj))

    for row in csv_data:
        point_wkt = Point2D.from_wkt(row["geom_wkt"])
        point_wkb = Point2D.from_wkb(bytes.fromhex(row["geom_wkb"]))
        if point_wkt != point_wkb or str(point_wkb) != str(point_wkt) or bytes(point_wkb) != bytes(point_wkt):
            print("Points differ:", point_wkt, point_wkb)

if __name__ == "__main__":
    main()
