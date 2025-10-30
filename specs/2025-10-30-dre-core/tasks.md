[x] 1. Especificar e validar esquema do dre.json
- Complexidade: medium
- Risco: low
- Passo 1: Definir campos obrigatórios e tipos (schemaVersion, periodo YYYY-MM, moeda ISO-4217, totais obj, porConta[])
- Passo 2: Definir conjunto de grupos permitidos e validações por item
- Passo 3: Padronizar mensagens de erro com detalhes (path)
- Critérios de Aceite:
  - Payload válido passa sem erros
  - Grupo inválido gera erro 400 com mensagem e details
- _Requirements: RF-1, RF-6_

[x] 2. Normalização monetária e moeda
- Complexidade: medium
- Risco: low
- Passo 1: Converter strings monetárias (“1.234,56”/“1,234.56”) em número decimal
- Passo 2: Normalizar sinais por grupo (positivo/negativo)
- Passo 3: Normalizar `moeda` para maiúsculas e validar 3 caracteres
- Critérios de Aceite:
  - Valores string e numéricos resultam em números consistentes
  - Sinais aplicados conforme grupo
- _Requirements: RF-2, RNF-1_

[ ] 3. Recalcular totais a partir de porConta
- Complexidade: medium
- Risco: medium
- Passo 1: Implementar somatórios por grupo conforme regras
- Passo 2: Classificar despesas em marketing (keywords) vs gerais/adm
- Passo 3: Consolidar objeto `totais` conforme fórmulas
- Critérios de Aceite:
  - `dre-baseline.json` gera totais iguais aos esperados
  - Idem para otimista e pessimista
- _Requirements: RF-3, RNF-2_

[ ] 4. Cálculo de margens (bruta/operacional/líquida)
- Complexidade: low
- Risco: low
- Passo 1: Implementar divisões com proteção a divisor zero
- Passo 2: Padronizar arredondamento (4 casas)
- Critérios de Aceite:
  - Margens coerentes com os totais
- _Requirements: RF-4, RNF-1_

[ ] 5. Serialização de saída (dre_core.json)
- Complexidade: low
- Risco: low
- Passo 1: Montar estrutura padronizada com `totais`, `margens` e `porConta` normalizado
- Passo 2: Gravar arquivo no mesmo diretório de entrada, nome `dre_core.json`
- Passo 3: Garantir números com 2 casas (totais) e 4 casas (margens)
- Critérios de Aceite:
  - Arquivo gerado com chaves e formatos definidos
- _Requirements: RF-5, RNF-1, RNF-3_

[ ] 6. Tratamento de erros claros (400)
- Complexidade: low
- Risco: low
- Passo 1: Implementar exceção de validação com `status_code=400`
- Passo 2: Incluir `message` e `details.path` sempre que possível
- Critérios de Aceite:
  - Inputs ruins retornam 400 com causa explícita
- _Requirements: RF-6_

[ ] 7. Testes com amostras (baseline/otimista/pessimista)
- Complexidade: medium
- Risco: low
- Passo 1: Executar processamento das três amostras em `01-dre/`
- Passo 2: Validar igualdade dos totais com os esperados (derivados de `porConta`)
- Passo 3: Validar margens coerentes
- Critérios de Aceite:
  - Três amostras passam com resultados consistentes
- _Requirements: RF-7, RNF-2_
