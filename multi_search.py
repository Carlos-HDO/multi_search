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

DEFAULT_INITIAL_DELAY = 1.0
DEFAULT_TAB_DELAY = 0.3


def detect_default_browser() -> str:
    """Detects the default browser available on the system (native/flatpak LibreWolf or Firefox)."""
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
               "  %(prog)s -p -e google,brave,ddg defensive security\n"
               "  %(prog)s --dry-run docker networking\n"
               "  %(prog)s --browser firefox linux kernel\n",
    )
    p.add_argument(
        "termo",
        nargs="*",
        metavar="QUERY",
        help="Search query (quotes are optional, multiple words are joined automatically).",
    )
    p.add_argument(
        "-e", "--engines",
        help="Filter desired search engines separated by comma (e.g. google,brave,ddg).",
    )
    p.add_argument(
        "-l", "--list-engines",
        action="store_true",
        help="List all supported search engines and exit.",
    )
    p.add_argument(
        "-b", "--browser",
        default=default_browser,
        help=f"Browser launcher command to invoke (default: {default_browser!r}).",
    )
    p.add_argument(
        "-p", "--private",
        action="store_true",
        help="Open search results in a new private browsing window.",
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

    if args.list_engines:
        list_engines()
        return 0

    if not args.termo:
        p.print_help(file=sys.stderr)
        return 2

    term = " ".join(args.termo).strip()
    if not term:
        print("Error: Search query cannot be empty.", file=sys.stderr)
        return 2

    browser_cmd = shlex.split(args.browser)
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

    if args.dry_run:
        print(f"\n🔍 Search Query: \"{term}\"")
        print(f"🌐 Browser: {args.browser}")
        print(f"📑 Total engines: {len(searches)}\n")
        for name, url in searches:
            print(f"  [{name:<11}] {url}")
        print()
        return 0

    mode_label = "private" if args.private else "standard"
    print(f"🔍 Multi-Search | Query: \"{term}\" | Engines: {len(searches)} | Window: {mode_label}")

    try:
        # 1) Open the first URL in a new window
        first_engine, first_url = searches[0]
        window_flag = "--private-window" if args.private else "--new-window"
        print(f" [1/{len(searches)}] 🚀 Spawning window with {first_engine}...")
        subprocess.Popen(browser_cmd + [window_flag, first_url])

        if len(searches) > 1:
            time.sleep(args.initial_delay)

            # 2) Open subsequent URLs in new tabs
            for idx, (name, url) in enumerate(searches[1:], start=2):
                print(f" [{idx}/{len(searches)}] 📄 Opening tab: {name}...")
                subprocess.Popen(browser_cmd + ["--new-tab", url])
                time.sleep(args.delay)

    except KeyboardInterrupt:
        print("\n\n⚠️ Interrupted by user.", file=sys.stderr)
        return 130

    print("✨ All tabs dispatched successfully!")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
