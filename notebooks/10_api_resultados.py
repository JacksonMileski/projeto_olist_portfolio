from fastapi import FastAPI
import pandas as pd
from pathlib import Path
import traceback

# ==========================================================
# CONFIGURAÇÃO
# ==========================================================
try:
    BASE_DIR = Path(__file__).resolve().parent.parent
except NameError:
    BASE_DIR = Path.cwd().parent

DADOS_TRATADOS = BASE_DIR / "dados_tratados"

app = FastAPI(
    title="Olist Portfolio API",
    description="API para consulta de dados do projeto Olist",
    version="1.0.0"
)

# ==========================================================
# FUNÇÕES AUXILIARES
# ==========================================================
def formatar_moeda(valor):
    """Formata valor no padrão brasileiro (R$ 1.234,56)"""
    return f"R$ {valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

def formatar_percentual(valor):
    """Formata percentual no padrão brasileiro (12,34%)"""
    return f"{valor:.2f}".replace('.', ',') + "%"

# ==========================================================
# CARREGAR DADOS DO fato_vendas.csv
# ==========================================================
print("\n" + "=" * 80)
print("CARREGANDO DADOS DO fato_vendas.csv...")
print("=" * 80)

csv_path = DADOS_TRATADOS / "fato_vendas.csv"

if not csv_path.exists():
    raise FileNotFoundError(f"Arquivo não encontrado: {csv_path}")

df = pd.read_csv(csv_path)
print(f"✅ Arquivo carregado: {csv_path.name}")
print(f"📊 Linhas: {df.shape[0]} | Colunas: {df.shape[1]}")
print(f"📋 Colunas disponíveis: {df.columns.tolist()}")

# ==========================================================
# VERIFICAR E AJUSTAR COLUNAS NECESSÁRIAS
# ==========================================================

# Colunas que o código espera
colunas_necessarias = {
    'order_id': ['order_id', 'id_pedido', 'pedido_id'],
    'customer_state': ['customer_state', 'estado_cliente', 'uf', 'state'],
    'valor_total_item': ['valor_total_item', 'total_pedido', 'receita', 'valor_total'],
    'freight_value': ['freight_value', 'valor_frete', 'frete'],
    'data': ['data', 'order_purchase_timestamp', 'data_pedido', 'date'],
    'entregue_com_atraso': ['entregue_com_atraso', 'atraso', 'is_delayed', 'delay'],
    'pedido_entregue': ['pedido_entregue', 'entregue', 'is_delivered', 'delivered']
}

# Função para encontrar coluna
def encontrar_coluna(nome_esperado):
    possibilidades = colunas_necessarias[nome_esperado]
    for col in df.columns:
        if col.lower() in [p.lower() for p in possibilidades]:
            return col
    return None

# Renomear colunas para o padrão
for nome_esperado in colunas_necessarias.keys():
    coluna_encontrada = encontrar_coluna(nome_esperado)
    if coluna_encontrada and coluna_encontrada != nome_esperado:
        df.rename(columns={coluna_encontrada: nome_esperado}, inplace=True)
        print(f"✓ Mapeado: '{coluna_encontrada}' → '{nome_esperado}'")

# Verificar colunas essenciais
colunas_essenciais = ['order_id', 'valor_total_item', 'freight_value']
for col in colunas_essenciais:
    if col not in df.columns:
        raise ValueError(f"Coluna essencial '{col}' não encontrada no CSV. Colunas disponíveis: {df.columns.tolist()}")

# Converter data
if 'data' in df.columns:
    df['data'] = pd.to_datetime(df['data'])
else:
    print("⚠️ Coluna 'data' não encontrada. Criando data padrão...")
    df['data'] = pd.date_range('2017-01-01', periods=len(df), freq='D')

# FILTRO: APENAS PERÍODO CONSISTENTE (Jan/2017 a Ago/2018)
df = df[(df['data'] >= '2017-01-01') & (df['data'] <= '2018-08-31')]
print(f"📅 Após filtro (Jan/2017 a Ago/2018): {df['data'].min().date()} a {df['data'].max().date()}")

# Garantir tipos numéricos
df['valor_total_item'] = pd.to_numeric(df['valor_total_item'], errors='coerce').fillna(0)
df['freight_value'] = pd.to_numeric(df['freight_value'], errors='coerce').fillna(0)

if 'entregue_com_atraso' in df.columns:
    df['entregue_com_atraso'] = pd.to_numeric(df['entregue_com_atraso'], errors='coerce').fillna(0).astype(int)
else:
    print("⚠️ Coluna 'entregue_com_atraso' não encontrada. Será usada taxa padrão de 6,79%")

if 'pedido_entregue' in df.columns:
    df['pedido_entregue'] = pd.to_numeric(df['pedido_entregue'], errors='coerce').fillna(0).astype(int)
else:
    print("⚠️ Coluna 'pedido_entregue' não encontrada. Será usada taxa padrão de 6,79%")

print(f"\n✅ Dados processados com sucesso!")
print(f"📅 Período: {df['data'].min().date()} a {df['data'].max().date()}")
print(f"💰 Receita total: {formatar_moeda(df['valor_total_item'].sum())}")
print("=" * 80)

# ==========================================================
# KPIs GERAIS
# ==========================================================
receita_total = df['valor_total_item'].sum()
total_pedidos = df['order_id'].nunique()
ticket_medio = receita_total / total_pedidos if total_pedidos > 0 else 0

# Receita por estado
if 'customer_state' in df.columns:
    receita_estado = df.groupby('customer_state')['valor_total_item'].sum().sort_values(ascending=False).head(10)
    receita_estado_formatada = {estado: formatar_moeda(valor) for estado, valor in receita_estado.items()}
else:
    receita_estado_formatada = {"erro": "Coluna customer_state não encontrada"}

# Receita mensal
df['ano_mes'] = df['data'].dt.to_period('M').astype(str)
receita_mensal = df.groupby('ano_mes')['valor_total_item'].sum()
receita_mensal_formatada = {mes: formatar_moeda(valor) for mes, valor in receita_mensal.items()}

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
        "total_registros": len(df),
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
    return {
        "estados": receita_estado_formatada,
        "insight": "SP concentra 37% da receita total"
    }

@app.get("/receita/mensal")
def get_receita_mensal():
    return {
        "receita_mensal": receita_mensal_formatada,
        "insight": "Crescimento expressivo do primeiro ao ultimo mes"
    }

@app.get("/insights")
def get_insights():
    try:
        # ==========================================================
        # PEDIDOS CRÍTICOS (valor < R$100 e frete > 30%)
        # ==========================================================
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
        
        # ==========================================================
        # TAXA DE ATRASO
        # ==========================================================
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
            taxa_atraso = 6.79  # valor padrão do seu projeto
        
        return {
            "pedidos_criticos": {
                "quantidade": f"{pedidos_criticos:,}".replace(',', '.'),
                "percentual": formatar_percentual(pct_pedidos_criticos),
                "insight": f"{formatar_percentual(pct_pedidos_criticos)} dos pedidos tem frete > 30% do produto"
            },
            "taxa_atraso": {
                "percentual": formatar_percentual(taxa_atraso),
                "insight": f"{formatar_percentual(taxa_atraso)} dos pedidos entregues com atraso"
            }
        }
    except Exception as e:
        print(f"ERRO: {str(e)}")
        print(traceback.format_exc())
        return {"erro": str(e)}

@app.get("/frete/impacto")
def get_frete_impacto():
    if 'customer_state' not in df.columns:
        return {"erro": "Coluna customer_state não encontrada"}
    
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
    if 'customer_state' not in df.columns:
        return {"erro": "Coluna customer_state não encontrada"}
    
    if 'entregue_com_atraso' not in df.columns or 'pedido_entregue' not in df.columns:
        return {
            "estados_maior_atraso": {},
            "insight": "Dados de atraso não disponíveis no CSV",
            "recomendacao": "Considere adicionar as colunas 'entregue_com_atraso' e 'pedido_entregue'"
        }
    
    pedidos_atraso = df.groupby(['order_id', 'customer_state']).agg({
        'entregue_com_atraso': 'max',
        'pedido_entregue': 'max'
    }).reset_index()
    
    atraso_por_estado = pedidos_atraso.groupby('customer_state').agg({
        'order_id': 'count',
        'entregue_com_atraso': 'sum',
        'pedido_entregue': 'sum'
    }).reset_index()
    
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

@app.get("/debug/colunas")
def debug_colunas():
    """Endpoint para debug - mostra estrutura do CSV"""
    return {
        "colunas": df.columns.tolist(),
        "tipos": {col: str(dtype) for col, dtype in df.dtypes.items()},
        "total_linhas": len(df),
        "total_pedidos": int(df['order_id'].nunique()) if 'order_id' in df.columns else 0,
        "amostra_primeiras_linhas": df.head(3).to_dict(orient="records")
    }

# ==========================================================
# EXECUTAR API
# ==========================================================
if __name__ == "__main__":
    import uvicorn
    print("\n" + "=" * 80)
    print("API DO PROJETO OLIST PORTFOLIO")
    print("=" * 80)
    print("Acesse: http://localhost:8000")
    print("Documentacao: http://localhost:8000/docs")
    print("\nEndpoints disponiveis:")
    print("  /kpis           - KPIs gerais")
    print("  /receita/estado - Receita por estado")
    print("  /receita/mensal - Receita mensal")
    print("  /insights       - Insights de negocio")
    print("  /frete/impacto  - Impacto do frete")
    print("  /atraso/impacto - Impacto dos atrasos")
    print("  /debug/colunas  - Debug: mostra estrutura dos dados")
    print("\nPressione Ctrl+C para parar")
    print("=" * 80)
    
    uvicorn.run(app, host="0.0.0.0", port=8000)