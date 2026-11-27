import unittest
from service import export_cases

class ExistingChecks(unittest.TestCase):
    def test_single_tenant_happy_path(self):
        csv = export_cases([{"id": 1, "title": "A", "status": "open", "tenant": "a"}], "a")
        self.assertIn("A", csv)

if __name__ == "__main__":
    unittest.main()
