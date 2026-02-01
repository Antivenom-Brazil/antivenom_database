# Sumário da Validação - Dataset Antivenom

**Dataset:** `antivenom_limpo4_corrigido.xlsx`  
**Executado em:** 2026-01-30 21:37:16  
**Tempo total:** 0.226s

---

## 📊 Visão Geral

### Status Global: ❌ **FALHOU**

- ✅ **6 checks passaram**
- ❌ **3 checks falharam**
- **Erros encontrados:** 3
- **Warnings encontrados:** 4
- **Informações:** 9

### Severidade dos Problemas

| Severidade | Quantidade |
|-----------|-----------|
| 🔴 BLOCKER | 0 |
| 🟠 MAJOR | 2 |
| 🟡 MINOR | 1 |

---

## 📈 Estatísticas do Dataset

- **Linhas:** 1.900
- **Colunas:** 15
- **Total de células:** 28.500
- **Células nulas:** 890 (3.12%)
- **Uso de memória:** 2.37 MB
- **Hash SHA256:** `c96a89e167ee572cfc2f9708509a140d92da115f21c66f25918cd821a3278391`

### Colunas Identificadas

```
Region, Federal_Un, FU, Municipio, Unidade de, Endereço, Telefone, 
CNES, Atendiment, Atendime_1, Lat, Lon, unknown, layer, path
```

---

## 🔍 Resultados Detalhados por Check

### 1. ✅ **Schema** - PASSOU

**Descrição:** Validação de estrutura e colunas do dataset

**Resultado:**
- 15 colunas encontradas (conforme esperado)
- INFO: Colunas não documentadas no manifesto

**Tempo:** 0.0018s

---

### 2. ✅ **Parsing** - PASSOU

**Descrição:** Validação de formatação e caracteres especiais

**Resultado:**
- ⚠️ WARNING: Whitespace extra detectado em 2 colunas
  - Coluna `CNES`: 10 células afetadas
  - Coluna `Atendiment`: 1 célula afetada
- ℹ️ INFO: Caracteres Unicode especiais detectados
  - `Endereço`: En-dash (–) em 37 células
  - `CNES`: Non-breaking space (NBSP) em 10 células
  - `Atendiment`: Non-breaking space (NBSP) em 1 célula

**Tempo:** 0.0163s

---

### 3. ❌ **Constraints** - FALHOU (MAJOR)

**Descrição:** Validação de formato e restrições de dados

**Problemas Críticos:**

#### 🟠 MAJOR: CNES Inválidos
- **Quantidade:** 55 registros (2.89% do dataset)
- **Padrão esperado:** 7 dígitos numéricos (`^\d{7}$`)
- **Linhas afetadas:** 36, 37, 38, 39, 40, 252, 327-330, 331-340, 379-384, 619-631, 804, 1147-1153, 1219-1221

**Exemplos de valores inválidos:**
```
- "937495" (6 dígitos)
- "Not informed1"
- "Not informed2"
- "Not informed3"
- "Not informed4"
```

#### 🟡 MINOR: Telefones Não-Padronizados
- **Quantidade:** 526 registros (27.68% do dataset)
- **Problema:** Formatos variados que não seguem padrão brasileiro
- **Linhas afetadas:** 6, 17-20, 23, 25, 33, 37-38, e outras 516

**Exemplos de telefones irregulares:**
```
- "(68) 99946-0048 / 99986 2932"
- "(82) 359-2450 e 3529-2488"
- "(82) 3315 1118"
- "(82) 98114-0105 / (82) 3421-9000"
- "0800 898 0000"
```

**Tempo:** 0.0035s

---

### 4. ✅ **Vocab** - PASSOU

**Descrição:** Validação de vocabulário controlado (Regiões e Estados)

**Resultado:**
- Todas as regiões e unidades federativas estão dentro do vocabulário controlado
- Nenhum erro ou warning

**Tempo:** 0.0038s

---

### 5. ✅ **Coherence** - PASSOU

**Descrição:** Validação de coerência interna entre colunas relacionadas

**Resultado:**
- ⚠️ WARNING: Contagem divergente entre colunas de atendimento
  - **Colunas:** `Atendiment` vs `Atendime_1`
  - **Registros afetados:** 6 linhas (0.32%)
  - **Linhas:** 1001, 1009, 1023, 1038, 1122, 1125

**Tempo:** 0.0889s

---

### 6. ❌ **Geospatial** - FALHOU (MINOR)

**Descrição:** Validação de coordenadas geográficas

**Problemas Identificados:**

#### 🟡 MINOR: Coordenada Fora dos Limites do Brasil
- **Quantidade:** 1 registro
- **Linha afetada:** 893
- **Coordenadas:** Latitude = -51.37°, Longitude = -11.67°
- **Problema:** Coordenadas invertidas ou erro de digitação

**Limites esperados do Brasil:**
```
Latitude: -33.75° a 5.27°
Longitude: -73.99° a -28.85°
```

#### ⚠️ WARNING: Outlier Geográfico
- **Linha:** 893 (mesma coordenada acima)

#### ℹ️ INFO: Coordenadas Duplicadas
- **Total:** 16 registros em 8 localizações únicas
- **Observação:** Pode indicar múltiplas unidades no mesmo endereço

**Tempo:** 0.0083s

---

### 7. ❌ **Uniqueness** - FALHOU (MAJOR)

**Descrição:** Validação de unicidade de chave primária (CNES)

**Problema Crítico:**

#### 🟠 MAJOR: CNES Duplicados
- **Total de duplicados:** 29 registros (1.53% do dataset)
- **Valores únicos duplicados:** 14 códigos CNES
- **Violação:** Chave primária deveria ser única

**Top 10 CNES Duplicados:**

| CNES | Ocorrências |
|------|------------|
| 2115786 | 3x |
| 2104067 | 3x |
| 2002302 | 3x |
| 3973077 | 2x |
| 2549158 | 2x |
| 2085496 | 2x |
| 0000086 | 2x |
| 3974286 | 2x |
| 2006324 | 2x |
| 6935427 | 2x |

**Impacto:** Impede uso do CNES como identificador único, pode causar conflitos em integrações

**Tempo:** 0.0066s

---

### 8. ✅ **Reproducibility** - PASSOU

**Descrição:** Verificação de reprodutibilidade e estabilidade do dataset

**Resultado:**

#### ℹ️ Hash do Dataset
- **Algoritmo:** SHA256
- **Hash:** `c96a89e167ee572cfc2f9708509a140d92da115f21c66f25918cd821a3278391`
- **Calculado em:** 2026-01-30T21:37:16.655136

#### ℹ️ Estatísticas de Estabilidade

**Distribuição de Tipos:**
- `object` (strings): 13 colunas
- `float64` (numéricos): 2 colunas (Lat, Lon)

**Uso de Memória por Coluna (Top 5):**
```
1. path: 453 KB
2. Atendime_1: 357 KB
3. Endereço: 243 KB
4. Atendiment: 213 KB
5. Unidade de: 204 KB
```

**Hashes por Coluna:** Gerados para detecção de mudanças futuras

**Tempo:** 0.0220s

---

### 9. ✅ **Performance** - PASSOU

**Descrição:** Avaliação de performance e eficiência

**Resultado:**

#### ℹ️ Uso de Memória
- **Total:** 2.37 MB
- **Dataset:** 1.900 linhas × 15 colunas = 28.500 células

#### ℹ️ Benchmark de Operações

| Operação | Tempo |
|----------|-------|
| Iterar 100 linhas | 0.0294s |
| Filtrar por região | 0.0005s |
| GroupBy por FU | 0.0003s |
| Ordenar primeira coluna | 0.0005s |

**Avaliação:** Performance adequada para o tamanho do dataset

**Tempo:** 0.0356s

---

## 🎯 Recomendações Prioritárias

### 🔴 Crítico (Resolver Antes da Produção)

1. **Corrigir CNES Duplicados**
   - 14 valores de CNES aparecem mais de uma vez
   - Investigar se são registros duplicados ou erros de digitação
   - CNES deve ser único para uso como chave primária

2. **Padronizar CNES Inválidos**
   - 55 registros com formato incorreto
   - Substituir "Not informed" por valores válidos ou NULL
   - Garantir 7 dígitos numéricos em todos os CNES

### 🟡 Importante (Melhorias de Qualidade)

3. **Corrigir Coordenada Invertida**
   - Linha 893 tem coordenadas fora do Brasil
   - Provavelmente latitude/longitude invertidas
   - Verificar fonte original e corrigir

4. **Padronizar Telefones**
   - 526 registros (27.7%) com formatos variados
   - Definir e aplicar padrão único: `(XX) XXXXX-XXXX`
   - Separar telefones múltiplos em campos diferentes

5. **Investigar Divergências de Atendimento**
   - 6 registros com contagens diferentes entre `Atendiment` e `Atendime_1`
   - Verificar qual coluna está correta
   - Sincronizar dados ou remover coluna redundante

### ⚪ Opcional (Melhorias Menores)

6. **Remover Whitespace Extra**
   - Limpar espaços desnecessários em CNES e Atendiment
   - Melhorará processamento e comparações

7. **Normalizar Unicode**
   - Substituir en-dash por hífen normal
   - Remover non-breaking spaces

---

## 📋 Resumo Executivo

O dataset **Antivenom_limpo4_corrigido.xlsx** apresenta **qualidade moderada**, com 3 problemas principais que impedem aprovação para uso em produção:

### Pontos Fortes ✅
- Estrutura e schema corretos (15 colunas)
- Vocabulário controlado validado
- Performance adequada (2.37 MB, operações < 0.03s)
- Reprodutibilidade garantida (hash SHA256 gerado)
- Coerência geral entre campos relacionados

### Pontos Críticos ❌
1. **CNES duplicados** (29 registros) - Impede uso como chave primária
2. **CNES inválidos** (55 registros) - Formato incorreto ou "Not informed"
3. **Coordenadas fora do Brasil** (1 registro) - Provável inversão lat/lon

### Próximos Passos

1. Corrigir duplicados de CNES (verificar fonte original)
2. Padronizar CNES inválidos (substituir ou remover)
3. Corrigir coordenada da linha 893
4. Re-executar validação para confirmar correções
5. Considerar padronização de telefones em fase posterior


---

## 📁 Arquivos Gerados

Esta validação gerou os seguintes relatórios detalhados em `reports/`:

- `validation_summary_20260130_213716.md` - Sumário da execução
- `validation_results_20260130_213716.json` - Resultados completos em JSON
- `check_schema_20260130_213716.md`
- `check_parsing_20260130_213716.md`
- `check_constraints_20260130_213716.md`
- `check_vocab_20260130_213716.md`
- `check_coherence_20260130_213716.md`
- `check_geospatial_20260130_213716.md`
- `check_uniqueness_20260130_213716.md`
- `check_reproducibility_20260130_213716.md`
- `check_perf_20260130_213716.md`

Para mais detalhes sobre qualquer check específico, consulte o arquivo Markdown correspondente.

---

*Para executar nova validação: `python run.py`*
