import dataclasses
import itertools
import posixpath
from json import JSONDecodeError

import requests
from pydantic import AnyUrl
from pydantic import parse_obj_as
from requests import HTTPError
from requests import Response

from bany.core.cache import cached
from bany.core.logger import logger
from bany.core.settings import Settings
from bany.ynab.transaction import Transaction
from bany.ynab.transaction import Transactions


KEYS = (
    lambda self: self.environ.YNAB_API_URL,
    lambda self: self.environ.YNAB_API_KEY.get_secret_value(),
)


@dataclasses.dataclass(frozen=True)
class YNAB:
    """
    This class can call the YNAB REST API.
    """

    environ: Settings

    def _make_url(self, *components: AnyUrl | str) -> AnyUrl:
        url = posixpath.join(*(str(c).lstrip("/") for c in itertools.chain((self.environ.YNAB_API_URL,), components)))
        return parse_obj_as(AnyUrl, url)

    def _make_headers(self, **kwargs):
        return dict(Authorization=f"Bearer {self.environ.YNAB_API_KEY.get_secret_value()}") | kwargs

    def _make_request(self, method: str, endpoint: str, **kwargs) -> Response:
        url = self._make_url(endpoint)
        headers = self._make_headers(**kwargs.pop("headers", {}))
        response = requests.request(method, url, headers=headers, **kwargs)
        try:
            response.raise_for_status()
            return response
        except HTTPError as e:
            logger.error(response.json())
            raise e from None

    @cached(*KEYS)
    def budgets(self) -> dict:
        response = self._make_request("GET", "budgets")
        return response.json().get("data").get("budgets")

    @cached(*KEYS)
    def budget_id(self, name: str) -> str:
        for budget in self.budgets():
            if budget["name"] == name:
                return budget["id"]

        raise RuntimeError(f"can not find budget id for {name}")

    @cached(*KEYS)
    def payees(self, budget_id: str) -> dict:
        response = self._make_request("GET", f"/budgets/{budget_id}/payees")
        return response.json().get("data").get("payees")

    @cached(*KEYS)
    def payee_id(self, budget_id: str, name: str) -> str:
        for payee in self.payees(budget_id):
            if payee["name"] == name:
                return payee["id"]

        raise RuntimeError(f"can not find payee id for {name}")

    @cached(*KEYS)
    def accounts(self, budget_id: str) -> dict:
        response = self._make_request("GET", f"/budgets/{budget_id}/accounts")
        try:
            return response.json().get("data").get("accounts")
        except JSONDecodeError:
            logger.exception(f"can not decode json for {response.url}!")
            return {}

    @cached(*KEYS)
    def account_id(self, budget_id: str, name: str) -> str:
        for account in self.accounts(budget_id):
            if account["name"] == name:
                return account["id"]

        raise RuntimeError(f"can not find account id for {name}")

    @cached(*KEYS)
    def categories(self, budget_id: str) -> dict:
        response = self._make_request("GET", f"/budgets/{budget_id}/categories")
        try:
            return response.json().get("data").get("category_groups")
        except JSONDecodeError:
            logger.exception(f"can not decode json for {response.url}!")
            return {}

    @cached(*KEYS)
    def category_id(self, budget_id: str, name: str) -> str:
        tokens = [token.strip() for token in name.partition(":")]
        group_, category_ = tokens[0], tokens[-1]
        for group in self.categories(budget_id):
            if group["name"] == group_:
                for category in group.get("categories"):
                    if category["name"] == category_:
                        return category["id"]

        raise RuntimeError(f"can not find category id for {name}")

    def transact(self, budget_id: str, *transactions: Transaction):
        transactions = Transactions.parse_obj({"transactions": transactions})
        return self._make_request(
            "POST",
            f"/budgets/{budget_id}/transactions",
            headers={"Content-type": "application/json"},
            data=transactions.json(exclude_none=True),
        )

    def __hash__(self) -> int:
        return id(self)
