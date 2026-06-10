import ftplib
import py7zr
import pandas as pd
from pathlib import Path
import shutil

FTP_HOST      = "ftp.mtps.gov.br"
FTP_BASE      = "/pdet/microdados/NOVO CAGED"
ANOS          = [2020, 2021, 2022, 2023, 2024, 2025, 2026]
PASTA_BRUTOS  = Path(__file__).parent / "dados_brutos"
PASTA_PARQUET = Path(__file__).parent / "dados_parquet"
PASTA_BRUTOS.mkdir(exist_ok=True)

COLUNAS_UTEIS = [
    "competênciamov", "região", "uf", "município", "seção", "subclasse",
    "saldomovimentação", "saldomensalremuneração", "sexotrabalhador",
    "raçacortrabalhador", "graudeinstruçãotrabalhador",
    "tipoempregador", "tipomovimentação", "tamestab",
]
RENAME = {
    "competênciamov":               "ano_mes",
    "uf":                           "sigla_uf",
    "região":                       "regiao_cod",
    "município":                    "cod_municipio",
    "seção":                        "secao_cnae",
    "subclasse":                    "cnae",
    "saldomovimentação":            "tipo_mov",
    "saldomensalremuneração":       "salario",
    "sexotrabalhador":              "sexo",
    "raçacortrabalhador":           "raca_cor",
    "graudeinstruçãotrabalhador":   "escolaridade",
}

existentes = {f.stem for f in PASTA_PARQUET.glob("CAGEDMOV*.parquet")}
print(f"Parquets existentes: {len(existentes)}")

print("Verificando FTP para encontrar arquivos faltando...")
faltando = []

for ano in ANOS:
    for mes in range(1, 13):
        pasta_ftp = f"{FTP_BASE}/{ano}/{ano}{mes:02d}"
        try:
            with ftplib.FTP(FTP_HOST, timeout=30) as ftp:
                ftp.login()
                ftp.cwd(pasta_ftp)
                arquivos = ftp.nlst()
                for nome in arquivos:
                    if "CAGEDMOV" in nome.upper() and nome.upper().endswith(".7Z"):
                        stem = nome.upper().replace(".7Z", "")
                        if stem not in existentes:
                            faltando.append((ano, mes, pasta_ftp, nome))
        except ftplib.error_perm:
            pass
        except Exception as e:
            print(f"  Erro ao verificar {ano}/{mes:02d}: {e}")

if not faltando:
    print("\nTodos os arquivos já estão processados!")
    exit(0)

print(f"\nArquivos faltando: {len(faltando)}")
for ano, mes, _, nome in faltando:
    print(f"  {ano}/{mes:02d} — {nome}")

def baixar(pasta_ftp, nome):
    destino = PASTA_BRUTOS / nome
    if destino.exists():
        try:
            with py7zr.SevenZipFile(destino, mode="r"): pass
            return destino
        except:
            destino.unlink()
    print(f"  Baixando: {nome} ...")
    with ftplib.FTP(FTP_HOST, timeout=60) as ftp:
        ftp.login()
        ftp.cwd(pasta_ftp)
        with open(destino, "wb") as f:
            ftp.retrbinary(f"RETR {nome}", f.write)
    print(f"  Concluído!")
    return destino

def extrair(caminho_7z):
    pasta_ext = PASTA_BRUTOS / caminho_7z.stem
    txts = list(pasta_ext.glob("*.txt")) if pasta_ext.exists() else []
    if txts:
        return txts[0], pasta_ext
    pasta_ext.mkdir(exist_ok=True)
    with py7zr.SevenZipFile(caminho_7z, mode="r") as z:
        z.extractall(path=pasta_ext)
    txts = list(pasta_ext.glob("*.txt"))
    return (txts[0], pasta_ext) if txts else (None, pasta_ext)

def processar_e_salvar(caminho_txt, nome_parquet):
    saida = PASTA_PARQUET / nome_parquet
    chunks = []
    reader = pd.read_csv(
        caminho_txt, sep=";", encoding="utf-8",
        low_memory=False, dtype=str, chunksize=300_000,
    )
    for chunk in reader:
        cols = [c for c in COLUNAS_UTEIS if c in chunk.columns]
        chunk = chunk[cols].copy()
        chunk = chunk.rename(columns={k: v for k, v in RENAME.items() if k in chunk.columns})
        if "salario" in chunk.columns:
            chunk["salario"] = pd.to_numeric(chunk["salario"], errors="coerce")
        if "tipo_mov" in chunk.columns:
            chunk["tipo_mov"] = pd.to_numeric(chunk["tipo_mov"], errors="coerce")
        chunks.append(chunk)
    df = pd.concat(chunks, ignore_index=True)
    df.to_parquet(saida, index=False)
    print(f"  Salvo: {nome_parquet} — {len(df):,} registros")
    del df, chunks

def limpar(caminho_7z, pasta_ext):
    try:
        if pasta_ext and pasta_ext.exists():
            shutil.rmtree(pasta_ext)
        if caminho_7z and caminho_7z.exists():
            caminho_7z.unlink()
        print(f"  Temporários removidos ✓")
    except Exception as e:
        print(f"  Aviso ao limpar: {e}")

for ano, mes, pasta_ftp, nome in faltando:
    print(f"\nProcessando: {nome}")
    nome_parquet = nome.upper().replace(".7Z", ".parquet")
    try:
        caminho_7z = baixar(pasta_ftp, nome)
        caminho_txt, pasta_ext = extrair(caminho_7z)
        processar_e_salvar(caminho_txt, nome_parquet)
        limpar(caminho_7z, pasta_ext)
    except Exception as e:
        print(f"  ERRO: {e}")

print(f"\nTotal de parquets agora: {len(list(PASTA_PARQUET.glob('*.parquet')))}")
print("Pronto! Execute integracao.py para continuar.")
