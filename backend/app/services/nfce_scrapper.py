#!/usr/bin/env python3
"""
NFC-e (SEFAZ-SP) scraper
Converts a "Consulta Pública" NFC-e page (accessed via its QR-code URL)
into structured JSON.

Usage:
    python3 nfce_scraper.py "https://www.nfce.fazenda.sp.gov.br/NFCeConsultaPublica/Paginas/ConsultaQRCode.aspx?p=...."
    python3 nfce_scraper.py "<url>" -o saida.json

Notes:
- This site blocks known bot/automation user-agents and disallows scraping
  via robots.txt for generic crawlers. Running this from your own machine
  as a normal browser-like request for a receipt YOU own is very different
  from mass-crawling; SEFANs generally intend this public page to be looked
  up by consumers checking their own purchase. Please scrape responsibly
  (rate-limit yourself, don't hammer the endpoint, respect the site if it
  starts blocking you).
- SEFAZ-SP sometimes serves the "full" data via an initial redirect/render
  that requires JS. If requests+BeautifulSoup returns an near-empty page,
  you likely need a real browser automation tool (Playwright/Selenium)
  instead of pure HTTP requests. A Playwright fallback is included below,
  commented out, in case the plain HTTP version doesn't return full data.
"""

import sys
import json
import re
import os
import socket
import argparse
import requests
import urllib3
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from urllib3.util.connection import create_connection
from bs4 import BeautifulSoup


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
}


def force_ipv4():
    """
    Some networks have a broken/blackholed IPv6 route, which makes
    urllib3 (used by requests) hang until timeout while curl (which
    often prefers IPv4 by default on Windows) connects fine.
    This monkey-patches urllib3's connection creation to only resolve
    A (IPv4) records, skipping AAAA (IPv6).
    """
    orig_getaddrinfo = socket.getaddrinfo

    def getaddrinfo_ipv4(host, port, family=0, type=0, proto=0, flags=0):
        return orig_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)

    socket.getaddrinfo = getaddrinfo_ipv4


def detect_system_proxy():
    """
    requests only reads HTTP_PROXY/HTTPS_PROXY env vars by default.
    On Windows, if a system/PAC proxy is configured (common in corporate
    environments) but not exported as an env var, curl/browsers may pick
    it up while requests won't. This tries to read it from the Windows
    registry as a fallback.
    """
    if os.environ.get("HTTPS_PROXY") or os.environ.get("HTTP_PROXY"):
        return None  # already set, nothing to do
    if sys.platform != "win32":
        return None
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Internet Settings",
        )
        proxy_enable, _ = winreg.QueryValueEx(key, "ProxyEnable")
        if proxy_enable:
            proxy_server, _ = winreg.QueryValueEx(key, "ProxyServer")
            return f"http://{proxy_server}"
    except Exception:
        return None
    return None


def build_session(proxy=None, use_ipv4_only=True):
    """
    Builds a requests Session with retries and (optionally) an explicit proxy.
    If --proxy isn't passed, requests will still honor HTTP_PROXY/HTTPS_PROXY
    env vars automatically, and this function will also try to auto-detect
    a Windows system proxy if none is set.
    """
    if use_ipv4_only:
        force_ipv4()

    session = requests.Session()
    retry = Retry(
        total=4,
        backoff_factor=1.5,  # 1.5s, 3s, 6s, 12s between retries
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)

    effective_proxy = proxy or detect_system_proxy()
    if effective_proxy:
        print(f"[info] Using proxy: {effective_proxy}", file=sys.stderr)
        session.proxies.update({"http": effective_proxy, "https": effective_proxy})

    return session


def clean(text):
    if text is None:
        return None
    return re.sub(r"\s+", " ", text).strip()


def parse_key_from_url(url):
    """Extract the 44-digit access key from the QR-code URL parameter."""
    m = re.search(r"p=(\d{44})", url)
    return m.group(1) if m else None


def fetch_html(url, session=None, timeout=30, proxy=None, use_ipv4_only=True):
    s = session or build_session(proxy=proxy, use_ipv4_only=use_ipv4_only)
    try:
        resp = s.get(url, timeout=timeout) # no headers=HEADERS, 
    except requests.exceptions.ConnectTimeout as e:
        raise SystemExit(
            "\nConnectTimeout: could not establish a connection to the server.\n"
            "This is a network-level problem, not a scraping/parsing problem. Try:\n"
            "  1) curl -v -m 20 \"<url>\"   -> if this also times out, it's your\n"
            "     network/firewall/VPN, not this script.\n"
            "  2) If you're behind a corporate proxy, pass it explicitly:\n"
            "     python3 nfce_scraper.py \"<url>\" --proxy http://user:pass@proxyhost:port\n"
            "  3) Try again later -- SEFAZ-SP's public consulta endpoint is known to be\n"
            "     flaky/slow and sometimes rate-limits or geo-blocks certain IP ranges.\n"
            f"\nOriginal error: {e}"
        )
    except requests.exceptions.SSLError as e:
        raise SystemExit(
            "\nSSLError: TLS handshake failed. Brazilian government sites sometimes\n"
            "require specific TLS/cipher configurations. Try updating 'certifi' and\n"
            "'requests', or test with curl -v to see the handshake details.\n"
            f"\nOriginal error: {e}"
        )
    resp.raise_for_status()
    resp.encoding = resp.apparent_encoding or "utf-8"
    return resp.text


def parse_nfce(html, source_url=None):
    soup = BeautifulSoup(html, "lxml")

    data = {
        "source_url": source_url,
        "chave_acesso": parse_key_from_url(source_url) if source_url else None,
        "emitente": {},
        "consumidor": None,
        "itens": [],
        "totais": {},
        "pagamentos": [],
        "protocolo_autorizacao": None,
        "numero": None,
        "serie": None,
        "emissao": None,
        "raw_text_fallback": None,
    }

    # --- Emitter block ---
    nome = soup.select_one("#u20.txtTopo")
    if nome:
        data["emitente"]["razao_social"] = clean(nome.get_text())

    endereco_divs = soup.select("#conteudo .txtCenter .text")
    if endereco_divs:
        for div in endereco_divs:
            txt = clean(div.get_text())
            if txt and txt.upper().startswith("CNPJ"):
                data["emitente"]["cnpj"] = clean(txt.split(":", 1)[1]) if ":" in txt else txt
            elif txt:
                data["emitente"]["endereco"] = txt

    # Fallback CNPJ regex if the block above didn't catch it
    if "cnpj" not in data["emitente"]:
        cnpj_match = re.search(r"CNPJ[:\s]*([\d./-]{14,18})", soup.get_text())
        if cnpj_match:
            data["emitente"]["cnpj"] = clean(cnpj_match.group(1))

    # --- Items: <table id="tabResult"><tr id="Item + N">...</tr></table> ---
    items = []
    for row in soup.select("table#tabResult tr"):
        desc_el = row.select_one("span.txtTit")
        cod_el = row.select_one("span.RCod")
        qtd_el = row.select_one("span.Rqtd")
        un_el = row.select_one("span.RUN")
        vl_unit_el = row.select_one("span.RvlUnit")
        vl_total_el = row.select_one("span.valor")

        if not (desc_el or vl_total_el):
            continue

        codigo = None
        if cod_el:
            m = re.search(r"(\d+)", cod_el.get_text())
            codigo = m.group(1) if m else clean(cod_el.get_text())

        qtd = None
        if qtd_el:
            qtd_text = qtd_el.get_text()
            m = re.search(r"Qtde\.?:?\s*([\d.,]+)", qtd_text)
            qtd = m.group(1) if m else clean(qtd_text)

        unidade = None
        if un_el:
            un_text = un_el.get_text()
            m = re.search(r"UN:\s*(\S+)", un_text)
            unidade = m.group(1) if m else clean(un_text)

        vl_unit = None
        if vl_unit_el:
            vl_text = vl_unit_el.get_text()
            m = re.search(r"Vl\.?\s*Unit\.?:?\s*([\d.,]+)", vl_text)
            vl_unit = m.group(1) if m else clean(vl_text)

            items.append({
                "descricao": clean(desc_el.get_text()) if desc_el else None,
            "codigo": codigo,
            "quantidade": qtd,
            "unidade": unidade,
            "valor_unitario": vl_unit,
            "valor_total": clean(vl_total_el.get_text()) if vl_total_el else None,
            })
    data["itens"] = items

    # --- Totals block: <div id="totalNota"> with repeated id="linhaTotal" divs ---
    total_nota = soup.select_one("#totalNota")
    if total_nota:
        for linha in total_nota.select("#linhaTotal"):
            label_el = linha.select_one("label")
            value_el = linha.select_one("span")
            if not label_el or not value_el:
                continue
            label = clean(label_el.get_text())
            value = clean(value_el.get_text())

            if "Qtd. total de itens" in label:
                data["totais"]["qtd_itens"] = value
            elif "Valor a pagar" in label:
                data["totais"]["valor_a_pagar"] = value
            elif "Troco" in label:
                data["totais"]["troco"] = value
            elif "Tributos Totais" in label:
                data["totais"]["tributos_totais"] = value
            else:
                # Payment method lines (e.g. "Cartão de Crédito") or generic rows
                data["pagamentos"].append({"forma": label, "valor": value})

        vpago_label = total_nota.select_one("#linhaForma span.txtTitR")
        if vpago_label:
            data["totais"]["valor_pago_label"] = clean(vpago_label.get_text())

    # --- Protocol / número / série / emissão ---
    info_text = soup.get_text()

    protocolo_match = re.search(r"Protocolo de Autoriza[cç][aã]o:\s*([\d]+)\s*([\d/: ]+)?", info_text)
    if protocolo_match:
        data["protocolo_autorizacao"] = clean(protocolo_match.group(0))

    numero_match = re.search(r"N[uú]mero:\s*(\d+)", info_text)
    if numero_match:
        data["numero"] = numero_match.group(1)

    serie_match = re.search(r"S[eé]rie:\s*(\d+)", info_text)
    if serie_match:
        data["serie"] = serie_match.group(1)

    emissao_match = re.search(r"Emiss[aã]o:\s*([\d/]+\s+[\d:]+)", info_text)
    if emissao_match:
        data["emissao"] = emissao_match.group(1)

    # --- Consumer ---
    consumidor_h4 = soup.find("h4", string=re.compile("Consumidor", re.I))
    if consumidor_h4:
        ul = consumidor_h4.find_next_sibling("ul")
        if ul:
            data["consumidor"] = clean(ul.get_text())

    # If very little was extracted, the page is likely structured differently
    # than expected (e.g. an error/expired-note page instead of a receipt).
    extracted_signal = any([data["emitente"], data["itens"], data["totais"]])
    if not extracted_signal:
        data["raw_text_fallback"] = clean(soup.get_text())[:5000]
        data["_warning"] = (
            "Little/no structured data was found. Double check the URL is a "
            "valid, non-expired NFC-e consulta link, or send the raw HTML "
            "for inspection."
        )

    return data


def main():
    url='https://www.nfce.fazenda.sp.gov.br/NFCeConsultaPublica/Paginas/ConsultaQRCode.aspx?p=35260845495694001276652020000778831002553100|2|1|1|9c56fb2e4e86f27c4a6ae1058618d07a52a4e6d5'

    html = fetch_html(url)
    print("*****", html)
    data = parse_nfce(html, source_url=url)
    print(data)
    output = json.dumps(data, ensure_ascii=False, indent=2)
    print(output)


if __name__ == "__main__":
    main()


# ---------------------------------------------------------------------------
# OPTIONAL: Playwright-based fallback for JS-rendered content.
# Uncomment and `pip install playwright && playwright install chromium`
# if the plain requests version above returns incomplete data.
# ---------------------------------------------------------------------------
#
# from playwright.sync_api import sync_playwright
#
# def fetch_html_js(url):
#     with sync_playwright() as p:
#         browser = p.chromium.launch(headless=True)
#         page = browser.new_page(user_agent=HEADERS["User-Agent"])
#         page.goto(url, wait_until="networkidle", timeout=30000)
#         html = page.content()
#         browser.close()
#         return html