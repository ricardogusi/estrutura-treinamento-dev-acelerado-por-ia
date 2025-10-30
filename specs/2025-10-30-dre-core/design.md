# Design — dre-core

Status: Draft (planning-only)

## Contexto

Processamento offline de um arquivo `dre.json` gerado pelo simulador, com validação de esquema, normalização de valores monetários, recálculo de totais e margens e emissão de `dre_core.json` padronizado.

## C4 — Container

```mermaid
C4Context
    title DRE Core — Contexto
    Person(usuario, "Usuário/Simulador")
    System(drecore, "dre-core", "Módulo offline de processamento DRE")
    System_Ext(fs, "File System", "Entrada/saída JSON")

    Rel(usuario, drecore, "Fornece dre.json")
    Rel(drecore, fs, "Lê/Escreve dre.json/dre_core.json")
```

## C4 — Componentes (dentro do Container `dre-core`)

```mermaid
C4Container
    title DRE Core — Componentes
    Container_Boundary(c1, "dre-core") {
      Component(loader, "Loader", "I/O", "Abre e lê JSON")
      Component(validator, "Validator", "Schema/Types", "Checagem de campos e grupos")
      Component(normalizer, "Normalizer", "Currency/Signs", "Normaliza moeda/valor e sinais por grupo")
      Component(aggregator, "Aggregator", "Totals", "Recalcula totais a partir de porConta")
      Component(margins, "Margins", "Ratios", "Calcula margens bruta/operacional/líquida")
      Component(serializer, "Serializer", "I/O", "Emite dre_core.json padronizado")
      Component(errors, "Error Handler", "Errors", "Erros 400 com detalhes")
    }

    Rel(loader, validator, "fornece payload para validação")
    Rel(validator, normalizer, "payload válido")
    Rel(normalizer, aggregator, "entradas normalizadas")
    Rel(aggregator, margins, "totais")
    Rel(margins, serializer, "totais + margens + porConta")
```

## Sequências

Happy path — processar DRE

```mermaid
sequenceDiagram
    participant U as Usuário/Simulador
    participant L as Loader
    participant V as Validator
    participant N as Normalizer
    participant A as Aggregator
    participant M as Margins
    participant S as Serializer

    U->>L: abrir caminho para dre.json
    L->>V: payload (objeto JSON)
    V-->>U: erro 400 (se inválido)
    V->>N: payload validado
    N->>A: porConta normalizado (números + sinais)
    A->>M: totais recalculados
    M->>S: totais + margens + porConta
    S-->>U: grava dre_core.json
```

Invalid input — erro claro (400)

```mermaid
sequenceDiagram
    participant U as Usuário
    participant L as Loader
    participant V as Validator

    U->>L: carregar dre.json
    L->>V: payload
    V-->>U: DreValidationError (400) { message, details.path }
```

## Modelo de Dados (resumo)

Entrada (simulador):
- `schemaVersion:int`, `periodo:YYYY-MM`, `moeda:ISO-4217`, `totais:obj`, `porConta:[{id, nome, grupo, valor}]`

Saída (`dre_core.json`):
- Mesmo cabeçalho (`schemaVersion`, `periodo`, `moeda`)
- `porConta` com `valor:number`
- `totais` recalculados conforme regras (ver requirements)
- `margens`: `margemBruta`, `margemOperacional`, `margemLiquida`

## Regras notáveis

- Classificação de despesas em marketing por keywords no `nome` (case-insensitive): “marketing”, “ads”, “publicidade”, “propaganda”.
- Arredondamento: totais em 2 casas (half-up), margens em 4 casas.
- Divisão por zero em margens retorna 0.
