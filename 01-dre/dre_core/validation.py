"""Schema validation utilities for dre-core."""

from __future__ import annotations

import re
from typing import Any, Iterable, Mapping, MutableMapping, Sequence


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
