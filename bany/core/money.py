"""
Helper functions for Money.
"""
import decimal
import itertools


def moneyfmt(value, *values, width: int = 12, decimals: int = 2) -> str:
    """
    A helper function to format a value or list of values as money rounded to pennies.

    Parameters:
        value: The 1st value to format.
        values: The remaining values to format.
        width: The output width to justify string in.
        decimals: The number of decimals to round to.

    Returns:
        The formatted money string.
    """
    cent = "0.{}1".format("0" * (decimals - 1))
    cent = decimal.Decimal(cent)
    if values:
        return ", ".join(
            "{:>{width},}".format(decimal.Decimal(v).quantize(cent, decimal.ROUND_HALF_UP), width=width)
            for v in itertools.chain([value], values)
        )
    else:
        return "{:>{width},}".format(decimal.Decimal(value).quantize(cent, decimal.ROUND_HALF_UP), width=width)
