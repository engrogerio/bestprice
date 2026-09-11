from datetime import datetime
from decimal import Decimal
from logging import getLogger

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.models import CupomHeader, CupomItem, CupomKeys

logger = getLogger(__name__)

def _parse_data(valor: str | None) -> datetime | None:
    if not valor:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%d/%m/%Y %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(valor, fmt)
        except ValueError:
            continue
    return None


async def save_cupom(db: AsyncSession, chave_acesso: str, raw: dict) -> CupomHeader:
    """
    Normaliza a resposta da Infosimples e grava em cupom_header + cupom_items.

    OBS: os nomes de campo abaixo (raw.get("cnpj"), raw.get("produtos") etc.)
    são a melhor aproximação com base no padrão de retorno da Infosimples para
    consultas de NFC-e/CF-e. Como a doc oficial não pôde ser raspada
    automaticamente, ao integrar de verdade: rode uma consulta de teste,
    salve o JSON puro (já cai em raw_response) e ajuste os `.get(...)`
    abaixo para bater exatamente com as chaves reais retornadas.
    """
    existente = await db.scalar(select(CupomHeader).where(CupomHeader.chave_acesso == chave_acesso))
    if existente:
        logger.info(f'cfe {chave_acesso} already on db!')
        return existente
    logger.info(f'cfe {chave_acesso} being processed!')
     
    data = raw.get("data")[0] # why always 0 ?
    header = CupomHeader(
        chave_acesso=chave_acesso,
        cnpj_emitente=data.get("emitente", {}).get("normalizado_cnpj"),
        razao_social=data.get("emitente", {}).get("nome_razao_social"),
        nome_fantasia=data.get("emitente", {}).get("nome_fantasia"),
        logradouro=data.get("emitente", {}).get("endereco"),
        bairro=data.get("emitente", {}).get("bairro_distrito"),
        municipio=data.get("emitente", {}).get("municipio"),
        uf=data.get("emitente", {}).get("uf"),
        cep=data.get("emitente", {}).get("cep"),
        data_emissao=datetime.fromisoformat(data.get("cfe").get("data_hora_emissao")),
        numero_cfe=data.get("cfe", {}).get("dados_cfe").get("numero_cfe"),
        valor_total=Decimal(str(data.get("totais").get("totais").get("normalizado_valor_total_cfe"))),
        status_consulta="ok",
        raw_response=raw,
    )
    db.add(header)
    await db.flush()  # garante header.id antes de criar os items

    for idx, item in enumerate(data.get("produtos_servicos", []), start=1):
        db.add(CupomItem(
            cupom_header_id=header.id,
            ordem=idx,
            codigo_barras=item.get("codigo_gtin"),
            descricao=item.get("descricao") or "Item sem descrição",
            quantidade=item.get("normalizado_qtd_comercial", 1),
            valor_unitario=item.get("normalizado_valor_unitario", 0),
            unidade=item.get("unidade_comercial"),
            valor_desconto=item.get("normalizado_valor_desconto", 0),
            valor_total=item.get("normalizado_valor_liquido_item"),
            raw_response=item,
        ))

    await db.commit()
    await db.refresh(header)
    return header

async def save_cupom_not_processed(db: AsyncSession, chave_acesso: str):
    """
    Salva cfe id que o infosimples retornou erros para processar no futuro.
    """
    existente = await db.scalar(select(CupomHeader).where(CupomHeader.chave_acesso == chave_acesso))
    if existente:
        logger.info(f'cfe {chave_acesso} already on db!')
        return
    logger.info(f'cfe {chave_acesso} being saved for future querying!')
    # if blank due to an error, saves on pending_cfes table

    header = CupomKeys(
        chave_acesso=chave_acesso,
    )
    db.add(header)
    await db.commit()
    await db.refresh(header)
    return

async def historico_precos(db: AsyncSession, codigo_barras: str, limite: int | None = None):
    """
    Retorna as últimas N compras do item (mais novo -> mais velho) e a
    diferença percentual entre a compra mais cara e a mais barata do período.
    """
    limite = limite or settings.historico_precos_limite

    sql = select(
        CupomItem.valor_unitario,
        CupomItem.descricao,
        CupomHeader.data_emissao,
        CupomHeader.nome_fantasia,
        CupomHeader.razao_social,
        CupomHeader.municipio,
        CupomHeader.uf,
    ).join(CupomHeader, CupomHeader.id == CupomItem.cupom_header_id
    ).where(CupomItem.codigo_barras == codigo_barras
    ).order_by(CupomHeader.data_emissao.desc()
    ).limit(limite)

    rows = (await db.execute(sql)).all()

    compras = [
        {
            "valor_unitario": float(r.valor_unitario),
            "descricao": r.descricao,
            "data_compra": r.data_emissao.isoformat() if r.data_emissao else None,
            "local": r.nome_fantasia or r.razao_social,
            "municipio": r.municipio,
            "uf": r.uf,
        }
        for r in rows
    ]

    if not compras:
        return {"compras": compras, "diferenca_percentual": None, "mais_barato": None, "mais_caro": None}

    valores = [c["valor_unitario"] for c in compras]
    mais_barato, mais_caro = min(valores), max(valores)
    diferenca_percentual = (
        round(((mais_caro - mais_barato) / mais_barato) * 100, 2) if mais_barato > 0 else None
    )

    return {
        "compras": compras,
        "diferenca_percentual": diferenca_percentual,
        "mais_barato": mais_barato,
        "mais_caro": mais_caro,
    }
