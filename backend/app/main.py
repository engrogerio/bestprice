from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import cupom, produto
import logging
import sys
from logging import getLogger

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    stream=sys.stdout  # Forces output to stdout instead of default stderr
)

logger = getLogger(__name__)

logger.info("Iniciando app...")


app = FastAPI(
    title="BestPrice API",
    description="Backend do app BestPrice: le cupons fiscais (Infosimples) e consulta produtos/preços (Cosmos).",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # restrinja em produção
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(cupom.router)
app.include_router(produto.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
