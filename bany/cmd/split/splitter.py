"""
A class to managed split expenses.
"""
import dataclasses
import functools
import itertools
from collections import Counter
from collections.abc import Iterator

import pandas as pd
from moneyed import Money
from moneyed import USD
from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import field_validator
from pydantic import ValidationInfo

from bany.core.money import as_money


BROKE = Money(0.00, USD)
PENNY = Money(0.01, USD)


class Split(BaseModel):
    """
    A transaction split among multiple payers.
    """

    #: This ID is used to group multiple splits together, such as the main split and the associated taxes or tips
    group: int = -1
    #: This is the amount of money spent by the payers (could be a total, a tax, or a tip)
    amount: int | float | Money
    #: When the amount is a tax or tip, this is the 0 to 1 based percentage
    rate: float = 0
    #: This is the entity to which the amount has been paid (Gas Station, Restaurant, etc)
    payee: str = "Unknown"
    #: This is a category for the transaction (Food, Cleaning, etc)
    category: str = "Unknown"
    #: This is a mapping from the amount owed for each payer
    debtors: str | tuple[str, ...] | dict[str, int | float] = Field(default=(), validate_default=True)
    #: This is the person or persons who paid for the transaction
    creditors: str | tuple[str, ...] | dict[str, int | float] = Field(default=(), validate_default=True)

    @field_validator("debtors", mode="before")
    def _validate_debtors(cls, value: str | tuple[str, ...], info: ValidationInfo) -> dict[str:int]:
        """
        Validate creation of debtors field.
        """
        if isinstance(value, str):
            value = (value,)
        if isinstance(value, tuple):
            value = {v: 1 for v in value}
        if not isinstance(value, dict):
            raise TypeError

        total = sum(value.values())
        amount = info.data["amount"].get_amount_in_sub_unit()
        return {k: v / total * amount for k, v in value.items()}

    @field_validator("creditors", mode="before")
    def _validate_creditors(cls, value: str | tuple[str, ...], info: ValidationInfo) -> dict[str:int]:
        """
        Validate creation of creditors field.
        """
        if isinstance(value, str):
            value = (value,)
        if isinstance(value, tuple):
            value = {v: 1 for v in value}
        if not isinstance(value, dict):
            raise TypeError

        total = sum(value.values())
        amount = info.data["amount"].get_amount_in_sub_unit()
        return {k: v / total * amount for k, v in value.items()}

    @field_validator("amount", mode="before")
    def _validate_amounts(cls, value: int | float | Money) -> Money:
        """
        Validate creation of Money Field.
        """
        return as_money(value)

    model_config = ConfigDict(extra="forbid", validate_assignment=True, arbitrary_types_allowed=True)


@dataclasses.dataclass(slots=True)
class Tax:
    """
    The tax rate associated with a split transaction.
    """

    #: When the amount is a tax or tip, this is the 0 to 1 based percentage
    rate: float
    #: This is the entity to which the amount has been paid (Gas Station, Restaurant, etc)
    payee: str = "SalesTax"


@dataclasses.dataclass(slots=True)
class Tip:
    """
    The tip amount associated with a split transaction.
    """

    #: This is the amount of money spent by the payers (could be a total, a tax, or a tip)
    amount: int | float | Money
    #: This is a category for the transaction (Food, Cleaning, etc)
    category: str | None = None

    def __post_init__(self):
        self.amount = self.amount if isinstance(self.amount, Money) else Money(self.amount, USD)


@dataclasses.dataclass()
class Splitter:
    """
    Calculate who owes what from a collection of split transactions.
    """

    splits: dict[int, list[Split, ...]] = dataclasses.field(default_factory=dict)

    @property
    @functools.lru_cache(maxsize=1)
    def names(self) -> tuple[str, ...]:
        """
        The names of all persons taking part across all splits.
        """
        return tuple(
            sorted(
                set(
                    itertools.chain(
                        *(s.debtors for s in itertools.chain(*self.splits.values())),
                        *(s.creditors for s in itertools.chain(*self.splits.values())),
                    )
                )
            )
        )

    @property
    @functools.lru_cache(maxsize=1)
    def frame(self) -> pd.DataFrame:
        """
        Create the table of transactions from the current splits.
        """
        table = self._make_table_from_splits()
        table = self._compute_weights_for_payers(table)
        table = self._drop_counts_for_all_payers(table)
        table = self._compute_amounts_for_payers(table)
        table = self._compute_pennies_for_payers(table)
        self._validate_table(table)
        return table

    def _make_table_from_splits(self) -> pd.DataFrame:
        """
        Turn the current splits into a table.
        """
        table = pd.DataFrame(data=[s.dict() for s in itertools.chain(*self.splits.values())])
        table = table[table.amount > BROKE].reset_index(drop=True)
        return table

    def _compute_weights_for_payers(self, table: pd.DataFrame) -> pd.DataFrame:
        """
        Compute weights for individual payees.
        """
        # todo: this must be fixed to take account of multiple creditors
        count = pd.DataFrame(iter(table.debtors.apply(Counter))).fillna(0).astype(int)
        total = count.sum(axis=1)
        for name in self.names:
            try:
                count[f"{name}.w"] = count[name] / total
            except KeyError:
                count[f"{name}.w"] = 0.0
        return pd.concat([table, count], axis=1)

    @staticmethod
    def _drop_counts_for_all_payers(table: pd.DataFrame) -> pd.DataFrame:
        """
        These counts are no longer needed so can be dropped.
        """
        table["debtors"] = table["debtors"].apply(frozenset)
        table["creditors"] = table["creditors"].apply(frozenset)
        return table

    def _compute_amounts_for_payers(self, table: pd.DataFrame) -> pd.DataFrame:
        """
        Compute amount owed for individual payees.
        """
        for name in self.names:
            table[f"{name}.$"] = (table[f"{name}.w"] * table["amount"]).apply(lambda v: v.round(2))
        return table

    def _compute_pennies_for_payers(self, table: pd.DataFrame) -> pd.DataFrame:
        """
        Assign pennies to individual payees for odd splits.
        """
        table["Who"] = "-"
        table["Delta"] = BROKE

        for payers, subset in table.groupby(by="debtors"):
            count = Counter({name: 0 for name in self.names if name in payers})
            for index, _ in subset.iterrows():
                expected = table.loc[index, "amount"]
                observed = sum(table.loc[index, f"{name}.$"] for name in self.names)

                if (delta := (expected - observed).round(2)) != BROKE:
                    delta = PENNY if delta > BROKE else -PENNY
                    payer = {n: count[n] for n in self.names if table.loc[index, n]}

                    if delta > BROKE:
                        payer = min(payer, key=lambda v: count[v])
                        count[payer] += 1
                    else:
                        payer = max(payer, key=lambda v: count[v])
                        count[payer] -= 1

                    table.loc[index, r"Who"] = payer
                    table.loc[index, r"Delta"] = delta
                    table.loc[index, f"{payer}.$"] += delta

        return table

    def _validate_table(self, table: pd.DataFrame):
        """
        Ensure the table does not have any inconsistencies.
        """
        # The sum of amount owed should equal the total amount for the transaction
        for index, _ in table.iterrows():
            expected = table.loc[index, "amount"]
            observed = sum(table.loc[index, f"{name}.$"] for name in self.names)
            if (delta := (expected - observed).round(2)) != BROKE:
                raise ValueError("[%s] %s != %s Δ=%s", index, expected, observed, delta)

        # When splitting pennies, the difference should not be greater than 1 penny between members
        for payers, subset in table.groupby(by="debtors"):
            counts = subset.groupby("Who").Delta.sum()
            select = counts.index.intersection(payers)
            if not select.empty:
                for i1, v1 in counts.loc[select].items():
                    for i2, v2 in counts.loc[select].items():
                        if abs(v1 - v2).round(2) > PENNY:
                            raise ValueError(f"{v1} - {v2} > {PENNY}")

    def tax(self, *taxes: Tax, group: int = -1):
        """
        Add taxes to a group (the most recent split by default).
        """
        group = list(self.splits.keys())[group]

        split = self.splits[group][0]
        if not isinstance(split, Split):
            raise TypeError(type(split).__name__)

        self.splits[group].extend(self._extract_tax_and_tip_for_split(split, *taxes))

    def tip(self, *tips: Tip, group: int = -1):
        """
        Add tips to a group (the most recent split by default).
        """
        group = list(self.splits.keys())[group]

        split = self.splits[group][0]
        if not isinstance(split, Split):
            raise TypeError(type(split).__name__)

        self.splits[group].extend(self._extract_tax_and_tip_for_split(split, *tips))

    def split(self, split: Split, *objs: Tax | Tip) -> int:
        """
        Add a group of splits to the tracked splits.
        """
        group = len(self.splits)
        split = split.model_copy(update=dict(group=group))
        self.splits[group] = [split, *self._extract_tax_and_tip_for_split(split, *objs)]
        return group

    def clear(self):
        """
        Remove all splits for all groups.
        """
        self.splits = {}

    def remove(self, *groups: int):
        """
        Remove all splits with the given group.
        """
        self.splits = {g: s for g, s in self.splits.items() if g not in groups}

    @property
    def summary(self) -> pd.DataFrame:
        """
        Group by category and payee to summarize the current transactions.
        """
        columns = ["amount", "category", "payee", *(f"{n}.$" for n in self.names)]
        summary = self.frame.loc[:, columns].groupby(by=["category", "payee"]).sum(numeric_only=False)
        summary = pd.concat([summary, summary.sum(axis=0).to_frame(("Total", "")).T])
        return summary

    def _extract_tax_and_tip_for_split(self, split: Split, *objs: Tax | Tip) -> Iterator[Split]:
        """
        Explode split into multiple splits using tip and tax information.
        """
        if split.rate > 0:
            raise NotImplementedError("can not set tip or tax rate of Split directly!")

        for obj in objs:
            match obj:
                case Tax():
                    amount = (split.amount * obj.rate).round(2)
                    yield Split(
                        group=split.group,
                        amount=amount,
                        rate=obj.rate,
                        payee=obj.payee,
                        creditors=split.creditors,
                        category=split.category,
                        debtors=split.debtors,
                    )
                case Tip():
                    rate = obj.amount.get_amount_in_sub_unit() / split.amount.get_amount_in_sub_unit()
                    yield Split(
                        group=split.group,
                        amount=obj.amount,
                        rate=rate,
                        payee=split.payee,
                        creditors=split.creditors,
                        category=obj.category,
                        debtors=split.debtors,
                    )
                case _:
                    raise TypeError(type(obj))

    def __hash__(self):
        return id(self) + len(self.splits) + sum(map(len, self.splits.values()))


if __name__ == "__main__":
    import bany.core.config

    bany.core.config.pandas()

    splitter = Splitter()
    splitter.split(
        Split(
            amount=1.99,
            payee="A",
            category="Food",
            creditors="Ethan",
            debtors={"Adam": 1, "Ethan": 1},
        ),
        Tax(rate=0.06, payee="SalesTax"),
        Tip(amount=0.50, category="TipA"),
    )

    print(splitter.frame, "\n")
    print(splitter.summary)
