import pytest

from bany.ynab.api import YNAB
from bany.ynab.mock import MockYNAB


@pytest.fixture()
def ynab() -> YNAB:
    return MockYNAB.create()


def test_budgets(ynab: YNAB):
    assert ynab.budgets() == [{"id": "b0_id", "name": "b0"}]


def test_budget_id(ynab: YNAB):
    assert ynab.budget_id("b0") == "b0_id"


def test_budget_id_raises(ynab: YNAB):
    with pytest.raises(RuntimeError, match="can not find budget id for b1"):
        assert ynab.budget_id("b1")


def test_payees(ynab: YNAB):
    assert ynab.payees("b0_id") == [{"id": "p0_id", "name": "p0"}]


def test_payee_id(ynab: YNAB):
    assert ynab.payee_id("b0_id", "p0") == "p0_id"


def test_payee_id_raises(ynab: YNAB):
    with pytest.raises(RuntimeError, match="can not find payee id for p1"):
        assert ynab.payee_id("b0_id", "p1")


def test_accounts(ynab: YNAB):
    assert ynab.accounts("b0_id") == [{"id": "a0_id", "name": "a0"}]


def test_account_id(ynab: YNAB):
    assert ynab.account_id("b0_id", "a0") == "a0_id"


def test_account_id_raises(ynab: YNAB):
    with pytest.raises(RuntimeError, match="can not find account id for a1"):
        assert ynab.account_id("b0_id", "a1")
