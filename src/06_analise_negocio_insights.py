import pandas as pd
import numpy as np
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy import text

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
# 2. CARREGAR DADOS DO POSTGRESQL (COM FILTRO - 2017-01 a 2018-08)
# ==========================================================
print("\n" + "=" * 80)
print("CARREGANDO DADOS DO POSTGRESQL (2017-01 a 2018-08)...")
print("=" * 80)

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
    dc.estado_cliente,
    dc.cidade_cliente,
    dp.categoria_produto,
    dv.estado_vendedor,
    dt.ano_mes,
    dt.ano,
    dt.mes
FROM portfolio.fato_vendas fv
LEFT JOIN portfolio.dim_clientes dc ON fv.id_cliente = dc.id_cliente
LEFT JOIN portfolio.dim_produtos dp ON fv.id_produto = dp.id_produto
LEFT JOIN portfolio.dim_vendedores dv ON fv.id_vendedor = dv.id_vendedor
LEFT JOIN portfolio.dim_tempo dt ON fv.data = dt.data
WHERE dt.ano_mes BETWEEN '2017-01' AND '2018-08'
"""

df = pd.read_sql(query, engine)

print(f"Dados carregados: {df.shape[0]} linhas, {df.shape[1]} colunas")

# ==========================================================
# 3. PREPARAÇÃO DOS DADOS
# ==========================================================
for col in ["valor_produto", "valor_frete", "valor_total_item", "tempo_entrega_dias", "atraso_entrega_dias"]:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

if "entregue_com_atraso" not in df.columns:
    df["entregue_com_atraso"] = np.where(df["atraso_entrega_dias"] > 0, 1, 0)

if "pedido_entregue" not in df.columns:
    df["pedido_entregue"] = np.where(df["pedido_entregue"] == 1, 1, 0)

df["peso_frete_pct"] = np.where(
    df["valor_produto"] > 0,
    (df["valor_frete"] / df["valor_produto"]) * 100,
    np.nan
)

# ==========================================================
# 4. BASE DE PEDIDOS ÚNICOS
# ==========================================================
pedidos = (
    df.groupby("id_pedido", as_index=False)
      .agg({
          "valor_total_item": "sum",
          "valor_frete": "sum",
          "estado_cliente": "first",
          "cidade_cliente": "first",
          "entregue_com_atraso": "max",
          "pedido_entregue": "max",
          "tempo_entrega_dias": "mean",
          "data": "first"
      })
)

pedidos["peso_frete_pedido_pct"] = np.where(
    pedidos["valor_total_item"] > 0,
    (pedidos["valor_frete"] / pedidos["valor_total_item"]) * 100,
    np.nan
)

pedidos["pedido_critico"] = np.where(
    (pedidos["valor_total_item"] < 100) & (pedidos["peso_frete_pedido_pct"] > 30),
    1,
    0
)

# ==========================================================
# 5. KPI BASE
# ==========================================================
receita_total = df["valor_total_item"].sum()
total_pedidos = pedidos["id_pedido"].nunique()
ticket_medio = pedidos["valor_total_item"].mean()
peso_frete_medio = pedidos["peso_frete_pedido_pct"].mean()

# ==========================================================
# 6. CRESCIMENTO MENSAL
# ==========================================================
vendas_mensais = (
    df.groupby("ano_mes", as_index=False)["valor_total_item"]
      .sum()
      .sort_values("ano_mes")
      .copy()
)

vendas_mensais = vendas_mensais[vendas_mensais["valor_total_item"] > 0].copy()

vendas_mensais["crescimento_mom_pct"] = (
    vendas_mensais["valor_total_item"].pct_change() * 100
)

crescimentos_validos = vendas_mensais["crescimento_mom_pct"].dropna()

if len(crescimentos_validos) >= 5:
    p5 = crescimentos_validos.quantile(0.05)
    p95 = crescimentos_validos.quantile(0.95)
    crescimentos_filtrados = crescimentos_validos[
        (crescimentos_validos >= p5) & (crescimentos_validos <= p95)
    ]
else:
    crescimentos_filtrados = crescimentos_validos

crescimento_medio = crescimentos_filtrados.mean()

primeiro_mes = vendas_mensais.iloc[0]
ultimo_mes = vendas_mensais.iloc[-1]

# ==========================================================
# 7. CONCENTRAÇÃO DE RECEITA POR ESTADO
# ==========================================================
receita_estado = (
    df.groupby("estado_cliente", as_index=False)["valor_total_item"]
      .sum()
      .sort_values("valor_total_item", ascending=False)
)

top5_estados = receita_estado.head(5).copy()
top5_estados["participacao_pct"] = (top5_estados["valor_total_item"] / receita_total) * 100
participacao_top5_estados = top5_estados["participacao_pct"].sum()

# ==========================================================
# 8. CONCENTRAÇÃO DE RECEITA POR VENDEDOR
# ==========================================================
receita_vendedor = (
    df.groupby("id_vendedor", as_index=False)["valor_total_item"]
      .sum()
      .sort_values("valor_total_item", ascending=False)
)

top10_vendedores = receita_vendedor.head(10).copy()
top10_vendedores["participacao_pct"] = (top10_vendedores["valor_total_item"] / receita_total) * 100
participacao_top10_vendedores = top10_vendedores["participacao_pct"].sum()

# ==========================================================
# 9. FRETE COMO RISCO DE EFICIÊNCIA
# ==========================================================
pedidos_criticos = pedidos["pedido_critico"].sum()
pct_pedidos_criticos = (pedidos_criticos / total_pedidos) * 100

frete_por_estado = (
    pedidos.groupby("estado_cliente", as_index=False)
          .agg({
              "valor_total_item": "sum",
              "valor_frete": "sum"
          })
)

frete_por_estado["peso_frete_pct"] = np.where(
    frete_por_estado["valor_total_item"] > 0,
    (frete_por_estado["valor_frete"] / frete_por_estado["valor_total_item"]) * 100,
    np.nan
)

top5_estados_frete_pesado = frete_por_estado.sort_values("peso_frete_pct", ascending=False).head(5)

# ==========================================================
# 10. ATRASO POR ESTADO
# ==========================================================
atraso_estado = (
    pedidos[pedidos["pedido_entregue"] == 1]
    .groupby("estado_cliente", as_index=False)
    .agg({
        "id_pedido": "count",
        "entregue_com_atraso": "sum",
        "tempo_entrega_dias": "mean"
    })
)

atraso_estado["taxa_atraso_pct"] = (
    atraso_estado["entregue_com_atraso"] / atraso_estado["id_pedido"]
) * 100

top5_estados_atraso = atraso_estado.sort_values("taxa_atraso_pct", ascending=False).head(5)

taxa_atraso_geral = (
    pedidos[pedidos["pedido_entregue"] == 1]["entregue_com_atraso"].mean()
) * 100

# ==========================================================
# 11. MESES DE QUEDA DE RECEITA
# ==========================================================
meses_queda = vendas_mensais[vendas_mensais["crescimento_mom_pct"] < 0].copy()
qtd_meses_queda = len(meses_queda)

# ==========================================================
# 12. IMPRESSÃO PROFISSIONAL
# ==========================================================
print("\n" + "=" * 80)
print("ANALISE DE NEGOCIO - INSIGHTS E RECOMENDACOES")
print("=" * 80)

print(f"\nReceita Total: R$ {receita_total:,.2f}")
print(f"Total de Pedidos: {total_pedidos:,}")
print(f"Ticket Medio por Pedido: R$ {ticket_medio:,.2f}")
print(f"Peso Medio do Frete por Pedido: {peso_frete_medio:.2f}%")

# ----------------------------------------------------------
print("\n" + "=" * 80)
print("1. CRESCIMENTO E SAZONALIDADE")
print("=" * 80)
print(f"Primeiro mes da serie: {primeiro_mes['ano_mes']} | Receita: R$ {primeiro_mes['valor_total_item']:,.2f}")
print(f"Ultimo mes da serie:   {ultimo_mes['ano_mes']} | Receita: R$ {ultimo_mes['valor_total_item']:,.2f}")
print(f"Crescimento medio mes a mes (MoM): {crescimento_medio:.2f}%")
print(f"Quantidade de meses com queda de receita: {qtd_meses_queda}")

# ----------------------------------------------------------
print("\n" + "=" * 80)
print("2. CONCENTRACAO GEOGRAFICA DA RECEITA")
print("=" * 80)
print(f"Top 5 estados concentram {participacao_top5_estados:.2f}% da receita total.\n")
print("Top 5 estados por receita:")
print(top5_estados.to_string(index=False))

# ----------------------------------------------------------
print("\n" + "=" * 80)
print("3. CONCENTRACAO DE RECEITA POR VENDEDORES")
print("=" * 80)
print(f"Top 10 vendedores concentram {participacao_top10_vendedores:.2f}% da receita total.\n")
print("Top 10 vendedores por receita:")
print(top10_vendedores.to_string(index=False))

# ----------------------------------------------------------
print("\n" + "=" * 80)
print("4. EFICIENCIA COMERCIAL / IMPACTO DO FRETE")
print("=" * 80)
print(f"Pedidos criticos (ticket < R$100 e frete > 30% do pedido): {pedidos_criticos:,}")
print(f"% de pedidos criticos: {pct_pedidos_criticos:.2f}%")
print(f"Peso medio do frete sobre o pedido: {peso_frete_medio:.2f}%\n")

print("Top 5 estados com maior peso relativo de frete:")
print(top5_estados_frete_pesado[["estado_cliente", "peso_frete_pct"]].to_string(index=False))

# ----------------------------------------------------------
print("\n" + "=" * 80)
print("5. EFICIENCIA OPERACIONAL / ATRASOS")
print("=" * 80)
print(f"Taxa geral de atraso (entre pedidos entregues): {taxa_atraso_geral:.2f}%\n")

print("Top 5 estados com maior taxa de atraso:")
print(top5_estados_atraso[["estado_cliente", "id_pedido", "taxa_atraso_pct", "tempo_entrega_dias"]].to_string(index=False))

# ----------------------------------------------------------
print("\n" + "=" * 80)
print("6. RECOMENDACOES DE NEGOCIO")
print("=" * 80)

print("\nRECOMENDACAO 1:")
print("- Revisar politica de frete para pedidos de baixo ticket, pois pedidos com valor menor que R$100 e frete proporcionalmente alto podem reduzir competitividade comercial.")

print("\nRECOMENDACAO 2:")
print("- Priorizar analise logistica nos estados com maior taxa de atraso, pois atrasos recorrentes impactam experiencia do cliente e potencial recompra.")

print("\nRECOMENDACAO 3:")
print("- Monitorar a concentracao de receita em poucos estados e poucos vendedores para reduzir risco operacional e dependencia comercial.")

print("\nRECOMENDACAO 4:")
print("- Investigar meses com queda de receita para identificar sazonalidade, campanhas ineficientes ou gargalos operacionais.")

print("\nRECOMENDACAO 5:")
print("- Criar indicadores continuos em Power BI para acompanhar: receita mensal, taxa de atraso, peso do frete, ticket medio e concentracao de receita.")

print("\n" + "=" * 80)
print("FIM DA ANALISE")
print("=" * 80)

# ==========================================================
# 13. SALVAR RESULTADOS
# ==========================================================
vendas_mensais.to_csv(DADOS_TRATADOS / "vendas_mensais.csv", index=False)
top5_estados.to_csv(DADOS_TRATADOS / "top_estados_receita.csv", index=False)
pedidos.to_csv(DADOS_TRATADOS / "pedidos_analise.csv", index=False)

print("\nArquivos salvos em /dados_tratados")