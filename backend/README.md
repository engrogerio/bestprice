# BestPrice API (backend)

API própria (FastAPI/Python) que fica entre o app mobile e as APIs
externas (Infosimples e Cosmos/Bluesoft), e é dona da conexão com o
Postgres.

## Rodar localmente

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env    # preencha token da Infosimples e a DATABASE_URL
# aplique db/schema.sql no Postgres apontado por DATABASE_URL

uvicorn app.main:app --reload --port 8000
```

## Endpoints

| Método | Rota                     | Descrição                                                   |
|--------|--------------------------|---------------------------------------------------------------|
| POST   | `/cupom/scan`            | Recebe o texto lido do código de barras/QR do cupom, consulta a Infosimples e grava no banco |
| GET    | `/produto/{codigo_barras}` | Histórico das últimas 5 compras, diferença %, e sugestões de marcas similares |
| GET    | `/health`                | Health check |

Docs interativas (Swagger) em `/docs` assim que o servidor sobe.

## Variáveis de ambiente (prefixo `BESTPRICE_`)

- `BESTPRICE_DATABASE_URL` — ex: `postgresql+asyncpg://user:pass@host:5432/bestprice`
- `BESTPRICE_INFOSIMPLES_TOKEN`
- `BESTPRICE_COSMOS_TOKEN`

## Deploy sugerido

Container Docker rodando em ECS Fargate / App Runner / EC2, na mesma
VPC do RDS criado pelo OpenTofu (`infra/opentofu`), liberando a porta
5432 apenas para o security group do backend.
