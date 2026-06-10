import pandas as pd
import numpy as np
import pyarrow.parquet as pq
import pyarrow as pa
from pathlib import Path
from sklearn.preprocessing import MinMaxScaler

PASTA_DADOS = Path(__file__).parent / "dados"
ENTRADA     = PASTA_DADOS / "caged_limpo.parquet"
SAIDA       = PASTA_DADOS / "caged_transformado.parquet"

print("Lendo metadados...")
parquet_file = pq.ParquetFile(ENTRADA)
total_rows   = parquet_file.metadata.num_rows
print(f"Total de registros: {total_rows:,}")

print("\nColetando amostra para calibrar transformações...")

amostra_lotes = []
for i, batch in enumerate(parquet_file.iter_batches(batch_size=5_000_000)):
    if i == 0:
        df_amostra = batch.to_pandas()
        amostra_lotes.append(df_amostra.sample(min(100_000, len(df_amostra)), random_state=42))
        break

amostra = pd.concat(amostra_lotes, ignore_index=True)
print(f"  Amostra: {len(amostra):,} registros")
print(f"  Colunas: {list(amostra.columns)}")

print(f"\n{'='*60}")
print("ETAPA 1 — Codificação de variáveis categóricas")
print(f"{'='*60}")

ORDEM_ESCOLARIDADE = {
    "Analfabeto": 0,
    "Fundamental incompleto": 1,
    "Fundamental completo": 2,
    "Médio incompleto": 3,
    "Médio completo": 4,
    "Superior incompleto": 5,
    "Superior completo": 6,
    "Mestrado": 7,
    "Doutorado": 8,
    "Não informado": -1,
}
print("\n  Escolaridade → LabelEncoder (ordinal)")
print("  Justificativa: variável ordinal — ordem entre categorias é significativa")
print("  Analfabeto(0) < Fund.Inc.(1) < ... < Doutorado(8)")

MAP_REGIAO_COD = {
    "Norte": 1, "Nordeste": 2, "Sudeste": 3, "Sul": 4, "Centro-Oeste": 5
}
print("\n  Região → código numérico (nominal, para agregações)")
print("  Justificativa: sem ordem natural entre regiões")

MAP_SEXO_COD = {"Masculino": 0, "Feminino": 1, "Não identificado": -1}
print("\n  Sexo → binário (0/1)")

print(f"\n{'='*60}")
print("ETAPA 2 — Discretização por período sazonal")
print(f"{'='*60}")

MAP_PERIODO = {
    1: "Jan-Mar", 2: "Jan-Mar", 3: "Jan-Mar",
    4: "Abr-Jun", 5: "Abr-Jun", 6: "Abr-Jun",
    7: "Jul-Set", 8: "Jul-Set", 9: "Jul-Set",
    10: "Out-Dez", 11: "Out-Dez", 12: "Out-Dez",
}
print("  Mês → período trimestral (equal width — 3 meses por faixa)")
print("  Justificativa: capturar sazonalidade do emprego formal")
print("  Jan-Mar: início de ano (baixo), Out-Dez: fim de ano (alto)")

print(f"\n{'='*60}")
print("ETAPA 3 — Normalização Min-Max (saldo por UF)")
print(f"{'='*60}")
print("  Variável: saldo acumulado por UF")
print("  Método: Min-Max → [0, 1]")
print("  Justificativa: permite comparação entre UFs de tamanhos")
print("  populacionais muito diferentes (SP vs AC, por exemplo)")
print("  Fórmula: x' = (x - x_min) / (x_max - x_min)")

saldo_uf_amostra = amostra.groupby("sigla_uf")["saldo"].sum().reset_index()
scaler = MinMaxScaler()
saldo_uf_amostra["saldo_normalizado"] = scaler.fit_transform(
    saldo_uf_amostra[["saldo"]]
)
print(f"\n  Exemplo (amostra de {len(amostra):,} registros):")
print(f"  {'UF':<6} {'Saldo':>12} {'Normalizado':>12}")
print(f"  {'-'*32}")
for _, row in saldo_uf_amostra.nlargest(3, "saldo").iterrows():
    print(f"  {row['sigla_uf']:<6} {row['saldo']:>12,.0f} {row['saldo_normalizado']:>12.4f}")
for _, row in saldo_uf_amostra.nsmallest(3, "saldo").iterrows():
    print(f"  {row['sigla_uf']:<6} {row['saldo']:>12,.0f} {row['saldo_normalizado']:>12.4f}")

print(f"\n{'='*60}")
print("ETAPA 4 — Criação de variáveis derivadas")
print(f"{'='*60}")
print("  1. saldo_acumulado_ano    → saldo acumulado por UF + ano")
print("  2. mes_relativo           → mês dentro do período pandemia/pós")
print("  3. fase_pandemia          → categoriza o período histórico")
print("  4. periodo_sazonal        → trimestre semântico (Jan-Mar etc)")
print("  5. escolaridade_cod       → LabelEncoder da escolaridade")
print("  6. regiao_cod             → código numérico da região")
print("  7. sexo_cod               → binário 0/1")

print("\n  Fases históricas definidas:")
print("    Pandemia aguda (Jan-Jun/2020)")
print("    Pandemia inicial (Jul-Dez/2020)")
print("    Pandemia tardia (2021)")
print("    Recuperação (2022)")
print("    Normalização (2023)")
print("    Expansão pós-pandemia (2024-2026)")

print(f"\n{'='*60}")
print("Aplicando transformações em streaming...")
print(f"{'='*60}")

writer = None
total_saida = 0

for i, batch in enumerate(parquet_file.iter_batches(batch_size=5_000_000)):
    df = batch.to_pandas()

    if "escolaridade" in df.columns:
        df["escolaridade_cod"] = df["escolaridade"].map(ORDEM_ESCOLARIDADE).fillna(-1).astype(int)

    if "regiao" in df.columns:
        df["regiao_cod_num"] = df["regiao"].map(MAP_REGIAO_COD).fillna(0).astype(int)

    if "sexo" in df.columns:
        df["sexo_cod"] = df["sexo"].map(MAP_SEXO_COD).fillna(-1).astype(int)

    if "mes" in df.columns:
        df["periodo_sazonal"] = df["mes"].map(MAP_PERIODO).fillna("Não informado")

    if "ano" in df.columns and "mes" in df.columns:
        ano = df["ano"]
        mes = df["mes"]
        df["fase_pandemia"] = np.select(
            [
                (ano == 2020) & (mes <= 6),
                (ano == 2020) & (mes > 6),
                ano == 2021,
                ano == 2022,
                ano == 2023,
            ],
            [
                "Pandemia aguda",
                "Pandemia inicial",
                "Pandemia tardia",
                "Recuperação",
                "Normalização",
            ],
            default="Expansão pós-pandemia",
        )

    if "ano" in df.columns and "mes" in df.columns:
        df["ano_mes_int"] = df["ano"] * 100 + df["mes"]

    total_saida += len(df)

    table = pa.Table.from_pandas(df, preserve_index=False)
    if writer is None:
        writer = pq.ParquetWriter(SAIDA, table.schema)
    writer.write_table(table)
    del df, table

    if (i+1) % 10 == 0:
        print(f"  Lote {i+1} — saída acumulada: {total_saida:,}")

if writer:
    writer.close()

print(f"  Concluído — total: {total_saida:,}")

print(f"\n{'='*60}")
print("ETAPA 5 — Gerando agregações para dashboard...")
print(f"{'='*60}")

print("  Lendo arquivo transformado para agregar...")
parquet_trans = pq.ParquetFile(SAIDA)

agg_mensal    = []
agg_uf        = []
agg_fase      = []

for batch in parquet_trans.iter_batches(batch_size=5_000_000):
    df = batch.to_pandas()

    g = df.groupby(["ano", "mes", "ano_mes"])["saldo"].sum().reset_index()
    agg_mensal.append(g)

    g = df.groupby(["ano", "sigla_uf"])["saldo"].sum().reset_index()
    agg_uf.append(g)

    if "fase_pandemia" in df.columns:
        g = df.groupby(["fase_pandemia", "setor"])["saldo"].sum().reset_index()
        agg_fase.append(g)

    del df

print("  Salvando tabelas agregadas...")

df_mensal = pd.concat(agg_mensal).groupby(["ano", "mes", "ano_mes"])["saldo"].sum().reset_index()
df_mensal = df_mensal.sort_values("ano_mes")
df_mensal["media_movel_3m"] = df_mensal["saldo"].rolling(3, center=True).mean()
df_mensal.to_parquet(PASTA_DADOS / "agg_saldo_mensal.parquet", index=False)
print(f"  agg_saldo_mensal.parquet — {len(df_mensal):,} linhas")

df_uf = pd.concat(agg_uf).groupby(["ano", "sigla_uf"])["saldo"].sum().reset_index()
df_uf.to_parquet(PASTA_DADOS / "agg_saldo_uf.parquet", index=False)
print(f"  agg_saldo_uf.parquet — {len(df_uf):,} linhas")

if agg_fase:
    df_fase = pd.concat(agg_fase).groupby(["fase_pandemia", "setor"])["saldo"].sum().reset_index()
    df_fase.to_parquet(PASTA_DADOS / "agg_saldo_fase.parquet", index=False)
    print(f"  agg_saldo_fase.parquet — {len(df_fase):,} linhas")

print(f"\n{'='*60}")
print("RELATÓRIO FINAL DE TRANSFORMAÇÃO")
print(f"{'='*60}")
print(f"\n  Registros transformados: {total_saida:,}")
print(f"\n  Variáveis criadas:")
print(f"    escolaridade_cod   → LabelEncoder ordinal (0–8)")
print(f"    regiao_cod_num     → código numérico da região (1–5)")
print(f"    sexo_cod           → binário (0=M, 1=F)")
print(f"    periodo_sazonal    → Jan-Mar / Abr-Jun / Jul-Set / Out-Dez")
print(f"    fase_pandemia      → 6 fases históricas (2020–2026)")
print(f"    ano_mes_int        → AAAAMM para ordenação")
print(f"\n  Tabelas agregadas geradas:")
print(f"    agg_saldo_mensal.parquet  → tendência temporal")
print(f"    agg_saldo_uf.parquet      → comparação regional")
print(f"    agg_saldo_fase.parquet    → impacto da pandemia por setor")
print(f"\n  Normalização Min-Max aplicada em amostra (demonstração)")
print(f"  para comparação de saldo entre UFs de tamanhos diferentes")
print(f"\nArquivo salvo em: {SAIDA}")
print(f"Tamanho: {SAIDA.stat().st_size / 1e9:.2f} GB")
print(f"\nTransformação concluída! Execute analise.py para continuar.")
