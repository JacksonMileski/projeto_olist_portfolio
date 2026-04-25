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
DADOS_TRATADOS = BASE_DIR / "dados_tratados"

# Criar pasta caso não exista
DADOS_TRATADOS.mkdir(exist_ok=True)

# ==========================================================
# 2. CARREGAR ARQUIVOS
# ==========================================================
orders = pd.read_csv(DADOS_BRUTOS / "olist_orders_dataset.csv")
order_items = pd.read_csv(DADOS_BRUTOS / "olist_order_items_dataset.csv")
customers = pd.read_csv(DADOS_BRUTOS / "olist_customers_dataset.csv")

# ==========================================================
# 3. CONVERTER DATAS
# ==========================================================
colunas_datas_orders = [
    "order_purchase_timestamp",
    "order_approved_at",
    "order_delivered_carrier_date",
    "order_delivered_customer_date",
    "order_estimated_delivery_date"
]

for coluna in colunas_datas_orders:
    orders[coluna] = pd.to_datetime(orders[coluna], errors="coerce")

order_items["shipping_limit_date"] = pd.to_datetime(
    order_items["shipping_limit_date"], errors="coerce"
)

# ==========================================================
# 4. CRIAR MÉTRICAS NA TABELA ORDERS
# ==========================================================

# Tempo real de entrega (em dias)
orders["tempo_entrega_dias"] = (
    orders["order_delivered_customer_date"] - orders["order_purchase_timestamp"]
).dt.days

# Prazo estimado em dias (da compra até a previsão)
orders["prazo_estimado_dias"] = (
    orders["order_estimated_delivery_date"] - orders["order_purchase_timestamp"]
).dt.days

# Atraso de entrega (em dias)
orders["atraso_entrega_dias"] = (
    orders["order_delivered_customer_date"] - orders["order_estimated_delivery_date"]
).dt.days

# Flag: pedido entregue com atraso?
def calcular_atraso(row):
    if row["order_status"] != "delivered":
        return pd.NA
    if pd.isnull(row["atraso_entrega_dias"]):
        return pd.NA
    return 1 if row["atraso_entrega_dias"] > 0 else 0

orders["entregue_com_atraso"] = orders.apply(calcular_atraso, axis=1)

# Flag: pedido entregue?
orders["pedido_entregue"] = orders["order_status"].apply(
    lambda x: 1 if x == "delivered" else 0
)

# ==========================================================
# 5. MERGE: ORDERS + CUSTOMERS
# ==========================================================
orders_customers = orders.merge(
    customers,
    on="customer_id",
    how="left"
)

# ==========================================================
# 6. MERGE: BASE ANALÍTICA INICIAL
#    ORDERS + CUSTOMERS + ORDER_ITEMS
# ==========================================================
base_analitica = orders_customers.merge(
    order_items,
    on="order_id",
    how="left"
)

# ==========================================================
# 7. CRIAR MÉTRICAS DE VALOR
# ==========================================================
base_analitica["valor_total_item"] = (
    base_analitica["price"] + base_analitica["freight_value"]
)

# Mês/ano para análises temporais
base_analitica["ano_mes"] = base_analitica["order_purchase_timestamp"].dt.to_period("M").astype(str)

# ==========================================================
# 8. INSPEÇÃO RÁPIDA PÓS-TRANSFORMAÇÃO
# ==========================================================
print("\n" + "=" * 80)
print("BASE ANALÍTICA - VISÃO GERAL")
print("=" * 80)
print(base_analitica.head())

print("\nDIMENSÃO DA BASE ANALÍTICA:")
print(base_analitica.shape)

print("\nTIPOS DE DADOS:")
print(base_analitica.dtypes)

print("\nNULOS NA BASE ANALÍTICA:")
print(base_analitica.isnull().sum().sort_values(ascending=False).head(15))

# ==========================================================
# 9. SALVAR ARQUIVOS TRATADOS
# ==========================================================
orders.to_csv(DADOS_TRATADOS / "orders_tratado.csv", index=False)
order_items.to_csv(DADOS_TRATADOS / "order_items_tratado.csv", index=False)
customers.to_csv(DADOS_TRATADOS / "customers_tratado.csv", index=False)
base_analitica.to_csv(DADOS_TRATADOS / "base_analitica_inicial.csv", index=False)

print("\nArquivos salvos com sucesso em /dados_tratados")


