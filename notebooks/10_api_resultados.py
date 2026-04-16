from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
import pandas as pd
from pathlib import Path
from typing import Optional
import uvicorn
from sqlalchemy import create_engine
import traceback
import os

# ==========================================================
# 1. CONFIGURAÇÃO
# ==========================================================
try:
    BASE_DIR = Path(__file__).resolve().parent.parent
except NameError:
    BASE_DIR = Path.cwd().parent

DADOS_TRATADOS = BASE_DIR / "dados_tratados"

# Configurações do PostgreSQL (compatível com Windows, Mac e Linux)
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "olist_portfolio")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "123")
SCHEMA_NAME = os.getenv("SCHEMA_NAME", "portfolio")

# Criar conexão
engine = create_engine(f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}")

app = FastAPI(
    title="Olist Portfolio API",
    description="API para consulta de dados do projeto Olist",
    version="1.0.0"
)

# ==========================================================
# 2. FUNÇÃO AUXILIAR PARA FORMATAR MOEDA
# ==========================================================
def formatar_moeda(valor):
    """Formata valor no padrão brasileiro (R$ 1.234,56)"""
    return f"R$ {valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

def formatar_percentual(valor):
    """Formata percentual no padrão brasileiro (12,34%)"""
    return f"{valor:.2f}".replace('.', ',') + "%"

# ==========================================================
# 3. CARREGAR DADOS DO POSTGRESQL
# ==========================================================
print("\n" + "=" * 80)
print("CARREGANDO DADOS DO POSTGRESQL...")
print("=" * 80)

query = """
SELECT 
    fv.id_pedido,
    fv.valor_total_item,
    fv.valor_frete,
    fv.valor_produto,
    fv.entregue_com_atraso,
    fv.pedido_entregue,
    fv.data,
    dc.estado_cliente,
    dc.cidade_cliente
FROM portfolio.fato_vendas fv
LEFT JOIN portfolio.dim_clientes dc ON fv.id_cliente = dc.id_cliente
WHERE fv.data BETWEEN '2017-01-01' AND '2018-08-31'
"""

df_vendas = pd.read_sql(query, engine)

# Renomear colunas para compatibilidade
df_vendas.rename(columns={
    'id_pedido': 'order_id',
    'estado_cliente': 'customer_state',
    'cidade_cliente': 'customer_city',
    'valor_produto': 'price',
    'valor_frete': 'freight_value'
}, inplace=True)

# Converter data para datetime
df_vendas['data'] = pd.to_datetime(df_vendas['data'])

print(f"Dados carregados: {df_vendas.shape[0]} linhas, {df_vendas.shape[1]} colunas")

# ==========================================================
# 4. KPIs GERAIS
# ==========================================================
receita_total = df_vendas['valor_total_item'].sum()
total_pedidos = df_vendas['order_id'].nunique()
ticket_medio = receita_total / total_pedidos if total_pedidos > 0 else 0

# Receita por estado
receita_estado = df_vendas.groupby('customer_state')['valor_total_item'].sum().sort_values(ascending=False).head(10)
receita_estado_formatada = {estado: formatar_moeda(valor) for estado, valor in receita_estado.items()}

# Receita mensal
df_vendas['ano_mes'] = df_vendas['data'].dt.to_period('M').astype(str)
receita_mensal = df_vendas[(df_vendas['ano_mes'] >= '2017-01') & (df_vendas['ano_mes'] <= '2018-08')].groupby('ano_mes')['valor_total_item'].sum()
receita_mensal_formatada = {mes: formatar_moeda(valor) for mes, valor in receita_mensal.items()}

# ==========================================================
# 5. ENDPOINTS
# ==========================================================

@app.get("/")
def root():
    return {
        "mensagem": "Bem-vindo à API do Projeto Olist Portfolio",
        "versao": "1.0.0",
        "endpoints_disponiveis": {
            "/kpis": "KPIs gerais do negocio",
            "/receita/estado": "Receita por estado",
            "/receita/mensal": "Receita mensal",
            "/insights": "Insights de negocio",
            "/frete/impacto": "Impacto do frete",
            "/atraso/impacto": "Impacto dos atrasos"
        }
    }

@app.get("/kpis")
def get_kpis_formatado():
    return {
        "receita_total": formatar_moeda(receita_total),
        "total_pedidos": f"{total_pedidos:,}".replace(',', '.'),
        "ticket_medio": formatar_moeda(ticket_medio)
    }

@app.get("/receita/estado")
def get_receita_estado_formatado():
    return {
        "estados": receita_estado_formatada,
        "insight": "SP concentra 37% da receita total"
    }

@app.get("/receita/mensal")
def get_receita_mensal_formatado():
    return {
        "receita_mensal": receita_mensal_formatada,
        "insight": "Crescimento expressivo do primeiro ao ultimo mes"
    }

@app.get("/insights")
def get_insights():
    try:
        # ==========================================================
        # PEDIDOS CRÍTICOS
        # ==========================================================
        # Agrupar por pedido
        pedidos_agg = df_vendas.groupby('order_id').agg({
            'valor_total_item': 'sum',
            'freight_value': 'sum'
        }).reset_index()
        
        # Calcular pedidos críticos
        pedidos_criticos = 0
        for _, row in pedidos_agg.iterrows():
            valor_pedido = row['valor_total_item']
            frete_pedido = row['freight_value']
            # Verificar se valor_pedido > 0 para evitar divisão por zero
            if valor_pedido > 0 and valor_pedido < 100 and (frete_pedido / valor_pedido) > 0.30:
                pedidos_criticos += 1
        
        total_pedidos_correto = len(pedidos_agg)
        pct_pedidos_criticos = (pedidos_criticos / total_pedidos_correto) * 100 if total_pedidos_correto > 0 else 0
        
        # ==========================================================
        # TAXA DE ATRASO
        # ==========================================================
        # Agrupar por pedido
        pedidos_atraso = df_vendas.groupby('order_id').agg({
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
    except Exception as e:
        print(f"ERRO: {str(e)}")
        print(traceback.format_exc())
        return {"erro": str(e)}

@app.get("/frete/impacto")
def get_frete_impacto():
    # ==========================================================
    # FRETE POR ESTADO - Cálculo correto (frete total / valor total)
    # ==========================================================
    # Primeiro, agrupar por pedido para ter o valor total por pedido
    pedidos_frete = df_vendas.groupby(['order_id', 'customer_state']).agg({
        'valor_total_item': 'sum',
        'freight_value': 'sum'
    }).reset_index()
    
    # Agrupar por estado: soma total de frete e soma total de valor
    frete_por_estado = pedidos_frete.groupby('customer_state').agg({
        'freight_value': 'sum',
        'valor_total_item': 'sum',
        'order_id': 'count'
    }).reset_index()
    
    # Calcular percentual correto: (frete total / valor total) * 100
    frete_por_estado['frete_pct'] = (frete_por_estado['freight_value'] / frete_por_estado['valor_total_item']) * 100
    
    frete_por_estado = frete_por_estado.sort_values('frete_pct', ascending=False).head(5)
    
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

@app.get("/kpis/raw", include_in_schema=False)
def get_kpis_raw():
    return {
        "receita_total": round(receita_total, 2),
        "total_pedidos": int(total_pedidos),
        "ticket_medio": round(ticket_medio, 2)
    }

# ==========================================================
# ENDPOINT DE ATRASO - CORRIGIDO
# ==========================================================
@app.get("/atraso/impacto")
def get_atraso_impacto():
    # ==========================================================
    # TAXA DE ATRASO POR ESTADO
    # ==========================================================
    # Calcular taxa de atraso por estado (agrupando por pedido)
    pedidos_atraso = df_vendas.groupby(['order_id', 'customer_state']).agg({
        'entregue_com_atraso': 'max',
        'pedido_entregue': 'max'
    }).reset_index()
    
    # Agrupar por estado
    atraso_por_estado = pedidos_atraso.groupby('customer_state').agg({
        'order_id': 'count',
        'entregue_com_atraso': 'sum',
        'pedido_entregue': 'sum'
    }).reset_index()
    
    # Calcular taxa de atraso por estado (apenas estados com >= 100 pedidos)
    atraso_por_estado['taxa_atraso'] = (atraso_por_estado['entregue_com_atraso'] / atraso_por_estado['pedido_entregue']) * 100
    atraso_por_estado = atraso_por_estado[atraso_por_estado['order_id'] >= 100]
    atraso_por_estado = atraso_por_estado.sort_values('taxa_atraso', ascending=False).head(5)
    
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

# ==========================================================
# 6. EXECUTAR API
# ==========================================================
if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("API DO PROJETO OLIST PORTFOLIO")
    print("=" * 80)
    print("Acesse: http://localhost:8000")
    print("Documentacao: http://localhost:8000/docs")
    print("\nEndpoints disponiveis:")
    print("  /kpis           - KPIs formatados")
    print("  /receita/estado - Receita por estado")
    print("  /receita/mensal - Receita mensal")
    print("  /insights       - Insights de negocio")
    print("  /frete/impacto  - Impacto do frete")
    print("  /atraso/impacto - Impacto dos atrasos")
    print("  /kpis/raw       - KPIs brutos (oculto)")
    print("\nPressione Ctrl+C para parar")
    print("=" * 80)
    
    uvicorn.run(app, host="0.0.0.0", port=8000)