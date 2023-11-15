"""
Parse an input file and create transactions in YNAB.
"""
import pathlib
import re
from pathlib import Path

import pandas as pd
from moneyed import Money
from moneyed import USD

from bany.cmd.extract.extractors import EXTRACTORS
from bany.cmd.extract.extractors.base import Extractor
from bany.core.logger import logger
from bany.core.logger import logline
from bany.ynab.api import YNAB


def main(extractor: str, inp: Path, config: Path, upload: bool) -> None:
    ynab = YNAB()

    if inp.is_dir():
        inp = _get_latest_pdf(root=inp)

    logger.info("inp: %s", inp)

    extractor: Extractor = EXTRACTORS[extractor].create(ynab=ynab, config=config)
    extracted = pd.DataFrame(
        extract.model_dump() | dict(transaction=extract) for extract in extractor.extract(path=inp)
    )

    if extracted.empty:
        logger.error("no extracted found in PDF")
    else:
        logline()
        excluded = {"transaction", "account_id", "budget_id", "category_id", "import_id"}
        logger.info("extracted:\n%s", extracted.loc[:, ~extracted.columns.isin(excluded)])

        logline()
        logger.info("%-9s : %12s", "TOTAL [+]", Money(extracted[extracted.amount > 0].amount.sum() / 1000, USD))
        logger.info("%-9s : %12s", "TOTAL [-]", Money(extracted[extracted.amount < 0].amount.sum() / 1000, USD))
        logger.info("%-9s : %12s", "TOTAL", Money(extracted.amount.sum() / 1000, USD))

        if upload:
            for i, extract in extracted.iterrows():
                transaction = extract.transaction
                ynab.transact(transaction.budget_id, transaction)


def _get_latest_pdf(root: pathlib.Path) -> pathlib.Path:
    for path in sorted(root.glob("*.pdf"), key=lambda p: [int(v) for v in re.findall(r"\d+", p.name)], reverse=True):
        return path
    raise FileNotFoundError(root.joinpath("*.pdf"))
