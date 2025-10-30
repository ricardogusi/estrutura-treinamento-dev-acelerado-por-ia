"""CLI para processar arquivos dre.json usando o módulo dre-core."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from dre_core import DreValidationError, process_dre, save_dre_core


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Processa um dre.json e produz dre_core.json com totais/margens recalculados.",
    )
    parser.add_argument("input", type=Path, help="Caminho para o dre.json gerado pelo simulador")
    parser.add_argument(
        "--output",
        type=Path,
        help="Caminho opcional para salvar o dre_core.json (default: mesmo diretório do input)",
    )
    parser.add_argument(
        "--print",
        dest="should_print",
        action="store_true",
        help="Exibe o JSON processado no stdout além de salvar o arquivo",
    )
    parser.add_argument(
        "--indent",
        type=int,
        default=2,
        help="Indentação para salvar/exibir JSON (default: 2). Use 0 para JSON compacto.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    try:
        processed = process_dre(args.input)
        output_path = save_dre_core(args.input, args.output, indent=args.indent)
    except DreValidationError as exc:
        message = str(exc) or "Entrada inválida"
        details = exc.details or {}
        print(f"Erro 400: {message}", file=sys.stderr)
        if details:
            print(f"Detalhes: {json.dumps(details, ensure_ascii=False)}", file=sys.stderr)
        return 1

    if args.should_print:
        json.dump(processed, sys.stdout, indent=args.indent, ensure_ascii=False)
        if args.indent:
            sys.stdout.write("\n")

    print(f"Arquivo gerado em: {output_path}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
