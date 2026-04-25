import pandas as pd
import numpy as np
from pathlib import Path
from sqlalchemy import create_engine
from sklearn.linear_model import LinearRegression  # ← MUDE AQUI
from sklearn.metrics import mean_absolute_error, r2_score
import matplotlib.pyplot as plt
import locale

# Configurar formato brasileiro
locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
try:
    locale.setlocale(locale.LC_ALL, 'portuguese_brazil')
except:
    pass

# ==========================================================
# 1. CONFIGURAÇÃO DE CAMINHOS E CONEXÃO
# ==========================================================
try:
    BASE_DIR = Path(__file__).resolve().parent.parent
except NameError:
    BASE_DIR = Path.cwd().parent

DADOS_TRATADOS = BASE_DIR / "dados_tratados"
PASTA_GRAFICOS = BASE_DIR / "graficos"

# Configurações do PostgreSQL
DB_HOST = "localhost"
DB_PORT = "5432"
DB_NAME = "olist_portfolio"
DB_USER = "postgres"
DB_PASSWORD = "123"

# Criar conexão
engine = create_engine(f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}")

# ==========================================================
# 2. CARREGAR DADOS DO POSTGRESQL
# ==========================================================
print("\n" + "=" * 80)
print("CARREGANDO DADOS DO POSTGRESQL...")
print("=" * 80)

query = """
SELECT 
    fv.data,
    fv.valor_total_item,
    dt.ano_mes
FROM portfolio.fato_vendas fv
LEFT JOIN portfolio.dim_tempo dt ON fv.data = dt.data
WHERE dt.ano_mes BETWEEN '2017-01' AND '2018-08'
"""

df = pd.read_sql(query, engine)

print(f"Dados carregados: {df.shape[0]} linhas")

# ==========================================================
# 3. AGREGAR RECEITA POR MÊS
# ==========================================================
# Garantir que data está no formato correto
df['data'] = pd.to_datetime(df['data'])

# Agregar receita por mês
receita_mensal = df.groupby(df['data'].dt.to_period('M'))['valor_total_item'].sum().reset_index()
receita_mensal['ano_mes'] = receita_mensal['data'].astype(str)
receita_mensal['mes_num'] = range(1, len(receita_mensal) + 1)

# Filtrar apenas meses completos (2017-01 a 2018-08)
receita_mensal = receita_mensal[receita_mensal['ano_mes'] >= '2017-01']
receita_mensal = receita_mensal[receita_mensal['ano_mes'] <= '2018-08']
receita_mensal['mes_num'] = range(1, len(receita_mensal) + 1)

print(f"Receita mensal agregada: {len(receita_mensal)} meses")

# ==========================================================
# 4. TREINAR MODELO DE PREVISÃO (Regressão Linear)
# ==========================================================
X = receita_mensal['mes_num'].values.reshape(-1, 1)
y = receita_mensal['valor_total_item'].values

# Treinar modelo com Regressão Linear
model = LinearRegression()  # ← ALTERADO
model.fit(X, y)

# Fazer previsões para os dados existentes
receita_mensal['previsao'] = model.predict(X)

# Prever próximos 3 meses
meses_futuros = np.array([len(receita_mensal) + 1, len(receita_mensal) + 2, len(receita_mensal) + 3]).reshape(-1, 1)
previsoes_futuras = model.predict(meses_futuros)

# ==========================================================
# 5. AVALIAR MODELO
# ==========================================================
mae = mean_absolute_error(y, receita_mensal['previsao'])
r2 = r2_score(y, receita_mensal['previsao'])

print("\n" + "=" * 80)
print("PREVISAO DE VENDAS - MACHINE LEARNING (Regressao Linear)")
print("=" * 80)

# Formatar valores no padrão brasileiro
print(f"MAE (Erro Medio Absoluto): R$ {mae:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
print(f"R² (Coeficiente de Determinacao): {r2:.2%}")

# ==========================================================
# 6. GRÁFICO DE PREVISÃO
# ==========================================================
plt.figure(figsize=(12, 6))
plt.plot(receita_mensal['ano_mes'], receita_mensal['valor_total_item'], 'o-', label='Real', linewidth=2)
plt.plot(receita_mensal['ano_mes'], receita_mensal['previsao'], 's--', label='Previsao (Treino)', linewidth=2)

# Adicionar previsões futuras
meses_previsao = ['Set/2018', 'Out/2018', 'Nov/2018']
plt.plot(meses_previsao, previsoes_futuras, '^--', label='Previsao (Futuro)', linewidth=2, color='green')
plt.axvline(x=receita_mensal['ano_mes'].iloc[-1], color='red', linestyle='--', alpha=0.5, label='Fim dos dados reais')

plt.title('Previsao de Receita Mensal - Regressao Linear', fontsize=14)
plt.xlabel('Mes')
plt.ylabel('Receita (R$)')
plt.xticks(rotation=45)
plt.legend()
plt.tight_layout()
plt.savefig(PASTA_GRAFICOS / "09_previsao_vendas_ml.png", dpi=300)
plt.close()

print(f"\n[OK] Grafico salvo: {PASTA_GRAFICOS / '09_previsao_vendas_ml.png'}")

# ==========================================================
# 7. INSIGHTS DE IMPACTO
# ==========================================================
print("\n" + "=" * 80)
print("INSIGHTS DE NEGOCIO COM ML")
print("=" * 80)

if r2 > 0.7:
    print("[OK] O modelo explica mais de 70% da variacao nas vendas")
else:
    print("[ATENCAO] As vendas tem alta variabilidade")

print(f"\nPREVISAO PARA PROXIMOS 3 MESES:")
for i, prev in enumerate(previsoes_futuras):
    valor_formatado = f"R$ {prev:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    print(f"{meses_previsao[i]}: {valor_formatado}")

# ==========================================================
# 8. SALVAR PREVISÕES EM CSV
# ==========================================================
# Criar DataFrame com previsões futuras
previsoes_df = pd.DataFrame({
    'mes': meses_previsao,
    'previsao_receita': previsoes_futuras
})

# Adicionar previsões ao DataFrame original
receita_mensal['valor_total_item'] = receita_mensal['valor_total_item'].apply(lambda x: round(x, 2))
receita_mensal['previsao'] = receita_mensal['previsao'].apply(lambda x: round(x, 2))

# Salvar
previsoes_df.to_csv(DADOS_TRATADOS / "previsoes_futuras.csv", index=False)
receita_mensal.to_csv(DADOS_TRATADOS / "receita_com_previsao.csv", 
                      index=False, 
                      decimal=',', 
                      sep=';')

print(f"\n[OK] Previsoes salvas em: {DADOS_TRATADOS / 'previsoes_futuras.csv'}")
print("[OK] Dados de treino salvos em: dados_tratados/receita_com_previsao.csv")

print("\n" + "=" * 80)
print("FIM DA ANALISE DE PREVISAO")
print("=" * 80)