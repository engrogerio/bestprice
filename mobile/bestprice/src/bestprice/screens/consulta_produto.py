import toga
from toga.style import Pack
from toga.style.pack import COLUMN, ROW, CENTER

from bestprice import colors
from bestprice.barcode import escanear_codigo
from bestprice.api_client import consultar_produto, BestPriceApiError


def _linha_compra(compra: dict, is_mais_barato: bool, is_mais_caro: bool) -> toga.Box:
    cor_valor = colors.PRETO
    if is_mais_barato:
        cor_valor = colors.VERDE_OK
    elif is_mais_caro:
        cor_valor = colors.VERMELHO_ALERTA

    return toga.Box(
        children=[
            toga.Label(f"R$ {compra['valor_unitario']:.2f}",
                       style=Pack(color=cor_valor, font_weight="bold", width=90)),
            toga.Box(
                children=[
                    toga.Label(compra.get("local") or "Local não informado", style=Pack(color=colors.PRETO)),
                    toga.Label(
                        f"{(compra.get('data_compra') or '')[:10]} · {compra.get('municipio') or ''}/{compra.get('uf') or ''}",
                        style=Pack(color="#555555", font_size=11),
                    ),
                ],
                style=Pack(direction=COLUMN),
            ),
        ],
        style=Pack(direction=ROW, padding=8, background_color=colors.CINZA_CLARO, padding_bottom=4),
    )


def _card_similar(produto: dict) -> toga.Box:
    return toga.Box(
        children=[
            toga.Label(produto.get("descricao") or "Produto similar", style=Pack(color=colors.PRETO, font_weight="bold")),
            toga.Label(produto.get("marca") or "", style=Pack(color="#555555", font_size=12)),
        ],
        style=Pack(
            direction=COLUMN, padding=10, background_color=colors.AMARELO,
            padding_right=8, width=160,
        ),
    )


def criar_tela_consulta_produto(app: toga.App) -> toga.Box:
    camera = toga.Camera(app)

    titulo = toga.Label(
        "Consultar Produto",
        style=Pack(font_size=20, font_weight="bold", color=colors.PRETO, padding_bottom=10),
    )

    status = toga.Label("", style=Pack(color=colors.PRETO, padding_top=10, text_align=CENTER))
    nome_produto = toga.Label("", style=Pack(font_size=17, font_weight="bold", color=colors.PRETO, padding_top=15))
    resumo_diferenca = toga.Label("", style=Pack(color=colors.PRETO, padding_bottom=10))

    historico_box = toga.Box(style=Pack(direction=COLUMN, padding_top=5))
    similares_titulo = toga.Label(
        "Outras marcas equivalentes", style=Pack(font_weight="bold", color=colors.PRETO, padding_top=20)
    )
    similares_box = toga.Box(style=Pack(direction=ROW, padding_top=8))

    async def ao_escanear(widget):
        status.text = "Abrindo câmera..."
        nome_produto.text = ""
        resumo_diferenca.text = ""
        historico_box.clear()
        similares_box.clear()

        try:
            codigo = await escanear_codigo(camera, app.main_window)
        except Exception as e:
            status.text = f"Erro na câmera: {e}"
            return

        if not codigo:
            status.text = "Nenhum código reconhecido. Tente novamente."
            return

        status.text = "Buscando histórico de preços..."
        try:
            dados = await consultar_produto(codigo)
        except BestPriceApiError as e:
            status.text = f"Erro: {e}"
            return

        status.text = ""
        nome_produto.text = dados.get("descricao") or f"Código {codigo}"

        if dados["diferenca_percentual"] is not None:
            resumo_diferenca.text = (
                f"Variação entre a compra mais cara e a mais barata: "
                f"{dados['diferenca_percentual']:.1f}%"
            )
        else:
            resumo_diferenca.text = "Ainda não há histórico de compras para este item."

        for compra in dados["historico"]:
            is_barato = compra["valor_unitario"] == dados["mais_barato"]
            is_caro = compra["valor_unitario"] == dados["mais_caro"]
            historico_box.add(_linha_compra(compra, is_barato, is_caro))

        for similar in dados["similares"]:
            similares_box.add(_card_similar(similar))

    botao_escanear = toga.Button(
        "📷  Escanear Produto",
        on_press=ao_escanear,
        style=Pack(
            background_color=colors.AMARELO,
            color=colors.PRETO,
            font_weight="bold",
            padding=15,
            font_size=16,
        ),
    )

    conteudo = toga.Box(
        children=[
            titulo, botao_escanear, status, nome_produto, resumo_diferenca,
            historico_box, similares_titulo, similares_box,
        ],
        style=Pack(direction=COLUMN, padding=25, background_color=colors.BRANCO),
    )

    return toga.ScrollContainer(content=conteudo, style=Pack(background_color=colors.BRANCO))
