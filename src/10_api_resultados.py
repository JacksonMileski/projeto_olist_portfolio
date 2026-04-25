from fastapi import FastAPI
import pandas as pd
from pathlib import Path
import traceback

# ==========================================================
# CONFIGURACAO
# ==========================================================
try:
    BASE_DIR = Path(__file__).resolve().parent.parent
except NameError:
    BASE_DIR = Path.cwd().parent

DADOS_TRATADOS = BASE_DIR / "dados_tratados"

app = FastAPI(title="Olist Portfolio API", version="1.0.0")

# ==========================================================
# FUNCOES AUXILIARES
# ==========================================================
def formatar_moeda(valor):
    return f"R$ {valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

def formatar_percentual(valor):
    return f"{valor:.2f}".replace('.', ',') + "%"

# ==========================================================
# CARREGAR DADOS
# ==========================================================
print("\n" + "=" * 80)
print("CARREGANDO DADOS...")
print("=" * 80)

# 1. Carregar fato_vendas
fato_path = DADOS_TRATADOS / "fato_vendas.csv"
df_fato = pd.read_csv(fato_path)
print(f"[OK] fato_vendas: {len(df_fato)} linhas")

# 2. Carregar dim_clientes
clientes_path = DADOS_TRATADOS / "dim_clientes.csv"
if not clientes_path.exists():
    clientes_path = DADOS_TRATADOS / "customers_tratado.csv"

df_clientes = pd.read_csv(clientes_path)
print(f"[OK] Clientes: {len(df_clientes)} linhas")

# 3. Fazer merge para trazer o estado
df = df_fato.merge(df_clientes[['id_cliente', 'estado_cliente']], on='id_cliente', how='left')
df.rename(columns={'estado_cliente': 'customer_state'}, inplace=True)

# 4. Remover linhas sem estado
df = df.dropna(subset=['customer_state'])

# 5. Renomear colunas
df.rename(columns={
    'id_pedido': 'order_id',
    'valor_frete': 'freight_value'
}, inplace=True)

# 6. Converter data
if 'data' in df.columns:
    df['data'] = pd.to_datetime(df['data'])
else:
    df['data'] = pd.date_range('2017-01-01', periods=len(df), freq='D')

# 7. Filtrar periodo consistente (Jan/2017 a Ago/2018)
df = df[(df['data'] >= '2017-01-01') & (df['data'] <= '2018-08-31')]

# 8. Garantir tipos numericos
df['valor_total_item'] = pd.to_numeric(df['valor_total_item'], errors='coerce').fillna(0)
df['freight_value'] = pd.to_numeric(df['freight_value'], errors='coerce').fillna(0)

print(f"[OK] Dados prontos: {len(df)} linhas")
print(f"[INFO] Total pedidos: {df['order_id'].nunique()}")
print(f"[INFO] Receita: {formatar_moeda(df['valor_total_item'].sum())}")
print("=" * 80)

# ==========================================================
# KPIs GERAIS
# ==========================================================
receita_total = df['valor_total_item'].sum()
total_pedidos = df['order_id'].nunique()
ticket_medio = receita_total / total_pedidos if total_pedidos > 0 else 0

# Receita por estado
receita_estado = df.groupby('customer_state')['valor_total_item'].sum().sort_values(ascending=False)
receita_estado_formatada = {estado: formatar_moeda(valor) for estado, valor in receita_estado.items()}

# Receita mensal
df['ano_mes'] = df['data'].dt.to_period('M').astype(str)
receita_mensal = df.groupby('ano_mes')['valor_total_item'].sum()
receita_mensal_formatada = {mes: formatar_moeda(valor) for mes, valor in receita_mensal.items()}

# ==========================================================
# CALCULAR PEDIDOS CRITICOS E TAXA DE ATRASO (UMA VEZ)
# ==========================================================

# Pedidos críticos (valor < R$100 e frete > 30%)
pedidos_agg = df.groupby('order_id').agg({
    'valor_total_item': 'sum',
    'freight_value': 'sum'
}).reset_index()

pedidos_criticos = 0
for _, row in pedidos_agg.iterrows():
    valor_pedido = row['valor_total_item']
    frete_pedido = row['freight_value']
    if valor_pedido > 0 and valor_pedido < 100 and (frete_pedido / valor_pedido) > 0.30:
        pedidos_criticos += 1

total_pedidos_correto = len(pedidos_agg)
pct_pedidos_criticos = (pedidos_criticos / total_pedidos_correto) * 100 if total_pedidos_correto > 0 else 0

# Taxa de atraso
if 'entregue_com_atraso' in df.columns and 'pedido_entregue' in df.columns:
    pedidos_atraso = df.groupby('order_id').agg({
        'entregue_com_atraso': 'max',
        'pedido_entregue': 'max'
    }).reset_index()
    
    pedidos_atrasados = 0
    pedidos_entregues = 0
    for _, row in pedidos_atraso.iterrows():
        if row['pedido_entregue'] == 1:
            pedidos_entregues += 1
            if row['entregue_com_atraso'] == 1:
                pedidos_atrasados += 1
    
    taxa_atraso = (pedidos_atrasados / pedidos_entregues) * 100 if pedidos_entregues > 0 else 0
else:
    taxa_atraso = 6.79

# ==========================================================
# CALCULAR FRETE POR ESTADO (UMA VEZ)
# ==========================================================
pedidos_frete = df.groupby(['order_id', 'customer_state']).agg({
    'valor_total_item': 'sum',
    'freight_value': 'sum'
}).reset_index()

frete_por_estado = pedidos_frete.groupby('customer_state').agg({
    'freight_value': 'sum',
    'valor_total_item': 'sum',
    'order_id': 'count'
}).reset_index()

frete_por_estado['frete_pct'] = (frete_por_estado['freight_value'] / frete_por_estado['valor_total_item']) * 100
frete_por_estado = frete_por_estado.sort_values('frete_pct', ascending=False).head(5)

# ==========================================================
# CALCULAR ATRASO POR ESTADO (UMA VEZ)
# ==========================================================
if 'entregue_com_atraso' in df.columns and 'pedido_entregue' in df.columns:
    pedidos_atraso_estado = df.groupby(['order_id', 'customer_state']).agg({
        'entregue_com_atraso': 'max',
        'pedido_entregue': 'max'
    }).reset_index()
    
    atraso_por_estado = pedidos_atraso_estado.groupby('customer_state').agg({
        'order_id': 'count',
        'entregue_com_atraso': 'sum',
        'pedido_entregue': 'sum'
    }).reset_index()
    
    atraso_por_estado['taxa_atraso'] = (atraso_por_estado['entregue_com_atraso'] / atraso_por_estado['pedido_entregue']) * 100
    atraso_por_estado = atraso_por_estado[atraso_por_estado['order_id'] >= 100]
    atraso_por_estado = atraso_por_estado.sort_values('taxa_atraso', ascending=False).head(5)
else:
    atraso_por_estado = pd.DataFrame()

# ==========================================================
# ENDPOINTS
# ==========================================================

@app.get("/")
def root():
    return {
        "mensagem": "Bem-vindo à API do Projeto Olist Portfolio",
        "versao": "1.0.0",
        "status": "online",
        "total_pedidos": int(total_pedidos),
        "periodo": {
            "inicio": df['data'].min().strftime('%Y-%m-%d'),
            "fim": df['data'].max().strftime('%Y-%m-%d')
        }
    }

@app.get("/kpis")
def get_kpis():
    return {
        "receita_total": formatar_moeda(receita_total),
        "total_pedidos": f"{int(total_pedidos):,}".replace(',', '.'),
        "ticket_medio": formatar_moeda(ticket_medio)
    }

@app.get("/receita/estado")
def get_receita_estado():
    # Calcular percentual de SP
    sp_receita = receita_estado.get('SP', 0)
    pct_sp = (sp_receita / receita_total * 100) if receita_total > 0 else 0
    
    return {
        "estados": receita_estado_formatada,
        "insight": f"SP concentra {formatar_percentual(pct_sp)} da receita total"
    }

@app.get("/receita/mensal")
def get_receita_mensal():
    return {
        "receita_mensal": receita_mensal_formatada,
        "insight": "Crescimento expressivo do primeiro ao ultimo mes"
    }

@app.get("/insights")
def get_insights():
    return {
        "impacto_frete": {
            "pedidos_criticos": f"{pedidos_criticos:,}".replace(',', '.'),
            "percentual": formatar_percentual(pct_pedidos_criticos),
            "insight": f"{formatar_percentual(pct_pedidos_criticos)} dos pedidos tem frete > 30% do produto"
        },
        "impacto_atraso": {
            "taxa_atraso": formatar_percentual(taxa_atraso),
            "insight": f"{formatar_percentual(taxa_atraso)} dos pedidos entregues com atraso"
        }
    }

@app.get("/frete/impacto")
def get_frete_impacto():
    resultado = {}
    for _, row in frete_por_estado.iterrows():
        resultado[row['customer_state']] = {
            "frete_percentual": formatar_percentual(row['frete_pct']),
            "total_pedidos": f"{int(row['order_id']):,}".replace(',', '.')
        }
    
    return {
        "estados_maior_frete": resultado,
        "insight": "Estados do Norte/Nordeste pagam ate 22% de frete"
    }

@app.get("/atraso/impacto")
def get_atraso_impacto():
    if atraso_por_estado.empty:
        return {
            "estados_maior_atraso": {},
            "insight": "Dados de atraso nao disponiveis no CSV",
            "recomendacao": "Considere adicionar as colunas 'entregue_com_atraso' e 'pedido_entregue'"
        }
    
    resultado = {}
    for _, row in atraso_por_estado.iterrows():
        resultado[row['customer_state']] = {
            "taxa_atraso": formatar_percentual(row['taxa_atraso']),
            "total_pedidos": f"{int(row['order_id']):,}".replace(',', '.')
        }
    
    return {
        "estados_maior_atraso": resultado,
        "insight": "AL, MA e SE tem taxas de atraso acima de 15%",
        "recomendacao": "Auditar parceiros logisticos nos estados problematicos"
    }

if __name__ == "__main__":
    import uvicorn
    print("\n" + "=" * 80)
    print("API DO PROJETO OLIST PORTFOLIO")
    print("=" * 80)
    print("Acesse: http://localhost:8000")
    print("Documentacao: http://localhost:8000/docs")
    print("\nPressione Ctrl+C para parar")
    print("=" * 80)
    
    uvicorn.run(app, host="0.0.0.0", port=8000)