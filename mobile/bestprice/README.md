# BestPrice - App Mobile (BeeWare / Toga)

App Python nativo (via BeeWare/Briefcase) com duas telas, navegação em abas:

1. **Ler Cupom** — fotografa o código de barras/QR do cupom fiscal, decodifica
   localmente (pyzbar) e envia para a BestPrice API (`POST /cupom/scan`).
2. **Consultar Produto** — fotografa o código de barras do produto e mostra:
   últimas 5 compras (mais nova → mais velha), variação % entre a mais cara
   e a mais barata, data/local de cada compra, e sugestões de marcas
   equivalentes (via `GET /produto/{codigo_barras}`).

## Limitação importante da câmera no BeeWare

A API `toga.Camera` tira uma **foto** (não é um stream contínuo com mira de
scanner em tempo real como apps nativos dedicados). O fluxo é: tocar no
botão → a câmera nativa abre → o usuário fotografa o código de barras →
o app decodifica a foto com `pyzbar`. Funciona bem para o caso de uso, mas
se quiser scanner "ao vivo" no futuro, essa tela específica pode precisar
de código nativo por plataforma.

## Rodar em desenvolvimento

```bash
pip install briefcase
cd mobile/bestprice
briefcase dev
```

## Empacotar para Android / iOS

```bash
briefcase create android
briefcase build android
briefcase run android

briefcase create iOS
briefcase build iOS
briefcase run iOS
```

Antes de gerar o build, edite `src/bestprice/api_client.py` e aponte
`BASE_URL` para o endereço público do backend (`/backend`).

## Paleta de cores

Amarelo `#FFC400`, preto `#111111`, branco `#FFFFFF` — ver `src/bestprice/colors.py`.
