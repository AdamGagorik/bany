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
    #: This is the person or persons who paid for the transaction
    Payer: str
    #: This is a mapping from the amount owed for each payer
    Payers: str | tuple[str, ...] | dict[str, int] = ()

    @validator("Payers", pre=True, always=True)
    def _validate_payers(cls, value: str | tuple[str, ...], values: dict) -> dict[str:int]:
        """
        Validate creation of Payers field.
        """
        if isinstance(value, str):
            value = (value,)
        if isinstance(value, tuple):
            value = {v: 1 for v in value}
        if not isinstance(value, dict):
            raise TypeError
        if (payer := values["Payer"]) not in value:
            value[payer] = 0
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


@dataclasses.dataclass()
class Splitter:
    splits: list[list[Split, ...]] = dataclasses.field(default_factory=list)

    @property
    @functools.lru_cache(maxsize=1)
    def names(self) -> tuple[str, ...]:
        """
        The names of all persons taking part across all splits.
        """
        return tuple(sorted(set(itertools.chain(*(s.Payers for s in itertools.chain(*self.splits))))))

    @property
    @functools.lru_cache(maxsize=1)
    def frame(self) -> pd.DataFrame:
        """
        Create the table of transactions from the current splits.
        """
        table = self._make_table_from_splits()
        count = self._compute_weights_for_payers(table)
        table["Payers"] = table["Payers"].apply(frozenset)
        table = pd.concat([table, count], axis=1)
        table = self._compute_amounts_for_payers(table)
        table = self._compute_pennies_for_payers(table)
        self._validate_table(table)
        return table

    def _make_table_from_splits(self) -> pd.DataFrame:
        """
        Turn the current splits into a table.
        """
        table = pd.DataFrame(data=[s.dict() for s in itertools.chain(*self.splits)])
        return table[table.Amount > BROKE].reset_index(drop=True)

    def _compute_weights_for_payers(self, table: pd.DataFrame) -> pd.DataFrame:
        """
        Compute weights for individual payees.
        """
        count = pd.DataFrame(iter(table.Payers.apply(Counter))).fillna(0).astype(int)
        total = count.sum(axis=1)
        for name in self.names:
            count[f"{name}.w"] = count[name] / total
        return count

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

        for payers, subset in table.groupby(by="Payers"):
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
        for payers, subset in table.groupby(by="Payers"):
            counts = subset.groupby("Who").Delta.sum()
            select = counts.index.intersection(payers)
            if not select.empty:
                for i1, v1 in counts.loc[select].items():
                    for i2, v2 in counts.loc[select].items():
                        if abs(v1 - v2).round(2) > PENNY:
                            raise ValueError(f"{v1} - {v2} > {PENNY}")

    def append(self, **kwargs):
        """
        Add a group of splits to the tracked splits.
        """
        tips = kwargs.pop("tips", {})
        taxes = kwargs.pop("taxes", {})
        self.splits.append(list(self._extract_tax_and_tip_for_split(split=Split(**kwargs), tips=tips, taxes=taxes)))

    def _extract_tax_and_tip_for_split(self, split: Split, tips: dict, taxes: dict) -> Iterator[Split]:
        """
        Explode split into multiple splits using tip and tax information.
        """
        if split.Rate > 0:
            raise NotImplementedError("can not set tip or tax rate of Split directly!")

        yield split.copy(update=dict(Group=len(self.splits)))

        for payee, rate in taxes.items():
            yield Split(
                Group=len(self.splits),
                Amount=(split.Amount * rate).round(2),
                Rate=rate,
                Payee=payee,
                Payer=split.Payer,
                Category=split.Category,
                Payers=split.Payers,
            )

        for amount in tips:
            if split.Amount > BROKE:
                amount = amount if isinstance(amount, Money) else Money(amount, USD)
                rate = amount.get_amount_in_sub_unit() / split.Amount.get_amount_in_sub_unit()
            else:
                rate = 0

            yield Split(
                Group=len(self.splits),
                Amount=amount,
                Rate=rate,
                Payee=split.Payee,
                Payer=split.Payer,
                Category=split.Category,
                Payers=split.Payers,
            )

    def __hash__(self):
        return id(self) + len(self.splits)


if __name__ == "__main__":
    import bany.core.config

    bany.core.config.pandas()
    splitter = Splitter()
    splitter.append(
        Amount=1.99,
        Payee="A",
        Category="Food",
        Payer="Ethan",
        Payers={"Adam": 1, "Ethan": 1},
        taxes=dict(SalesTax=0.06, DrinkTax=0.10, OtherTax=0.0),
    )

    splitter.append(
        Amount=1.99,
        Payee="A",
        Category="Food",
        Payer="Ethan",
        Payers={"Adam": 1, "Ethan": 1},
        taxes=dict(SalesTax=0.06, DrinkTax=0.10, OtherTax=0.0),
    )

    print(splitter.frame, "\n")
    columns = ["Amount", "Category", "Payee", *(f"{n}.$" for n in splitter.names)]
    print(splitter.frame.loc[:, columns].groupby(by=["Category", "Payee"], level=0).sum(numeric_only=False))
