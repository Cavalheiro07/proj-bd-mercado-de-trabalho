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
PASTA_PARQUET.mkdir(exist_ok=True)

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

def listar_arquivos_mes(ano, mes):
    pasta_ftp = f"{FTP_BASE}/{ano}/{ano}{mes:02d}"
    try:
        with ftplib.FTP(FTP_HOST, timeout=30) as ftp:
            ftp.login()
            ftp.cwd(pasta_ftp)
            return ftp.nlst(), pasta_ftp
    except ftplib.error_perm:
        return [], pasta_ftp
    except Exception as e:
        print(f"  Erro ao listar {ano}/{mes:02d}: {e}")
        return [], pasta_ftp

def baixar(pasta_ftp, nome):
    destino = PASTA_BRUTOS / nome
    if destino.exists():
        try:
            with py7zr.SevenZipFile(destino, mode="r"):
                pass
            return destino
        except Exception:
            print(f"  Arquivo corrompido, baixando novamente: {nome}")
            destino.unlink()

    print(f"  Baixando: {nome} ...")
    try:
        with ftplib.FTP(FTP_HOST, timeout=60) as ftp:
            ftp.login()
            ftp.cwd(pasta_ftp)
            with open(destino, "wb") as f:
                ftp.retrbinary(f"RETR {nome}", f.write)
        print(f"  Concluído: {nome}")
        return destino
    except Exception as e:
        print(f"  ERRO ao baixar {nome}: {e}")
        if destino.exists():
            destino.unlink()
        return None

def extrair(caminho_7z):
    pasta_ext = PASTA_BRUTOS / caminho_7z.stem
    txts = list(pasta_ext.glob("*.txt")) if pasta_ext.exists() else []
    if txts:
        return txts[0], pasta_ext
    pasta_ext.mkdir(exist_ok=True)
    try:
        with py7zr.SevenZipFile(caminho_7z, mode="r") as z:
            z.extractall(path=pasta_ext)
        txts = list(pasta_ext.glob("*.txt"))
        return (txts[0], pasta_ext) if txts else (None, pasta_ext)
    except Exception as e:
        print(f"  ERRO ao extrair: {e}")
        return None, pasta_ext

def processar_e_salvar(caminho_txt, nome_parquet):
    saida = PASTA_PARQUET / nome_parquet
    if saida.exists():
        print(f"  Parquet já existe, pulando: {nome_parquet}")
        return True

    chunks = []
    try:
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

        if not chunks:
            return False

        df = pd.concat(chunks, ignore_index=True)
        df.to_parquet(saida, index=False)
        print(f"  Salvo: {nome_parquet} — {len(df):,} registros")
        del df, chunks
        return True

    except Exception as e:
        print(f"  ERRO ao processar {caminho_txt.name}: {e}")
        return False

def limpar(caminho_7z, pasta_ext):
    try:
        if pasta_ext and pasta_ext.exists():
            shutil.rmtree(pasta_ext)
        if caminho_7z and caminho_7z.exists():
            caminho_7z.unlink()
    except Exception as e:
        print(f"  Aviso: não foi possível limpar arquivos temporários: {e}")

processados = []
erros = []

for ano in ANOS:
    print(f"\n{'='*50}")
    print(f"Ano: {ano}")
    print(f"{'='*50}")

    for mes in range(1, 13):
        arquivos, pasta_ftp = listar_arquivos_mes(ano, mes)
        if not arquivos:
            continue

        for nome in arquivos:
            if "CAGEDMOV" not in nome.upper() or not nome.upper().endswith(".7Z"):
                continue

            nome_parquet = nome.upper().replace(".7Z", ".parquet")

            if (PASTA_PARQUET / nome_parquet).exists():
                print(f"  Já processado: {nome_parquet}")
                processados.append(nome_parquet)
                continue

            caminho_7z = baixar(pasta_ftp, nome)
            if not caminho_7z:
                erros.append(nome)
                continue

            caminho_txt, pasta_ext = extrair(caminho_7z)
            if not caminho_txt:
                erros.append(nome)
                limpar(caminho_7z, pasta_ext)
                continue

            ok = processar_e_salvar(caminho_txt, nome_parquet)
            limpar(caminho_7z, pasta_ext)

            if ok:
                processados.append(nome_parquet)
                print(f"  Arquivos temporários removidos ✓")
            else:
                erros.append(nome)

print(f"\n{'='*50}")
print(f"Arquivos processados: {len(processados)}")
print(f"Erros:                {len(erros)}")
if erros:
    print(f"Com erro: {erros}")
print(f"\nParquets salvos em: {PASTA_PARQUET}/")
print(f"{'='*50}")
print("\nColeta concluída! Execute integracao.py para continuar.")
