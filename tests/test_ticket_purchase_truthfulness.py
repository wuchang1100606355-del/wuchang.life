import ast
from pathlib import Path
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "Taiji_Odoo/addons/wuchang_core/controllers/ticket_controller.py"

class NoRuntimeAccess:
    def __getattr__(self, name):
        raise AssertionError("Ticket hold must not access members, balances or transactions: " + name)

def load_controller(path=SOURCE):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    tree.body = [node for node in tree.body if isinstance(node, ast.ClassDef)]
    http = SimpleNamespace(Controller=object, route=lambda *a, **k: lambda fn: fn)
    scope = {"http": http, "request": NoRuntimeAccess()}
    exec(compile(tree, str(path), "exec"), scope)
    return scope["TicketController"]()

class TicketPurchaseTruthfulnessTest(unittest.TestCase):
    def test_unbound_catalogue_never_fabricates_items_or_prices(self):
        result = load_controller().list_tickets()
        self.assertEqual(result["items"], [])
        self.assertFalse(result["purchase_enabled"])
        self.assertEqual(result["state"], "HOLD_TICKET_SALES_NOT_BOUND")

    def test_purchase_never_claims_unperformed_effect(self):
        for value in (None, 1, "invalid"):
            result = load_controller().buy_ticket(value)
            self.assertFalse(result["success"])
            self.assertFalse(result["payment_capture"])
            self.assertFalse(result["voucher_issued"])
            self.assertNotIn("new_balance", result)

if __name__ == "__main__":
    unittest.main()
