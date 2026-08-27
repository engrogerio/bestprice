"""
Leitura de código de barras usando a API de câmera do Toga (toga.Camera)
+ decodificação com pyzbar.

IMPORTANTE (limitação conhecida do BeeWare/Toga): a API de câmera do Toga
tira uma FOTO (não é um stream de vídeo ao vivo com overlay de mira, como
em apps nativos de scanner). Ou seja, o fluxo aqui é:
  1) usuário toca em "Escanear"
  2) abre a câmera nativa, usuário fotografa o código de barras
  3) o app decodifica a foto localmente com pyzbar

Isso é suficiente para o caso de uso (ler cupom fiscal e produtos), mas
se no futuro for necessário scanner em tempo real com overlay, considere
usar um plugin nativo específico da plataforma via bindings do Toga, ou
migrar essa tela específica para código nativo (Kotlin/Swift) chamado
pela ponte do Briefcase.
"""
from pyzbar.pyzbar import decode
from PIL import Image


async def escanear_codigo(camera, window) -> str | None:
    """
    Abre a câmera, tira a foto e retorna o primeiro código de barras
    decodificado (texto). Retorna None se nada for reconhecido.
    """
    foto = await camera.take_photo()
    if foto is None:
        return None

    imagem = Image.open(foto)
    resultados = decode(imagem)
    if not resultados:
        return None

    return resultados[0].data.decode("utf-8")
