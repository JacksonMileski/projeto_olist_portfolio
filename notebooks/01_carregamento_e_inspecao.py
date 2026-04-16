import pandas as pd
from pathlib import Path

# ==========================================================
# 1. CONFIGURAÇÃO DE CAMINHOS
# ==========================================================
try:
    BASE_DIR = Path(__file__).resolve().parent.parent
except NameError:
    BASE_DIR = Path.cwd().parent
DADOS_BRUTOS = BASE_DIR / "dados_brutos"

# ==========================================================
# 2. CARREGAR ARQUIVOS PRINCIPAIS
# ==========================================================
orders = pd.read_csv(DADOS_BRUTOS / "olist_orders_dataset.csv")
order_items = pd.read_csv(DADOS_BRUTOS / "olist_order_items_dataset.csv")
customers = pd.read_csv(DADOS_BRUTOS / "olist_customers_dataset.csv")

# ==========================================================
# 3. FUNÇÃO DE INSPEÇÃO
# ==========================================================
def inspecionar_dataframe(nome, df):
    print("\n" + "=" * 80)
    print(f"DATAFRAME: {nome}")
    print("=" * 80)

    print("\n--- PRIMEIRAS 5 LINHAS ---")
    print(df.head())

    print("\n--- DIMENSÃO (LINHAS, COLUNAS) ---")
    print(df.shape)

    print("\n--- TIPOS DE DADOS ---")
    print(df.dtypes)

    print("\n--- VALORES NULOS POR COLUNA ---")
    print(df.isnull().sum())

    print("\n--- VALORES NULOS (%) POR COLUNA ---")
    print((df.isnull().mean() * 100).round(2))

    print("\n--- DUPLICADOS TOTAIS ---")
    print(df.duplicated().sum())

# ==========================================================
# 4. INSPECIONAR TABELAS
# ==========================================================
inspecionar_dataframe("orders", orders)
inspecionar_dataframe("order_items", order_items)
inspecionar_dataframe("customers", customers)