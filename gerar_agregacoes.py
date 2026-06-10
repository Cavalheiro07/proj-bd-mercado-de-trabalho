import pandas as pd
import pyarrow.parquet as pq
from pathlib import Path

PASTA_DADOS = Path(__file__).parent / "dados"
ENTRADA     = PASTA_DADOS / "caged_transformado.parquet"

print("Gerando agregações extras para os dashboards...")
parquet_file = pq.ParquetFile(ENTRADA)

agg_municipio  = []
agg_setor_ano  = []
agg_mes_ano    = []

for i, batch in enumerate(parquet_file.iter_batches(batch_size=5_000_000)):
    df = batch.to_pandas()

    if "nome_municipio" in df.columns and "sigla_uf" in df.columns and "ano" in df.columns:
        g = df.groupby(["ano", "nome_municipio", "sigla_uf", "regiao"])["saldo"].sum().reset_index()
        agg_municipio.append(g)

    if "setor" in df.columns and "ano" in df.columns:
        g = df.groupby(["ano", "setor"])["saldo"].sum().reset_index()
        agg_setor_ano.append(g)

    if "mes" in df.columns and "ano" in df.columns:
        g = df.groupby(["ano", "mes"])["saldo"].sum().reset_index()
        agg_mes_ano.append(g)

    if (i+1) % 10 == 0:
        print(f"  Processado lote {i+1}")

print("Consolidando e salvando...")

df_mun = pd.concat(agg_municipio).groupby(
    ["ano", "nome_municipio", "sigla_uf", "regiao"]
)["saldo"].sum().reset_index()
df_mun.to_parquet(PASTA_DADOS / "agg_municipios.parquet", index=False)
print(f"  agg_municipios.parquet — {len(df_mun):,} municípios")

df_setor_ano = pd.concat(agg_setor_ano).groupby(
    ["ano", "setor"]
)["saldo"].sum().reset_index()

df_2020 = df_setor_ano[df_setor_ano["ano"] == 2020][["setor","saldo"]].rename(columns={"saldo":"saldo_2020"})
df_2026 = df_setor_ano[df_setor_ano["ano"] == 2026][["setor","saldo"]].rename(columns={"saldo":"saldo_2026"})
df_cresc = df_2020.merge(df_2026, on="setor", how="outer").fillna(0)
df_cresc["variacao_pct"] = ((df_cresc["saldo_2026"] - df_cresc["saldo_2020"]) /
    df_cresc["saldo_2020"].abs().replace(0, 1) * 100).round(1)
df_cresc.to_parquet(PASTA_DADOS / "agg_crescimento_setor.parquet", index=False)
print(f"  agg_crescimento_setor.parquet — {len(df_cresc)} setores")

df_setor_ano.to_parquet(PASTA_DADOS / "agg_setor_ano.parquet", index=False)
print(f"  agg_setor_ano.parquet — {len(df_setor_ano)} linhas")

df_mes_ano = pd.concat(agg_mes_ano).groupby(
    ["ano", "mes"]
)["saldo"].sum().reset_index()
df_mes_ano.to_parquet(PASTA_DADOS / "agg_mes_ano.parquet", index=False)
print(f"  agg_mes_ano.parquet — {len(df_mes_ano)} linhas")

print("\nAgregações concluídas!")
