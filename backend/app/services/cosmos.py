"""
Cliente para a API Cosmos/Bluesoft (catálogo de produtos por GTIN/EAN).
https://cosmos.bluesoft.com.br/api
"""
import httpx

from app.config import settings

HEADERS = {
    "X-Cosmos-Token": settings.cosmos_token,
    "User-Agent": "BestPrice/1.0 (contato@example.com)",
}


class CosmosError(Exception):
    pass


async def consultar_produto(codigo_barras: str) -> dict | None:
    """Busca um produto pelo GTIN/EAN. Retorna None se não encontrado (404)."""
    url = f"{settings.cosmos_base_url}/gtins/{codigo_barras}.json"

    async with httpx.AsyncClient(timeout=30, headers=HEADERS) as client:
        resp = await client.get(url)

    if resp.status_code == 404:
        return None
    if resp.status_code != 200:
        raise CosmosError(f"Cosmos HTTP {resp.status_code}: {resp.text[:300]}")

    return resp.json()


async def buscar_similares(descricao: str, categoria: str | None, marca_atual: str | None, limit: int = 6) -> list[dict]:
    """
    Sugere produtos "iguais de outras marcas": busca por descrição/categoria
    no Cosmos e filtra fora a marca do produto original.
    """
    url = f"{settings.cosmos_base_url}/products"
    params = {"query": categoria or descricao}

    async with httpx.AsyncClient(timeout=30, headers=HEADERS) as client:
        resp = await client.get(url, params=params)

    if resp.status_code != 200:
        return []

    resultados = resp.json().get("products", []) if isinstance(resp.json(), dict) else []
    similares = [
        p for p in resultados
        if p.get("brand", {}).get("name") and p.get("brand", {}).get("name") != marca_atual
    ]
    return similares[:limit]
