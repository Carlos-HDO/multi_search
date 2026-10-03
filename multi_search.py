#!/usr/bin/env python3
"""
Multi-Search CLI & Web Hub Tool
Dispatches simultaneous searches across multiple web search engines in browser tabs.
Optimized for General Web Research, Threat Intel, and OSINT (Open Source Intelligence).
"""

from __future__ import annotations

import argparse
import json
import os
import random
import shlex
import shutil
import subprocess
import sys
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import quote_plus

CONFIG_DIR = Path.home() / ".config" / "multi_search"
CONFIG_FILE = CONFIG_DIR / "config.json"
UI_DIR = Path(__file__).resolve().parent / "ui"

DEFAULT_ENGINES: list[dict[str, str]] = [
    # General & Independent Web Indexes
    {"name": "Google",          "key": "google",        "url_template": "https://www.google.com/search?q={q}", "category_tag": "web"},
    {"name": "Brave",           "key": "brave",         "url_template": "https://search.brave.com/search?q={q}", "category_tag": "web"},
    {"name": "DuckDuckGo",      "key": "duckduckgo",    "url_template": "https://duckduckgo.com/?q={q}", "category_tag": "web"},
    {"name": "Startpage",       "key": "startpage",     "url_template": "https://www.startpage.com/sp/search?query={q}", "category_tag": "web"},
    {"name": "Yandex",          "key": "yandex",        "url_template": "https://yandex.com/search/?text={q}", "category_tag": "web"},
    {"name": "Bing",            "key": "bing",          "url_template": "https://www.bing.com/search?q={q}", "category_tag": "web"},
    {"name": "Perplexity",      "key": "perplexity",    "url_template": "https://www.perplexity.ai/search?q={q}", "category_tag": "web"},

    # OSINT: Archives & Historical Caches
    {"name": "Wayback Machine", "key": "wayback",       "url_template": "https://web.archive.org/web/*/{q}", "category_tag": "archive"},
    {"name": "Archive.today",   "key": "archive-today", "url_template": "https://archive.ph/{q}", "category_tag": "archive"},

    # OSINT: Leaks, Pastes & Public Intelligence
    {"name": "Intelligence X",  "key": "intelx",        "url_template": "https://intelx.io/?s={q}", "category_tag": "osint"},
    {"name": "Reddit",          "key": "reddit",        "url_template": "https://www.reddit.com/search/?q={q}", "category_tag": "osint"},

    # OSINT: Code, Secrets & Developer Footprint
    {"name": "GitHub Code",     "key": "github",        "url_template": "https://github.com/search?q={q}&type=code", "category_tag": "code"},
    {"name": "Grep.app",        "key": "grepapp",       "url_template": "https://grep.app/search?q={q}", "category_tag": "code"},

    # OSINT: Infrastructure, Network & Threat Intel
    {"name": "URLScan",         "key": "urlscan",       "url_template": "https://urlscan.io/search/#{q}", "category_tag": "infra"},
    {"name": "Shodan",          "key": "shodan",        "url_template": "https://www.shodan.io/search?query={q}", "category_tag": "infra"},
    {"name": "VirusTotal",      "key": "virustotal",    "url_template": "https://www.virustotal.com/gui/search/{q}", "category_tag": "infra"},

    # Pentest & Vulnerability Research: Exploits, CVEs & PoCs
    {"name": "Exploit-DB",      "key": "exploitdb",     "url_template": "https://www.exploit-db.com/search?q={q}", "category_tag": "pentest"},
    {"name": "Sploitus",        "key": "sploitus",      "url_template": "https://sploitus.com/?query={q}", "category_tag": "pentest"},
    {"name": "Packet Storm",    "key": "packetstorm",   "url_template": "https://packetstormsecurity.com/search/?q={q}", "category_tag": "pentest"},
    {"name": "Rapid7 (MSF)",    "key": "rapid7",        "url_template": "https://www.rapid7.com/db/?q={q}", "category_tag": "pentest"},
    {"name": "SecLists",        "key": "seclists",      "url_template": "https://seclists.org/search/?q={q}", "category_tag": "pentest"},
    {"name": "GitHub PoC",      "key": "githubpoc",     "url_template": "https://github.com/search?q={q}+poc+OR+exploit&type=repositories", "category_tag": "pentest"},
    {"name": "NVD (NIST)",      "key": "nvd",           "url_template": "https://nvd.nist.gov/vuln/search/results?form_type=Basic&results_type=overview&query={q}&search_type=all", "category_tag": "pentest"},
    {"name": "Vulners",         "key": "vulners",       "url_template": "https://vulners.com/search?query={q}", "category_tag": "pentest"},
]

DEFAULT_CATEGORIES: dict[str, dict] = {
    "osint": {
        "title": "OSINT & Pessoas",
        "icon": "🕵️‍♂️",
        "description": "Inteligência investigativa, arquivos históricos, dumps de leaks e fóruns públicos",
        "engines": ["google", "brave", "yandex", "intelx", "wayback", "archive-today", "urlscan", "reddit"],
    },
    "infra": {
        "title": "Infra & Threat Intel",
        "icon": "📡",
        "description": "Infraestrutura de rede, certificados, portas abertas, DNS e reputação de ameaças",
        "engines": ["shodan", "urlscan", "virustotal", "intelx"],
    },
    "pentest": {
        "title": "Pentest & CVEs",
        "icon": "💣",
        "description": "Bancos de exploits, CVEs, PoCs, advisories de segurança e módulos Metasploit",
        "engines": ["exploitdb", "sploitus", "packetstorm", "rapid7", "seclists", "githubpoc", "nvd", "vulners"],
    },
    "code": {
        "title": "Código & Secrets",
        "icon": "💻",
        "description": "Repositórios públicos, busca em código-fonte, API keys e pegadas de desenvolvedor",
        "engines": ["github", "grepapp", "google"],
    },
    "archive": {
        "title": "Arquivos & Caches",
        "icon": "🏛️",
        "description": "Snapshots históricos na Wayback Machine e no Archive.today para páginas deletadas",
        "engines": ["wayback", "archive-today"],
    },
    "web": {
        "title": "Web Geral",
        "icon": "🌐",
        "description": "Motores de busca convencionais e independentes sem perfilamento cruzado",
        "engines": ["google", "brave", "duckduckgo", "startpage", "yandex", "bing", "perplexity"],
    },
    "all": {
        "title": "Todas as Plataformas",
        "icon": "⚡",
        "description": "Disparo simultâneo em todas as plataformas cadastradas",
        "engines": [e["key"] for e in DEFAULT_ENGINES],
    },
}

ALIASES: dict[str, str] = {
    "ddg": "duckduckgo",
    "sp": "startpage",
    "perp": "perplexity",
    "wb": "wayback",
    "archive": "wayback",
    "at": "archive-today",
    "gh": "github",
    "grep": "grepapp",
    "vt": "virustotal",
    "edb": "exploitdb",
    "ps": "packetstorm",
    "msf": "rapid7",
    "metasploit": "rapid7",
    "poc": "githubpoc",
    "sploit": "sploitus",
}

KNOWN_BROWSERS = [
    ("LibreWolf",     "librewolf", ["librewolf"],                              "io.gitlab.librewolf-community",      False),
    ("Firefox",       "firefox",   ["firefox", "firefox-esr"],                 "org.mozilla.firefox",                False),
    ("Brave",         "brave",     ["brave", "brave-browser"],                 "com.brave.Browser",                  True),
    ("Google Chrome", "chrome",    ["google-chrome", "google-chrome-stable"],  "com.google.Chrome",                  True),
    ("Chromium",      "chromium",  ["chromium", "chromium-browser"],           "org.chromium.Chromium",              True),
    ("Tor Browser",   "tor",       ["tor-browser"],                            "org.torproject.torbrowser-launcher", False),
    ("Zen Browser",   "zen",       ["zen-browser", "zen"],                     "io.github.zen_browser.zen",          False),
    ("Vivaldi",       "vivaldi",   ["vivaldi", "vivaldi-stable"],              "com.vivaldi.Vivaldi",                True),
    ("Opera",         "opera",     ["opera"],                                  "com.opera.Opera",                    True),
    ("Microsoft Edge","edge",      ["microsoft-edge", "microsoft-edge-stable"], "com.microsoft.Edge",               True),
]

DEFAULT_INITIAL_DELAY = 1.0
DEFAULT_TAB_DELAY = 0.3


def get_default_config() -> dict:
    return {
        "engines": [dict(e) for e in DEFAULT_ENGINES],
        "categories": {k: dict(v) for k, v in DEFAULT_CATEGORIES.items()},
    }


def load_config() -> dict:
    """Loads configuration from ~/.config/multi_search/config.json or initializes default."""
    if not CONFIG_FILE.exists():
        cfg = get_default_config()
        save_config(cfg)
        return cfg
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            cfg = json.load(f)
            if "engines" not in cfg or "categories" not in cfg:
                raise ValueError("Formato de configuração inválido.")
            return cfg
    except Exception as e:
        print(f"⚠️ Erro ao ler {CONFIG_FILE} ({e}). Carregando catálogo padrão.", file=sys.stderr)
        return get_default_config()


def save_config(cfg: dict) -> bool:
    """Saves configuration to ~/.config/multi_search/config.json."""
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"⚠️ Erro ao salvar {CONFIG_FILE}: {e}", file=sys.stderr)
        return False


def reset_config() -> dict:
    """Restores default configuration in ~/.config/multi_search/config.json."""
    cfg = get_default_config()
    save_config(cfg)
    return cfg


class BrowserInfo:
    def __init__(self, name: str, alias: str, command: str, btype: str, is_chromium: bool):
        self.name = name
        self.alias = alias
        self.command = command
        self.btype = btype
        self.is_chromium = is_chromium

    def to_dict(self, default_cmd: str) -> dict:
        return {
            "name": self.name,
            "alias": self.alias,
            "command": self.command,
            "btype": self.btype,
            "is_chromium": self.is_chromium,
            "is_default": (self.command == default_cmd),
        }


def get_installed_browsers() -> list[BrowserInfo]:
    """Scans the system for installed browsers (Native, Flatpak, Snap)."""
    flatpak_apps: set[str] = set()
    if shutil.which("flatpak"):
        try:
            res = subprocess.run(
                ["flatpak", "list", "--app", "--columns=application"],
                capture_output=True,
                text=True,
                check=True,
            )
            flatpak_apps = set(res.stdout.strip().split())
        except Exception:
            pass

    installed: list[BrowserInfo] = []
    for name, alias, bins, flatpak_id, is_chromium in KNOWN_BROWSERS:
        found_bin = None
        for b in bins:
            p = shutil.which(b)
            if p:
                found_bin = b
                break
        if found_bin:
            resolved_path = shutil.which(found_bin) or ""
            btype = "Snap" if "/snap/" in resolved_path else "Native"
            installed.append(BrowserInfo(name, alias, found_bin, btype, is_chromium))
        elif flatpak_id and flatpak_id in flatpak_apps:
            installed.append(BrowserInfo(name, alias, f"flatpak run {flatpak_id}", "Flatpak", is_chromium))

    return installed


def detect_default_browser() -> str:
    """Detects the preferred default browser available on the system."""
    installed = get_installed_browsers()
    if not installed:
        return "flatpak run io.gitlab.librewolf-community"

    priority = ["librewolf", "firefox", "brave", "chrome", "chromium"]
    by_alias = {b.alias: b for b in installed}

    for p in priority:
        if p in by_alias:
            return by_alias[p].command

    return installed[0].command


def list_browsers() -> None:
    """Displays all detected web browsers installed on the system."""
    browsers = get_installed_browsers()
    default_cmd = detect_default_browser()

    print("Detected browsers on this system:\n")
    print(f"  {'Name':<16} {'Alias':<12} {'Type':<10} {'Command'}")
    print(f"  {'-'*14:<16} {'-'*10:<12} {'-'*8:<10} {'-'*35}")

    if not browsers:
        print("  No recognized browsers detected. You can specify any browser command using -b/--browser.")
    else:
        for b in browsers:
            is_def = " (DEFAULT)" if b.command == default_cmd else ""
            print(f"  {b.name:<16} {b.alias:<12} {b.btype:<10} {b.command}{is_def}")

    print("\nUsage tips:")
    print("  Run with an alias:   msearch -b brave 'search query'")
    print("  Run with a command: msearch -b 'firefox' 'search query'")


def resolve_browser(input_browser: str) -> tuple[list[str], bool]:
    """Resolves a browser input (alias or raw command) into (command_list, is_chromium)."""
    clean = input_browser.strip()
    browsers = get_installed_browsers()

    for b in browsers:
        if clean.lower() == b.alias:
            return shlex.split(b.command), b.is_chromium

    for _, alias, bins, flatpak_id, is_chromium in KNOWN_BROWSERS:
        if clean.lower() == alias:
            cmd = bins[0] if shutil.which(bins[0]) else f"flatpak run {flatpak_id}"
            return shlex.split(cmd), is_chromium

    cmd_list = shlex.split(clean)
    binary_name = cmd_list[0].lower() if cmd_list else ""
    is_chrom = any(
        x in binary_name or (len(cmd_list) > 2 and x in cmd_list[2].lower())
        for x in ["chrome", "chromium", "brave", "vivaldi", "opera", "edge"]
    )
    return cmd_list, is_chrom


def list_engines(cfg: dict | None = None) -> None:
    """Displays the list of supported search engines."""
    cfg = cfg or load_config()
    print("Supported search engines:\n")
    print(f"  {'Identifier':<16} {'Name':<18} {'Base URL'}")
    print(f"  {'-'*14:<16} {'-'*16:<18} {'-'*40}")
    for item in cfg.get("engines", []):
        print(f"  {item['key']:<16} {item['name']:<18} {item['url_template']}")

    print("\nShortcuts accepted in -e/--engines:")
    print("  ddg -> duckduckgo, sp -> startpage, perp -> perplexity, wb -> wayback,")
    print("  at -> archive-today, gh -> github, grep -> grepapp, vt -> virustotal,")
    print("  edb -> exploitdb, sploit -> sploitus, ps -> packetstorm, msf -> rapid7, poc -> githubpoc")


def list_categories(cfg: dict | None = None) -> None:
    """Displays available search category presets."""
    cfg = cfg or load_config()
    categories = cfg.get("categories", {})
    print("Available category presets (-c / --category):\n")
    print(f"  {'Category':<12} {'Engines Count':<15} {'Description'}")
    print(f"  {'-'*10:<12} {'-'*13:<15} {'-'*50}")
    for cat_name, info in categories.items():
        desc = info.get("description", "")
        engs = info.get("engines", [])
        print(f"  {cat_name:<12} {len(engs):<15} {desc}")
        print(f"  {'':<12} Engines: {', '.join(engs)}\n")


def filter_engines(selected: list[str], cfg: dict | None = None) -> list[tuple[str, str, str]]:
    """Filters the engine list by provided names or aliases."""
    cfg = cfg or load_config()
    all_engines = {e["key"]: (e["name"], e["key"], e["url_template"]) for e in cfg.get("engines", [])}

    selected_keys = set()
    for item in selected:
        for key in item.split(","):
            cleaned = key.strip().lower()
            if not cleaned:
                continue
            resolved = ALIASES.get(cleaned, cleaned)
            selected_keys.add(resolved)

    filtered = [all_engines[k] for k in selected_keys if k in all_engines]
    if not filtered:
        valid = ", ".join(all_engines.keys())
        print(f"Error: No valid search engine selected. Available engines: {valid}", file=sys.stderr)
        sys.exit(2)
    return filtered


def get_engines_by_category(category: str, cfg: dict | None = None) -> list[tuple[str, str, str]]:
    """Returns engines corresponding to a category preset."""
    cfg = cfg or load_config()
    categories = cfg.get("categories", {})
    cat_lower = category.strip().lower()

    if cat_lower not in categories:
        valid_cats = ", ".join(categories.keys())
        print(f"Error: Unknown category '{category}'. Available categories: {valid_cats}", file=sys.stderr)
        sys.exit(2)

    all_engines = {e["key"]: (e["name"], e["key"], e["url_template"]) for e in cfg.get("engines", [])}
    keys = categories[cat_lower].get("engines", [])
    return [all_engines[k] for k in keys if k in all_engines]


def calculate_delay(base: float, jitter: float) -> float:
    """Calculates delay applying random jitter variation (±jitter)."""
    if jitter <= 0.0:
        return max(0.05, base)
    low = max(0.1, base - jitter)
    high = max(low + 0.1, base + jitter)
    return round(random.uniform(low, high), 2)


def build_searches(term: str, engines: list[tuple[str, str, str]]) -> list[tuple[str, str]]:
    """Generates (Name, formatted URL) pairs for the given search term."""
    q = quote_plus(term)
    return [(name, tpl.format(q=q)) for name, _, tpl in engines]


def dispatch_searches(
    term: str,
    engines: list[tuple[str, str, str]],
    browser_str: str,
    private: bool = False,
    human: bool = False,
    delay: float = DEFAULT_TAB_DELAY,
    jitter: float = 0.0,
    initial_delay: float = DEFAULT_INITIAL_DELAY,
    shuffle: bool = False,
    dry_run: bool = False,
) -> int:
    """Executes the search opening pipeline across browser tabs/windows."""
    browser_cmd, is_chromium = resolve_browser(browser_str)
    if not browser_cmd:
        print("Error: Invalid browser command.", file=sys.stderr)
        return 2

    if shutil.which(browser_cmd[0]) is None:
        print(f"Error: Executable '{browser_cmd[0]}' not found in PATH.", file=sys.stderr)
        return 1

    if human:
        shuffle = True
        if delay == DEFAULT_TAB_DELAY:
            delay = 1.8
        if jitter == 0.0:
            jitter = 0.8
        if initial_delay == DEFAULT_INITIAL_DELAY:
            initial_delay = 2.2

    searches = build_searches(term, engines)
    if shuffle:
        random.shuffle(searches)

    cmd_display = " ".join(browser_cmd)
    if dry_run:
        print(f"\n🔍 Search Query: \"{term}\"")
        print(f"🌐 Browser: {cmd_display} ({'Chromium-based' if is_chromium else 'Firefox-based'})")
        if human:
            print("👤 Human Simulation: Enabled (shuffled order, dynamic jitter 1.0s-2.6s)")
        elif shuffle:
            print("🔀 Shuffled Order: Enabled")
        print(f"📑 Total engines: {len(searches)}\n")
        for name, url in searches:
            print(f"  [{name:<16}] {url}")
        print()
        return 0

    mode_label = "private/incognito" if private else "standard"
    human_tag = " | Human Simulation: ON" if human else ""
    print(f"🔍 Multi-Search | Query: \"{term}\" | Engines: {len(searches)} | Browser: {cmd_display} | Mode: {mode_label}{human_tag}")

    try:
        first_engine, first_url = searches[0]
        if is_chromium:
            window_flags = ["--incognito", "--new-window", first_url] if private else ["--new-window", first_url]
        else:
            window_flags = ["--private-window", first_url] if private else ["--new-window", first_url]

        print(f" [1/{len(searches)}] 🚀 Spawning window with {first_engine}...")
        subprocess.Popen(browser_cmd + window_flags)

        if len(searches) > 1:
            init_wait = calculate_delay(initial_delay, 0.4 if human else 0.0)
            time.sleep(init_wait)

            for idx, (name, url) in enumerate(searches[1:], start=2):
                wait_time = calculate_delay(delay, jitter)
                delay_info = f" (interval: {wait_time}s)" if (human or jitter > 0) else ""
                print(f" [{idx}/{len(searches)}] 📄 Opening tab: {name}{delay_info}...")
                if is_chromium:
                    tab_flags = ["--incognito", url] if private else [url]
                else:
                    tab_flags = ["--new-tab", url]
                subprocess.Popen(browser_cmd + tab_flags)
                time.sleep(wait_time)

    except KeyboardInterrupt:
        print("\n\n⚠️ Interrupted by user.", file=sys.stderr)
        return 130

    print("✨ All tabs dispatched successfully!")
    return 0


# ============================================================================
# EMBEDDED HTTP SERVER FOR WEB UI
# ============================================================================

class MultiSearchRequestHandler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args) -> None:
        pass  # Suppress default noisy console logs

    def _send_json(self, data: dict, status: int = 200) -> None:
        encoded = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(encoded)

    def do_GET(self) -> None:
        path = self.path.split("?")[0]
        if path in ("/", "/index.html", "/ui"):
            html_file = UI_DIR / "index.html"
            if not html_file.exists():
                self.send_error(404, "UI index.html não encontrado no pacote.")
                return
            content = html_file.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        elif path == "/api/config":
            cfg = load_config()
            installed = get_installed_browsers()
            default_cmd = detect_default_browser()
            cfg["installed_browsers"] = [b.to_dict(default_cmd) for b in installed]
            self._send_json(cfg)
        else:
            self.send_error(404, "Endpoint não encontrado.")

    def do_POST(self) -> None:
        path = self.path.split("?")[0]
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length) if length > 0 else b"{}"

        try:
            payload = json.loads(body.decode("utf-8"))
        except Exception:
            payload = {}

        if path == "/api/config":
            if "engines" in payload and "categories" in payload:
                save_config(payload)
                self._send_json({"status": "ok", "message": "Configuração salva com sucesso!"})
            else:
                self._send_json({"status": "error", "message": "Estrutura de dados inválida."}, status=400)

        elif path == "/api/reset":
            cfg = reset_config()
            installed = get_installed_browsers()
            default_cmd = detect_default_browser()
            cfg["installed_browsers"] = [b.to_dict(default_cmd) for b in installed]
            self._send_json(cfg)

        elif path == "/api/launch":
            term = payload.get("query", "").strip()
            if not term:
                self._send_json({"status": "error", "message": "Termo de busca vazio."}, status=400)
                return

            cfg = load_config()
            all_engines = {e["key"]: (e["name"], e["key"], e["url_template"]) for e in cfg.get("engines", [])}
            selected_keys = payload.get("engines", [])
            target_engines = [all_engines[k] for k in selected_keys if k in all_engines]

            if not target_engines:
                self._send_json({"status": "error", "message": "Nenhuma plataforma válida encontrada."}, status=400)
                return

            browser_req = payload.get("browser") or detect_default_browser()
            is_private = bool(payload.get("private", False))
            is_human = bool(payload.get("human", False))
            delay = float(payload.get("delay", DEFAULT_TAB_DELAY))

            # Dispatch asynchronously in host so HTTP endpoint returns immediately
            def run_dispatch():
                dispatch_searches(
                    term=term,
                    engines=target_engines,
                    browser_str=browser_req,
                    private=is_private,
                    human=is_human,
                    delay=delay,
                )

            t = threading.Thread(target=run_dispatch, daemon=True)
            t.start()

            self._send_json({
                "status": "ok",
                "message": f"Disparando {len(target_engines)} plataformas no host via {browser_req}!",
                "engines_count": len(target_engines),
            })
        else:
            self.send_error(404, "Endpoint não encontrado.")


def start_ui_server(port: int = 7890, open_browser: bool = True) -> int:
    """Starts the embedded HTTP server for the web interface and opens the default browser."""
    server_address = ("127.0.0.1", port)
    try:
        httpd = HTTPServer(server_address, MultiSearchRequestHandler)
    except OSError:
        # Try alternate port
        port += 1
        server_address = ("127.0.0.1", port)
        httpd = HTTPServer(server_address, MultiSearchRequestHandler)

    url = f"http://localhost:{port}"
    print("=" * 68)
    print("  🕵️‍♂️  MULTI-SEARCH — OSINT Recon Hub & Command Center")
    print(f"  🌐 Servidor local ativo em: {url}")
    print("  ⚙️  Configuração salva em: ~/.config/multi_search/config.json")
    print("  ⌨️  Pressione [Ctrl + C] para encerrar.")
    print("=" * 68)

    if open_browser:
        try:
            webbrowser.open(url)
        except Exception:
            pass

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Servidor Multi-Search encerrado.")
    return 0


# ============================================================================
# CLI MAIN ENTRYPOINT
# ============================================================================

def main() -> int:
    # If invoked with no arguments or explicitly requesting UI, launch web hub
    if len(sys.argv) == 1:
        return start_ui_server()

    if len(sys.argv) == 2 and sys.argv[1] in ("--ui", "--web", "ui", "web"):
        return start_ui_server()

    cfg = load_config()
    default_browser = detect_default_browser()

    p = argparse.ArgumentParser(
        description="Multi-Search: Opens multiple browser tabs across search engines and OSINT sources.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Examples:\n"
               "  %(prog)s                       (Launches the interactive Web UI hub)\n"
               "  %(prog)s python web scraping\n"
               "  %(prog)s -c osint john doe target\n"
               "  %(prog)s -c infra malicious-domain.com\n"
               "  %(prog)s -c code AWS_SECRET_ACCESS_KEY\n"
               "  %(prog)s -c archive https://example.com/deleted-article\n"
               "  %(prog)s -b brave -e shodan,urlscan,vt 1.1.1.1\n"
               "  %(prog)s --list-categories\n"
               "  %(prog)s --dry-run -c osint suspicious-actor\n",
    )
    p.add_argument(
        "termo",
        nargs="*",
        metavar="QUERY",
        help="Search query (quotes are optional, multiple words are joined automatically).",
    )
    p.add_argument(
        "--ui", "--web",
        dest="open_ui",
        action="store_true",
        help="Launch the interactive Web UI Command Center in your browser.",
    )
    p.add_argument(
        "-c", "--category",
        default="web",
        help="Category preset to search (default: 'web'). Options: web, osint, infra, code, archive, pentest, all.",
    )
    p.add_argument(
        "-e", "--engines",
        metavar="ENGINE,ENGINE",
        help="Filter specific engines by comma-separated names/aliases (e.g. -e shodan,vt,intelx).",
    )
    p.add_argument(
        "-lc", "--list-categories",
        action="store_true",
        help="List available search categories and exit.",
    )
    p.add_argument(
        "-l", "--list-engines",
        action="store_true",
        help="List all supported search engines and exit.",
    )
    p.add_argument(
        "-lb", "--list-browsers",
        action="store_true",
        help="List all detected web browsers on this system and exit.",
    )
    p.add_argument(
        "-b", "--browser",
        default=default_browser,
        help=f"Browser alias or launcher command to invoke (default: {default_browser!r}).",
    )
    p.add_argument(
        "-p", "--private",
        action="store_true",
        help="Open search results in a new private/incognito browsing window.",
    )
    p.add_argument(
        "-H", "--human",
        action="store_true",
        help="Simulate human pacing: randomize delay intervals and shuffle engine order to reduce CAPTCHAs.",
    )
    p.add_argument(
        "--shuffle",
        action="store_true",
        help="Randomize the opening order of search engine tabs to break request patterns.",
    )
    p.add_argument(
        "-j", "--jitter",
        type=float,
        default=0.0,
        metavar="SECONDS",
        help="Add random variation (±SECONDS) around the tab delay (e.g. -j 0.8).",
    )
    p.add_argument(
        "-d", "--delay",
        type=float,
        default=DEFAULT_TAB_DELAY,
        help=f"Delay in seconds between opening each tab (default: {DEFAULT_TAB_DELAY}s).",
    )
    p.add_argument(
        "--initial-delay",
        type=float,
        default=DEFAULT_INITIAL_DELAY,
        help=f"Wait time in seconds for the initial window to spawn (default: {DEFAULT_INITIAL_DELAY}s).",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview formatted URLs without opening the browser.",
    )

    args = p.parse_args()

    if args.open_ui:
        return start_ui_server()

    if args.list_categories:
        list_categories(cfg)
        return 0

    if args.list_engines:
        list_engines(cfg)
        return 0

    if args.list_browsers:
        list_browsers()
        return 0

    if not args.termo:
        return start_ui_server()

    term = " ".join(args.termo).strip()
    if not term:
        print("Error: Search query cannot be empty.", file=sys.stderr)
        return 2

    # Resolve target engines
    if args.engines:
        engines = filter_engines([args.engines], cfg)
    else:
        engines = get_engines_by_category(args.category, cfg)

    return dispatch_searches(
        term=term,
        engines=engines,
        browser_str=args.browser,
        private=args.private,
        human=args.human,
        delay=args.delay,
        jitter=args.jitter,
        initial_delay=args.initial_delay,
        shuffle=args.shuffle,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    raise SystemExit(main())
