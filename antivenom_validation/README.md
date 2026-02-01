# Antivenom Validation Suite

Suite de validação de qualidade de dados para o dataset de localização de pontos de distribuição de antivenenos no Brasil.

---

## Visão Geral

Esta suite realiza validações automatizadas no arquivo `antivenom_limpo4_corrigido.xlsx`, que contém informações críticas sobre 1.900 unidades de saúde brasileiras que distribuem soros antiofídicos. O objetivo é garantir a **integridade**, **consistência** e **qualidade** dos dados antes de qualquer uso em produção ou análise.

O sistema executa **9 categorias de validação** diferentes, desde verificações básicas de estrutura até análises complexas de coerência geográfica e unicidade de chaves primárias.

> 📋 **SUMÁRIO DOS RESULTADOS:** Para uma visão consolidada das últimas validações executadas, consulte o arquivo [summary.md](summary.md), que contém um resumo executivo de todos os checks realizados.

---

## Como Executar

### Execução Rápida

```bash
cd antivenom_validation
python run.py ../antivenom_limpo4_corrigido.xlsx
```

### Pré-requisitos

```bash
pip install pandas openpyxl pyyaml
```

### Saída

A execução gera dois tipos de relatórios no diretório `reports/`:

1. **JSON completo**: `validation_report_YYYYMMDD_HHMMSS.json`
   - Estrutura completa com todos os detalhes técnicos
   - Útil para integração automatizada

2. **Markdown individuais**: Um arquivo `.md` por check + sumário geral
   - `validation_summary_YYYYMMDD_HHMMSS.md` - Visão geral
   - `check_schema_YYYYMMDD_HHMMSS.md` - Detalhes de cada validação
   - Formatação legível para revisão manual

---

## Categorias de Validação

### 1. Schema (Estrutura de Colunas)

**O que valida:**
- Verifica se todas as **15 colunas obrigatórias** estão presentes
- Confirma tipos de dados (texto, número, coordenadas)
- Identifica colunas extras não esperadas

**Saída de Sucesso:**
```
✅ schema - 0 erros
Todas as 15 colunas esperadas encontradas
```

**Saída de Erro:**
```
❌ schema - BLOCKER
Coluna obrigatória 'CNES' não encontrada
Ou: 3 colunas extras detectadas: ['campo_novo', 'teste', 'temp']
```

**Impacto:** Severidade BLOCKER - sem a estrutura correta, análises posteriores falharão.

---

### 2. Parsing (Formatação e Normalização)

**O que valida:**
- Remove espaços em branco extras no início/fim de campos
- Detecta caracteres Unicode problemáticos (tabulações invisíveis)
- Normaliza vírgulas decimais para ponto
- Identifica quebras de linha indevidas

**Saída de Sucesso:**
```
✅ parsing - 0 erros, 1 warning
Warning: 23 células com espaços extras removíveis
```

**Saída de Erro:**
```
❌ parsing - MINOR
145 registros com caracteres Unicode não esperados
Ex: Tabs invisíveis em campos de texto
```

**Impacto:** Severidade MINOR - problemas de formatação podem afetar buscas e comparações de texto.

---

### 3. Constraints (Restrições de Formato)

**O que valida:**

#### CNES (Cadastro Nacional de Estabelecimentos de Saúde)
- Formato: **7 dígitos numéricos** (ex: 2451573)
- Aceita valores especiais: "Not informed", "Not informed1-4"
- Remove tabs e espaços no início

#### Telefone
- Formato brasileiro: (XX) XXXXX-XXXX ou (XX) XXXX-XXXX
- Aceita variações com espaços, hífens, parênteses
- Permite múltiplos números separados por "/"

#### Missingness (Valores Nulos)
- Verifica taxa de campos vazios por coluna
- Lat/Lon: máximo 5% nulos
- CNES: máximo 1% nulo

**Saída de Sucesso:**
```
✅ constraints - 0 erros
CNES: 100% válidos (1.900 registros)
Telefone: 72% válidos (526 com formato não padrão)
```

**Saída de Erro:**
```
❌ constraints - MAJOR
55 CNES inválidos (2.9%):
  - "937495" (6 dígitos - falta 1)
  - "Not informed1" (valor especial com numeração)
  
Warning: 526 telefones com formato não padrão (27.7%)
  - "(68) 99946-0048 / 99986 2932" (múltiplos números)
  - "0800 898 0000" (número gratuito)
```

**Impacto:** Severidade MAJOR - CNES é chave primária, valores inválidos impedem cruzamento com outras bases.

---

### 4. Vocab (Vocabulário Controlado)

**O que valida:**
- **Region**: Apenas 5 valores permitidos (North, Northeast, Midwest, Southeast, South)
- **FU**: Apenas 27 siglas estaduais (AC, AL, AM, ..., TO)
- **Federal_Un**: Nomes completos dos 27 estados brasileiros
- Detecta erros de digitação com fuzzy matching

**Saída de Sucesso:**
```
✅ vocab - 0 erros
Region: 100% válidos (5 valores únicos)
FU: 100% válidos (27 valores únicos)
```

**Saída de Erro:**
```
❌ vocab - MAJOR
12 valores inválidos em 'Region':
  - "Nort" (sugestão: North - 89% similar)
  - "Centro-Oeste" (deve ser: Midwest)
  
8 valores inválidos em 'FU':
  - "SP " (espaço extra)
  - "sp" (caixa incorreta)
```

**Impacto:** Severidade MAJOR - vocabulário incorreto quebra agregações e filtros.

---

### 5. Coherence (Coerência Entre Campos)

**O que valida:**

#### FU ↔ Federal_Un
- Confirma que sigla do estado (FU) corresponde ao nome completo (Federal_Un)
- Ex: FU="SP" deve ter Federal_Un="São Paulo"

#### Region ↔ FU
- Verifica se estado pertence à região correta
- Ex: FU="SP" (São Paulo) deve estar em Region="Southeast"

#### Atendiment ↔ Atendime_1
- Compara quantidade de itens separados por vírgula em ambos os campos
- Devem ter o mesmo número de elementos

**Saída de Sucesso:**
```
✅ coherence - 0 erros, 1 warning
Warning: 3 registros com contagem diferente entre Atendiment/Atendime_1
```

**Saída de Erro:**
```
❌ coherence - MAJOR
45 inconsistências FU ↔ Federal_Un:
  - FU="RJ" mas Federal_Un="Rio Grande do Sul" (esperado: "Rio de Janeiro")
  
12 inconsistências Region ↔ FU:
  - FU="BA" (Bahia) em Region="South" (deveria ser "Northeast")
```

**Impacto:** Severidade MAJOR - inconsistências entre campos relacionados indicam erros de entrada de dados.

---

### 6. Geospatial (Validação Geográfica)

**O que valida:**

#### Bounding Box do Brasil
- Latitude: -33.75° a 5.27°
- Longitude: -73.99° a -32.39°
- Identifica coordenadas fora do território brasileiro

#### Valores Nulos
- Detecta registros sem coordenadas
- Calcula percentual de dados geográficos faltantes

#### Coordenadas Duplicadas
- Identifica múltiplas unidades no mesmo local exato
- Pode indicar erro de entrada ou filiais

#### Outliers Estatísticos
- Usa método IQR×3 para detectar coordenadas anômalas
- Identifica valores suspeitos como (0, 0) ou números inteiros exatos

**Saída de Sucesso:**
```
✅ geospatial - 0 erros, 2 info
Info: 16 coordenadas duplicadas em 8 localizações
Info: 0.5% coordenadas nulas (10 registros)
```

**Saída de Erro:**
```
❌ geospatial - MINOR
1 coordenada fora dos limites (linha 893):
  - Lat: -51.37° (limite: -33.75°)
  - Lon: -11.67° (limite: -32.39°)
  
Warning: 1 outlier detectado (linha 893)
```

**Impacto:** Severidade MINOR - coordenadas fora dos limites impedem visualização em mapas do Brasil.

---

### 7. Uniqueness (Unicidade de Chaves)

**O que valida:**
- **CNES deve ser único** - cada unidade tem um código exclusivo
- Detecta valores duplicados exatos
- Ignora espaços e caracteres invisíveis na comparação
- Identifica quantos registros compartilham o mesmo valor

**Saída de Sucesso:**
```
✅ uniqueness - 0 erros
CNES: 1.900 valores únicos (100%)
```

**Saída de Erro:**
```
❌ uniqueness - MAJOR
29 registros com CNES duplicados (1.53%):
  - "2115786" aparece 3 vezes (linhas 26, 499, 770)
  - "4156714" aparece 2 vezes (linhas 35, 729)
  - 12 outros valores duplicados
  
Total: 14 CNESs únicos com duplicatas
```

**Impacto:** Severidade MAJOR - CNES duplicado viola integridade referencial, pode indicar:
- Erro de importação (mesma unidade inserida múltiplas vezes)
- Filiais usando mesmo código (incorreto)
- Dados históricos não removidos

---

### 8. Reproducibility (Reprodutibilidade)

**O que valida:**
- Gera **hash SHA256** do dataset completo
- Compara com hash esperado (se configurado)
- Verifica número de linhas e colunas
- Calcula estatísticas de estabilidade (% nulos, tipos de dados)
- Permite rastreamento de mudanças entre versões

**Saída de Sucesso:**
```
✅ reproducibility - 0 erros, 1 info
Info: Hash do dataset: a3f52e8c...
  - 1.900 linhas × 15 colunas
  - 4.2% células nulas
  - 2.5 MB memória
```

**Saída de Erro:**
```
❌ reproducibility - BLOCKER
Hash não corresponde ao esperado:
  - Esperado: a3f52e8c1d4f...
  - Atual: b7e93d2a8c1e...
  
Ou: 1.950 linhas (esperado: 1.900) - 50 linhas extras
```

**Impacto:** Severidade INFO normalmente, BLOCKER se hash divergir - garante que análises usem sempre a mesma versão dos dados.

---

### 9. Perf (Performance)

**O que valida:**

#### Uso de Memória
- Mede RAM consumida pelo DataFrame
- Warning: > 100 MB
- Error: > 500 MB

#### Tamanho do Dataset
- Warning se > 100.000 linhas

#### Tempo de Operações
- Benchmarks de: filtragem, agrupamento, ordenação, iteração
- Identifica gargalos potenciais

**Saída de Sucesso:**
```
✅ perf - 0 erros, 3 info
Info: Uso de memória: 2.3 MB
Info: 1.900 linhas × 15 colunas (28.500 células)
Info: Benchmarks:
  - Filtro por região: 0.0012s
  - GroupBy FU: 0.0034s
  - Ordenação: 0.0089s
```

**Saída de Erro:**
```
❌ perf - MINOR
Uso de memória elevado: 120 MB (threshold: 100 MB)
  - Breakdown: coluna 'Endereço' = 45 MB (37%)
```

**Impacto:** Severidade MINOR - problemas de performance não afetam qualidade dos dados, mas podem causar lentidão em análises.

---

## Interpretação de Severidades

### 🔴 BLOCKER (Bloqueante)
- **Quando aparece:** Problemas críticos que impedem uso dos dados
- **Exemplos:** Colunas obrigatórias faltando, hash divergente
- **Ação requerida:** CORRIGIR IMEDIATAMENTE - dados não podem ser usados

### 🟠 MAJOR (Grave)
- **Quando aparece:** Erros sérios que comprometem análises
- **Exemplos:** CNES duplicados, inconsistências FU↔Estado, vocabulário inválido
- **Ação requerida:** Corrigir antes de análises críticas

### 🟡 MINOR (Menor)
- **Quando aparece:** Problemas que não impedem uso mas reduzem qualidade
- **Exemplos:** Telefones não padronizados, coordenadas fora dos limites
- **Ação requerida:** Corrigir quando possível, mas não bloqueia uso

### 🔵 INFO (Informativo)
- **Quando aparece:** Apenas informações sobre os dados
- **Exemplos:** Hash calculado, estatísticas de memória, coordenadas duplicadas
- **Ação requerida:** Nenhuma - apenas para conhecimento

---

## Exemplo de Relatório Real

```
==================================================
  RESULTADO: [FALHOU]
==================================================

[*] Resumo:
   * Linhas: 1,900
   * Colunas: 15
   * Checks executados: 9
   * Passou: 6
   * Falhou: 3

[*] Ocorrencias:
   * Erros: 3
   * Warnings: 4
   * Info: 9

[!] Por severidade:
   * BLOCKER: 0
   * MAJOR: 2
   * MINOR: 1

[*] Tempo: 0.200s
```

**Interpretação:** 
- Dataset tem problemas mas **nenhum bloqueante** (BLOCKER: 0)
- 2 problemas graves (MAJOR) precisam correção antes de uso crítico
- 1 problema menor (MINOR) pode ser tolerado
- Execução rápida (0.2s) permite validação contínua

**Checks que falharam:**
1. **constraints** (MAJOR): 55 CNES inválidos + 526 telefones não padronizados
2. **geospatial** (MINOR): 1 coordenada fora do Brasil
3. **uniqueness** (MAJOR): 29 registros com CNES duplicados

---

## Configuração Avançada

O arquivo `validation.manifest.yaml` permite customizar:

- **Thresholds**: Alterar limites de memória, % nulos aceitável, etc.
- **Vocabulário**: Adicionar novos valores válidos
- **Severidades**: Rebaixar MAJOR para MINOR se aceitável no seu contexto
- **Checks**: Desabilitar validações não aplicáveis

---

## Quando Executar

✅ **Antes de importar** dados em sistema de produção  
✅ **Após limpeza** manual ou automática de dados  
✅ **Periodicamente** (diário/semanal) para monitorar qualidade  
✅ **Antes de análises críticas** ou publicações  
✅ **Após mesclagem** de múltiplas fontes de dados  

---

## Suporte

Para dúvidas ou reportar bugs, consulte a documentação técnica em `MODELAGEM/` ou abra uma issue.
