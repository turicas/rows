as_tuple = (0, 5, 0, "dev0")
as_string = (
    ".".join(str(item) for item in as_tuple[:3])
    + "-{}".format("-".join(str(item) for item in as_tuple[3:])) if len(as_tuple) > 3 else ""
)
