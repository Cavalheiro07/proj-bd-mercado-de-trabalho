# integracao.py — Etapa 2 do pipeline: integração de fontes.
# Junta os dados do CAGED com a tabela de municípios do IBGE
# (para ter nome do município, UF e região), traduz os códigos
# numéricos em textos legíveis e gera o arquivo caged_integrado.parquet.

import pandas as pd
import requests
import pyarrow.parquet as pq
from pathlib import Path

PASTA_PARQUET = Path(__file__).parent / "dados_parquet"
PASTA_SAIDA   = Path(__file__).parent / "dados"
PASTA_SAIDA.mkdir(exist_ok=True)

SAIDA_FINAL   = PASTA_SAIDA / "caged_integrado.parquet"
TAMANHO_LOTE  = 10  # quantos arquivos parquet são processados por vez

# ---- Tabela de municípios do IBGE (segunda fonte de dados) ----
print("Buscando tabela de municípios do IBGE...")
municipios_path = PASTA_SAIDA / "municipios_ibge.parquet"

if municipios_path.exists():
    print("  Já existe, carregando do disco...")
    municipios = pd.read_parquet(municipios_path)
else:
    # Consulta a API pública do IBGE e monta um DataFrame
    # com código, nome, UF e região de cada município
    print("  Baixando da API do IBGE...")
    url = "https://servicodados.ibge.gov.br/api/v1/localidades/municipios"
    resp = requests.get(url, timeout=30)
    dados = resp.json()

    municipios = pd.DataFrame([{
        "cod_municipio": str(m["id"])[:6],
        "nome_municipio": m.get("nome", ""),
        "sigla_uf":  (m.get("microrregiao") or {}).get("mesorregiao", {}).get("UF", {}).get("sigla", ""),
        "nome_uf":   (m.get("microrregiao") or {}).get("mesorregiao", {}).get("UF", {}).get("nome", ""),
        "regiao":    (m.get("microrregiao") or {}).get("mesorregiao", {}).get("UF", {}).get("regiao", {}).get("nome", ""),
    } for m in dados])

    municipios.to_parquet(municipios_path, index=False)
    print(f"  Salvo: {municipios_path}")

# Garante que o código do município tenha sempre 6 dígitos (chave do merge)
municipios["cod_municipio"] = municipios["cod_municipio"].astype(str).str.zfill(6)
print(f"  {len(municipios):,} municípios carregados")

arquivos = sorted(PASTA_PARQUET.glob("CAGEDMOV*.parquet"))
print(f"\nProcessando {len(arquivos)} arquivos em lotes de {TAMANHO_LOTE}...")

# Dicionários que traduzem os códigos do CAGED para textos legíveis
MAP_SEXO  = {"1": "Masculino", "3": "Feminino", "9": "Não identificado"}
MAP_RACA  = {"1": "Branca", "2": "Preta", "3": "Parda",
             "6": "Amarela", "7": "Indígena", "9": "Não identificado"}
MAP_ESCOL = {"1": "Analfabeto", "2": "Fundamental incompleto",
             "3": "Fundamental completo", "4": "Médio incompleto",
             "5": "Médio completo", "6": "Superior incompleto",
             "7": "Superior completo", "8": "Mestrado", "9": "Doutorado"}
MAP_SECAO = {
    "A": "Agropecuária", "B": "Indústria extrativa",
    "C": "Indústria de transformação", "D": "Energia e utilidades",
    "E": "Saneamento e gestão de resíduos", "F": "Construção civil",
    "G": "Comércio", "H": "Transporte e armazenagem",
    "I": "Alimentação e hospedagem", "J": "Informação e comunicação",
    "K": "Atividades financeiras", "L": "Atividades imobiliárias",
    "M": "Serviços profissionais", "N": "Serviços administrativos",
    "O": "Administração pública", "P": "Educação",
    "Q": "Saúde e assistência social", "R": "Artes e cultura",
    "S": "Outras atividades de serviços", "T": "Serviços domésticos",
    "U": "Organismos internacionais",
}

# Recebe um lote de DataFrames e aplica todo o tratamento:
# converte datas, traduz códigos e faz o merge com os municípios do IBGE
def tratar_lote(dfs_lote, municipios):
    df = pd.concat(dfs_lote, ignore_index=True)

    # Converte o campo AAAAMM em data e extrai ano e mês
    df["ano_mes"] = pd.to_datetime(
        df["ano_mes"].astype(str).str.strip(),
        format="%Y%m", errors="coerce"
    )
    df["ano"] = df["ano_mes"].dt.year
    df["mes"] = df["ano_mes"].dt.month

    # tipo_mov: 1 = admissão, -1 = desligamento → vira a coluna "saldo"
    df["tipo_mov"] = pd.to_numeric(df["tipo_mov"], errors="coerce")
    df["saldo"]    = df["tipo_mov"]

    if "salario" in df.columns:
        df["salario"] = pd.to_numeric(df["salario"], errors="coerce")

    # Aplica os dicionários de tradução nas colunas categóricas
    if "sexo" in df.columns:
        df["sexo"] = df["sexo"].astype(str).map(MAP_SEXO).fillna("Não identificado")
    if "raca_cor" in df.columns:
        df["raca_cor"] = df["raca_cor"].astype(str).map(MAP_RACA).fillna("Não identificado")
    if "escolaridade" in df.columns:
        df["escolaridade"] = df["escolaridade"].astype(str).map(MAP_ESCOL).fillna("Não informado")

    df["setor"] = df["secao_cnae"].astype(str).str.upper().str.strip().map(MAP_SECAO).fillna("Não informado")

    # Merge com a tabela do IBGE pelo código do município (6 dígitos)
    df["cod_municipio_6"] = df["cod_municipio"].astype(str).str[:6].str.zfill(6)
    df = df.merge(municipios, left_on="cod_municipio_6", right_on="cod_municipio",
                  how="left", suffixes=("", "_ibge"))
    df = df.drop(columns=["cod_municipio_6", "cod_municipio_ibge"], errors="ignore")

    return df

# ---- Processamento em lotes ----
# Divide os arquivos em grupos de 10 para não estourar a memória
lotes = [arquivos[i:i+TAMANHO_LOTE] for i in range(0, len(arquivos), TAMANHO_LOTE)]
total_registros = 0
parquets_lote = []

for i, lote in enumerate(lotes):
    print(f"\nLote {i+1}/{len(lotes)}: {[a.name for a in lote]}")

    dfs_lote = []
    for arq in lote:
        df_arq = pd.read_parquet(arq)
        dfs_lote.append(df_arq)
        print(f"  Lido: {arq.name} — {len(df_arq):,} registros")

    df_lote = tratar_lote(dfs_lote, municipios)
    del dfs_lote

    saida_lote = PASTA_SAIDA / f"lote_{i+1:02d}.parquet"
    df_lote.to_parquet(saida_lote, index=False)
    total_registros += len(df_lote)
    parquets_lote.append(saida_lote)
    print(f"  Lote {i+1} salvo: {len(df_lote):,} registros — {saida_lote.name}")
    del df_lote

print(f"\nTodos os lotes processados: {total_registros:,} registros no total")

print("\nCombinando lotes no arquivo final (streaming)...")

# Junta todos os lotes em um único parquet, escrevendo aos poucos
writer = None
for p in parquets_lote:
    table = pq.read_table(p)
    if writer is None:
        writer = pq.ParquetWriter(SAIDA_FINAL, table.schema)
    writer.write_table(table)
    del table
    print(f"  Combinado: {p.name}")
if writer:
    writer.close()

for p in parquets_lote:
    p.unlink()
print("  Lotes temporários removidos ✓")

print(f"\n{'='*50}")
print(f"=== Relatório de qualidade ===")
print(f"{'='*50}")
print(f"Total de registros:      {total_registros:,}")
print(f"\nArquivo salvo em: {SAIDA_FINAL}")
print(f"Tamanho: {SAIDA_FINAL.stat().st_size / 1e9:.2f} GB")
print(f"\nIntegração concluída! Execute limpeza.py para continuar.")
