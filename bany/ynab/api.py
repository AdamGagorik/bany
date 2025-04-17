import dataclasses
import itertools
import posixpath
import re
from collections.abc import Generator
from json import JSONDecodeError

import requests
from pydantic import AnyUrl, TypeAdapter
from requests import HTTPError, Response

from bany.core.cache import cached
from bany.core.logger import logger
from bany.core.settings import Settings
from bany.ynab.transaction import ScheduledTransaction, Transaction, Transactions

KEYS = (
    lambda self: self.environ.YNAB_API_URL,
    lambda self: self.environ.YNAB_API_KEY.get_secret_value(),
)


@dataclasses.dataclass(frozen=True)
class YNAB:
    """
    This class can call the YNAB REST API.
    """

    environ: Settings = dataclasses.field(default_factory=Settings)

    def _make_url(self, *components: AnyUrl | str) -> AnyUrl:
        url = posixpath.join(*(str(c).lstrip("/") for c in itertools.chain((self.environ.YNAB_API_URL,), components)))
        return TypeAdapter(AnyUrl).validate_python(url)

    def _make_headers(self, **kwargs):
        return {"Authorization": f"Bearer {self.environ.YNAB_API_KEY.get_secret_value()}"} | kwargs

    def _make_request(self, method: str, endpoint: str, timeout: int | None = None, **kwargs) -> Response:
        url = self._make_url(endpoint)
        headers = self._make_headers(**kwargs.pop("headers", {}))
        response = requests.request(method, str(url), headers=headers, timeout=timeout, **kwargs)
        try:
            response.raise_for_status()
        except HTTPError as e:
            logger.error(response.json())
            raise e from None
        else:
            return response

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
        lut = self.category_lut(budget_id)
        return lut[self._norm_category_name(name)]

    @cached(*KEYS)
    def category_lut(self, budget_id: str) -> dict[str, str]:
        def _() -> Generator[tuple[str, str], None, None]:
            for group in self.categories(budget_id):
                for category in group.get("categories"):
                    name = f"{group['name']} : {category['name']}"
                    yield self._norm_category_name(name), category["id"]

        return dict(_())

    @staticmethod
    def _norm_category_name(name: str) -> str:
        return re.sub(r"\s+", "", name).strip().lower()

    def transact(self, budget_id: str, *transactions: Transaction):
        transactions = Transactions.parse_obj({"transactions": transactions})
        return self._make_request(
            "POST",
            f"/budgets/{budget_id}/transactions",
            headers={"Content-type": "application/json"},
            data=transactions.json(exclude_none=True, exclude={"frequency"}),
        )

    def scheduled_transact(self, budget_id: str, transaction: Transaction):
        scheduled_transaction = ScheduledTransaction.parse_obj({"scheduled_transaction": transaction})
        return self._make_request(
            "POST",
            f"/budgets/{budget_id}/scheduled_transactions",
            headers={"Content-type": "application/json"},
            data=scheduled_transaction.json(exclude_none=True),
        )

    def __hash__(self) -> int:
        return id(self)
