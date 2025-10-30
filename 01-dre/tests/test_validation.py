import json
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from dre_core.validation import DreValidationError, validate_schema  # noqa: E402


FIXTURES_DIR = Path(__file__).resolve().parents[1]


def load_fixture(name: str) -> dict:
    path = FIXTURES_DIR / f"{name}.json"
    with path.open() as fh:
        return json.load(fh)


class ValidateSchemaTests(unittest.TestCase):
    def test_valid_payload_passes(self) -> None:
        payload = load_fixture("dre-baseline")
        result = validate_schema(payload)
        self.assertIsInstance(result, dict)
        self.assertEqual(payload["schemaVersion"], result["schemaVersion"])

    def test_missing_required_field(self) -> None:
        payload = load_fixture("dre-baseline")
        payload.pop("schemaVersion")

        with self.assertRaises(DreValidationError) as ctx:
            validate_schema(payload)

        self.assertIn("schemaVersion", str(ctx.exception))
        self.assertEqual(ctx.exception.details.get("path"), "schemaVersion")

    def test_por_conta_must_be_list(self) -> None:
        payload = load_fixture("dre-baseline")
        payload["porConta"] = "not-a-list"

        with self.assertRaises(DreValidationError) as ctx:
            validate_schema(payload)

        self.assertEqual(ctx.exception.details.get("path"), "porConta")

    def test_rejects_invalid_group(self) -> None:
        payload = load_fixture("dre-baseline")
        payload["porConta"][0]["grupo"] = "invalid"

        with self.assertRaises(DreValidationError) as ctx:
            validate_schema(payload)

        message = str(ctx.exception)
        self.assertIn("porConta[0].grupo", ctx.exception.details.get("path", ""))
        self.assertIn("grupo inválido", message.lower())
        self.assertIn("receita", ctx.exception.details.get("permitidos", []))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
