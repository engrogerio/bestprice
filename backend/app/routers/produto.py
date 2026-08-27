from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.models import ProdutoCache
from app.schemas import ConsultaProdutoResponse, ProdutoSimilar
from app.services.cosmos import consultar_produto, buscar_similares
from app.services.pricing import historico_precos

router = APIRouter(prefix="/produto", tags=["produto"])


@router.get("/{codigo_barras}", response_model=ConsultaProdutoResponse)
async def consultar(codigo_barras: str, db: AsyncSession = Depends(get_db)):
    """
    Tela 2 do app: lê o código de barras do produto e devolve:
    - últimas N compras (mais nova -> mais velha), diferença % entre mais caro/barato, data e local
    - sugestões de produtos similares de outras marcas (via Cosmos)
    """
    # 1) histórico de preços a partir do nosso próprio banco (cupons já lidos)
    historico = await historico_precos(db, codigo_barras)

    # 2) dados de catálogo do produto (nome, marca, foto) - cache local + Cosmos
    cache = await db.get(ProdutoCache, codigo_barras)
    if not cache or cache.consultado_em < datetime.utcnow() - timedelta(days=30):
        cosmos_data = await consultar_produto(codigo_barras)
        if cosmos_data:
            cache = ProdutoCache(
                codigo_barras=codigo_barras,
                descricao=cosmos_data.get("description"),
                marca=(cosmos_data.get("brand") or {}).get("name"),
                categoria=(cosmos_data.get("ncm") or {}).get("description"),
                ncm=(cosmos_data.get("ncm") or {}).get("code"),
                thumbnail_url=cosmos_data.get("thumbnail"),
                raw_response=cosmos_data,
            )
            await db.merge(cache)
            await db.commit()

    # 3) sugestões de itens equivalentes de outras marcas
    similares_raw = []
    if cache:
        similares_raw = await buscar_similares(cache.descricao, cache.categoria, cache.marca)

    similares = [
        ProdutoSimilar(
            descricao=p.get("description", ""),
            marca=(p.get("brand") or {}).get("name"),
            codigo_barras=p.get("gtin"),
            thumbnail_url=p.get("thumbnail"),
        )
        for p in similares_raw
    ]

    return ConsultaProdutoResponse(
        codigo_barras=codigo_barras,
        descricao=cache.descricao if cache else None,
        marca=cache.marca if cache else None,
        thumbnail_url=cache.thumbnail_url if cache else None,
        historico=historico["compras"],
        diferenca_percentual=historico["diferenca_percentual"],
        mais_barato=historico["mais_barato"],
        mais_caro=historico["mais_caro"],
        similares=similares,
    )
