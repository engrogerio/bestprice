"""Cliente HTTP para a BestPrice API (backend próprio - ver pasta /backend)."""
import httpx

# Aponte para o backend publicado (ex.: atrás de um Application Load Balancer / API Gateway)
BASE_URL = "https://api.bestprice.example.com"


class BestPriceApiError(Exception):
    pass


async def enviar_cupom(codigo_lido: str) -> dict:
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(f"{BASE_URL}/cupom/scan", json={"codigo_barras_cupom": codigo_lido})
    if resp.status_code != 200:
        raise BestPriceApiError(resp.json().get("detail", resp.text))
    return resp.json()


async def consultar_produto(codigo_barras: str) -> dict:
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(f"{BASE_URL}/produto/{codigo_barras}")
    if resp.status_code != 200:
        raise BestPriceApiError(resp.json().get("detail", resp.text))
    return resp.json()
