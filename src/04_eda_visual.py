import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from sqlalchemy import create_engine

# ==========================================================
# 1. CONFIGURAÇÕES VISUAIS
# ==========================================================
sns.set_theme(style="whitegrid")
plt.rcParams["figure.figsize"] = (12, 6)

# ==========================================================
# 2. CAMINHOS E CONEXÃO
# ==========================================================
try:
    BASE_DIR = Path(__file__).resolve().parent.parent
except NameError:
    BASE_DIR = Path.cwd().parent

DADOS_TRATADOS = BASE_DIR / "dados_tratados"
PASTA_GRAFICOS = BASE_DIR / "graficos"

PASTA_GRAFICOS.mkdir(exist_ok=True)

# Configurações do PostgreSQL
DB_HOST = "localhost"
DB_PORT = "5432"
DB_NAME = "olist_portfolio"
DB_USER = "postgres"
DB_PASSWORD = "123"

# Criar conexão
engine = create_engine(f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}")

# ==========================================================
# 3. CARREGAR DADOS DO POSTGRESQL
# ==========================================================
print("\n" + "=" * 80)
print("CARREGANDO DADOS DO POSTGRESQL...")
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
    dt.ano_mes,
    dt.ano,
    dt.mes
FROM portfolio.fato_vendas fv
LEFT JOIN portfolio.dim_clientes dc ON fv.id_cliente = dc.id_cliente
LEFT JOIN portfolio.dim_produtos dp ON fv.id_produto = dp.id_produto
LEFT JOIN portfolio.dim_tempo dt ON fv.data = dt.data
WHERE dt.ano_mes BETWEEN '2017-01' AND '2018-08'
"""

base = pd.read_sql(query, engine)

print(f"Base carregada: {base.shape[0]} linhas, {base.shape[1]} colunas")

# Renomear colunas para compatibilidade com os gráficos existentes
base.rename(columns={
    'id_pedido': 'order_id',
    'estado_cliente': 'customer_state',
    'cidade_cliente': 'customer_city',
    'valor_produto': 'price',
    'valor_frete': 'freight_value'
}, inplace=True)

# ==========================================================
# 4. BASE SEM DUPLICIDADE DE PEDIDOS
# ==========================================================
base_pedidos = base.drop_duplicates(subset=["order_id"]).copy()

# ==========================================================
# 5. GRÁFICO 1 - EVOLUÇÃO DA RECEITA MENSAL
# ==========================================================
vendas_mensais = (
    base.groupby("ano_mes")["valor_total_item"]
    .sum()
    .reset_index()
    .sort_values("ano_mes")
)

plt.figure()
sns.lineplot(data=vendas_mensais, x="ano_mes", y="valor_total_item", marker="o")
plt.title("Evolução da Receita Mensal")
plt.xlabel("Ano-Mês")
plt.ylabel("Receita (R$)")
plt.xticks(rotation=45)
plt.tight_layout()
plt.savefig(PASTA_GRAFICOS / "01_receita_mensal.png", dpi=300)
plt.close()

# ==========================================================
# 6. GRÁFICO 2 - TOP 10 ESTADOS POR RECEITA
# ==========================================================
top_estados = (
    base.groupby("customer_state")["valor_total_item"]
    .sum()
    .reset_index()
    .sort_values("valor_total_item", ascending=False)
    .head(10)
)

plt.figure()
sns.barplot(data=top_estados, x="customer_state", y="valor_total_item")
plt.title("Top 10 Estados por Receita")
plt.xlabel("Estado")
plt.ylabel("Receita (R$)")
plt.tight_layout()
plt.savefig(PASTA_GRAFICOS / "02_top_estados_receita.png", dpi=300)
plt.close()

# ==========================================================
# 7. GRÁFICO 3 - TOP 10 CIDADES POR PEDIDOS
# ==========================================================
# Padronizar nomes das cidades
correcao_cidades = {
    "sao paulo": "São Paulo",
    "rio de janeiro": "Rio de Janeiro",
    "belo horizonte": "Belo Horizonte",
    "brasilia": "Brasília",
    "curitiba": "Curitiba",
    "campinas": "Campinas",
    "porto alegre": "Porto Alegre",
    "salvador": "Salvador",
    "guarulhos": "Guarulhos",
    "sao bernardo do campo": "São Bernardo do Campo"
}

base_pedidos_cidades = base_pedidos.copy()

base_pedidos_cidades["customer_city"] = (
    base_pedidos_cidades["customer_city"]
    .str.strip()
    .str.lower()
    .replace(correcao_cidades)
)

top_cidades = (
    base_pedidos_cidades.groupby("customer_city")["order_id"]
    .nunique()
    .reset_index()
    .sort_values("order_id", ascending=False)
    .head(10)
)

plt.figure()
sns.barplot(data=top_cidades, x="order_id", y="customer_city")
plt.title("Top 10 Cidades por Número de Pedidos")
plt.xlabel("Quantidade de Pedidos")
plt.ylabel("Cidade")
plt.tight_layout()
plt.savefig(PASTA_GRAFICOS / "03_top_cidades_pedidos.png", dpi=300)
plt.close()

# ==========================================================
# 8. GRÁFICO 4 - DISTRIBUIÇÃO DO TICKET POR PEDIDO
# ==========================================================
receita_por_pedido = (
    base.groupby("order_id")["valor_total_item"]
    .sum()
    .reset_index()
    .rename(columns={"valor_total_item": "receita_pedido"})
)

plt.figure()
sns.histplot(receita_por_pedido["receita_pedido"], bins=50, kde=True)
plt.title("Distribuição do Ticket por Pedido")
plt.xlabel("Ticket por Pedido (R$)")
plt.ylabel("Frequência")
plt.tight_layout()
plt.savefig(PASTA_GRAFICOS / "04_distribuicao_ticket_pedido.png", dpi=300)
plt.close()

# ==========================================================
# 9. GRÁFICO 5 - DISTRIBUIÇÃO DO TEMPO DE ENTREGA
# ==========================================================
entregues = base_pedidos[base_pedidos["pedido_entregue"] == 1].copy()

plt.figure()
sns.histplot(entregues["tempo_entrega_dias"].dropna(), bins=40, kde=True)
plt.title("Distribuição do Tempo de Entrega")
plt.xlabel("Tempo de Entrega (dias)")
plt.ylabel("Frequência")
plt.tight_layout()
plt.savefig(PASTA_GRAFICOS / "05_distribuicao_tempo_entrega.png", dpi=300)
plt.close()

# ==========================================================
# 10. GRÁFICO 6 - ENTREGUES VS NÃO ENTREGUES
# ==========================================================
status_entrega = base_pedidos["pedido_entregue"].value_counts().sort_index()
labels_entrega = ["Não Entregue", "Entregue"]

plt.figure()
plt.pie(status_entrega, labels=labels_entrega, autopct="%1.1f%%", startangle=90)
plt.title("Pedidos Entregues vs Não Entregues")
plt.tight_layout()
plt.savefig(PASTA_GRAFICOS / "06_entregues_vs_nao_entregues.png", dpi=300)
plt.close()

# ==========================================================
# 11. GRÁFICO 7 - ATRASO VS NO PRAZO (SOMENTE ENTREGUES)
# ==========================================================
atraso_counts = entregues["entregue_com_atraso"].value_counts().sort_index()
labels_atraso = ["No Prazo", "Com Atraso"]

plt.figure()
plt.pie(atraso_counts, labels=labels_atraso, autopct="%1.1f%%", startangle=90)
plt.title("Pedidos Entregues: No Prazo vs Com Atraso")
plt.tight_layout()
plt.savefig(PASTA_GRAFICOS / "07_atraso_vs_prazo.png", dpi=300)
plt.close()

# ==========================================================
# 12. RESUMO FINAL
# ==========================================================
print("\n" + "=" * 80)
print("GRAFICOS GERADOS COM SUCESSO")
print("=" * 80)

arquivos = sorted(PASTA_GRAFICOS.glob("*.png"))
for arquivo in arquivos:
    print(arquivo.name)

print(f"\nTotal de graficos gerados: {len(arquivos)}")
print(f"Pasta de saida: {PASTA_GRAFICOS}")
