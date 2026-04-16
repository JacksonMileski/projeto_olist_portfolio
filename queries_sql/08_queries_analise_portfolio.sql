-- ==========================================================
-- PROJETO OLIST PORTFOLIO - QUERIES SQL PROFISSIONAIS
-- Schema: portfolio
-- Banco: olist_portfolio
-- Autor: Jackson Luis Mileski
-- ==========================================================

-- ==========================================================
-- 1. VISÃO GERAL DAS TABELAS
-- ==========================================================
SELECT table_schema, table_name
FROM information_schema.tables
WHERE table_schema = 'portfolio'
ORDER BY table_name;

-- ==========================================================
-- 2. CONTAGEM DE REGISTROS POR TABELA
-- ==========================================================
SELECT 'dim_clientes' AS tabela, COUNT(*) AS quantidade FROM portfolio.dim_clientes
UNION ALL
SELECT 'dim_produtos', COUNT(*) FROM portfolio.dim_produtos
UNION ALL
SELECT 'dim_vendedores', COUNT(*) FROM portfolio.dim_vendedores
UNION ALL
SELECT 'dim_tempo', COUNT(*) FROM portfolio.dim_tempo
UNION ALL
SELECT 'fato_vendas', COUNT(*) FROM portfolio.fato_vendas;

-- ==========================================================
-- 3. RECEITA TOTAL, TOTAL DE PEDIDOS E TICKET MÉDIO
-- ==========================================================
SELECT 
    'R$ ' || TO_CHAR(SUM(valor_total_item), 'FM999G999G999D99') AS receita_total,
    TO_CHAR(COUNT(DISTINCT id_pedido), 'FM999G999') AS total_pedidos,
    'R$ ' || TO_CHAR(SUM(valor_total_item) / COUNT(DISTINCT id_pedido), 'FM999G999D99') AS ticket_medio
FROM portfolio.fato_vendas
WHERE data BETWEEN '2017-01-05' AND '2018-08-31';

-- ==========================================================
-- 4. RECEITA MENSAL
-- ==========================================================
SELECT
    dt.ano_mes,
    'R$ ' || TO_CHAR(SUM(fv.valor_total_item), 'FM999G999G999D99') AS receita_mensal
FROM portfolio.fato_vendas fv
JOIN portfolio.dim_tempo dt ON fv.data = dt.data
WHERE dt.ano_mes BETWEEN '2017-01' AND '2018-08'
GROUP BY dt.ano_mes
ORDER BY dt.ano_mes;

-- ==========================================================
-- 5. TOP 10 ESTADOS POR RECEITA
-- ==========================================================
SELECT
    dc.estado_cliente,
    'R$ ' || TO_CHAR(SUM(fv.valor_total_item), 'FM999G999G999D99') AS receita_total
FROM portfolio.fato_vendas fv
JOIN portfolio.dim_clientes dc ON fv.id_cliente = dc.id_cliente
WHERE fv.data BETWEEN '2017-01-05' AND '2018-08-31'
GROUP BY dc.estado_cliente
ORDER BY SUM(fv.valor_total_item) DESC
LIMIT 10;

-- ==========================================================
-- 6. TOP 10 CIDADES POR QUANTIDADE DE PEDIDOS
-- ==========================================================
SELECT
    dc.cidade_cliente,
    TO_CHAR(COUNT(DISTINCT fv.id_pedido), 'FM999G999') AS total_pedidos
FROM portfolio.fato_vendas fv
JOIN portfolio.dim_clientes dc ON fv.id_cliente = dc.id_cliente
WHERE fv.data BETWEEN '2017-01-05' AND '2018-08-31'
GROUP BY dc.cidade_cliente
ORDER BY COUNT(DISTINCT fv.id_pedido) DESC
LIMIT 10;

-- ==========================================================
-- 7. TOP 10 VENDEDORES POR RECEITA
-- ==========================================================
SELECT
    dv.id_vendedor,
    'R$ ' || TO_CHAR(SUM(fv.valor_total_item), 'FM999G999G999D99') AS receita_total
FROM portfolio.fato_vendas fv
JOIN portfolio.dim_vendedores dv ON fv.id_vendedor = dv.id_vendedor
WHERE fv.data BETWEEN '2017-01-05' AND '2018-08-31'  -- ← adicionar
GROUP BY dv.id_vendedor
ORDER BY SUM(fv.valor_total_item) DESC
LIMIT 10;

-- ==========================================================
-- 8. TOP 10 CATEGORIAS POR RECEITA
-- ==========================================================
SELECT
    dp.categoria_produto,
    'R$ ' || TO_CHAR(SUM(fv.valor_total_item), 'FM999G999G999D99') AS receita_total
FROM portfolio.fato_vendas fv
JOIN portfolio.dim_produtos dp ON fv.id_produto = dp.id_produto
WHERE fv.data BETWEEN '2017-01-05' AND '2018-08-31'  -- ← adicionar
GROUP BY dp.categoria_produto
ORDER BY SUM(fv.valor_total_item) DESC
LIMIT 10;

-- ==========================================================
-- 9. TOP 10 CATEGORIAS POR ITENS VENDIDOS
-- ==========================================================
SELECT
    dp.categoria_produto,
    TO_CHAR(COUNT(*), 'FM999G999') AS total_itens_vendidos
FROM portfolio.fato_vendas fv
JOIN portfolio.dim_produtos dp ON fv.id_produto = dp.id_produto
WHERE fv.data BETWEEN '2017-01-05' AND '2018-08-31'  -- ← adicionar
GROUP BY dp.categoria_produto
ORDER BY COUNT(*) DESC
LIMIT 10;

-- ==========================================================
-- 10. TICKET MÉDIO POR ESTADO 
-- ==========================================================
SELECT
    dc.estado_cliente,
    'R$ ' || TO_CHAR(ROUND(SUM(fv.valor_total_item)::NUMERIC / COUNT(DISTINCT fv.id_pedido)::NUMERIC, 2), 'FM999G999D99') AS ticket_medio
FROM portfolio.fato_vendas fv
JOIN portfolio.dim_clientes dc ON fv.id_cliente = dc.id_cliente
WHERE fv.data BETWEEN '2017-01-05' AND '2018-08-31'
GROUP BY dc.estado_cliente
ORDER BY SUM(fv.valor_total_item) DESC;

-- ==========================================================
-- 11. PESO MÉDIO DO FRETE POR ESTADO
-- ==========================================================
SELECT
    dc.estado_cliente,
    TO_CHAR(
        (SUM(fv.valor_frete) / NULLIF(SUM(fv.valor_total_item), 0) * 100),
        'FM999D99'
    ) || '%' AS "frete_%_sobre_produto"
FROM portfolio.fato_vendas fv
JOIN portfolio.dim_clientes dc ON fv.id_cliente = dc.id_cliente
WHERE fv.data BETWEEN '2017-01-05' AND '2018-08-31'
GROUP BY dc.estado_cliente
ORDER BY (SUM(fv.valor_frete) / NULLIF(SUM(fv.valor_total_item), 0) * 100) DESC;

-- ==========================================================
-- 12. TAXA DE ATRASO POR ESTADO 
-- ==========================================================
SELECT
    dc.estado_cliente,
    TO_CHAR(COUNT(DISTINCT fv.id_pedido), 'FM999G999') AS total_pedidos,
    TO_CHAR(
        (COUNT(DISTINCT CASE WHEN fv.entregue_com_atraso = 1 THEN fv.id_pedido END)::numeric 
        / NULLIF(COUNT(DISTINCT CASE WHEN fv.pedido_entregue = 1 THEN fv.id_pedido END), 0) * 100),
        'FM999D99'
    ) || '%' AS taxa_atraso_pct
FROM portfolio.fato_vendas fv
JOIN portfolio.dim_clientes dc ON fv.id_cliente = dc.id_cliente
WHERE fv.data BETWEEN '2017-01-05' AND '2018-08-31'
GROUP BY dc.estado_cliente
HAVING COUNT(DISTINCT fv.id_pedido) >= 100
ORDER BY (COUNT(DISTINCT CASE WHEN fv.entregue_com_atraso = 1 THEN fv.id_pedido END)::numeric 
    / NULLIF(COUNT(DISTINCT CASE WHEN fv.pedido_entregue = 1 THEN fv.id_pedido END), 0) * 100) DESC;

-- ==========================================================
-- 13. TEMPO MÉDIO DE ENTREGA POR ESTADO
-- ==========================================================
SELECT
    dc.estado_cliente,
    TO_CHAR(ROUND(AVG(fv.tempo_entrega_dias)::NUMERIC, 0), 'FM999') || ' dias' AS tempo_medio_entrega_dias
FROM portfolio.fato_vendas fv
JOIN portfolio.dim_clientes dc ON fv.id_cliente = dc.id_cliente
JOIN portfolio.dim_tempo dt ON fv.data = dt.data
WHERE fv.tempo_entrega_dias IS NOT NULL
  AND dt.ano_mes BETWEEN '2017-01' AND '2018-08'
GROUP BY dc.estado_cliente
ORDER BY AVG(fv.tempo_entrega_dias) DESC;

-- ==========================================================
-- 14. PEDIDOS CRÍTICOS
-- ==========================================================
WITH pedidos AS (
    SELECT
        id_pedido,
        SUM(valor_total_item) AS valor_pedido,
        SUM(valor_frete) AS frete_pedido
    FROM portfolio.fato_vendas
    WHERE data BETWEEN '2017-01-05' AND '2018-08-31'
    GROUP BY id_pedido
)
SELECT 
    COUNT(*) AS pedidos_criticos,
    ROUND(COUNT(*)::numeric / (SELECT COUNT(DISTINCT id_pedido) FROM portfolio.fato_vendas WHERE data BETWEEN '2017-01-05' AND '2018-08-31') * 100, 2) AS percentual
FROM pedidos
WHERE valor_pedido < 100
  AND (frete_pedido / NULLIF(valor_pedido, 0)) > 0.30;

-- ==========================================================
-- 15. RECEITA POR STATUS DO PEDIDO
-- ==========================================================
SELECT
    status_pedido,
    'R$ ' || TO_CHAR(SUM(valor_total_item), 'FM999G999G999D99') AS receita_total,
    TO_CHAR(COUNT(DISTINCT id_pedido), 'FM999G999') AS total_pedidos
FROM portfolio.fato_vendas
WHERE data BETWEEN '2017-01-05' AND '2018-08-31' 
GROUP BY status_pedido
ORDER BY SUM(valor_total_item) DESC;

-- ==========================================================
-- 16. RECEITA ACUMULADA MENSAL 
-- ==========================================================
WITH receita_mensal AS (
    SELECT
        dt.ano_mes,
        SUM(fv.valor_total_item) AS receita_mensal
    FROM portfolio.fato_vendas fv
    JOIN portfolio.dim_tempo dt ON fv.data = dt.data
    WHERE dt.ano_mes BETWEEN '2017-01' AND '2018-08'
    GROUP BY dt.ano_mes
)
SELECT
    ano_mes,
    'R$ ' || TO_CHAR(receita_mensal, 'FM999G999G999D99') AS receita_mensal,
    'R$ ' || TO_CHAR(SUM(receita_mensal) OVER (ORDER BY ano_mes), 'FM999G999G999D99') AS receita_acumulada
FROM receita_mensal
ORDER BY ano_mes;

-- ==========================================================
-- 17. VARIAÇÃO MÊS A MÊS 
-- ==========================================================
WITH receita_mensal AS (
    SELECT
        dt.ano_mes,
        SUM(fv.valor_total_item) AS receita_mensal
    FROM portfolio.fato_vendas fv
    JOIN portfolio.dim_tempo dt ON fv.data = dt.data
    WHERE dt.ano_mes BETWEEN '2017-01' AND '2018-08'
    GROUP BY dt.ano_mes
)
SELECT
    ano_mes,
    'R$ ' || TO_CHAR(receita_mensal, 'FM999G999G999D99') AS receita_mensal,
    TO_CHAR(
        ((receita_mensal - LAG(receita_mensal) OVER (ORDER BY ano_mes))
         / NULLIF(LAG(receita_mensal) OVER (ORDER BY ano_mes), 0) * 100),
        'FM999D99'
    ) || '%' AS variacao_mom_pct
FROM receita_mensal
ORDER BY ano_mes;

-- ==========================================================
-- 18. DASHBOARD EXECUTIVO 
-- ==========================================================
WITH pedidos AS (
    SELECT
        id_pedido,
        SUM(valor_total_item) AS valor_pedido,
        SUM(valor_frete) AS frete_pedido,
        MAX(entregue_com_atraso) AS entregue_com_atraso,
        MAX(pedido_entregue) AS pedido_entregue
    FROM portfolio.fato_vendas
    WHERE data BETWEEN '2017-01-05' AND '2018-08-31'
    GROUP BY id_pedido
)
SELECT 
    'R$ ' || TO_CHAR((SELECT SUM(valor_total_item) FROM portfolio.fato_vendas WHERE data BETWEEN '2017-01-05' AND '2018-08-31'), 'FM999G999G999D99') AS receita_total,
    TO_CHAR((SELECT COUNT(DISTINCT id_pedido) FROM portfolio.fato_vendas WHERE data BETWEEN '2017-01-05' AND '2018-08-31'), 'FM999G999') AS total_pedidos,
    'R$ ' || TO_CHAR(
        (SELECT SUM(valor_total_item) FROM portfolio.fato_vendas WHERE data BETWEEN '2017-01-05' AND '2018-08-31')::numeric 
        / (SELECT COUNT(DISTINCT id_pedido) FROM portfolio.fato_vendas WHERE data BETWEEN '2017-01-05' AND '2018-08-31')::numeric, 
        'FM999G999D99'
    ) AS ticket_medio,
    TO_CHAR(
        (SELECT SUM(valor_frete) FROM portfolio.fato_vendas WHERE data BETWEEN '2017-01-05' AND '2018-08-31')::numeric 
        / NULLIF((SELECT SUM(valor_total_item) FROM portfolio.fato_vendas WHERE data BETWEEN '2017-01-05' AND '2018-08-31')::numeric, 0) * 100, 
        'FM999D99'
    ) || '%' AS peso_frete_pct,
    TO_CHAR(
        (SELECT COUNT(*) FROM pedidos WHERE pedido_entregue = 1 AND entregue_com_atraso = 1)::numeric
        / NULLIF((SELECT COUNT(*) FROM pedidos WHERE pedido_entregue = 1), 0) * 100,
        'FM999D99'
    ) || '%' AS taxa_atraso_pct,
    TO_CHAR(
        (SELECT COUNT(*) FROM pedidos WHERE valor_pedido < 100 AND (frete_pedido / NULLIF(valor_pedido, 0)) > 0.30),
        'FM999G999'
    ) AS pedidos_criticos;


-- ==========================================================
-- VIEWS - CONSULTAS REUTILIZÁVEIS
-- ==========================================================

-- VIEW 1: Resumo de Vendas por Estado
CREATE OR REPLACE VIEW portfolio.vw_resumo_vendas_estado AS
SELECT 
    dc.estado_cliente,
    COUNT(DISTINCT fv.id_pedido) AS total_pedidos_bruto,  -- ← para ordenação
    TO_CHAR(COUNT(DISTINCT fv.id_pedido), 'FM999G999') AS total_pedidos,
    TO_CHAR(ROUND(CAST(SUM(fv.valor_total_item) AS numeric), 2), 'FM999G999G999D99') AS receita_total,
    TO_CHAR(ROUND(CAST(SUM(fv.valor_total_item) / COUNT(DISTINCT fv.id_pedido) AS numeric), 2), 'FM999G999D99') AS ticket_medio,
    TO_CHAR(ROUND(CAST(SUM(fv.valor_frete) AS numeric) / NULLIF(CAST(SUM(fv.valor_total_item) AS numeric), 0) * 100, 2), 'FM999D99') || '%' AS peso_frete_pct
FROM portfolio.fato_vendas fv
JOIN portfolio.dim_clientes dc ON fv.id_cliente = dc.id_cliente
WHERE fv.data BETWEEN '2017-01-01' AND '2018-08-31'
GROUP BY dc.estado_cliente;

-- VIEW 2: Resumo de Vendas por Mês
CREATE OR REPLACE VIEW portfolio.vw_resumo_vendas_mensal AS
SELECT 
    dt.ano_mes,
    TO_CHAR(COUNT(DISTINCT fv.id_pedido), 'FM999G999') AS total_pedidos,
    TO_CHAR(ROUND(CAST(SUM(fv.valor_total_item) AS numeric), 2), 'FM999G999G999D99') AS receita_total,
    TO_CHAR(ROUND(CAST(SUM(fv.valor_total_item) / COUNT(DISTINCT fv.id_pedido) AS numeric), 2), 'FM999G999D99') AS ticket_medio,
    TO_CHAR(ROUND(
        (CAST(SUM(fv.valor_total_item) AS numeric) - CAST(LAG(SUM(fv.valor_total_item)) OVER (ORDER BY dt.ano_mes) AS numeric)) 
        / NULLIF(CAST(LAG(SUM(fv.valor_total_item)) OVER (ORDER BY dt.ano_mes) AS numeric), 0) * 100, 2
    ), 'FM990D99') || '%' AS variacao_pct,
    dt.ano_mes AS _ordenacao
FROM portfolio.fato_vendas fv
JOIN portfolio.dim_tempo dt ON fv.data = dt.data
WHERE dt.ano_mes BETWEEN '2017-01' AND '2018-08'
GROUP BY dt.ano_mes
ORDER BY _ordenacao;

-- VIEW 3: Pedidos Críticos por Pedido
CREATE OR REPLACE VIEW portfolio.vw_pedidos_criticos AS
WITH pedidos_agg AS (
    SELECT
        id_pedido,
        SUM(valor_total_item) AS valor_pedido,
        SUM(valor_frete) AS frete_pedido
    FROM portfolio.fato_vendas
    WHERE data BETWEEN '2017-01-01' AND '2018-08-31'
    GROUP BY id_pedido
)
SELECT 
    id_pedido,
    TO_CHAR(ROUND(CAST(valor_pedido AS numeric), 2), 'FM999G999D99') AS valor_pedido,
    TO_CHAR(ROUND(CAST(frete_pedido AS numeric), 2), 'FM999G999D99') AS frete_pedido,
    TO_CHAR(ROUND(CAST(frete_pedido AS numeric) / NULLIF(CAST(valor_pedido AS numeric), 0) * 100, 2), 'FM990D99') || '%' AS peso_frete_pct,
    CASE 
        WHEN valor_pedido < 100 AND (CAST(frete_pedido AS numeric) / NULLIF(CAST(valor_pedido AS numeric), 0)) > 0.30 
        THEN 'Sim' 
        ELSE 'Não' 
    END AS is_critico,
    -- Coluna oculta para ordenação (usar na consulta)
    ROUND(CAST(frete_pedido AS numeric) / NULLIF(CAST(valor_pedido AS numeric), 0), 4) AS _ordem_critico
FROM pedidos_agg;

-- VIEW 4: Performance de Entregas por Estado
CREATE OR REPLACE VIEW portfolio.vw_performance_entregas AS
SELECT 
    dc.estado_cliente,
    COUNT(DISTINCT fv.id_pedido) AS total_pedidos,
    COUNT(DISTINCT CASE WHEN fv.pedido_entregue = 1 THEN fv.id_pedido END) AS pedidos_entregues,
    COUNT(DISTINCT CASE WHEN fv.entregue_com_atraso = 1 THEN fv.id_pedido END) AS pedidos_atrasados,
    ROUND(CAST(AVG(CASE WHEN fv.tempo_entrega_dias IS NOT NULL THEN fv.tempo_entrega_dias END) AS numeric), 0) AS tempo_medio_entrega_dias,
    ROUND(
        CAST(COUNT(DISTINCT CASE WHEN fv.entregue_com_atraso = 1 THEN fv.id_pedido END) AS numeric) 
        / NULLIF(CAST(COUNT(DISTINCT CASE WHEN fv.pedido_entregue = 1 THEN fv.id_pedido END) AS numeric), 0) * 100, 2
    ) AS taxa_atraso_pct,
    CAST(COUNT(DISTINCT CASE WHEN fv.entregue_com_atraso = 1 THEN fv.id_pedido END) AS numeric) 
        / NULLIF(CAST(COUNT(DISTINCT CASE WHEN fv.pedido_entregue = 1 THEN fv.id_pedido END) AS numeric), 0) AS _ordem_atraso
FROM portfolio.fato_vendas fv
JOIN portfolio.dim_clientes dc ON fv.id_cliente = dc.id_cliente
WHERE fv.data BETWEEN '2017-01-01' AND '2018-08-31'
GROUP BY dc.estado_cliente;

-- ==========================================================
-- CONSULTAS DAS VIEWS (EXEMPLOS DE USO)
-- ==========================================================
-- Resumo por estado
SELECT 
    estado_cliente,
    total_pedidos,
    receita_total,
    ticket_medio,
    peso_frete_pct
FROM portfolio.vw_resumo_vendas_estado
ORDER BY total_pedidos_bruto DESC;

-- Resumo mensal
SELECT * FROM portfolio.vw_resumo_vendas_mensal;

-- Pedidos críticos
SELECT * FROM portfolio.vw_pedidos_criticos WHERE is_critico = 'Sim';

-- Performance de entregas
SELECT 
    estado_cliente,
    TO_CHAR(total_pedidos, 'FM999G999') AS total_pedidos,
    TO_CHAR(pedidos_entregues, 'FM999G999') AS pedidos_entregues,
    TO_CHAR(pedidos_atrasados, 'FM999G999') AS pedidos_atrasados,
    TO_CHAR(tempo_medio_entrega_dias, 'FM999') || ' dias' AS tempo_medio_entrega,
    TO_CHAR(taxa_atraso_pct, 'FM990D99') || '%' AS taxa_atraso_pct
FROM portfolio.vw_performance_entregas
ORDER BY _ordem_atraso DESC;

-- ==========================================================
-- PROCEDURES - ROTINAS REUTILIZÁVEIS
-- ==========================================================
-- Tabela de KPIs
CREATE TABLE portfolio.tb_kpis (
    data_calculo DATE DEFAULT CURRENT_DATE,
    receita_total DECIMAL(15,2),
    total_pedidos INTEGER,
    ticket_medio DECIMAL(10,2),
    taxa_atraso DECIMAL(5,2),
    perc_pedidos_criticos DECIMAL(5,2)
);

-- Procedure: Calcular KPIs
CREATE OR REPLACE PROCEDURE portfolio.sp_calcular_kpis()
LANGUAGE plpgsql
AS $$
BEGIN
    INSERT INTO portfolio.tb_kpis (receita_total, total_pedidos, ticket_medio, taxa_atraso, perc_pedidos_criticos)
    SELECT 
        SUM(valor_total_item)::DECIMAL(15,2),
        COUNT(DISTINCT id_pedido),
        ROUND((SUM(valor_total_item)::NUMERIC / COUNT(DISTINCT id_pedido)::NUMERIC), 2),
        (
            WITH pedidos AS (
                SELECT
                    id_pedido,
                    MAX(entregue_com_atraso) AS entregue_com_atraso,
                    MAX(pedido_entregue) AS pedido_entregue
                FROM portfolio.fato_vendas
                WHERE data BETWEEN '2017-01-05' AND '2018-08-31'
                GROUP BY id_pedido
            )
            SELECT ROUND(
                COUNT(CASE WHEN pedido_entregue = 1 AND entregue_com_atraso = 1 THEN 1 END)::NUMERIC 
                / NULLIF(COUNT(CASE WHEN pedido_entregue = 1 THEN 1 END), 0) * 100, 2
            )
            FROM pedidos
        ),
        (
            WITH pedidos_agg AS (
                SELECT 
                    id_pedido, 
                    SUM(valor_total_item) AS valor_pedido, 
                    SUM(valor_frete) AS frete_pedido
                FROM portfolio.fato_vendas
                WHERE data BETWEEN '2017-01-05' AND '2018-08-31'
                GROUP BY id_pedido
            )
            SELECT ROUND(
                (COUNT(*)::NUMERIC / (SELECT COUNT(DISTINCT id_pedido)::NUMERIC FROM portfolio.fato_vendas WHERE data BETWEEN '2017-01-05' AND '2018-08-31') * 100), 2
            )
            FROM pedidos_agg
            WHERE valor_pedido < 100 AND (frete_pedido / NULLIF(valor_pedido, 0)) > 0.30
        )
    FROM portfolio.fato_vendas
    WHERE data BETWEEN '2017-01-05' AND '2018-08-31';
    
    RAISE NOTICE 'KPIs calculados e salvos com sucesso!';
END;
$$;

CREATE OR REPLACE VIEW portfolio.vw_kpis_formatado AS
SELECT 
    data_calculo,
    'R$ ' || TO_CHAR(receita_total, 'FM999G999G999D99') AS receita_total,
    TO_CHAR(total_pedidos, 'FM999G999') AS total_pedidos,
    'R$ ' || TO_CHAR(ticket_medio, 'FM999G999D99') AS ticket_medio,
    TO_CHAR(taxa_atraso, 'FM999D99') || '%' AS taxa_atraso,
    TO_CHAR(perc_pedidos_criticos, 'FM999D99') || '%' AS perc_pedidos_criticos
FROM portfolio.tb_kpis;

-- Calcula receita, pedidos e ticket médio por mês
CREATE OR REPLACE PROCEDURE portfolio.sp_atualizar_resumo_mensal()
LANGUAGE plpgsql
AS $$
BEGIN
    CREATE TABLE IF NOT EXISTS portfolio.tb_resumo_mensal (
        ano_mes VARCHAR(7),
        receita_total DECIMAL(15,2),
        total_pedidos INTEGER,
        ticket_medio DECIMAL(10,2),
        PRIMARY KEY (ano_mes)
    );
    
    DELETE FROM portfolio.tb_resumo_mensal;
    
    INSERT INTO portfolio.tb_resumo_mensal (ano_mes, receita_total, total_pedidos, ticket_medio)
    SELECT 
        dt.ano_mes,
        SUM(fv.valor_total_item)::DECIMAL(15,2),
        COUNT(DISTINCT fv.id_pedido),
        ROUND((SUM(fv.valor_total_item)::NUMERIC / COUNT(DISTINCT fv.id_pedido)::NUMERIC), 2)
    FROM portfolio.fato_vendas fv
    JOIN portfolio.dim_tempo dt ON fv.data = dt.data
    WHERE dt.ano_mes BETWEEN '2017-01' AND '2018-08'
    GROUP BY dt.ano_mes
    ORDER BY dt.ano_mes;
    
    RAISE NOTICE 'Resumo mensal atualizado com sucesso!';
END;
$$;

CREATE OR REPLACE VIEW portfolio.vw_resumo_mensal_formatado AS
SELECT 
    ano_mes,
    'R$ ' || TO_CHAR(receita_total, 'FM999G999G999D99') AS receita_total,
    TO_CHAR(total_pedidos, 'FM999G999') AS total_pedidos,
    'R$ ' || TO_CHAR(ticket_medio, 'FM999G999D99') AS ticket_medio
FROM portfolio.tb_resumo_mensal
ORDER BY ano_mes;

-- Exibe relatório de vendas para um estado específico
CREATE OR REPLACE PROCEDURE portfolio.sp_relatorio_estado(p_estado VARCHAR(2))
LANGUAGE plpgsql
AS $$
DECLARE
    v_receita DECIMAL(15,2);
    v_pedidos INTEGER;
    v_ticket_medio DECIMAL(10,2);
BEGIN
    -- Buscar dados do estado (com conversão para NUMERIC)
    SELECT 
        SUM(fv.valor_total_item)::DECIMAL(15,2),
        COUNT(DISTINCT fv.id_pedido),
        ROUND((SUM(fv.valor_total_item)::NUMERIC / COUNT(DISTINCT fv.id_pedido)::NUMERIC), 2)
    INTO v_receita, v_pedidos, v_ticket_medio
    FROM portfolio.fato_vendas fv
    JOIN portfolio.dim_clientes dc ON fv.id_cliente = dc.id_cliente
    WHERE dc.estado_cliente = p_estado
      AND fv.data BETWEEN '2017-01-05' AND '2018-08-31';
    
    RAISE NOTICE '==========================================';
    RAISE NOTICE 'RELATÓRIO DO ESTADO: %', p_estado;
    RAISE NOTICE '==========================================';
    RAISE NOTICE 'Receita Total: R$ %', TO_CHAR(v_receita, 'FM999G999G999D99');
    RAISE NOTICE 'Total de Pedidos: %', TO_CHAR(v_pedidos, 'FM999G999');
    RAISE NOTICE 'Ticket Médio: R$ %', TO_CHAR(v_ticket_medio, 'FM999G999D99');
    RAISE NOTICE '==========================================';
END;
$$;

-- ==========================================================
-- EXECUÇÃO DOS EXEMPLOS
-- ==========================================================

-- 1. KPIs do negócio
CALL portfolio.sp_calcular_kpis();
SELECT * FROM portfolio.vw_kpis_formatado;

-- 2. Resumo mensal
CALL portfolio.sp_atualizar_resumo_mensal();
SELECT * FROM portfolio.vw_resumo_mensal_formatado;

-- 3. Relatório por estado
CALL portfolio.sp_relatorio_estado('SP');

-- ==========================================================
-- CONTROLE DE ACESSO E AUDITORIA
-- ==========================================================

-- 1. Criar usuários para diferentes perfis
DO $$
BEGIN
    -- Criar usuário analista se não existir
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'analista') THEN
        CREATE USER analista WITH PASSWORD 'Analista@2024';
    END IF;
    
    -- Criar usuário leitor se não existir
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'leitor') THEN
        CREATE USER leitor WITH PASSWORD 'Leitor@2024';
    END IF;
    
    -- Criar role de gerente se não existir
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'gerente') THEN
        CREATE ROLE gerente;
    END IF;
END$$;

-- 2. Conceder permissões específicas
-- Analista: pode ler e inserir dados
GRANT SELECT, INSERT ON portfolio.fato_vendas TO analista;
GRANT SELECT, INSERT ON portfolio.dim_clientes TO analista;
GRANT SELECT, INSERT ON portfolio.dim_produtos TO analista;
GRANT SELECT, INSERT ON portfolio.dim_vendedores TO analista;
GRANT SELECT, INSERT ON portfolio.dim_tempo TO analista;

-- Leitor: apenas consulta (SELECT)
GRANT SELECT ON ALL TABLES IN SCHEMA portfolio TO leitor;

-- Gerente: todas as permissões
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA portfolio TO gerente;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA portfolio TO gerente;

-- 1. Tabela de auditoria para log de consultas
CREATE TABLE IF NOT EXISTS portfolio.log_consultas (
    id SERIAL PRIMARY KEY,
    usuario VARCHAR(100),
    operacao VARCHAR(20),
    tabela_afetada VARCHAR(100),
    dados_anteriores TEXT,
    dados_novos TEXT,
    data_consulta TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ip_origem INET,
    query_text TEXT
);

-- 2. Função de auditoria (trigger)
CREATE OR REPLACE FUNCTION portfolio.audit_log()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO portfolio.log_consultas (
        usuario,
        operacao,
        tabela_afetada,
        dados_anteriores,
        dados_novos,
        ip_origem,
        query_text
    ) VALUES (
        CURRENT_USER,
        TG_OP,
        TG_TABLE_NAME,
        CASE WHEN TG_OP IN ('UPDATE', 'DELETE') THEN row_to_json(OLD)::TEXT ELSE NULL END,
        CASE WHEN TG_OP IN ('INSERT', 'UPDATE') THEN row_to_json(NEW)::TEXT ELSE NULL END,
        inet_client_addr(),
        current_query()
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 3. View para consultar logs (apenas para administradores)
CREATE OR REPLACE VIEW portfolio.vw_log_consultas AS
SELECT 
    id,
    usuario,
    operacao,
    tabela_afetada,
    data_consulta,
    ip_origem,
    SUBSTRING(query_text, 1, 200) AS query_resumida
FROM portfolio.log_consultas
ORDER BY data_consulta DESC;

-- 4. Política de retenção de logs (manter apenas 90 dias)
CREATE OR REPLACE FUNCTION portfolio.limpar_logs_antigos()
RETURNS void AS $$
BEGIN
    DELETE FROM portfolio.log_consultas 
    WHERE data_consulta < CURRENT_DATE - INTERVAL '90 days';
    RAISE NOTICE 'Logs anteriores a 90 dias removidos';
END;
$$ LANGUAGE plpgsql;

-- ==========================================================
-- TESTES PRÁTICOS
-- ==========================================================

-- 5. Ativar trigger em uma tabela (ex: dim_clientes)
DROP TRIGGER IF EXISTS audit_dim_clientes ON portfolio.dim_clientes;
CREATE TRIGGER audit_dim_clientes
    AFTER INSERT OR UPDATE OR DELETE ON portfolio.dim_clientes
    FOR EACH ROW EXECUTE FUNCTION portfolio.audit_log();

-- 6. Inserir dados de teste
INSERT INTO portfolio.dim_clientes (id_cliente, cidade_cliente, estado_cliente, cep_prefixo_cliente)
VALUES ('TESTE001', 'Cidade Teste', 'XX', '00000');

-- 7. Atualizar dados de teste
UPDATE portfolio.dim_clientes 
SET cidade_cliente = 'Nova Cidade Teste'
WHERE id_cliente = 'TESTE001';

-- 8. Deletar dados de teste
DELETE FROM portfolio.dim_clientes WHERE id_cliente = 'TESTE001';

-- ==========================================================
-- RESULTADOS FINAIS
-- ==========================================================

-- Verificar logs gerados
SELECT * FROM portfolio.vw_log_consultas;

-- Verificar KPIs calculados
SELECT * FROM portfolio.vw_kpis_formatado;

-- Verificar resumo mensal
SELECT * FROM portfolio.vw_resumo_mensal_formatado;
