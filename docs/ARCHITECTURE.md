# BestPrice — Arquitetura

## Visão geral

```
┌─────────────────────┐        HTTPS        ┌───────────────────────────┐
│   App Mobile         │  ───────────────▶  │   BestPrice API (backend)  │
│   (BeeWare / Toga)    │  ◀───────────────  │   FastAPI / Python          │
│                       │                     │                            │
│  • Tela: Ler Cupom     │                     │  POST /cupom/scan          │
│  • Tela: Consultar     │                     │  GET  /produto/{codigo}    │
│    Produto             │                     └─────────┬───────────┬─────┘
└───────────────────────┘                               │           │
                                                          │           │
                                     ┌────────────────────┘           └───────────────────┐
                                     ▼                                                     ▼
                     ┌───────────────────────────┐                       ┌───────────────────────────┐
                     │  Infosimples API            │                       │  Cosmos / Bluesoft API      │
                     │  SEFAZ SP · CF-e Completa    │                       │  Catálogo de produtos GTIN   │
                     └───────────────────────────┘                       └───────────────────────────┘

                     ┌──────────────────────────────────────────────────────────┐
                     │                Postgres (AWS RDS)                          │
                     │  cupom_header · cupom_items · produtos_cache               │
                     │  provisionado via OpenTofu (infra/opentofu)                 │
                     └──────────────────────────────────────────────────────────┘
```

## Por que uma API própria (backend) em vez do app chamar as APIs públicas direto?

- **Segurança das chaves**: os tokens da Infosimples e da Cosmos nunca ficam
  no app (que pode ser descompilado); ficam só no servidor.
- **Persistência centralizada**: só o backend tem credencial de escrita no
  Postgres.
- **Regra de negócio**: cálculo de histórico de últimas 5 compras, % de
  variação e sugestão de marcas similares roda em SQL/servidor, não no
  celular.
- **Controle de custo**: cache de produto (`produtos_cache`, 30 dias) evita
  bater na Cosmos toda vez; dedupe por `chave_acesso` evita reconsultar o
  mesmo cupom na Infosimples.

## Fluxo 1 — Leitura do cupom fiscal

1. Usuário abre a tela **"Ler Cupom"** e fotografa o código de barras/QR
   impresso no cupom.
2. O app decodifica a imagem localmente (`pyzbar`) e extrai a chave de
   acesso de 44 dígitos.
3. O app envia `POST /cupom/scan { codigo_barras_cupom }` para o backend.
4. O backend chama a **Infosimples** (`GET /api/v2/consultas/sefaz/sp/cfe-completa`).
5. O backend grava o cabeçalho em `cupom_header` e os itens em `cupom_items`
   (guardando também o JSON bruto em `raw_response`, como rede de segurança).
6. O app mostra confirmação (quantidade de itens e valor total).

## Fluxo 2 — Consulta de produto

1. Usuário abre a tela **"Consultar Produto"** e fotografa o código de
   barras do produto (na prateleira, por exemplo).
2. O app chama `GET /produto/{codigo_barras}`.
3. O backend:
   - Busca no próprio Postgres (`cupom_items` + `cupom_header`) as últimas
     5 compras daquele código de barras, calcula a diferença percentual
     entre a mais cara e a mais barata.
   - Busca (ou usa cache de) dados de catálogo do produto na **Cosmos**
     (nome, marca, categoria, foto).
   - Busca na Cosmos produtos da mesma categoria com marca diferente, para
     sugerir alternativas.
4. O app mostra: histórico ordenado (mais novo → mais velho), % de
   variação, data/local de cada compra, e cards de marcas equivalentes.

## Modelo de dados (resumo — ver `db/schema.sql` para o DDL completo)

| Tabela            | Papel                                                          |
|-------------------|------------------------------------------------------------------|
| `cupom_header`    | 1 linha por cupom fiscal lido (emitente, data, valor total, raw JSON) |
| `cupom_items`     | 1 linha por item do cupom (código de barras, descrição, valor unitário) |
| `produtos_cache`  | Cache local (30 dias) dos dados de catálogo vindos da Cosmos      |
| `vw_historico_precos` | View de conveniência que já faz o JOIN item + cupom            |

## Infraestrutura (OpenTofu)

`infra/opentofu` provisiona, na AWS:

- `aws_db_instance` (Postgres, RDS) — storage criptografado, backup automático,
  `db.t4g.micro` por padrão (ajustável).
- `aws_security_group` — libera porta 5432 **só** para o CIDR do backend.
- `aws_db_subnet_group` — usa subnets privadas.
- `aws_db_parameter_group` — log de queries lentas (> 500ms).

O backend roda fora do escopo do RDS (ex.: ECS Fargate/App Runner) na mesma
VPC, e recebe a `DATABASE_URL` a partir do output `db_endpoint`.

## Identidade visual

Paleta: **amarelo** `#FFC400`, **preto** `#111111`, **branco** `#FFFFFF`,
aplicada nos botões de ação (amarelo com texto preto), fundo branco e
textos em preto — ver `mobile/bestprice/src/bestprice/colors.py`.

## Limitações conhecidas / próximos passos

- O mapeamento exato dos campos JSON da Infosimples (`app/services/pricing.py::salvar_cupom`)
  precisa ser validado contra uma resposta real da API (a página de docs
  bloqueia scraping automatizado); o `raw_response` em JSONB garante que
  nenhum dado se perde enquanto isso é ajustado.
- A câmera do BeeWare/Toga tira foto, não faz streaming em tempo real —
  ver nota em `mobile/bestprice/README.md`.
- Autenticação de usuário (login) não foi incluída neste MVP; recomenda-se
  adicionar (ex. JWT) antes de ir a produção, para vincular cupons a um
  usuário e não expor `/cupom/scan` publicamente.
