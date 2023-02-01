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
from pydantic import validator


BROKE = Money(0.00, USD)
PENNY = Money(0.01, USD)


class Split(BaseModel):
    """
    A transaction split among multiple payers.
    """

    #: This ID is used to group multiple splits together, such as the main split and the associated taxes or tips
    Group: int = -1
    #: This is the amount of money spent by the payers (could be a total, a tax, or a tip)
    Amount: int | float | Money
    #: When the amount is a tax or tip, this is the 0 to 1 based percentage
    Rate: float = 0
    #: This is the entity to which the amount has been paid (Gas Station, Restaurant, etc)
    Payee: str = "Unknown"
    #: This is a category for the transaction (Food, Cleaning, etc)
    Category: str = "Unknown"
    #: This is a mapping from the amount owed for each payer
    Debtors: str | tuple[str, ...] | dict[str, int] = ()
    #: This is the person or persons who paid for the transaction
    Creditors: str | tuple[str, ...] | dict[str, int] = ()

    @validator("Debtors", pre=True, always=True)
    def _validate_debtors(cls, value: str | tuple[str, ...]) -> dict[str:int]:
        """
        Validate creation of Debtors field.
        """
        if isinstance(value, str):
            value = (value,)
        if isinstance(value, tuple):
            value = {v: 1 for v in value}
        if not isinstance(value, dict):
            raise TypeError
        return {k: v for k, v in value.items()}

    @validator("Creditors", pre=True, always=True)
    def _validate_creditors(cls, value: str | tuple[str, ...]) -> dict[str:int]:
        """
        Validate creation of Creditors field.
        """
        if isinstance(value, str):
            value = (value,)
        if isinstance(value, tuple):
            value = {v: 1 for v in value}
        if not isinstance(value, dict):
            raise TypeError
        return {k: v for k, v in value.items()}

    @validator("Amount", pre=True, always=True)
    def _validate_amounts(cls, value: int | float | Money) -> Money:
        """
        Validate creation of Money Field.
        """
        if not isinstance(value, Money):
            return Money(value, USD)
        return value

    class Config:
        extra = "forbid"
        validate_assignment = True
        arbitrary_types_allowed = True


@dataclasses.dataclass(slots=True)
class Tax:
    """
    The tax rate associated with a split transaction.
    """

    #: When the amount is a tax or tip, this is the 0 to 1 based percentage
    Rate: float
    #: This is the entity to which the amount has been paid (Gas Station, Restaurant, etc)
    Payee: str = "SalesTax"


@dataclasses.dataclass(slots=True)
class Tip:
    """
    The tip amount associated with a split transaction.
    """

    #: This is the amount of money spent by the payers (could be a total, a tax, or a tip)
    Amount: int | float | Money
    #: This is a category for the transaction (Food, Cleaning, etc)
    Category: str | None = None

    def __post_init__(self):
        self.Amount = self.Amount if isinstance(self.Amount, Money) else Money(self.Amount, USD)


@dataclasses.dataclass()
class Splitter:
    """
    Calculate who owes what from a collection of split transactions.
    """

    #: todo change this to a dict from group to list of splits for easier deletion, etc
    splits: list[list[Split, ...]] = dataclasses.field(default_factory=list)

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
                        *(s.Debtors for s in itertools.chain(*self.splits)),
                        *(s.Creditors for s in itertools.chain(*self.splits)),
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
        table = pd.DataFrame(data=[s.dict() for s in itertools.chain(*self.splits)])
        table = table[table.Amount > BROKE].reset_index(drop=True)
        return table

    def _compute_weights_for_payers(self, table: pd.DataFrame) -> pd.DataFrame:
        """
        Compute weights for individual payees.
        """
        # todo: this must be fixed to take account of multiple creditors
        count = pd.DataFrame(iter(table.Debtors.apply(Counter))).fillna(0).astype(int)
        total = count.sum(axis=1)
        for name in self.names:
            count[f"{name}.w"] = count[name] / total
        return pd.concat([table, count], axis=1)

    @staticmethod
    def _drop_counts_for_all_payers(table: pd.DataFrame) -> pd.DataFrame:
        """
        These counts are no longer needed so can be dropped.
        """
        table["Debtors"] = table["Debtors"].apply(frozenset)
        table["Creditors"] = table["Creditors"].apply(frozenset)
        return table

    def _compute_amounts_for_payers(self, table: pd.DataFrame) -> pd.DataFrame:
        """
        Compute amount owed for individual payees.
        """
        for name in self.names:
            table[f"{name}.$"] = (table[f"{name}.w"] * table["Amount"]).apply(lambda v: v.round(2))
        return table

    def _compute_pennies_for_payers(self, table: pd.DataFrame) -> pd.DataFrame:
        """
        Assign pennies to individual payees for odd splits.
        """
        table["Who"] = "-"
        table["Delta"] = BROKE

        for payers, subset in table.groupby(by="Debtors"):
            count = Counter({name: 0 for name in self.names if name in payers})
            for index, _ in subset.iterrows():
                expected = table.loc[index, "Amount"]
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
            expected = table.loc[index, "Amount"]
            observed = sum(table.loc[index, f"{name}.$"] for name in self.names)
            if (delta := (expected - observed).round(2)) != BROKE:
                raise ValueError("[%s] %s != %s Δ=%s", index, expected, observed, delta)

        # When splitting pennies, the difference should not be greater than 1 penny between members
        for payers, subset in table.groupby(by="Debtors"):
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
        split = self.splits[group][0]
        assert isinstance(split, Split)
        self.splits[-1].extend(self._extract_tax_and_tip_for_split(split, *taxes))

    def tip(self, *tips: Tip, group: int = -1):
        """
        Add tips to a group (the most recent split by default).
        """
        split = self.splits[group][0]
        assert isinstance(split, Split)
        self.splits[group].extend(self._extract_tax_and_tip_for_split(split, *tips))

    def split(self, split: Split, *objs: Tax | Tip):
        """
        Add a group of splits to the tracked splits.
        """
        split = split.copy(update=dict(Group=len(self.splits)))
        self.splits.append([split, *self._extract_tax_and_tip_for_split(split, *objs)])

    def remove(self, *groups: int):
        """
        Remove all splits with the given group.
        """
        self.splits = [splits for splits in self.splits if not splits[0].Group in groups]

    def _extract_tax_and_tip_for_split(self, split: Split, *objs: Tax | Tip) -> Iterator[Split]:
        """
        Explode split into multiple splits using tip and tax information.
        """
        if split.Rate > 0:
            raise NotImplementedError("can not set tip or tax rate of Split directly!")

        for obj in objs:
            match obj:
                case Tax():
                    amount = (split.Amount * obj.Rate).round(2)
                    yield Split(
                        Group=split.Group,
                        Amount=amount,
                        Rate=obj.Rate,
                        Payee=obj.Payee,
                        Creditors=split.Creditors,
                        Category=split.Category,
                        Debtors=split.Debtors,
                    )
                case Tip():
                    rate = obj.Amount.get_amount_in_sub_unit() / split.Amount.get_amount_in_sub_unit()
                    yield Split(
                        Group=split.Group,
                        Amount=obj.Amount,
                        Rate=rate,
                        Payee=split.Payee,
                        Creditors=split.Creditors,
                        Category=obj.Category,
                        Debtors=split.Debtors,
                    )
                case _:
                    raise TypeError(type(obj))

    def __hash__(self):
        return id(self) + sum(map(len, self.splits))


if __name__ == "__main__":
    import bany.core.config

    bany.core.config.pandas()

    splitter = Splitter()
    splitter.split(
        Split(
            Amount=1.99,
            Payee="A",
            Category="Food",
            Creditors="Ethan",
            Debtors={"Adam": 1, "Ethan": 1},
        ),
        Tax(Rate=0.06, Payee="SalesTax"),
        Tip(Amount=0.50, Category="TipA"),
    )

    print(splitter.frame, "\n")
    columns = ["Amount", "Category", "Payee", *(f"{n}.$" for n in splitter.names)]
    print(splitter.frame.loc[:, columns].groupby(by=["Category", "Payee"], level=0).sum(numeric_only=False))
