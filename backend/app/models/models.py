import uuid
from datetime import datetime

from sqlalchemy import String, Numeric, DateTime, ForeignKey, Integer, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class CupomHeader(Base):
    __tablename__ = "cupom_header"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chave_acesso: Mapped[str] = mapped_column(String(44), unique=True, nullable=False)
    cnpj_emitente: Mapped[str | None] = mapped_column(String(14))
    razao_social: Mapped[str | None] = mapped_column(String(255))
    nome_fantasia: Mapped[str | None] = mapped_column(String(255))
    municipio: Mapped[str | None] = mapped_column(String(120))
    uf: Mapped[str | None] = mapped_column(String(2))
    data_emissao: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    valor_total: Mapped[float | None] = mapped_column(Numeric(12, 2))
    status_consulta: Mapped[str] = mapped_column(String(20), default="ok")
    raw_response: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    items: Mapped[list["CupomItem"]] = relationship(back_populates="header", cascade="all, delete-orphan")


class CupomItem(Base):
    __tablename__ = "cupom_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cupom_header_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cupom_header.id", ondelete="CASCADE"))
    ordem: Mapped[int | None] = mapped_column(Integer)
    codigo_barras: Mapped[str | None] = mapped_column(String(30), index=True)
    descricao: Mapped[str] = mapped_column(String(255), nullable=False)
    quantidade: Mapped[float] = mapped_column(Numeric(12, 3), default=1)
    valor_unitario: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False)
    valor_total: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    raw_response: Mapped[dict | None] = mapped_column(JSONB)

    header: Mapped["CupomHeader"] = relationship(back_populates="items")


class ProdutoCache(Base):
    __tablename__ = "produtos_cache"

    codigo_barras: Mapped[str] = mapped_column(String(30), primary_key=True)
    descricao: Mapped[str | None] = mapped_column(String(255))
    marca: Mapped[str | None] = mapped_column(String(120))
    categoria: Mapped[str | None] = mapped_column(String(120))
    ncm: Mapped[str | None] = mapped_column(String(10))
    thumbnail_url: Mapped[str | None] = mapped_column(String)
    raw_response: Mapped[dict] = mapped_column(JSONB, nullable=False)
    consultado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
