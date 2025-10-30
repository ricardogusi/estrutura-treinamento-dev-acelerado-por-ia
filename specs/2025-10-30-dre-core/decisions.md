# decisions.md — dre-core

## [2025-10-30] Planejamento inicial (spec-only)
- Contexto: Criar especificação do módulo `dre-core` para processar `dre.json` offline e produzir `dre_core.json` padronizado, seguindo o arquivo base `01-dre/dre-baseline.json` e testando também com `dre-otimista.json` e `dre-pessimista.json`.
- Opções consideradas: (A) Implementação Node.js; (B) Implementação Python; (C) Outra linguagem.
- Decisão: Adiar escolha da linguagem (sem preferência do usuário). Foco: especificação completa e rastreável.
- Riscos e mitigação:
  - Classificação de despesas de marketing por keywords pode não cobrir casos futuros → Documentado; fácil ajustar lista de palavras‑chave.
  - Variações de formato monetário → Normalização robusta com suporte a “1.234,56” e “1,234.56”.
  - Diferenças de arredondamento → Regras explícitas: half‑up; 2 casas (totais), 4 casas (margens).
- Gate aplicado: Gate 0–4 concluídos (documentação). Gate 5 pendente de GO do usuário (ready-to-build).
- Confidence: 92% (requisitos claros; implementação direta; linguagem ainda a escolher).
- Próximos passos: Aguardar GO para implementar conforme `tasks.md`.

## Outputs da Fase 0–4
- Resumo das decisões: Linguagem adiada; regras de validação, normalização, totais e margens definidas; classificação de marketing por keywords.
- Confidence atualizado: 92%
- Artefatos atualizados: `requirements.md`, `design.md`, `tasks.md` criados.
- Lacunas: Escolha de linguagem/stack na hora da implementação.

## Go/No‑Go (Fase 5)
- Status: No‑Go (aguardando aprovação do usuário para implementar).

## [2025-10-30] Execução Tarefa 1 — Validação de esquema
- Contexto: Implementar validação de esquema para `dre.json` seguindo Tarefa 1 (RF-1, RF-6).
- Ações: Criados testes `01-dre/tests/test_validation.py` (unittest) antes do código; implementado módulo `dre_core.validation` com `validate_schema` e `DreValidationError` (status_code=400, path e details).
- Resultados: Testes passam (`python3 -m unittest discover -s 01-dre/tests`). Task 1 marcada como concluída em `tasks.md`.
- Riscos: Dependência de futuras normalizações (Tarefa 2) — função hoje retorna payload bruto; ajustes poderão ser necessários.
- Confidence: 90% para Task 1 (escopo atendido, aguardando próximas tarefas para integração completa).

## [2025-10-30] Execução Tarefa 2 — Normalização monetária e moeda
- Contexto: Implementar normalização de valores monetários e moeda conforme Tarefa 2 (RF-2, RNF-1).
- Ações: Ampliados testes `NormalizePayloadTests` cobrindo formatação brasileira, sinais por grupo e uppercase de moeda; implementado `normalize_payload` no módulo `dre_core.validation`, com parsing decimal resiliente e aplicação de sinais (receita positivo; deducao/custo/despesa/imposto negativo).
- Resultados: suíte `python3 -m unittest discover -s 01-dre/tests` aprovada; Task 2 marcada como concluída.
- Riscos: Conversão retorna `float`; etapas futuras podem optar por `Decimal` se necessário para maior precisão antes da serialização.
- Confidence: 90% (normalização atende requisitos; ajustes posteriores podem ocorrer durante cálculo de totais/margens).

## [2025-10-30] Execução Tarefa 3 — Recalcular totais
- Contexto: Recalcular todos os totais apenas a partir de `porConta`, incluindo split de despesas marketing vs gerais (RF-3, RNF-2).
- Ações: Estendidos testes (`ComputeTotalsTests`) comparando com `dre-baseline/otimista/pessimista` e cobrindo classificação de despesas; implementado `compute_totals` em `dre_core.validation` com somatórios por grupo e funções auxiliares (`_sum_group`, `_sum_operational`).
- Resultados: `python3 -m unittest discover -s 01-dre/tests` passou (11 testes); validação manual dos três cenários retorna totais idênticos aos esperados.
- Riscos: Totais retornam `float`; manter atenção na etapa de serialização para garantir arredondamento conforme RNF-1.
- Confidence: 91% (fluxo confirmado com amostras; dependerá de integração com margens/serialização para completar pipeline).

## [2025-10-30] Execução Tarefa 4 — Cálculo de margens
- Contexto: Calcular margens bruta, operacional e líquida com arredondamento e proteção a divisões por zero (RF-4, RNF-1).
- Ações: Novos testes `ComputeMarginsTests` cobrindo cenário baseline e receita zero; implementado `compute_margins` com `Decimal`, fallback para receita bruta quando receita líquida ≤ 0 e quantização half-up em 4 casas; helpers `_safe_ratio`, `_quantize_ratio`, `_total_to_decimal` adicionados.
- Resultados: Suíte `python3 -m unittest discover -s 01-dre/tests` (13 testes) passando; margens baseline batendo (0.5556, 0.2778, 0.2044).
- Riscos: Margens retornadas como float pós-quantização; manter consistência na serialização para evitar perdas futuramente.
- Confidence: 91% (cálculo estável; observar impactos quando serialização for implementada).

## [2025-10-30] Execução Tarefa 5 — Serialização padronizada
- Contexto: Consolidar pipeline completo produzindo `dre_core.json` padrão com totais recalculados, margens e dados normalizados (RF-5, RNF-1, RNF-3).
- Ações: Adicionados testes (`ProcessDreTests`) validando estrutura retornada e gravação em arquivo temporário; implementados `process_dre` e `save_dre_core` orquestrando normalização, totais, margens, formatação de moeda (2 casas) e margens (4 casas), além de salvamento default `dre_core.json`.
- Resultados: `python3 -m unittest discover -s 01-dre/tests` (15 testes) passando; serialização gera valores idênticos aos esperados nas amostras.
- Riscos: Saída utiliza floats para valores não inteiros após quantização; precisa alinhar com consumidores se exigirem strings formatadas.
- Confidence: 92% (pipeline pronto para Task 6 – erros claros já implementados nas etapas anteriores).

## [2025-10-30] Execução Tarefa 6 — Erros claros (400)
- Contexto: Garantir mensagens claras, `status_code=400` e `details.path` para entradas inválidas (RF-6).
- Ações: Novos testes (`ProcessDreTests` e `DreValidationErrorTests`) cobrindo grupo inválido, arquivo inexistente, JSON inválido e verificação explícita de `status_code`; ajustes em `DreValidationError` e `_load_payload` para incluir `status_code` e `path` nas exceções.
- Resultados: `python3 -m unittest discover -s 01-dre/tests` (19 testes) todos verdes; mensagens de erro incluem `path` e mantêm status 400.
- Riscos: Mensagens permanecem simples; se consumidores desejarem internacionalização ou códigos específicos por causa, futura extensão pode ser necessária.
- Confidence: 93% (cobertura completa de cenários críticos de erro; dependências consolidadas).

## [2025-10-30] Execução Tarefa 7 — Testes com amostras
- Contexto: Validar pipeline completo contra as três amostras oficiais (RF-7, RNF-2).
- Ações: Criada suíte `IntegrationSamplesTests` que processa `dre-baseline`, `dre-otimista` e `dre-pessimista`, comparando `totais`, `margens` e estrutura de `porConta` com os esperados.
- Resultados: `python3 -m unittest discover -s 01-dre/tests` (20 testes) aprovado, confirmando consistência entre amostras e saída padrão.
- Riscos: Nenhum adicional identificado; cobertura satisfatória para cenários fornecidos.
- Confidence: 94% (pipeline completo e validado).
