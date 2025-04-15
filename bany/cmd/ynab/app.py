"""
Parse an input file and create transactions in YNAB.
"""

import logging

from bany.core.logger import logline
from bany.ynab.api import YNAB


def main(budget_name: str, show_categories: bool) -> None:
    ynab = YNAB()

    budget_id = ynab.budget_id(budget_name)
    if show_categories:
        categories = ynab.categories(budget_id=budget_id)
        for group in categories:
            logline(level=logging.INFO)
            for category in group["categories"]:
                name = f"{group['name']} : {category['name']}"
                category_id = ynab.category_id(budget_id=budget_id, name=name)
                logging.info("%s %s", category_id, name)
