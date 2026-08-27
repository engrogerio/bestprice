# BestPrice

App para comparar preços a partir de cupons fiscais: leia o cupom uma vez
e depois, no mercado, escaneie o código de barras do produto para ver o
histórico de preços das suas últimas compras e sugestões de marcas mais
baratas.

## Estrutura do repositório

```
bestprice/
├── docs/
│   └── ARCHITECTURE.md      ← arquitetura completa + diagrama
├── infra/opentofu/          ← provisionamento do Postgres (AWS RDS)
├── db/schema.sql            ← DDL das tabelas
├── backend/                 ← API própria (FastAPI/Python)
└── mobile/bestprice/        ← app mobile (BeeWare/Toga)
```

## Ordem sugerida para colocar no ar

1. **Infra**: `cd infra/opentofu && tofu init && tofu apply` (preencha
   `terraform.tfvars` a partir do `.example`).
2. **Banco**: aplique `db/schema.sql` no endpoint gerado pelo OpenTofu.
3. **Backend**: `cd backend`, configure `.env` (token Infosimples +
   `DATABASE_URL`), `pip install -r requirements.txt`,
   `uvicorn app.main:app`. Publique atrás de HTTPS (ECS/App Runner/EC2).
4. **Mobile**: `cd mobile/bestprice`, ajuste `BASE_URL` em `api_client.py`
   para a URL pública do backend, `briefcase dev` para testar,
   `briefcase build android` / `briefcase build iOS` para gerar o app.

Veja `docs/ARCHITECTURE.md` para o diagrama e detalhes de cada fluxo.
