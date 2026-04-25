import pandas as pd
import psycopg2
from pathlib import Path
from sqlalchemy import create_engine

# ==========================================================
# 1. CONFIGURAÇÃO DE CAMINHOS E CONEXÃO
# ==========================================================
try:
    BASE_DIR = Path(__file__).resolve().parent.parent
except NameError:
    BASE_DIR = Path.cwd().parent

DADOS_TRATADOS = BASE_DIR / "dados_tratados"

# Configurações do PostgreSQL
DB_HOST = "localhost"
DB_PORT = "5432"
DB_NAME = "olist_portfolio"
DB_USER = "postgres"
DB_PASSWORD = "123"
SCHEMA_NAME = "portfolio"

# Criar conexão
engine = create_engine(f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}")

# ==========================================================
# 2. CARREGAR DADOS DO POSTGRESQL
# ==========================================================
print("\n" + "=" * 80)
print("CARREGANDO DADOS DO POSTGRESQL...")
print("=" * 80)

# Query com as colunas corretas
query = """
SELECT 
    fv.id_pedido,
    fv.id_item_pedido,
    fv.id_produto,
    fv.id_vendedor,
    fv.id_cliente,
    fv.data,
    fv.status_pedido,
    fv.valor_produto,
    fv.valor_frete,
    fv.valor_total_item,
    fv.tempo_entrega_dias,
    fv.prazo_estimado_dias,
    fv.atraso_entrega_dias,
    fv.entregue_com_atraso,
    fv.pedido_entregue,
    dc.id_cliente,
    dc.cidade_cliente,
    dc.estado_cliente,
    dp.categoria_produto,
    dv.cidade_vendedor,
    dv.estado_vendedor,
    dt.ano,
    dt.mes,
    dt.ano_mes
FROM portfolio.fato_vendas fv
LEFT JOIN portfolio.dim_clientes dc ON fv.id_cliente = dc.id_cliente
LEFT JOIN portfolio.dim_produtos dp ON fv.id_produto = dp.id_produto
LEFT JOIN portfolio.dim_vendedores dv ON fv.id_vendedor = dv.id_vendedor
LEFT JOIN portfolio.dim_tempo dt ON fv.data = dt.data
WHERE dt.ano_mes BETWEEN '2017-01' AND '2018-08'
"""

base = pd.read_sql(query, engine)

print(f"Base carregada: {base.shape[0]} linhas, {base.shape[1]} colunas")

# ==========================================================
# 3. CRIAR BASE DE PEDIDOS (SEM DUPLICAR PEDIDOS)
# ==========================================================
base_pedidos = base.drop_duplicates(subset=["id_pedido"]).copy()

# ==========================================================
# 4. KPIs GERAIS
# ==========================================================
receita_total = base["valor_total_item"].sum()
total_pedidos = base_pedidos["id_pedido"].nunique()

# Ticket médio por pedido
receita_por_pedido = base.groupby("id_pedido")["valor_total_item"].sum()
ticket_medio_pedido = receita_por_pedido.mean()

# Ticket médio por item
ticket_medio_item = base["valor_total_item"].mean()

# Pedidos entregues
pedidos_entregues = base_pedidos["pedido_entregue"].sum()
percentual_entregues = (pedidos_entregues / total_pedidos) * 100 if total_pedidos > 0 else 0

# Pedidos com atraso (considerando apenas pedidos entregues)
pedidos_entregues_df = base_pedidos[base_pedidos["pedido_entregue"] == 1].copy()
pedidos_com_atraso = pedidos_entregues_df["entregue_com_atraso"].fillna(0).sum()
percentual_atraso = (pedidos_com_atraso / len(pedidos_entregues_df)) * 100 if len(pedidos_entregues_df) > 0 else 0

# ==========================================================
# 5. VENDAS POR MÊS
# ==========================================================
vendas_mensais = (
    base.groupby("ano_mes")["valor_total_item"]
    .sum()
    .reset_index()
    .sort_values("ano_mes")
)

# ==========================================================
# 6. TOP ESTADOS POR RECEITA
# ==========================================================
top_estados_receita = (
    base.groupby("estado_cliente")["valor_total_item"]
    .sum()
    .reset_index()
    .sort_values("valor_total_item", ascending=False)
    .head(10)
)

# ==========================================================
# 7. TOP CIDADES POR NÚMERO DE PEDIDOS
# ==========================================================
top_cidades_pedidos = (
    base_pedidos.groupby("cidade_cliente")["id_pedido"]
    .nunique()
    .reset_index()
    .sort_values("id_pedido", ascending=False)
    .head(10)
)

# ==========================================================
# 8. EXIBIR KPIs
# ==========================================================
print("\n" + "=" * 80)
print("KPIs GERAIS")
print("=" * 80)

print(f"Receita Total: R$ {receita_total:,.2f}")
print(f"Total de Pedidos: {total_pedidos:,}")
print(f"Ticket Médio por Pedido: R$ {ticket_medio_pedido:,.2f}")
print(f"Ticket Médio por Item: R$ {ticket_medio_item:,.2f}")
print(f"Pedidos Entregues: {pedidos_entregues:,}")
print(f"% Pedidos Entregues: {percentual_entregues:.2f}%")
print(f"Pedidos com Atraso: {pedidos_com_atraso:,}")
print(f"% Pedidos com Atraso (entre entregues): {percentual_atraso:.2f}%")

# ==========================================================
# 9. EXIBIR TABELAS RESUMO
# ==========================================================
print("\n" + "=" * 80)
print("VENDAS MENSAIS (TOP 12)")
print("=" * 80)
print(vendas_mensais.head(12))

print("\n" + "=" * 80)
print("TOP 10 ESTADOS POR RECEITA")
print("=" * 80)
print(top_estados_receita)

print("\n" + "=" * 80)
print("TOP 10 CIDADES POR PEDIDOS")
print("=" * 80)
print(top_cidades_pedidos)

# ==========================================================
# 10. SALVAR RESULTADOS (opcional)
# ==========================================================
vendas_mensais.to_csv(DADOS_TRATADOS / "vendas_mensais.csv", index=False)
top_estados_receita.to_csv(DADOS_TRATADOS / "top_estados_receita.csv", index=False)
top_cidades_pedidos.to_csv(DADOS_TRATADOS / "top_cidades_pedidos.csv", index=False)

print("\nArquivos salvos em /dados_tratados")