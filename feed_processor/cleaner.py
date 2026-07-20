def to_float(value, default=0.0):
    """
    Safely convert a value to float.

    Examples:
        "59"      -> 59.0
        "4.82"    -> 4.82
        ""        -> 0.0
        None      -> 0.0
        "abc"     -> 0.0
    """

    if value is None:
        return default

    value = str(value).strip()

    if value == "":
        return default

    try:
        return float(value)
    except (ValueError, TypeError):
        return default