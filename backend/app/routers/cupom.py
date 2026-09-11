import re

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from logging import getLogger

from app.db import get_db
from app.schemas import ScanCupomRequest, ScanCupomResponse
from app.services.infosimples import consultar_cupom, InfosimplesError
from app.services.pricing import save_cupom, save_cupom_not_processed


logger = getLogger(__name__)

router = APIRouter(prefix="/cupom", tags=["cupom"])

def _extrair_chave_acesso(codigo_lido: str) -> str:
    """
    O QR Code / código de barras do CF-e paulista traz uma URL com a
    chave de acesso de 44 dígitos (ex: ...?p=35...|2|1|1|...).
    Aqui extraímos apenas os 44 dígitos numéricos.
    """
    digitos = re.sub(r"\D", "", codigo_lido)
    match = re.search(r"\d{44}", digitos)
    if not match:
        raise HTTPException(400, "Não foi possível extrair a chave de acesso (44 dígitos) do código lido")
    return match.group(0)


@router.post("/scan", response_model=ScanCupomResponse)
async def scan_cupom(payload: ScanCupomRequest, db: AsyncSession = Depends(get_db)):
    """
    Recebe o texto bruto lido da câmera (QR/código de barras do cupom fiscal),
    consulta a Infosimples e persiste o cupom + itens no banco.
    """
    chave_acesso = _extrair_chave_acesso(payload.codigo_barras_cupom)

    try:
        raw = await consultar_cupom(chave_acesso)
    except InfosimplesError as e:
        # save cfe id to scan again later in case it failed for any reason...
        # await save_cupom_not_processed(db, chave_acesso)
        raise HTTPException(502, f"Falha ao consultar SEFAZ: {e}")
    header = await save_cupom(db, chave_acesso, raw)
    logger.info(f'cfe {chave_acesso} processed!')
    return ScanCupomResponse(
        cupom_header_id=str(header.id),
        chave_acesso=header.chave_acesso,
        total_itens=len(header.items),
        valor_total=float(header.valor_total) if header.valor_total is not None else None,
    )
