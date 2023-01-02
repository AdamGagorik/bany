"""
Parse an input file and create transactions in YNAB.
"""
import dataclasses
import pathlib
import re
from argparse import ArgumentParser
from argparse import Namespace

import pandas as pd
from moneyed import Money
from moneyed import USD

from bany.cmd.base import Controller as BaseController
from bany.cmd.extract.extractors import EXTRACTORS
from bany.cmd.extract.extractors.base import Extractor
from bany.core.logger import logger
from bany.core.logger import logline
from bany.core.settings import Settings
from bany.ynab.api import YNAB


DEFAULT_CONFIG: pathlib.Path = pathlib.Path.cwd().joinpath("config.yml")


@dataclasses.dataclass(frozen=True)
class Controller(BaseController):
    """
    A class to orchestrate the main logic.
    """

    environ: Settings
    options: Namespace

    @classmethod
    def add_args(cls, parser: ArgumentParser):
        group = parser.add_argument_group("extract")
        group.add_argument(
            default="pdf",
            dest="extractor",
            choices=list(EXTRACTORS.keys()),
            help="the extraction backend to use",
        )

        group.add_argument("--inp", required=True, type=pathlib.Path, help="the input file to parse")
        group.add_argument("--config", default=DEFAULT_CONFIG, type=pathlib.Path, help="the config file to use")

        group = parser.add_argument_group("ynab")
        group.add_argument("--upload", dest="upload", action="store_true", help="upload transactions to YNAB budget")

    def __call__(self):
        ynab = YNAB(environ=self.environ)

        if self.options.inp.is_dir():
            self.options.inp = self._get_latest_pdf(root=self.options.inp)

        logger.info("inp: %s", self.options.inp)

        extractor: Extractor = EXTRACTORS[self.options.extractor].create(ynab=ynab, config=self.options.config)
        extracted = pd.DataFrame(
            extract.dict() | dict(transaction=extract) for extract in extractor.extract(path=self.options.inp)
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

            if self.options.upload:
                for i, extract in extracted.iterrows():
                    transaction = extract.transaction
                    ynab.transact(transaction.budget_id, transaction)

    @staticmethod
    def _get_latest_pdf(root: pathlib.Path) -> pathlib.Path:
        for path in sorted(
            root.glob("*.pdf"), key=lambda p: [int(v) for v in re.findall(r"\d+", p.name)], reverse=True
        ):
            return path
        raise FileNotFoundError(root.joinpath("*.pdf"))
