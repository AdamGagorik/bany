"""
The data associated with each node or column when representing the problem.
"""

import dataclasses
import typing
from functools import partial


def format_number(value: int | float, width: int, precision: int = 2, filler=" ", sign: bool = False) -> str:
    sign = "" if not sign else ("-" if value < 0 else ("+" if value > 0 else " "))
    mark = "red" if value < 0 else ("cyan" if value > 0 else "default")
    numb = f"{abs(value):,.{precision}f}" if abs(value) > 0 else filler * width
    return f"[[bold]{sign}[/][bold {mark}]{numb:>{width}}[/]]"


FORMAT_RATIO = partial(format_number, width=5, precision=3)
FORMAT_VALUE = partial(format_number, width=11, precision=2, sign=True)


# filter constants
INPUT_VALUE: int = 1 << 0
DISPLAY_ALL: int = 1 << 1
DISPLAY_INP: int = 1 << 2
DISPLAY_OUT: int = 1 << 3


@dataclasses.dataclass()
class Attribute:
    # name of node attribute
    column: str
    # type of node attribute
    dtype: typing.Callable
    # default value
    value: typing.Any
    # format attribute in display?
    display: bool | str | typing.Callable = False
    # subset filter
    filters: int = 0

    def __str__(self) -> str:
        return self.column


@dataclasses.dataclass()
class Attributes:
    # The label for the node
    label: Attribute = dataclasses.field(default_factory=lambda: Attribute("label", str, "", "{}", INPUT_VALUE))
    # The level for the node in the tree
    level: Attribute = dataclasses.field(
        default_factory=lambda: Attribute("level", int, -1, "[{:}]", DISPLAY_ALL | DISPLAY_INP | DISPLAY_OUT)
    )
    # The current amount in this bucket
    current_value: Attribute = dataclasses.field(
        default_factory=lambda: Attribute(
            "current_value", float, 1.0, FORMAT_VALUE, DISPLAY_ALL | INPUT_VALUE | DISPLAY_INP
        )
    )
    # The optimal amount in this bucket
    optimal_value: Attribute = dataclasses.field(
        default_factory=lambda: Attribute("optimal_value", float, 0.0, FORMAT_VALUE, DISPLAY_ALL)
    )
    # The solvers amount in this bucket (what we solve for)
    results_value: Attribute = dataclasses.field(
        default_factory=lambda: Attribute("results_value", float, 0.0, FORMAT_VALUE, DISPLAY_ALL | DISPLAY_OUT)
    )
    # The current amount in this bucket as a fraction over its level
    current_ratio: Attribute = dataclasses.field(
        default_factory=lambda: Attribute("current_ratio", float, 1.0, FORMAT_RATIO, DISPLAY_ALL)
    )
    # The desired amount in this bucket as a fraction over its level
    optimal_ratio: Attribute = dataclasses.field(
        default_factory=lambda: Attribute(
            "optimal_ratio", float, 0.0, FORMAT_RATIO, DISPLAY_ALL | INPUT_VALUE | DISPLAY_INP
        )
    )
    # The solvers amount in this bucket as a fraction over its level
    results_ratio: Attribute = dataclasses.field(
        default_factory=lambda: Attribute("results_ratio", float, 0.0, FORMAT_RATIO, DISPLAY_ALL | DISPLAY_OUT)
    )
    # The product amount in this bucket as a fraction by multiplying over ancestors optimal
    # For example, given the path 1->2->3, the ratio at 3 would be ratio_1 * ratio_2 * ratio_3
    product_ratio: Attribute = dataclasses.field(
        default_factory=lambda: Attribute("product_ratio", float, 0.0, FORMAT_RATIO, DISPLAY_ALL)
    )
    # The amount to distribute at this source over the descendents
    amount_to_add: Attribute = dataclasses.field(
        default_factory=lambda: Attribute(
            "amount_to_add", float, 0.0, FORMAT_VALUE, DISPLAY_ALL | INPUT_VALUE | DISPLAY_INP | DISPLAY_OUT
        )
    )

    def subset(
        self, *columns, filters: int | None = None, strict: bool = True, name: str | None = None
    ) -> typing.Generator[Attribute | str, None, None]:
        """
        Select a subset of the node attributes.

        Parameters:
            columns: Only fields with these column names will be returned.
            filters: A bitfield mask to filter out certain fields based on their properties.
            strict: If column names were given that do not match known fields, raise an error.
            name: Instead of returning fields, return the field.name attribute with the given name.

        Yields:
            The fields or field.name attribute with the given name.
        """
        fields = {f.name: getattr(self, f.name) for f in dataclasses.fields(self)}

        if filters is not None:
            fields = {n: f for n, f in fields.items() if f.filters & filters}

        if columns:
            for label in columns:
                try:
                    if name is not None:
                        yield getattr(fields[label], name)
                    else:
                        yield fields[label]
                except KeyError:
                    if strict:
                        raise ValueError(label) from None
                    else:
                        pass
        else:
            for f in fields.values():
                if name is not None:
                    yield getattr(f, name)
                else:
                    yield f

    def dtypes(self, *columns, **kwargs):
        """
        Get the dtypes for the node attributes.
        """
        return {f.column: f.dtype for f in self.subset(*columns, **kwargs)}

    def columns(self, *columns, **kwargs):
        """
        Get the labels for the node attributes.
        """
        return [f.column for f in self.subset(*columns, **kwargs)]


node_attrs: Attributes = Attributes()
