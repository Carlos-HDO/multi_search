#!/usr/bin/env python3
"""
Multi-Search CLI Tool
Dispatches simultaneous searches across multiple web search engines in browser tabs.
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

# (Display Name, Alias, [Native Binaries], Flatpak App ID, is_chromium)
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


class BrowserInfo:
    def __init__(self, name: str, alias: str, command: str, btype: str, is_chromium: bool):
        self.name = name
        self.alias = alias
        self.command = command
        self.btype = btype
        self.is_chromium = is_chromium


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

    # Preference order: LibreWolf -> Firefox -> Brave -> Chrome -> Chromium -> First available
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
    """
    Resolves a browser input (alias or raw command) into (command_list, is_chromium).
    """
    clean = input_browser.strip()
    browsers = get_installed_browsers()

    # Match installed browser alias
    for b in browsers:
        if clean.lower() == b.alias:
            return shlex.split(b.command), b.is_chromium

    # Match known browser definition even if not in installed list
    for _, alias, bins, flatpak_id, is_chromium in KNOWN_BROWSERS:
        if clean.lower() == alias:
            cmd = bins[0] if shutil.which(bins[0]) else f"flatpak run {flatpak_id}"
            return shlex.split(cmd), is_chromium

    # Raw command
    cmd_list = shlex.split(clean)
    binary_name = cmd_list[0].lower() if cmd_list else ""
    is_chrom = any(
        x in binary_name or (len(cmd_list) > 2 and x in cmd_list[2].lower())
        for x in ["chrome", "chromium", "brave", "vivaldi", "opera", "edge"]
    )
    return cmd_list, is_chrom


def list_engines() -> None:
    """Displays the list of supported search engines."""
    print("Supported search engines:\n")
    print(f"  {'Identifier':<15} {'Name':<15} {'Base URL'}")
    print(f"  {'-'*13:<15} {'-'*13:<15} {'-'*30}")
    for name, key, tpl in ENGINES:
        print(f"  {key:<15} {name:<15} {tpl}")
    print("\nAccepted shortcuts in -e/--engines filter: ddg (duckduckgo), sp (startpage), perp (perplexity)")


def filter_engines(selected: list[str]) -> list[tuple[str, str, str]]:
    """Filters the engine list by provided names or aliases."""
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
        print(f"Error: No valid search engine selected. Available engines: {valid}", file=sys.stderr)
        sys.exit(2)
    return filtered


def build_searches(term: str, engines: list[tuple[str, str, str]]) -> list[tuple[str, str]]:
    """Generates (Name, formatted URL) pairs for the given search term."""
    q = quote_plus(term)
    return [(name, tpl.format(q=q)) for name, _, tpl in engines]


def main() -> int:
    default_browser = detect_default_browser()

    p = argparse.ArgumentParser(
        description="Multi-Search: Opens multiple browser tabs, each searching across a different engine.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Examples:\n"
               "  %(prog)s python web scraping\n"
               "  %(prog)s -b brave -e google,brave,ddg cybersecurity\n"
               "  %(prog)s -p -b firefox defensive security\n"
               "  %(prog)s --list-browsers\n"
               "  %(prog)s --dry-run docker networking\n",
    )
    p.add_argument(
        "termo",
        nargs="*",
        metavar="QUERY",
        help="Search query (quotes are optional, multiple words are joined automatically).",
    )
    p.add_argument(
        "-e", "--engines",
        metavar="ENGINE,ENGINE",
        help="Filter search engines by comma-separated names (e.g. -e google,brave,ddg).",
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

    if args.list_browsers:
        list_browsers()
        return 0

    if args.list_engines:
        list_engines()
        return 0

    if not args.termo:
        print("Error: Missing search query (QUERY). See usage below:\n", file=sys.stderr)
        p.print_help(file=sys.stderr)
        return 2

    term = " ".join(args.termo).strip()
    if not term:
        print("Error: Search query cannot be empty.", file=sys.stderr)
        return 2

    browser_cmd, is_chromium = resolve_browser(args.browser)
    if not browser_cmd:
        print("Error: Invalid browser command.", file=sys.stderr)
        return 2

    if shutil.which(browser_cmd[0]) is None:
        print(f"Error: Executable '{browser_cmd[0]}' not found in PATH.", file=sys.stderr)
        return 1

    engines = ENGINES
    if args.engines:
        engines = filter_engines([args.engines])

    searches = build_searches(term, engines)

    cmd_display = " ".join(browser_cmd)
    if args.dry_run:
        print(f"\n🔍 Search Query: \"{term}\"")
        print(f"🌐 Browser: {cmd_display} ({'Chromium-based' if is_chromium else 'Firefox-based'})")
        print(f"📑 Total engines: {len(searches)}\n")
        for name, url in searches:
            print(f"  [{name:<11}] {url}")
        print()
        return 0

    mode_label = "private/incognito" if args.private else "standard"
    print(f"🔍 Multi-Search | Query: \"{term}\" | Engines: {len(searches)} | Browser: {cmd_display} | Mode: {mode_label}")

    try:
        # 1) Open first URL in a new window
        first_engine, first_url = searches[0]
        if is_chromium:
            window_flags = ["--incognito", "--new-window", first_url] if args.private else ["--new-window", first_url]
        else:
            window_flags = ["--private-window", first_url] if args.private else ["--new-window", first_url]

        print(f" [1/{len(searches)}] 🚀 Spawning window with {first_engine}...")
        subprocess.Popen(browser_cmd + window_flags)

        if len(searches) > 1:
            time.sleep(args.initial_delay)

            # 2) Open subsequent URLs in new tabs
            for idx, (name, url) in enumerate(searches[1:], start=2):
                print(f" [{idx}/{len(searches)}] 📄 Opening tab: {name}...")
                if is_chromium:
                    tab_flags = ["--incognito", url] if args.private else [url]
                else:
                    tab_flags = ["--new-tab", url]
                subprocess.Popen(browser_cmd + tab_flags)
                time.sleep(args.delay)

    except KeyboardInterrupt:
        print("\n\n⚠️ Interrupted by user.", file=sys.stderr)
        return 130

    print("✨ All tabs dispatched successfully!")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
