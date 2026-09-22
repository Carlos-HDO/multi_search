#!/usr/bin/env python3
"""
Multi-Search CLI Tool
Dispara buscas simultâneas em múltiplos motores de busca em abas do navegador.
"""

from __future__ import annotations

import argparse
import shlex
import shutil
import subprocess
import sys
import time
from urllib.parse import quote_plus

ENGINES: list[tuple[str, str, str]] = [
    ("Google",     "google",      "https://www.google.com/search?q={q}"),
    ("Bing",       "bing",        "https://www.bing.com/search?q={q}"),
    ("DuckDuckGo", "duckduckgo",  "https://duckduckgo.com/?q={q}"),
    ("Startpage",  "startpage",   "https://www.startpage.com/sp/search?query={q}"),
    ("Ecosia",     "ecosia",      "https://www.ecosia.org/search?q={q}"),
    ("Qwant",      "qwant",       "https://www.qwant.com/?q={q}"),
    ("Yahoo",      "yahoo",       "https://search.yahoo.com/search?p={q}"),
    ("Yandex",     "yandex",      "https://yandex.com/search/?text={q}"),
    ("Mojeek",     "mojeek",      "https://www.mojeek.com/search?q={q}"),
    ("Perplexity", "perplexity",  "https://www.perplexity.ai/search?q={q}"),
    ("Brave",      "brave",       "https://search.brave.com/search?q={q}"),
]

ALIASES: dict[str, str] = {
    "ddg": "duckduckgo",
    "sp": "startpage",
    "perp": "perplexity",
}

DEFAULT_INITIAL_DELAY = 1.0
DEFAULT_TAB_DELAY = 0.3


def detect_default_browser() -> str:
    """Detecta o navegador padrão disponível no sistema (LibreWolf nativo/flatpak ou Firefox)."""
    if shutil.which("librewolf"):
        return "librewolf"

    if shutil.which("flatpak"):
        try:
            res = subprocess.run(
                ["flatpak", "info", "io.gitlab.librewolf-community"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            if res.returncode == 0:
                return "flatpak run io.gitlab.librewolf-community"
        except Exception:
            pass

    if shutil.which("firefox"):
        return "firefox"

    return "flatpak run io.gitlab.librewolf-community"


def list_engines() -> None:
    """Exibe a lista de motores de busca suportados."""
    print("Motores de busca disponíveis:\n")
    print(f"  {'Identificador':<15} {'Nome':<15} {'URL Base'}")
    print(f"  {'-'*13:<15} {'-'*13:<15} {'-'*30}")
    for name, key, tpl in ENGINES:
        print(f"  {key:<15} {name:<15} {tpl}")
    print("\nAtalhos aceitos no filtro -e/--engines: ddg (duckduckgo), sp (startpage), perp (perplexity)")


def filter_engines(selected: list[str]) -> list[tuple[str, str, str]]:
    """Filtra a lista de motores pelo nome ou alias informado."""
    selected_keys = set()
    for item in selected:
        for key in item.split(","):
            cleaned = key.strip().lower()
            if not cleaned:
                continue
            resolved = ALIASES.get(cleaned, cleaned)
            selected_keys.add(resolved)

    filtered = [e for e in ENGINES if e[1] in selected_keys]
    if not filtered:
        valid = ", ".join([e[1] for e in ENGINES])
        print(f"Erro: Nenhum motor válido selecionado. Motores disponíveis: {valid}", file=sys.stderr)
        sys.exit(2)
    return filtered


def build_searches(term: str, engines: list[tuple[str, str, str]]) -> list[tuple[str, str]]:
    """Gera pares (Nome, URL formatada) para o termo informado."""
    q = quote_plus(term)
    return [(name, tpl.format(q=q)) for name, _, tpl in engines]


def main() -> int:
    default_browser = detect_default_browser()

    p = argparse.ArgumentParser(
        description="Multi-Search: Abre várias abas no navegador, cada uma pesquisando em um buscador.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Exemplos:\n"
               "  %(prog)s python web scraping\n"
               "  %(prog)s -p -e google,brave,ddg segurança defensiva\n"
               "  %(prog)s --dry-run docker networking\n"
               "  %(prog)s --browser firefox linux kernel\n",
    )
    p.add_argument(
        "termo",
        nargs="*",
        help="Termo de busca (aspas são opcionais, múltiplas palavras são combinadas).",
    )
    p.add_argument(
        "-e", "--engines",
        help="Filtra os motores de busca desejados separados por vírgula (ex: google,brave,ddg).",
    )
    p.add_argument(
        "-l", "--list-engines",
        action="store_true",
        help="Lista todos os motores de busca suportados e encerra.",
    )
    p.add_argument(
        "-b", "--browser",
        default=default_browser,
        help=f"Comando do navegador a ser invocado (padrão: {default_browser!r}).",
    )
    p.add_argument(
        "-p", "--private",
        action="store_true",
        help="Abre os resultados em uma nova janela de navegação privada.",
    )
    p.add_argument(
        "-d", "--delay",
        type=float,
        default=DEFAULT_TAB_DELAY,
        help=f"Intervalo em segundos entre a abertura de cada aba (padrão: {DEFAULT_TAB_DELAY}s).",
    )
    p.add_argument(
        "--initial-delay",
        type=float,
        default=DEFAULT_INITIAL_DELAY,
        help=f"Tempo de espera em segundos para o carregamento da janela inicial (padrão: {DEFAULT_INITIAL_DELAY}s).",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Apenas lista as URLs formatadas sem abrir o navegador.",
    )

    args = p.parse_args()

    if args.list_engines:
        list_engines()
        return 0

    if not args.termo:
        p.print_help(file=sys.stderr)
        return 2

    term = " ".join(args.termo).strip()
    if not term:
        print("Erro: Termo de busca vazio.", file=sys.stderr)
        return 2

    browser_cmd = shlex.split(args.browser)
    if not browser_cmd:
        print("Erro: Comando de navegador inválido.", file=sys.stderr)
        return 2

    if shutil.which(browser_cmd[0]) is None:
        print(f"Erro: Executável '{browser_cmd[0]}' não foi encontrado no sistema (PATH).", file=sys.stderr)
        return 1

    engines = ENGINES
    if args.engines:
        engines = filter_engines([args.engines])

    searches = build_searches(term, engines)

    if args.dry_run:
        print(f"\n🔍 Termo de busca: \"{term}\"")
        print(f"🌐 Navegador: {args.browser}")
        print(f"📑 Total de motores: {len(searches)}\n")
        for name, url in searches:
            print(f"  [{name:<11}] {url}")
        print()
        return 0

    mode_label = "privada" if args.private else "comum"
    print(f"🔍 Multi-Search | Termo: \"{term}\" | Motores: {len(searches)} | Modo: Janela {mode_label}")

    try:
        # 1) Abre a primeira URL em uma nova janela
        first_engine, first_url = searches[0]
        window_flag = "--private-window" if args.private else "--new-window"
        print(f" [1/{len(searches)}] 🚀 Abrindo janela com {first_engine}...")
        subprocess.Popen(browser_cmd + [window_flag, first_url])

        if len(searches) > 1:
            time.sleep(args.initial_delay)

            # 2) Abre as demais URLs em novas abas
            for idx, (name, url) in enumerate(searches[1:], start=2):
                print(f" [{idx}/{len(searches)}] 📄 Abrindo aba: {name}...")
                subprocess.Popen(browser_cmd + ["--new-tab", url])
                time.sleep(args.delay)

    except KeyboardInterrupt:
        print("\n\n⚠️ Interrompido pelo usuário.", file=sys.stderr)
        return 130

    print("✨ Todas as abas foram disparadas com sucesso!")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
