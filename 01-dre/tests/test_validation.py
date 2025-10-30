import json
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from dre_core.validation import (
    DreValidationError,
    normalize_payload,
    validate_schema,
    compute_totals,
    compute_margins,
)  # noqa: E402


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


class NormalizePayloadTests(unittest.TestCase):
    def test_baseline_values_are_normalized(self) -> None:
        payload = load_fixture("dre-baseline")
        normalized = normalize_payload(payload)

        self.assertEqual(normalized["moeda"], "BRL")
        for entry in payload["porConta"]:
            norm_entry = next(item for item in normalized["porConta"] if item["id"] == entry["id"])
            self.assertIsInstance(norm_entry["valor"], (int, float))
            self.assertEqual(norm_entry["grupo"], entry["grupo"].lower())

    def test_string_currency_with_brazilian_format(self) -> None:
        payload = load_fixture("dre-baseline")
        payload["porConta"][0]["valor"] = "1.234,56"

        normalized = normalize_payload(payload)
        entry = next(item for item in normalized["porConta"] if item["id"] == payload["porConta"][0]["id"])
        self.assertAlmostEqual(entry["valor"], 1234.56, places=2)

    def test_group_sign_applied(self) -> None:
        payload = load_fixture("dre-baseline")
        payload["porConta"][0]["grupo"] = "RECEITA"
        payload["porConta"][0]["valor"] = -500
        payload["porConta"][1]["valor"] = "2.000,00"

        normalized = normalize_payload(payload)
        receita_entry = next(item for item in normalized["porConta"] if item["id"] == payload["porConta"][0]["id"])
        deducao_entry = next(item for item in normalized["porConta"] if item["id"] == payload["porConta"][1]["id"])

        self.assertGreater(receita_entry["valor"], 0)
        self.assertLess(deducao_entry["valor"], 0)

    def test_currency_code_enforced(self) -> None:
        payload = load_fixture("dre-baseline")
        payload["moeda"] = "brl"

        normalized = normalize_payload(payload)
        self.assertEqual(normalized["moeda"], "BRL")


class ComputeTotalsTests(unittest.TestCase):
    def test_totals_match_baseline(self) -> None:
        payload = normalize_payload(load_fixture("dre-baseline"))
        totals = compute_totals(payload["porConta"])
        expected = load_fixture("dre-baseline")["totais"]

        for key, value in expected.items():
            self.assertAlmostEqual(totals[key], value, places=2, msg=f"Mismatch on {key}")

    def test_marketing_and_admin_split(self) -> None:
        payload = {
            "schemaVersion": 1,
            "periodo": "2025-01",
            "moeda": "BRL",
            "totais": {},
            "porConta": [
                {"id": "E1", "nome": "Marketing Ads", "grupo": "despesa", "valor": "-1.200,00"},
                {"id": "E2", "nome": "Salários administrativos", "grupo": "despesa", "valor": -8000},
            ],
        }
        normalized = normalize_payload(payload)
        totals = compute_totals(normalized["porConta"])

        self.assertAlmostEqual(totals["despesasMarketing"], 1200)
        self.assertAlmostEqual(totals["despesasGeraisAdm"], 8000)
        self.assertAlmostEqual(totals["despesasOperacionais"], 9200)

    def test_other_income_flow(self) -> None:
        payload = normalize_payload(load_fixture("dre-baseline"))
        totals = compute_totals(payload["porConta"])

        self.assertAlmostEqual(
            totals["resultadoLiquido"],
            totals["resultadoAntesIR"] - load_fixture("dre-baseline")["totais"]["impostoRenda"],
            places=2,
        )


class ComputeMarginsTests(unittest.TestCase):
    def test_baseline_margins(self) -> None:
        payload = normalize_payload(load_fixture("dre-baseline"))
        totals = compute_totals(payload["porConta"])
        margins = compute_margins(totals)

        self.assertAlmostEqual(margins["margemBruta"], 0.5556, places=4)
        self.assertAlmostEqual(margins["margemOperacional"], 0.2778, places=4)
        self.assertAlmostEqual(margins["margemLiquida"], 0.2044, places=4)

    def test_zero_revenue_returns_zero_margins(self) -> None:
        totals = {
            "receitaBruta": 0,
            "receitaLiquida": 0,
            "lucroBruto": 1000,
            "resultadoOperacional": 500,
            "resultadoLiquido": 200,
        }

        margins = compute_margins(totals)
        self.assertEqual(margins["margemBruta"], 0.0)
        self.assertEqual(margins["margemOperacional"], 0.0)
        self.assertEqual(margins["margemLiquida"], 0.0)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
