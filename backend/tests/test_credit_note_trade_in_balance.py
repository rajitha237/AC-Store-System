import ast
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from types import SimpleNamespace


SOURCE = Path(__file__).resolve().parents[1] / "app/services/credit_note.py"


def load_calculations():
    tree = ast.parse(SOURCE.read_text())
    names = {
        "net_invoice_total",
        "invoice_outstanding",
        "invoice_overpayment",
    }
    nodes = [
        node for node in tree.body
        if isinstance(node, ast.FunctionDef)
        and node.name in names
    ]
    assert len(nodes) == 3

    def money(value):
        return Decimal(value).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

    namespace = {
        "Decimal": Decimal,
        "ZERO_2": Decimal("0.00"),
        "money": money,
        "SalesInvoice": SimpleNamespace,
    }
    exec(
        compile(ast.Module(body=nodes, type_ignores=[]), str(SOURCE), "exec"),
        namespace,
    )
    return namespace


def test_trade_in_invoice_balance():
    functions = load_calculations()
    invoice = SimpleNamespace(
        grand_total=Decimal("255000.00"),
        credited_amount=Decimal("0.00"),
        trade_in_amount=Decimal("45000.00"),
        paid_amount=Decimal("150000.00"),
    )

    assert functions["net_invoice_total"](invoice) == Decimal("210000.00")
    assert functions["invoice_outstanding"](invoice) == Decimal("60000.00")
    assert functions["invoice_overpayment"](invoice) == Decimal("0.00")


def test_trade_in_with_credit_note_and_overpayment():
    functions = load_calculations()
    invoice = SimpleNamespace(
        grand_total=Decimal("100000.00"),
        credited_amount=Decimal("10000.00"),
        trade_in_amount=Decimal("20000.00"),
        paid_amount=Decimal("80000.00"),
    )

    assert functions["net_invoice_total"](invoice) == Decimal("70000.00")
    assert functions["invoice_outstanding"](invoice) == Decimal("0.00")
    assert functions["invoice_overpayment"](invoice) == Decimal("10000.00")
