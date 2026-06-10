# CAGED — Mercado de Trabalho Formal no Brasil

Dashboard interativo de análise do Novo CAGED (2020–2026), desenvolvido como trabalho final da disciplina **Estudos Avançados de Banco de Dados — PUC-Campinas**.

Explora 270 milhões de registros de admissões e desligamentos do emprego formal brasileiro, com foco no impacto da pandemia de COVID-19 e na recuperação do mercado de trabalho.

---

## Instalação

```bash
pip install py7zr pandas pyarrow requests scikit-learn dash dash-bootstrap-components plotly
```

## Como rodar

```bash
# Pipeline completo + dashboard (primeira execução)
py main.py

# Só o dashboard (dados já gerados)
py app.py
```

O pipeline verifica automaticamente quais etapas já foram concluídas e pula as que já possuem saída em disco.

---

## Estrutura de arquivos

### Pipeline de dados

| Arquivo | Descrição |
|---|---|
| `main.py` | Orquestra o pipeline completo em sequência e inicia o dashboard ao final |
| `coleta_caged.py` | Baixa os arquivos `.7z` mensais via FTP do MTE, extrai e converte para Parquet |
| `integracao.py` | Combina os Parquets mensais, enriquece com dados de municípios da API do IBGE e salva `caged_integrado.parquet` |
| `limpeza.py` | Remove registros inválidos (UF ausente, tipo de movimentação fora do domínio), padroniza strings e cria variáveis auxiliares (`trimestre`, `tipo_mov_label`) |
| `transformacao.py` | Cria variáveis derivadas (`fase_pandemia`, `periodo_sazonal`, `escolaridade_cod`, `ano_mes_int`), aplica normalização Min-Max e gera as agregações principais |
| `gerar_agregacoes.py` | Gera agregações extras para os dashboards: ranking de municípios, evolução setorial anual, heatmap mês×ano e crescimento % por setor |

### Utilitários

| Arquivo | Descrição |
|---|---|
| `corrigir_faltantes.py` | Verifica o FTP e baixa apenas os arquivos mensais que falharam na coleta original |
| `combinar_lotes.py` | Combina arquivos `lote_XX.parquet` gerados pela integração caso `integracao.py` tenha sido interrompido antes de finalizar |

### Dashboard

| Arquivo | Descrição |
|---|---|
| `app.py` | Inicializa a aplicação Dash com navegação entre as 4 páginas |
| `theme.py` | Paleta de cores, tamanhos de fonte e funções de layout compartilhadas por todos os dashboards |
| `pages/visao_geral.py` | Painel executivo: KPIs, tendência mensal, mapa coroplético por UF e saldo por setor e fase histórica |
| `pages/regional.py` | Análise regional interativa: mapa clicável por estado, ranking de UFs e Top 10 municípios criadores/destruidores de emprego |
| `pages/setorial.py` | Análise setorial: evolução anual por setor, crescimento % (2020 vs 2026) e heatmap de sazonalidade mês×ano |
| `pages/pandemia.py` | Zoom no impacto da pandemia: série 2019–2022, heatmap setor×fase histórica e comparação regional por fase |

---

## Dados

| Diretório / Arquivo | Conteúdo |
|---|---|
| `dados_parquet/` | Parquets mensais brutos do CAGED (um por mês, jan/2020–abr/2026) |
| `dados/caged_integrado.parquet` | Dataset integrado com dados do IBGE (~270M registros) |
| `dados/caged_limpo.parquet` | Dataset após limpeza e validação |
| `dados/caged_transformado.parquet` | Dataset com variáveis derivadas (~2.4 GB) |
| `dados/agg_*.parquet` | Tabelas pré-agregadas usadas pelos dashboards (< 200 linhas cada) |

**Fontes:**
- Novo CAGED — FTP público do Ministério do Trabalho e Emprego
- Municípios — API pública do IBGE

---

## Dashboards

- **Visão Geral** — painel executivo com KPIs e evolução temporal
- **Regional** — comparação entre estados e municípios com mapa interativo
- **Setorial** — desempenho por setor econômico (CNAE)
- **Pandemia** — análise do impacto do COVID-19 e da recuperação pós-2021

---

## Stack

Python 3.14 · pandas · pyarrow · py7zr · requests · scikit-learn · Dash · Plotly
