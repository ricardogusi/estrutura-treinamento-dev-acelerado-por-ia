# Requirements — dre-core

Status: Draft (planning-only)

## Escopo

O módulo `dre-core` processa um `dre.json` offline (simulador) com a estrutura `{ schemaVersion, periodo, moeda, totais, porConta[] }`, valida o esquema, normaliza valores monetários, recalcula totais e margens e produz `dre_core.json` padronizado. Sem implementação agora — apenas especificação.

## Definições

- Grupo permitido: `receita`, `deducao`, `custo`, `despesa`, `outras`, `imposto`.
- Sinal por grupo:
  - `receita`: positivo
  - `deducao`, `custo`, `despesa`, `imposto`: negativo
  - `outras`: pode ser positivo ou negativo
- Classificação de despesas operacionais:
  - `despesasMarketing`: itens com `grupo=despesa` cujo `nome` contenha “marketing”, “ads”, “publicidade” ou “propaganda” (case-insensitive)
  - `despesasGeraisAdm`: demais itens com `grupo=despesa`

## Requisitos Funcionais (EARS)

RF-1 — Validação de Esquema
- Quando o módulo receber um `dre.json`, o sistema deverá validar a presença e tipo dos campos: `schemaVersion:int`, `periodo:string YYYY-MM`, `moeda:string (3 letras)`, `totais:obj`, `porConta:array`.
- E cada item de `porConta[]` deverá conter `id:string`, `nome:string`, `grupo:string (valor permitido)`, `valor:(number|string)`.
- E o sistema deverá rejeitar grupos não permitidos com erro 400 contendo mensagem e detalhes.

RF-2 — Normalização Monetária
- Quando `valor` for string (ex.: “1.234,56” ou “1,234.56”), o sistema deverá normalizar para número decimal, preservando o sinal.
- E o sistema deverá aplicar o sinal conforme o grupo (vide Definições), garantindo consistência interna para os cálculos.
- E `moeda` deverá ser normalizada para maiúsculas e validada com 3 caracteres.

RF-3 — Recalcular Totais (a partir de `porConta`)
- O sistema deverá recalcular, ignorando `totais` de entrada:
  - `receitaBruta` = soma de `receita`
  - `deducoes` = valor absoluto da soma de `deducao`
  - `receitaLiquida` = `receitaBruta` + soma(`deducao`)
  - `custoProdutosServicos` = abs(soma(`custo`))
  - `lucroBruto` = `receitaLiquida` + soma(`custo`)
  - `despesasMarketing` = soma absoluta de despesas classificadas como marketing
  - `despesasGeraisAdm` = soma absoluta de demais despesas
  - `despesasOperacionais` = `despesasMarketing` + `despesasGeraisAdm`
  - `resultadoOperacional` = `lucroBruto` − `despesasOperacionais`
  - `outrasReceitasDespesas` = soma(`outras`)
  - `resultadoAntesIR` = `resultadoOperacional` + `outrasReceitasDespesas`
  - `impostoRenda` = abs(soma(`imposto`))
  - `resultadoLiquido` = `resultadoAntesIR` + soma(`imposto`)

RF-4 — Cálculo de Margens
- O sistema deverá calcular:
  - `margemBruta` = `lucroBruto` / (`receitaLiquida` se > 0, senão `receitaBruta`)
  - `margemOperacional` = `resultadoOperacional` / `receitaLiquida`
  - `margemLiquida` = `resultadoLiquido` / `receitaLiquida`

RF-5 — Saída Padronizada (`dre_core.json`)
- O sistema deverá produzir JSON com:
  - `schemaVersion`, `periodo`, `moeda`
  - `totais` recalculados (valores numéricos normalizados)
  - `margens` conforme RF-4
  - `porConta` normalizado (valores como número)
- E deverá gravar por padrão ao lado do arquivo de entrada com nome `dre_core.json`.

RF-6 — Tratamento de Erros (400)
- Quando a entrada for inválida, o sistema deverá sinalizar erro 400 (mensagem clara + `details` com `path` ou contexto do campo).
- E o sistema deverá listar campos ausentes/tipos incorretos ou grupos inválidos.

RF-7 — Testes com Amostras
- O sistema deverá validar contra três amostras: `01-dre/dre-baseline.json`, `01-dre/dre-otimista.json`, `01-dre/dre-pessimista.json`, produzindo `totais` e `margens` consistentes.

## Requisitos Não Funcionais

RNF-1 — Precisão & Arredondamento
- Totais: serialização com 2 casas decimais, arredondamento half-up; inteiros quando aplicável.
- Margens: 4 casas decimais.

RNF-2 — Determinismo
- Processamento determinístico a partir de um mesmo `dre.json`.

RNF-3 — Offline
- Sem dependência de rede; I/O em arquivo local.

## Critérios de Aceite Globais

- Dado o `dre-baseline.json`, quando processado, então os `totais` resultantes devem igualar os valores esperados do arquivo base (recalculados por `porConta`) e `margens` devem ser coerentes com os totais.
- Idem para `dre-otimista.json` e `dre-pessimista.json`.
- Dado um `porConta` com grupo inválido, quando processado, então deve ocorrer erro 400 com mensagem e `details` apontando o campo inválido.
