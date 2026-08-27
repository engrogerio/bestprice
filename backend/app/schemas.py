from pydantic import BaseModel


class ScanCupomRequest(BaseModel):
    codigo_barras_cupom: str  # conteúdo lido do código de barras/QR do cupom (chave de acesso 44 díg.)


class ScanCupomResponse(BaseModel):
    cupom_header_id: str
    chave_acesso: str
    total_itens: int
    valor_total: float | None


class CompraHistorico(BaseModel):
    valor_unitario: float
    descricao: str
    data_compra: str | None
    local: str | None
    municipio: str | None
    uf: str | None


class ProdutoSimilar(BaseModel):
    descricao: str
    marca: str | None = None
    codigo_barras: str | None = None
    thumbnail_url: str | None = None


class ConsultaProdutoResponse(BaseModel):
    codigo_barras: str
    descricao: str | None
    marca: str | None
    thumbnail_url: str | None
    historico: list[CompraHistorico]
    diferenca_percentual: float | None
    mais_barato: float | None
    mais_caro: float | None
    similares: list[ProdutoSimilar]
