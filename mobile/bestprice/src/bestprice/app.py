import toga
from toga.style import Pack
from toga.style.pack import COLUMN

from bestprice import colors
from bestprice.screens.scan_cupom import criar_tela_scan_cupom
from bestprice.screens.consulta_produto import criar_tela_consulta_produto


class BestPriceApp(toga.App):
    def startup(self):
        tela_cupom = criar_tela_scan_cupom(self)
        tela_produto = criar_tela_consulta_produto(self)

        # OptionContainer = navegação em abas, nativo em cada plataforma
        abas = toga.OptionContainer(
            content=[
                toga.OptionItem("Ler Cupom", tela_cupom),
                toga.OptionItem("Consultar Produto", tela_produto),
            ],
            style=Pack(background_color=colors.BRANCO),
        )

        self.main_window = toga.MainWindow(title="BestPrice")
        self.main_window.content = toga.Box(
            children=[abas],
            style=Pack(direction=COLUMN, flex=1, background_color=colors.BRANCO),
        )
        self.main_window.show()


def main():
    return BestPriceApp("BestPrice", "com.bestprice")


if __name__ == "__main__":
    main().main_loop()
