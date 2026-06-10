import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent

def run(label, script):
    print(f"\n{label}")
    result = subprocess.run([sys.executable, str(ROOT / script)], check=False)
    if result.returncode != 0:
        print(f"  ERRO: {script} terminou com código {result.returncode}")
        sys.exit(result.returncode)

# [1/5] Coleta
dados_parquet = ROOT / "dados_parquet"
if not dados_parquet.exists() or not any(dados_parquet.glob("CAGEDMOV*.parquet")):
    run("[1/5] Coletando dados do FTP...", "coleta_caged.py")
else:
    print("[1/5] Dados já coletados — pulando coleta.")

# [2/5] Integração
if not (ROOT / "dados" / "caged_integrado.parquet").exists():
    run("[2/5] Integrando CAGED + IBGE...", "integracao.py")
else:
    print("[2/5] Integração já concluída — pulando.")

# [3/5] Limpeza
if not (ROOT / "dados" / "caged_limpo.parquet").exists():
    run("[3/5] Limpando dados...", "limpeza.py")
else:
    print("[3/5] Limpeza já concluída — pulando.")

# [4/5] Transformação
if not (ROOT / "dados" / "caged_transformado.parquet").exists():
    run("[4/5] Transformando dados...", "transformacao.py")
else:
    print("[4/5] Transformação já concluída — pulando.")

# [5/5] Agregações
if not (ROOT / "dados" / "agg_municipios.parquet").exists():
    run("[5/5] Gerando agregações...", "gerar_agregacoes.py")
else:
    print("[5/5] Agregações já geradas — pulando.")

print("\nIniciando dashboard...")
subprocess.run([sys.executable, str(ROOT / "app.py")])
