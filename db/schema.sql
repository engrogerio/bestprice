-- ============================================================
-- BestPrice - Schema PostgreSQL
-- ============================================================
-- Convenção: todo dado bruto retornado pelas APIs externas é
-- guardado em colunas JSONB (raw_response) para nunca perdermos
-- informação, mesmo que o mapeamento de campos abaixo precise
-- de ajuste fino depois de validar contra respostas reais da
-- Infosimples/Cosmos.

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm"; -- busca fuzzy por descrição de produto

-- ------------------------------------------------------------
-- 1. cupom_header: um registro por cupom fiscal (CF-e/NFC-e) lido
-- ------------------------------------------------------------
CREATE TABLE cupom_header (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    chave_acesso        VARCHAR(44) NOT NULL UNIQUE, -- chave de 44 dígitos do código de barras
    cnpj_emitente       VARCHAR(14),
    razao_social        VARCHAR(255),
    nome_fantasia       VARCHAR(255),
    logradouro          VARCHAR(255),
    numero              VARCHAR(20),
    bairro              VARCHAR(120),
    municipio           VARCHAR(120),
    uf                  CHAR(2),
    cep                 VARCHAR(9),
    data_emissao        TIMESTAMPTZ,
    numero_cfe          VARCHAR(20),
    serie_cfe           VARCHAR(10),
    valor_total          NUMERIC(12,2),
    valor_descontos      NUMERIC(12,2) DEFAULT 0,
    forma_pagamento     VARCHAR(60),
    status_consulta     VARCHAR(20) NOT NULL DEFAULT 'ok', -- ok | erro | processando
    raw_response        JSONB NOT NULL,          -- payload completo da Infosimples
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_cupom_header_data_emissao ON cupom_header (data_emissao DESC);
CREATE INDEX idx_cupom_header_cnpj ON cupom_header (cnpj_emitente);
CREATE INDEX idx_cupom_header_raw_gin ON cupom_header USING GIN (raw_response);

-- ------------------------------------------------------------
-- 2. cupom_items: um registro por item de um cupom
-- ------------------------------------------------------------
CREATE TABLE cupom_items (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    cupom_header_id     UUID NOT NULL REFERENCES cupom_header(id) ON DELETE CASCADE,
    ordem               INT,
    codigo_barras       VARCHAR(30),              -- GTIN/EAN do produto (usado na tela 2)
    codigo_produto_estabelecimento VARCHAR(60),    -- código interno do mercado, se vier
    descricao           VARCHAR(255) NOT NULL,
    ncm                 VARCHAR(10),
    cfop                VARCHAR(6),
    unidade             VARCHAR(10),
    quantidade          NUMERIC(12,3) NOT NULL DEFAULT 1,
    valor_unitario      NUMERIC(12,4) NOT NULL,
    valor_total         NUMERIC(12,2) NOT NULL,
    valor_desconto      NUMERIC(12,2) DEFAULT 0,
    raw_response        JSONB,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_cupom_items_barcode ON cupom_items (codigo_barras);
CREATE INDEX idx_cupom_items_header ON cupom_items (cupom_header_id);
CREATE INDEX idx_cupom_items_descricao_trgm ON cupom_items USING GIN (descricao gin_trgm_ops);

-- ------------------------------------------------------------
-- 3. produtos_cache: cache local das consultas ao Cosmos/Bluesoft
--    (evita bater na API externa toda vez e permite sugestão
--     de produtos similares por NCM/categoria/marca)
-- ------------------------------------------------------------
CREATE TABLE produtos_cache (
    codigo_barras       VARCHAR(30) PRIMARY KEY,
    descricao           VARCHAR(255),
    marca               VARCHAR(120),
    categoria           VARCHAR(120),
    subcategoria        VARCHAR(120),
    ncm                 VARCHAR(10),
    gpc                 VARCHAR(20),
    thumbnail_url       TEXT,
    raw_response        JSONB NOT NULL,           -- payload completo do Cosmos
    consultado_em       TIMESTAMPTZ NOT NULL DEFAULT now(),
    expira_em           TIMESTAMPTZ NOT NULL DEFAULT (now() + INTERVAL '30 days')
);

CREATE INDEX idx_produtos_cache_categoria ON produtos_cache (categoria);
CREATE INDEX idx_produtos_cache_ncm ON produtos_cache (ncm);
CREATE INDEX idx_produtos_cache_descricao_trgm ON produtos_cache USING GIN (descricao gin_trgm_ops);

-- ------------------------------------------------------------
-- 4. view auxiliar: histórico de preços por código de barras
--    (usada diretamente pela tela 2 do app)
-- ------------------------------------------------------------
CREATE VIEW vw_historico_precos AS
SELECT
    ci.codigo_barras,
    ci.descricao,
    ci.valor_unitario,
    ci.quantidade,
    ch.data_emissao,
    ch.nome_fantasia,
    ch.razao_social,
    ch.municipio,
    ch.uf,
    ch.id AS cupom_header_id
FROM cupom_items ci
JOIN cupom_header ch ON ch.id = ci.cupom_header_id
WHERE ci.codigo_barras IS NOT NULL;

-- ------------------------------------------------------------
-- 5. trigger simples para updated_at
-- ------------------------------------------------------------
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_cupom_header_updated_at
BEFORE UPDATE ON cupom_header
FOR EACH ROW EXECUTE FUNCTION set_updated_at();
