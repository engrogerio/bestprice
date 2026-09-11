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
from . import fake_response


logger = getLogger(__name__)

class InfosimplesError(Exception):
    """Erro genérico de comunicação/contrato com a Infosimples."""
    pass


class InfosimplesTimeoutError(InfosimplesError):
    """A Infosimples não respondeu dentro do tempo esperado."""
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
    # Timeouts separados: connect (conseguir abrir conexão) vs read (esperar resposta)
    timeout = httpx.Timeout(connect=10.0, read=300.0, write=10.0, pool=10.0)

    try:

        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(
                settings.infosimples_base_url, data=payload, headers=headers
            )

    except httpx.ConnectTimeout as e:
        raise InfosimplesTimeoutError(
            "Infosimples: timeout ao conectar"
        ) from e
    except httpx.ReadTimeout as e:
        raise InfosimplesTimeoutError(
            "Infosimples: timeout aguardando resposta"
        ) from e
    except httpx.RequestError as e:
        # cobre ConnectError, PoolTimeout, etc.
        raise InfosimplesError(f"Infosimples: falha de rede ({e!r})") from e

    if resp.status_code != 200:
        raise InfosimplesError(
            f"Infosimples HTTP {resp.status_code}: {resp.text[:500]}"
        )

    try:
        body = resp.json()
    except ValueError as e:
        raise InfosimplesError("Infosimples: resposta não é JSON válido") from e

    if body.get("code") != 200:
        raise InfosimplesError(
            f"Infosimples code={body.get('code')} msg={body.get('code_message')}"
        )

    if not body.get("data"):
        raise InfosimplesError(
            "Infosimples retornou sucesso mas sem dados (cupom não encontrado?)"
        )

    return body #["data"][0]

async def consultar_cupom_fake(chave_acesso: str) -> dict:
    return fake_response.response