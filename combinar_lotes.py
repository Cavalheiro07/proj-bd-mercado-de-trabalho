import pyarrow.parquet as pq
import pyarrow as pa
from pathlib import Path

PASTA_SAIDA = Path(__file__).parent / "dados"
SAIDA_FINAL = PASTA_SAIDA / "caged_integrado.parquet"

lotes = sorted(PASTA_SAIDA.glob("lote_*.parquet"))
print(f"Lotes encontrados: {len(lotes)}")
for l in lotes:
    print(f"  {l.name}")

if not lotes:
    print("ERRO: Nenhum lote encontrado em dados/")
    exit(1)

print(f"\nCombinando {len(lotes)} lotes em {SAIDA_FINAL}...")
print("(Isso pode demorar alguns minutos mas não vai crashar)")

writer = None
total = 0

for lote in lotes:
    print(f"  Processando: {lote.name}...")
    table = pq.read_table(lote)
    total += len(table)

    if writer is None:
        writer = pq.ParquetWriter(SAIDA_FINAL, table.schema)

    writer.write_table(table)
    del table
    print(f"  OK — total acumulado: {total:,}")

if writer:
    writer.close()

for lote in lotes:
    lote.unlink()
print("  Lotes temporários removidos ✓")

print(f"\nArquivo final: {SAIDA_FINAL}")
print(f"Tamanho: {SAIDA_FINAL.stat().st_size / 1e9:.2f} GB")
print(f"Total de registros: {total:,}")
print("\nConcluído! Execute limpeza.py para continuar.")
