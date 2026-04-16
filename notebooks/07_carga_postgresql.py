import pandas as pd
from sqlalchemy import create_engine, text
from pathlib import Path

# ==========================================================
# 1. CONFIGURAÇÕES DO POSTGRESQL
# ==========================================================
DB_HOST = "localhost"
DB_PORT = "5432"
DB_NAME = "olist_portfolio"
DB_USER = "postgres"
DB_PASSWORD = "123"
SCHEMA_NAME = "portfolio"

# ==========================================================
# 2. CAMINHOS DO PROJETO
# ==========================================================
try:
    BASE_DIR = Path(__file__).resolve().parent.parent
except NameError:
    BASE_DIR = Path.cwd().parent

DADOS_TRATADOS = BASE_DIR / "dados_tratados"

arquivos = {
    "dim_clientes": DADOS_TRATADOS / "dim_clientes.csv",
    "dim_produtos": DADOS_TRATADOS / "dim_produtos.csv",
    "dim_vendedores": DADOS_TRATADOS / "dim_vendedores.csv",
    "dim_tempo": DADOS_TRATADOS / "dim_tempo.csv",
    "fato_vendas": DADOS_TRATADOS / "fato_vendas.csv"
}

# ==========================================================
# 3. VALIDAR ARQUIVOS
# ==========================================================
for nome, arq in arquivos.items():
    if not arq.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {arq}")

# ==========================================================
# 4. LER CSVs
# ==========================================================
print("\n" + "=" * 80)
print("LENDO ARQUIVOS CSV...")
print("=" * 80)

dfs = {nome: pd.read_csv(caminho) for nome, caminho in arquivos.items()}

for nome, df in dfs.items():
    print(f"{nome}: {df.shape}")

# ==========================================================
# 5. CONEXÃO COM POSTGRESQL
# ==========================================================
print("\n" + "=" * 80)
print("CONECTANDO AO POSTGRESQL...")
print("=" * 80)

engine = create_engine(
    f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

# ==========================================================
# 6. GARANTIR SCHEMA
# ==========================================================
with engine.begin() as conn:
    conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA_NAME};"))

print(f"Schema garantido: {SCHEMA_NAME}")

# ==========================================================
# 7. DESATIVAR CONSTRAINTS (FKs)
# ==========================================================
print("\nDesativando FKs...")

with engine.begin() as conn:
    conn.execute(text("SET session_replication_role = 'replica';"))

# ==========================================================
# 8. LIMPAR TABELAS (SEM DROP)
# ==========================================================
print("\nLimpando tabelas...")

with engine.begin() as conn:
    conn.execute(text(f"""
        TRUNCATE TABLE 
            {SCHEMA_NAME}.fato_vendas,
            {SCHEMA_NAME}.dim_clientes,
            {SCHEMA_NAME}.dim_produtos,
            {SCHEMA_NAME}.dim_vendedores,
            {SCHEMA_NAME}.dim_tempo
        CASCADE;
    """))

print("[OK] Tabelas limpas")

# ==========================================================
# 9. CARGA (APPEND — SEM DROP!)
# ==========================================================
print("\nCarregando dados...")

dfs["dim_clientes"].to_sql(
    "dim_clientes", engine, schema=SCHEMA_NAME,
    if_exists="append", index=False
)
print("[OK] dim_clientes")

dfs["dim_produtos"].to_sql(
    "dim_produtos", engine, schema=SCHEMA_NAME,
    if_exists="append", index=False
)
print("[OK] dim_produtos")

dfs["dim_vendedores"].to_sql(
    "dim_vendedores", engine, schema=SCHEMA_NAME,
    if_exists="append", index=False
)
print("[OK] dim_vendedores")

dfs["dim_tempo"].to_sql(
    "dim_tempo", engine, schema=SCHEMA_NAME,
    if_exists="append", index=False
)
print("[OK] dim_tempo")

dfs["fato_vendas"].to_sql(
    "fato_vendas", engine, schema=SCHEMA_NAME,
    if_exists="append", index=False
)
print("[OK] fato_vendas")

# ==========================================================
# 10. REATIVAR CONSTRAINTS
# ==========================================================
print("\nReativando FKs...")

with engine.begin() as conn:
    conn.execute(text("SET session_replication_role = 'origin';"))

print("[OK] Constraints reativadas")

# ==========================================================
# 11. VALIDAÇÃO
# ==========================================================
print("\nValidando carga...")

query = f"""
SELECT table_name
FROM information_schema.tables
WHERE table_schema = '{SCHEMA_NAME}'
ORDER BY table_name;
"""

with engine.connect() as conn:
    tabelas = pd.read_sql(query, conn)

with engine.connect() as conn:
    for tabela in tabelas["table_name"]:
        qtd = pd.read_sql(
            f"SELECT COUNT(*) AS qtd FROM {SCHEMA_NAME}.{tabela}",
            conn
        )["qtd"][0]
        print(f"{tabela}: {qtd:,}")

# ==========================================================
# 12. FINAL
# ==========================================================
print("\n" + "=" * 80)
print("CARGA FINALIZADA COM SUCESSO")
print("=" * 80)