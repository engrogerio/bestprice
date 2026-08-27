import toga
from toga.style import Pack
from toga.style.pack import COLUMN, ROW, CENTER

from bestprice import colors
from bestprice.barcode import escanear_codigo
from bestprice.api_client import enviar_cupom, BestPriceApiError


def criar_tela_scan_cupom(app: toga.App) -> toga.Box:
    camera = toga.Camera(app)

    titulo = toga.Label(
        "Ler Cupom Fiscal",
        style=Pack(font_size=20, font_weight="bold", color=colors.PRETO, padding_bottom=10),
    )

    instrucao = toga.Label(
        "Aponte para o código de barras ou QR Code impresso no cupom fiscal.",
        style=Pack(color=colors.PRETO, padding_bottom=20, text_align=CENTER),
    )

    status = toga.Label("", style=Pack(color=colors.PRETO, padding_top=15, text_align=CENTER))
    resultado_box = toga.Box(style=Pack(direction=COLUMN, padding_top=10))

    async def ao_escanear(widget):
        status.text = "Abrindo câmera..."
        try:
            codigo = await escanear_codigo(camera, app.main_window)
        except Exception as e:
            status.text = f"Erro na câmera: {e}"
            return

        if not codigo:
            status.text = "Nenhum código reconhecido. Tente novamente."
            return

        status.text = "Consultando SEFAZ e salvando cupom..."
        resultado_box.clear()
        try:
            dados = await enviar_cupom(codigo)
        except BestPriceApiError as e:
            status.text = f"Erro: {e}"
            return

        status.text = "Cupom salvo com sucesso!"
        resultado_box.add(
            toga.Label(f"Itens lidos: {dados['total_itens']}", style=Pack(color=colors.PRETO)),
            toga.Label(f"Valor total: R$ {dados['valor_total']:.2f}" if dados["valor_total"] else "",
                       style=Pack(color=colors.PRETO)),
        )

    botao_escanear = toga.Button(
        "📷  Escanear Cupom",
        on_press=ao_escanear,
        style=Pack(
            background_color=colors.AMARELO,
            color=colors.PRETO,
            font_weight="bold",
            padding=15,
            font_size=16,
        ),
    )

    return toga.Box(
        children=[titulo, instrucao, botao_escanear, status, resultado_box],
        style=Pack(direction=COLUMN, padding=25, background_color=colors.BRANCO, alignment=CENTER),
    )
