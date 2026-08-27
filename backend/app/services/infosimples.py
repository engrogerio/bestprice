"""
Cliente para a API Infosimples - SEFAZ/SP CF-e Completa.
https://api.infosimples.com/api/v2/consultas/sefaz/sp/cfe-completa

A chave do código de barras do cupom fiscal paulista contém a chave de
acesso de 44 dígitos do CF-e. É esse valor que enviamos como parâmetro.
"""
import httpx
import requests

from app.config import settings
from logging import getLogger

logger = getLogger(__name__)

class InfosimplesError(Exception):
    pass


async def consultar_cupom(chave_acesso: str) -> dict:
    """
    Consulta o CF-e completo na SEFAZ/SP via Infosimples.

    Retorna o JSON bruto da API (o parsing/normalização para as tabelas
    do banco fica em app/services/pricing.py::salvar_cupom, justamente
    para preservarmos o raw_response mesmo se o formato mudar).
    """
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    payload = f'chave={chave_acesso}&token={settings.infosimples_token}'
    
    logger.info(f"Infosimples consulta: {payload}")
    async with httpx.AsyncClient(timeout=310) as client:
       resp = await client.post(settings.infosimples_base_url, data=payload, headers=headers)
    #resp = requests.request("POST", settings.infosimples_base_url, data=payload, headers=headers)
    #resp.encoding = 'utf-8'
    if resp.status_code != 200:
        raise InfosimplesError(f"Infosimples HTTP {resp.status_code}: {resp.text[:500]}")
    print(resp.json())
    body = resp.json()

    # Contrato padrão Infosimples: {"code": 200, "code_message": "...", "data": [...]}
    if body.get("code") != 200:
        raise InfosimplesError(f"Infosimples code={body.get('code')} msg={body.get('code_message')}")

    if not body.get("data"):
        raise InfosimplesError("Infosimples retornou sucesso mas sem dados (cupom não encontrado?)")

    return body["data"][0]
