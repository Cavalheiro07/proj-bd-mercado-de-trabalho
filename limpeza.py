# limpeza.py — Etapa 3 do pipeline: limpeza dos dados.
# Analisa valores ausentes, remove registros inválidos (sem UF,
# UF errada ou movimentação diferente de admissão/desligamento)
# e padroniza textos. Gera o arquivo caged_limpo.parquet.

import pandas as pd
import pyarrow.parquet as pq
import pyarrow as pa
from pathlib import Path

PASTA_DADOS = Path(__file__).parent / "dados"
ENTRADA     = PASTA_DADOS / "caged_integrado.parquet"
SAIDA       = PASTA_DADOS / "caged_limpo.parquet"

# Lista oficial das 27 UFs — qualquer coisa fora disso é descartada
UFS_VALIDAS = {
    "AC","AL","AM","AP","BA","CE","DF","ES","GO","MA","MG","MS","MT",
    "PA","PB","PE","PI","PR","RJ","RN","RO","RR","RS","SC","SE","SP","TO"
}

print("Lendo metadados do arquivo...")
parquet_file = pq.ParquetFile(ENTRADA)
total_rows   = parquet_file.metadata.num_rows
print(f"Total de registros: {total_rows:,}")

print("\nAnalisando qualidade dos dados (passagem 1/2)...")

# Primeira passagem: só conta os valores nulos de cada coluna,
# lendo o arquivo em lotes de 5 milhões de linhas
nulos_total = {}
registros_analisados = 0

for i, batch in enumerate(parquet_file.iter_batches(batch_size=5_000_000)):
    df_b = batch.to_pandas()
    for col in df_b.columns:
        nulos_total[col] = nulos_total.get(col, 0) + int(df_b[col].isna().sum())
    registros_analisados += len(df_b)
    if (i+1) % 10 == 0:
        print(f"  Analisado: {registros_analisados:,} registros")

print(f"  Analisado: {registros_analisados:,} registros — concluído")

print(f"\n{'='*60}")
print("ETAPA 1 — Análise de valores ausentes")
print(f"{'='*60}")
print(f"\n{'Coluna':<30} {'Nulos':>12} {'%':>8}")
print("-"*52)
tem_nulos = False
for col, n in nulos_total.items():
    if n > 0:
        print(f"  {col:<28} {n:>12,} {n/total_rows*100:>7.1f}%")
        tem_nulos = True
if not tem_nulos:
    print("  Nenhum valor ausente encontrado ✓")

print(f"\n  Nota sobre duplicatas: o CAGED registra movimentações")
print(f"  individuais de trabalhadores — múltiplos registros com")
print(f"  mesmos atributos são legítimos (vários funcionários do")
print(f"  mesmo CNAE no mesmo município). Não aplicar dedup.")

print(f"\n  Nota: coluna 'salario' ausente no arquivo integrado.")
print(f"  Motivo: CAGEDMOV202001 gerado com esquema diferente.")
print(f"  Impacto: análises salariais excluem janeiro/2020 (~2,6M registros).")

print(f"\n{'='*60}")
print("Aplicando limpeza (passagem 2/2)...")
print(f"{'='*60}")

# Segunda passagem: aplica os filtros e padronizações
# e escreve o resultado limpo em streaming
writer = None
stats  = {
    "sem_uf": 0, "uf_invalida": 0, "mov_invalida": 0,
    "total_entrada": 0, "total_saida": 0
}

for i, batch in enumerate(parquet_file.iter_batches(batch_size=5_000_000)):
    df = batch.to_pandas()
    stats["total_entrada"] += len(df)

    # Usa a sigla de UF vinda do IBGE (mais confiável que a original)
    if "sigla_uf_ibge" in df.columns:
        df["sigla_uf"] = df["sigla_uf_ibge"]

    # Remove registros sem UF
    antes = len(df)
    df = df[df["sigla_uf"].notna() & (df["sigla_uf"] != "")]
    stats["sem_uf"] += antes - len(df)

    # Remove registros com UF que não existe
    antes = len(df)
    df = df[df["sigla_uf"].isin(UFS_VALIDAS)]
    stats["uf_invalida"] += antes - len(df)

    # Mantém só admissão (1) e desligamento (-1)
    antes = len(df)
    df = df[df["tipo_mov"].isin([1, -1])]
    stats["mov_invalida"] += antes - len(df)

    # Padroniza os textos (maiúsculas, espaços, title case)
    df["sigla_uf"] = df["sigla_uf"].str.strip().str.upper()
    if "nome_municipio" in df.columns:
        df["nome_municipio"] = df["nome_municipio"].str.strip().str.title()
    if "regiao" in df.columns:
        df["regiao"] = df["regiao"].str.strip().str.title()
    if "setor" in df.columns:
        df["setor"] = df["setor"].str.strip()

    # Cria colunas novas: rótulo da movimentação e trimestre
    df["tipo_mov_label"] = df["tipo_mov"].map({1: "Admissão", -1: "Desligamento"})
    if "mes" in df.columns:
        df["trimestre"]     = df["mes"].apply(
            lambda m: f"T{(m-1)//3+1}" if pd.notna(m) else None
        )
        df["ano_trimestre"] = df["ano"].astype(str) + "-" + df["trimestre"].astype(str)

    df = df.drop(columns=["sigla_uf_ibge", "regiao_cod"], errors="ignore")

    stats["total_saida"] += len(df)

    table = pa.Table.from_pandas(df, preserve_index=False)
    if writer is None:
        writer = pq.ParquetWriter(SAIDA, table.schema)
    writer.write_table(table)
    del df, table

    if (i+1) % 10 == 0:
        print(f"  Lote {i+1} — saída acumulada: {stats['total_saida']:,}")

if writer:
    writer.close()

print(f"  Concluído — saída final: {stats['total_saida']:,}")

# Relatório final: quantos registros entraram, saíram e foram removidos
print(f"\n{'='*60}")
print("RELATÓRIO FINAL DE LIMPEZA")
print(f"{'='*60}")
removidos = stats['total_entrada'] - stats['total_saida']
print(f"\n  Registros entrada:        {stats['total_entrada']:,}")
print(f"  Sem UF removidos:         {stats['sem_uf']:,}")
print(f"  UF inválida removidos:    {stats['uf_invalida']:,}")
print(f"  Mov. inválida removidos:  {stats['mov_invalida']:,}")
print(f"  Registros finais:         {stats['total_saida']:,}")
print(f"  Removidos total:          {removidos:,} ({removidos/stats['total_entrada']:.2%})")

print(f"\n  Padronizações aplicadas:")
print(f"    sigla_uf       → substituída por sigla_uf_ibge (siglas oficiais)")
print(f"    nome_municipio → title case (ex: 'SÃO PAULO' → 'São Paulo')")
print(f"    regiao         → title case")
print(f"    setor          → espaços removidos")
print(f"    tipo_mov_label → 'Admissão' / 'Desligamento'")
print(f"    trimestre      → T1, T2, T3, T4")
print(f"    ano_trimestre  → ex: '2020-T1'")

print(f"\nArquivo salvo em: {SAIDA}")
print(f"Tamanho: {SAIDA.stat().st_size / 1e9:.2f} GB")
print(f"\nLimpeza concluída! Execute transformacao.py para continuar.")
