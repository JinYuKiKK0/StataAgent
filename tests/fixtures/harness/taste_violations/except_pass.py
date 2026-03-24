def swallow_errors() -> None:
    try:
        value = 1 / 0
        _ = value
    except ZeroDivisionError:
        pass
