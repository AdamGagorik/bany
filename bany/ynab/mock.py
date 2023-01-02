import dataclasses

import responses
from pydantic import SecretStr
from requests import Response

from bany.core.settings import Settings
from bany.ynab.api import YNAB


@dataclasses.dataclass(frozen=True)
class MockYNAB(YNAB):
    """
    This class mocks the YNAB REST API during testing.
    """

    mockdata: dict = dataclasses.field(default_factory=dict)

    @classmethod
    def create(cls) -> YNAB:
        mock = cls(environ=Settings(YNAB_API_KEY=SecretStr("")))
        mock.mockdata.update(**mock_json_for_budgets(b0="b0_id"))
        mock.mockdata.update(**mock_json_for_payees("b0_id", p0="p0_id"))
        mock.mockdata.update(**mock_json_for_accounts("b0_id", a0="a0_id"))
        return mock

    def _make_request(self, method: str, endpoint: str, **kwargs) -> Response:
        with responses.RequestsMock() as mocker:
            mocker.add(
                method=method,
                url=self._make_url(endpoint),
                headers=self._make_headers(**kwargs.pop("headers", {})),
                **self.mockdata.get(endpoint, {}),
            )
            return super()._make_request(method, endpoint, **kwargs)

    def __hash__(self) -> int:
        return id(self)


def mock_json_for_budgets(**kwargs) -> dict:
    return {"budgets": {"json": {"data": {"budgets": [{"name": name, "id": id} for name, id in kwargs.items()]}}}}


def mock_json_for_payees(budget_id: str, **kwargs) -> dict:
    return {
        f"/budgets/{budget_id}/payees": {
            "json": {"data": {"payees": [{"name": name, "id": id} for name, id in kwargs.items()]}}
        }
    }


def mock_json_for_accounts(budget_id: str, **kwargs) -> dict:
    return {
        f"/budgets/{budget_id}/accounts": {
            "json": {"data": {"accounts": [{"name": name, "id": id} for name, id in kwargs.items()]}}
        }
    }
