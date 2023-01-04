"""
Configuration helpers.
"""


def pandas():
    """
    Set up the pandas module.
    """
    import pandas as _pandas

    _pandas.set_option("display.max_colwidth", 1024)
    _pandas.set_option("display.max_columns", 1024)
    _pandas.set_option("display.max_rows", 1024)
    _pandas.set_option("display.width", 4096)
