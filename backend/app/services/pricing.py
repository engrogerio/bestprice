from datetime import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.models import CupomHeader, CupomItem


def _parse_data(valor: str | None) -> datetime | None:
    if not valor:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%d/%m/%Y %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(valor, fmt)
        except ValueError:
            continue
    return None


async def salvar_cupom(db: AsyncSession, chave_acesso: str, raw: dict) -> CupomHeader:
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
        return existente

    header = CupomHeader(
        chave_acesso=chave_acesso,
        cnpj_emitente=raw.get("cnpj") or raw.get("emitente", {}).get("cnpj"),
        razao_social=raw.get("razao_social") or raw.get("emitente", {}).get("razao_social"),
        nome_fantasia=raw.get("nome_fantasia") or raw.get("emitente", {}).get("nome_fantasia"),
        municipio=raw.get("municipio") or raw.get("emitente", {}).get("municipio"),
        uf=raw.get("uf") or raw.get("emitente", {}).get("uf") or "SP",
        data_emissao=_parse_data(raw.get("data_emissao")),
        valor_total=raw.get("valor_total"),
        status_consulta="ok",
        raw_response=raw,
    )
    db.add(header)
    await db.flush()  # garante header.id antes de criar os items

    for idx, item in enumerate(raw.get("produtos", []) or raw.get("itens", []), start=1):
        db.add(CupomItem(
            cupom_header_id=header.id,
            ordem=idx,
            codigo_barras=item.get("codigo_barras") or item.get("ean") or item.get("gtin"),
            descricao=item.get("descricao") or item.get("descricao_produto") or "Item sem descrição",
            quantidade=Decimal(str(item.get("quantidade", 1))),
            valor_unitario=Decimal(str(item.get("valor_unitario", 0))),
            valor_total=Decimal(str(item.get("valor_total", 0))),
            raw_response=item,
        ))

    await db.commit()
    await db.refresh(header)
    return header


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
