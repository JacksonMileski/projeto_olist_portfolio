import pandas as pd
import requests
from pathlib import Path
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
from sqlalchemy import create_engine

# ==========================================================
# 1. BUSCAR COTAÇÃO DO DÓLAR (API gratuita)
# ==========================================================
print("\n" + "=" * 80)
print("WEB SCRAPING - DADOS ECONOMICOS")
print("=" * 80)

try:
    # API do Banco Central (dólar comercial)
    url_dolar = "https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/CotacaoDolarPeriodo(dataInicial=@dataInicial,dataFinalCotacao=@dataFinalCotacao)?@dataInicial='01-01-2017'&@dataFinalCotacao='12-31-2018'&$top=100&$format=json"
    
    response = requests.get(url_dolar)
    dados_dolar = response.json()
    
    # Processar dados
    cotacoes = []
    for item in dados_dolar.get('value', []):
        cotacoes.append({
            'data': item['dataHoraCotacao'].split(' ')[0],
            'dolar_compra': item['cotacaoCompra'],
            'dolar_venda': item['cotacaoVenda']
        })
    
    df_dolar = pd.DataFrame(cotacoes)
    df_dolar['data'] = pd.to_datetime(df_dolar['data'])
    df_dolar['ano_mes'] = df_dolar['data'].dt.to_period('M').astype(str)
    
    # Média mensal do dólar
    dolar_mensal = df_dolar.groupby('ano_mes')['dolar_venda'].mean().reset_index()
    print(f"[OK] Dolar: {len(df_dolar)} cotacoes obtidas")
    
except Exception as e:
    print(f"[ERRO] Dolar: {e}")
    print("[INFO] Usando dados simulados para demonstracao")
    # Dados simulados (caso a API falhe)
    meses = ['2017-01', '2017-02', '2017-03', '2017-04', '2017-05', '2017-06',
             '2017-07', '2017-08', '2017-09', '2017-10', '2017-11', '2017-12',
             '2018-01', '2018-02', '2018-03', '2018-04', '2018-05', '2018-06',
             '2018-07', '2018-08']
    dolar_mensal = pd.DataFrame({
        'ano_mes': meses,
        'dolar_venda': [3.15, 3.12, 3.18, 3.22, 3.25, 3.28, 3.30, 3.32, 3.18, 3.15, 3.20, 3.30,
                        3.25, 3.28, 3.32, 3.45, 3.50, 3.60, 3.72, 3.85]
    })

# ==========================================================
# 2. CRIAR LISTA COMPLETA DE MESES (2017-01 a 2018-08)
# ==========================================================
meses_completos = []
ano = 2017
mes = 1
while ano <= 2018:
    if ano == 2018 and mes > 8:
        break
    meses_completos.append(f"{ano}-{mes:02d}")
    mes += 1
    if mes > 12:
        mes = 1
        ano += 1

print(f"[INFO] Total de meses na analise: {len(meses_completos)}")

# ==========================================================
# 3. CARREGAR DADOS DE VENDAS DO POSTGRESQL
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

# Criar conexão
engine = create_engine(f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}")

# Query para buscar receita mensal
query = """
SELECT 
    dt.ano_mes,
    SUM(fv.valor_total_item) AS receita
FROM portfolio.fato_vendas fv
LEFT JOIN portfolio.dim_tempo dt ON fv.data = dt.data
WHERE dt.ano_mes BETWEEN '2017-01' AND '2018-08'
GROUP BY dt.ano_mes
ORDER BY dt.ano_mes
"""

df_vendas = pd.read_sql(query, engine)
print(f"[OK] Vendas carregadas: {len(df_vendas)} meses")

# ==========================================================
# 4. GARANTIR TODOS OS MESES NA TABELA DE RECEITA
# ==========================================================
df_receita_completo = pd.DataFrame({'ano_mes': meses_completos})
df_receita_completo = df_receita_completo.merge(df_vendas, on='ano_mes', how='left')
df_receita_completo['receita'] = df_receita_completo['receita'].fillna(0)

# ==========================================================
# 5. GARANTIR TODOS OS MESES NA TABELA DO DÓLAR
# ==========================================================
df_dolar_completo = pd.DataFrame({'ano_mes': meses_completos})
df_dolar_completo = df_dolar_completo.merge(dolar_mensal, on='ano_mes', how='left')

# Preencher valores faltantes do dólar (forward fill)
df_dolar_completo['dolar_venda'] = df_dolar_completo['dolar_venda'].ffill().bfill()

# ==========================================================
# 6. CORRELACIONAR VENDAS COM DÓLAR
# ==========================================================
df_analise = df_receita_completo.merge(df_dolar_completo, on='ano_mes', how='inner')
correlacao = df_analise['receita'].corr(df_analise['dolar_venda'])

# Arredondar o dólar para 2 casas decimais
df_analise['dolar_venda'] = df_analise['dolar_venda'].round(2)

print(f"\n[INFO] Correlacao entre vendas e dolar: {correlacao:.2f}")
print(f"[INFO] Total de meses na analise final: {len(df_analise)}")

if correlacao > 0.5:
    print("   -> Forte correlacao positiva: quando dolar sobe, vendas sobem")
    print("   -> Aumento do dolar pode indicar maior competitividade de produtos importados")
elif correlacao < -0.5:
    print("   -> Forte correlacao negativa: quando dolar sobe, vendas caem")
    print("   -> Aumento do dolar encarece produtos importados, reduzindo vendas")
else:
    print("   -> Baixa correlacao: vendas nao sao fortemente influenciadas pelo dolar")

# ==========================================================
# 7. SALVAR DADOS ENRIQUECIDOS
# ==========================================================
# Criar uma cópia para formatar (sem perder os dados originais)
df_analise_salvar = df_analise.copy()

# Arredondar os valores
df_analise_salvar['dolar_venda'] = df_analise_salvar['dolar_venda'].round(2)
df_analise_salvar['receita'] = df_analise_salvar['receita'].round(2)

# Salvar com vírgula decimal (formato brasileiro)
df_analise_salvar.to_csv(DADOS_TRATADOS / "vendas_com_economia.csv", 
                         index=False, 
                         decimal=',', 
                         sep=';')

print(f"\n[OK] Dados salvos: {DADOS_TRATADOS / 'vendas_com_economia.csv'}")
print(f"[OK] Total de registros salvos: {len(df_analise_salvar)}")

# ==========================================================
# 8. GRÁFICO DE CORRELAÇÃO
# ==========================================================
fig, ax1 = plt.subplots(figsize=(12, 6))

ax1.set_xlabel('Mes')
ax1.set_ylabel('Receita (R$ milhoes)', color='blue')
ax1.plot(df_analise['ano_mes'], df_analise['receita'] / 1000000, 'o-', color='blue', label='Receita')
ax1.tick_params(axis='y', labelcolor='blue')
ax1.set_xticks(range(len(df_analise['ano_mes'])))
ax1.set_xticklabels(df_analise['ano_mes'], rotation=45)

ax2 = ax1.twinx()
ax2.set_ylabel('Dolar (R$)', color='red')
ax2.plot(df_analise['ano_mes'], df_analise['dolar_venda'], 's--', color='red', label='Dolar')
ax2.tick_params(axis='y', labelcolor='red')

plt.title(f'Correlacao entre Vendas e Dolar: {correlacao:.2f}')
fig.tight_layout()

PASTA_GRAFICOS = BASE_DIR / "graficos"
PASTA_GRAFICOS.mkdir(exist_ok=True)
plt.savefig(PASTA_GRAFICOS / "10_correlacao_dolar_vendas.png", dpi=300)
plt.close()

print(f"[OK] Grafico salvo: {PASTA_GRAFICOS / '10_correlacao_dolar_vendas.png'}")

# ==========================================================
# 9. INSIGHTS ADICIONAIS
# ==========================================================
print("\n" + "=" * 80)
print("INSIGHTS ECONOMICOS")
print("=" * 80)

# Calcular variação do dólar
dolar_inicio = df_analise['dolar_venda'].iloc[0]
dolar_fim = df_analise['dolar_venda'].iloc[-1]
variacao_dolar = ((dolar_fim - dolar_inicio) / dolar_inicio) * 100

print(f"Variacao do dolar no periodo: {variacao_dolar:.1f}%")
print(f"Receita inicial (Jan/2017): R$ {df_analise['receita'].iloc[0]:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
print(f"Receita final (Ago/2018): R$ {df_analise['receita'].iloc[-1]:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))

if correlacao > 0.5:
    print("\n[INSIGHT] O dolar e as vendas sobem juntos")
    print("Recomendacao: Aproveitar momentos de dolar alto para importar")
elif correlacao < -0.5:
    print("\n[INSIGHT] Dolar alto reduz as vendas")
    print("Recomendacao: Buscar fornecedores locais para proteger margem")
else:
    print("\n[INSIGHT] Vendas nao sao fortemente impactadas pelo dolar")
    print("Recomendacao: Foco em outras variaveis como marketing e sazonalidade")

print("\n" + "=" * 80)
print("FIM DA ANALISE ECONOMICA")
print("=" * 80)