"""Schema validation utilities for dre-core."""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any, Mapping, Sequence


ALLOWED_GROUPS = {
    "receita",
    "deducao",
    "custo",
    "despesa",
    "outras",
    "imposto",
}

_PERIODO_PATTERN = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


class DreValidationError(ValueError):
    """Exception raised for invalid dre.json payloads."""

    status_code: int = 400

    def __init__(self, message: str, *, path: str | None = None, details: Mapping[str, Any] | None = None) -> None:
        super().__init__(message)
        extra = dict(details or {})
        if path and "path" not in extra:
            extra["path"] = path
        self.details = extra


def validate_schema(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    """Validate that the payload matches dre.json schema requirements."""

    if not isinstance(payload, Mapping):
        raise DreValidationError("Payload raiz deve ser um objeto JSON.", path="$")

    _require_field(payload, "schemaVersion", int)
    _require_field(payload, "periodo", str)
    _require_field(payload, "moeda", str)
    _require_field(payload, "totais", Mapping)
    _require_field(payload, "porConta", Sequence, path="porConta", allow_str=False)

    schema_version = payload["schemaVersion"]
    if isinstance(schema_version, bool) or not isinstance(schema_version, int) or schema_version < 1:
        raise DreValidationError("schemaVersion deve ser inteiro positivo.", path="schemaVersion")

    periodo = payload["periodo"]
    if not isinstance(periodo, str) or not _PERIODO_PATTERN.match(periodo):
        raise DreValidationError("periodo deve estar no formato YYYY-MM.", path="periodo")

    moeda = payload["moeda"]
    if not isinstance(moeda, str) or len(moeda.strip()) != 3:
        raise DreValidationError("moeda deve conter 3 letras (ISO 4217).", path="moeda")

    totais = payload["totais"]
    if not isinstance(totais, Mapping):
        raise DreValidationError("totais deve ser um objeto.", path="totais")

    por_conta = payload["porConta"]
    if not isinstance(por_conta, Sequence) or isinstance(por_conta, (str, bytes)):
        raise DreValidationError("porConta deve ser uma lista.", path="porConta")

    for idx, entry in enumerate(por_conta):
        _validate_entry(entry, idx)

    return payload


def normalize_payload(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    validated = validate_schema(payload)

    moneda = validated["moeda"].strip().upper()
    por_conta_normalized = []
    for idx, entry in enumerate(validated["porConta"]):
        grupo = entry["grupo"].strip().lower()
        valor = _normalize_value(entry["valor"], grupo, idx)
        por_conta_normalized.append(
            {
                "id": entry["id"].strip(),
                "nome": entry["nome"].strip(),
                "grupo": grupo,
                "valor": valor,
            }
        )

    return {
        "schemaVersion": validated["schemaVersion"],
        "periodo": validated["periodo"],
        "moeda": moneda,
        "totais": validated["totais"],
        "porConta": por_conta_normalized,
    }


def compute_totals(entries: Sequence[Mapping[str, Any]]) -> Mapping[str, float]:
    receita = _sum_group(entries, "receita")
    deducao = _sum_group(entries, "deducao")
    custo = _sum_group(entries, "custo")
    outras = _sum_group(entries, "outras")
    imposto = _sum_group(entries, "imposto")

    desp_marketing = _sum_operational(entries, marketing=True)
    desp_gerais = _sum_operational(entries, marketing=False)
    despesas_operacionais = desp_marketing + desp_gerais

    receita_bruta = receita
    deducoes = abs(deducao)
    receita_liquida = receita + deducao
    custo_produtos = abs(custo)
    lucro_bruto = receita_liquida + custo
    resultado_operacional = lucro_bruto - despesas_operacionais
    resultado_antes_ir = resultado_operacional + outras
    imposto_renda = abs(imposto)
    resultado_liquido = resultado_antes_ir + imposto

    return {
        "receitaBruta": float(receita_bruta),
        "deducoes": float(deducoes),
        "receitaLiquida": float(receita_liquida),
        "custoProdutosServicos": float(custo_produtos),
        "lucroBruto": float(lucro_bruto),
        "despesasMarketing": float(desp_marketing),
        "despesasGeraisAdm": float(desp_gerais),
        "despesasOperacionais": float(despesas_operacionais),
        "resultadoOperacional": float(resultado_operacional),
        "outrasReceitasDespesas": float(outras),
        "resultadoAntesIR": float(resultado_antes_ir),
        "impostoRenda": float(imposto_renda),
        "resultadoLiquido": float(resultado_liquido),
    }


def compute_margins(totals: Mapping[str, Any]) -> Mapping[str, float]:
    receita_liquida = _total_to_decimal(totals.get("receitaLiquida", 0))
    receita_bruta = _total_to_decimal(totals.get("receitaBruta", 0))
    lucro_bruto = _total_to_decimal(totals.get("lucroBruto", 0))
    resultado_operacional = _total_to_decimal(totals.get("resultadoOperacional", 0))
    resultado_liquido = _total_to_decimal(totals.get("resultadoLiquido", 0))

    base_bruta = receita_liquida if receita_liquida > 0 else receita_bruta

    margem_bruta = _safe_ratio(lucro_bruto, base_bruta)
    margem_operacional = _safe_ratio(resultado_operacional, receita_liquida)
    margem_liquida = _safe_ratio(resultado_liquido, receita_liquida)

    return {
        "margemBruta": _quantize_ratio(margem_bruta),
        "margemOperacional": _quantize_ratio(margem_operacional),
        "margemLiquida": _quantize_ratio(margem_liquida),
    }


def _require_field(
    payload: Mapping[str, Any],
    key: str,
    expected_type: type,
    *,
    path: str | None = None,
    allow_str: bool = True,
) -> None:
    if key not in payload:
        raise DreValidationError(f"Campo obrigatório ausente: {key}.", path=path or key)

    value = payload[key]
    if expected_type is Sequence:
        if not isinstance(value, Sequence) or (not allow_str and isinstance(value, (str, bytes))):
            raise DreValidationError(f"{key} deve ser uma lista.", path=path or key)
        return

    if expected_type is Mapping:
        if not isinstance(value, Mapping):
            raise DreValidationError(f"{key} deve ser um objeto.", path=path or key)
        return

    if not isinstance(value, expected_type) or (expected_type is int and isinstance(value, bool)):
        raise DreValidationError(f"{key} deve ser do tipo {expected_type.__name__}.", path=path or key)


def _validate_entry(entry: Any, index: int) -> None:
    path_prefix = f"porConta[{index}]"
    if not isinstance(entry, Mapping):
        raise DreValidationError("Cada item de porConta deve ser um objeto.", path=path_prefix)

    for field in ("id", "nome", "grupo", "valor"):
        if field not in entry:
            raise DreValidationError(
                f"Campo obrigatório ausente em porConta[{index}]: {field}.",
                path=f"{path_prefix}.{field}",
            )

    if not isinstance(entry["id"], str) or not entry["id"].strip():
        raise DreValidationError(
            "porConta.id deve ser string não vazia.",
            path=f"{path_prefix}.id",
        )

    if not isinstance(entry["nome"], str) or not entry["nome"].strip():
        raise DreValidationError(
            "porConta.nome deve ser string não vazia.",
            path=f"{path_prefix}.nome",
        )

    grupo = entry["grupo"]
    if not isinstance(grupo, str) or grupo.strip().lower() not in ALLOWED_GROUPS:
        raise DreValidationError(
            f"Grupo inválido em porConta[{index}]: {grupo}.",
            path=f"{path_prefix}.grupo",
            details={"permitidos": sorted(ALLOWED_GROUPS)},
        )

    valor = entry["valor"]
    if not isinstance(valor, (int, float, str)):
        raise DreValidationError(
            "porConta.valor deve ser number ou string.",
            path=f"{path_prefix}.valor",
        )


def _normalize_value(value: Any, group: str, index: int) -> float:
    decimal_value = _to_decimal(value, index)
    if group in {"receita"}:
        decimal_value = abs(decimal_value)
    elif group in {"deducao", "custo", "despesa", "imposto"}:
        decimal_value = -abs(decimal_value)
    return float(decimal_value)


def _quantize_ratio(value: Decimal) -> float:
    if value.is_nan():  # pragma: no cover - defensive, should not occur
        return 0.0
    quantized = value.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
    return float(quantized)


def _sum_group(entries: Sequence[Mapping[str, Any]], group: str) -> Decimal:
    total = Decimal("0")
    for entry in entries:
        if entry["grupo"] == group:
            total += Decimal(str(entry["valor"]))
    return total


def _sum_operational(entries: Sequence[Mapping[str, Any]], *, marketing: bool) -> Decimal:
    keywords = {"marketing", "ads", "publicidade", "propaganda"}
    total = Decimal("0")
    for entry in entries:
        if entry["grupo"] != "despesa":
            continue
        name = entry["nome"].lower()
        is_marketing = any(keyword in name for keyword in keywords)
        if is_marketing != marketing:
            continue
        total += abs(Decimal(str(entry["valor"])))
    return total


def _safe_ratio(numerator: Decimal, denominator: Decimal) -> Decimal:
    if denominator == 0:
        return Decimal("0")
    return numerator / denominator


def _total_to_decimal(value: Any) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _to_decimal(value: Any, index: int) -> Decimal:
    if isinstance(value, Decimal):
        return value
    if isinstance(value, (int, float)):
        return Decimal(str(value))
    if isinstance(value, str):
        cleaned = value.strip()
        if not cleaned:
            raise DreValidationError(
                "porConta.valor não pode ser vazio.",
                path=f"porConta[{index}].valor",
            )
        normalized = re.sub(r"[^0-9,\.-]", "", cleaned)
        if not normalized or normalized in {"-", "+", ".", ","}:
            raise DreValidationError(
                "porConta.valor inválido.",
                path=f"porConta[{index}].valor",
            )
        if "," in normalized and "." in normalized:
            if normalized.rfind(",") > normalized.rfind("."):
                normalized = normalized.replace(".", "")
                normalized = normalized.replace(",", ".")
            else:
                normalized = normalized.replace(",", "")
        elif "," in normalized:
            normalized = normalized.replace(".", "")
            normalized = normalized.replace(",", ".")
        else:
            normalized = normalized.replace(",", "")
        try:
            return Decimal(normalized)
        except InvalidOperation as exc:
            raise DreValidationError(
                "porConta.valor inválido.",
                path=f"porConta[{index}].valor",
            ) from exc
    raise DreValidationError(
        "porConta.valor tipo não suportado.",
        path=f"porConta[{index}].valor",
    )
