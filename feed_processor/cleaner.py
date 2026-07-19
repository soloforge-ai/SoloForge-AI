def to_float(value):
    """
    Convert a value to float.

    Examples:
        "59"    -> 59.0
        "4.82"  -> 4.82
        ""      -> None
        None    -> None
    """

    if value is None:
        return None

    value = str(value).strip()

    if value == "":
        return None

    try:
        return float(value)
    except ValueError:
        return None