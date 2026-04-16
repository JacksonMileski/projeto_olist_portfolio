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

# ==========================================================
# 2. CARREGAR BASE ANALÍTICA E TABELAS ORIGINAIS
# ==========================================================
base = pd.read_csv(
    DADOS_TRATADOS / "base_analitica_inicial.csv",
    parse_dates=[
        "order_purchase_timestamp",
        "order_approved_at",
        "order_delivered_carrier_date",
        "order_delivered_customer_date",
        "order_estimated_delivery_date",
        "shipping_limit_date"
    ]
)

products = pd.read_csv(DADOS_BRUTOS / "olist_products_dataset.csv")
sellers = pd.read_csv(DADOS_BRUTOS / "olist_sellers_dataset.csv")

# ==========================================================
# 3. ENRIQUECER BASE COM PRODUTOS
# ==========================================================
base = base.merge(
    products,
    on="product_id",
    how="left"
)

# ==========================================================
# 4. ENRIQUECER BASE COM SELLERS
# ==========================================================
base = base.merge(
    sellers,
    on="seller_id",
    how="left"
)

# ==========================================================
# 5. CRIAR CHAVE DE TEMPO
# ==========================================================
base["data_pedido"] = base["order_purchase_timestamp"].dt.date
base["ano"] = base["order_purchase_timestamp"].dt.year
base["mes"] = base["order_purchase_timestamp"].dt.month
base["nome_mes"] = base["order_purchase_timestamp"].dt.month_name()
base["trimestre"] = base["order_purchase_timestamp"].dt.quarter

# ==========================================================
# 6. DIMENSÃO CLIENTES
# ==========================================================
dim_clientes = (
    base[[
        "customer_unique_id",
        "customer_zip_code_prefix",
        "customer_city",
        "customer_state"
    ]]
    .drop_duplicates(subset=["customer_unique_id"])
    .dropna(subset=["customer_unique_id"])
    .reset_index(drop=True)
)

# ==========================================================
# 7. DIMENSÃO PRODUTOS
# ==========================================================
dim_produtos = (
    base[[
        "product_id",
        "product_category_name",
        "product_name_lenght",
        "product_description_lenght",
        "product_photos_qty",
        "product_weight_g",
        "product_length_cm",
        "product_height_cm",
        "product_width_cm"
    ]]
    .drop_duplicates()
    .dropna(subset=["product_id"])
    .reset_index(drop=True)
)

# ==========================================================
# 8. DIMENSÃO VENDEDORES
# ==========================================================
dim_vendedores = (
    base[[
        "seller_id",
        "seller_zip_code_prefix",
        "seller_city",
        "seller_state"
    ]]
    .drop_duplicates()
    .dropna(subset=["seller_id"])
    .reset_index(drop=True)
)

# ==========================================================
# 9. DIMENSÃO TEMPO
# ==========================================================
dim_tempo = (
    base[[
        "data_pedido",
        "ano",
        "mes",
        "nome_mes",
        "trimestre",
        "ano_mes"
    ]]
    .drop_duplicates()
    .dropna(subset=["data_pedido"])
    .sort_values("data_pedido")
    .reset_index(drop=True)
)

# ==========================================================
# 10. TABELA FATO VENDAS
# ==========================================================
fato_vendas = (
    base[[
        "order_id",
        "order_item_id",
        "product_id",
        "seller_id",
        "customer_unique_id",
        "data_pedido",
        "order_status",
        "price",
        "freight_value",
        "valor_total_item",
        "tempo_entrega_dias",
        "prazo_estimado_dias",
        "atraso_entrega_dias",
        "entregue_com_atraso",
        "pedido_entregue"
    ]]
    .copy()
)

# ==========================================================
# 11. AJUSTE DE NOMES DE COLUNAS (PORTUGUÊS MAIS PROFISSIONAL)
# ==========================================================
dim_clientes = dim_clientes.rename(columns={
    "customer_unique_id": "id_cliente",
    "customer_zip_code_prefix": "cep_prefixo_cliente",
    "customer_city": "cidade_cliente",
    "customer_state": "estado_cliente"
})

dim_produtos = dim_produtos.rename(columns={
    "product_id": "id_produto",
    "product_category_name": "categoria_produto",
    "product_name_lenght": "tamanho_nome_produto",
    "product_description_lenght": "tamanho_descricao_produto",
    "product_photos_qty": "qtd_fotos_produto",
    "product_weight_g": "peso_produto_g",
    "product_length_cm": "comprimento_produto_cm",
    "product_height_cm": "altura_produto_cm",
    "product_width_cm": "largura_produto_cm"
})

dim_vendedores = dim_vendedores.rename(columns={
    "seller_id": "id_vendedor",
    "seller_zip_code_prefix": "cep_prefixo_vendedor",
    "seller_city": "cidade_vendedor",
    "seller_state": "estado_vendedor"
})

dim_tempo = dim_tempo.rename(columns={
    "data_pedido": "data"
})

fato_vendas = fato_vendas.rename(columns={
    "order_id": "id_pedido",
    "order_item_id": "id_item_pedido",
    "product_id": "id_produto",
    "seller_id": "id_vendedor",
    "customer_unique_id": "id_cliente",
    "data_pedido": "data",
    "order_status": "status_pedido",
    "price": "valor_produto",
    "freight_value": "valor_frete",
    "valor_total_item": "valor_total_item",
    "tempo_entrega_dias": "tempo_entrega_dias",
    "prazo_estimado_dias": "prazo_estimado_dias",
    "atraso_entrega_dias": "atraso_entrega_dias",
    "entregue_com_atraso": "entregue_com_atraso",
    "pedido_entregue": "pedido_entregue"
})

# ==========================================================
# 12. SALVAR TABELAS FINAIS
# ==========================================================
dim_clientes.to_csv(DADOS_TRATADOS / "dim_clientes.csv", index=False)
dim_produtos.to_csv(DADOS_TRATADOS / "dim_produtos.csv", index=False)
dim_vendedores.to_csv(DADOS_TRATADOS / "dim_vendedores.csv", index=False)
dim_tempo.to_csv(DADOS_TRATADOS / "dim_tempo.csv", index=False)
fato_vendas.to_csv(DADOS_TRATADOS / "fato_vendas.csv", index=False)

# ==========================================================
# 13. EXIBIR RESUMO
# ==========================================================
print("\n" + "=" * 80)
print("MODELAGEM FINAL - TABELAS GERADAS")
print("=" * 80)

print(f"dim_clientes: {dim_clientes.shape}")
print(f"dim_produtos: {dim_produtos.shape}")
print(f"dim_vendedores: {dim_vendedores.shape}")
print(f"dim_tempo: {dim_tempo.shape}")
print(f"fato_vendas: {fato_vendas.shape}")

print("\nArquivos salvos com sucesso em /dados_tratados")

