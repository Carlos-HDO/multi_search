#!/usr/bin/env python3
"""
Multi-Search CLI Tool
Dispatches simultaneous searches across multiple web search engines in browser tabs.
Optimized for General Web Research and OSINT (Open Source Intelligence).
"""

from __future__ import annotations

import argparse
import random
import shlex
import shutil
import subprocess
import sys
import time
from urllib.parse import quote_plus

ENGINES: list[tuple[str, str, str]] = [
    # General & Independent Web Indexes
    ("Google",          "google",        "https://www.google.com/search?q={q}"),
    ("Brave",           "brave",         "https://search.brave.com/search?q={q}"),
    ("DuckDuckGo",      "duckduckgo",    "https://duckduckgo.com/?q={q}"),
    ("Startpage",       "startpage",     "https://www.startpage.com/sp/search?query={q}"),
    ("Yandex",          "yandex",        "https://yandex.com/search/?text={q}"),
    ("Bing",            "bing",          "https://www.bing.com/search?q={q}"),
    ("Perplexity",      "perplexity",    "https://www.perplexity.ai/search?q={q}"),

    # OSINT: Archives & Historical Caches
    ("Wayback Machine", "wayback",       "https://web.archive.org/web/*/{q}"),
    ("Archive.today",   "archive-today", "https://archive.ph/{q}"),

    # OSINT: Leaks, Pastes & Public Intelligence
    ("Intelligence X",  "intelx",        "https://intelx.io/?s={q}"),
    ("Reddit",          "reddit",        "https://www.reddit.com/search/?q={q}"),

    # OSINT: Code, Secrets & Developer Footprint
    ("GitHub Code",     "github",        "https://github.com/search?q={q}&type=code"),
    ("Grep.app",        "grepapp",       "https://grep.app/search?q={q}"),

    # OSINT: Infrastructure, Network & Threat Intel
    ("URLScan",         "urlscan",       "https://urlscan.io/search/#{q}"),
    ("Shodan",          "shodan",        "https://www.shodan.io/search?query={q}"),
    ("VirusTotal",      "virustotal",    "https://www.virustotal.com/gui/search/{q}"),

    # Pentest & Vulnerability Research: Exploits, CVEs & PoCs
    ("Exploit-DB",      "exploitdb",     "https://www.exploit-db.com/search?q={q}"),
    ("Sploitus",        "sploitus",      "https://sploitus.com/?query={q}"),
    ("Packet Storm",    "packetstorm",   "https://packetstormsecurity.com/search/?q={q}"),
    ("Rapid7 (MSF)",    "rapid7",        "https://www.rapid7.com/db/?q={q}"),
    ("SecLists",        "seclists",      "https://seclists.org/search/?q={q}"),
    ("GitHub PoC",      "githubpoc",     "https://github.com/search?q={q}+poc+OR+exploit&type=repositories"),
    ("NVD (NIST)",      "nvd",           "https://nvd.nist.gov/vuln/search/results?form_type=Basic&results_type=overview&query={q}&search_type=all"),
    ("Vulners",         "vulners",       "https://vulners.com/search?query={q}"),
]

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

CATEGORIES: dict[str, tuple[str, list[str]]] = {
    "web": (
        "General web search across unprofiled & independent engines",
        ["google", "brave", "duckduckgo", "startpage", "yandex", "bing", "perplexity"],
    ),
    "osint": (
        "Core intelligence, archives, leak dumps, and investigative search",
        ["google", "brave", "yandex", "intelx", "wayback", "archive-today", "urlscan", "reddit"],
    ),
    "infra": (
        "Network infrastructure, open ports, certificates, and threat intel",
        ["shodan", "urlscan", "virustotal", "intelx"],
    ),
    "code": (
        "Public repositories, code search, API keys, and developer footprinting",
        ["github", "grepapp", "google"],
    ),
    "archive": (
        "Historical snapshots, cached sites, and deleted page recovery",
        ["wayback", "archive-today"],
    ),
    "pentest": (
        "Penetration testing, exploits, CVEs, security advisories, and PoC repositories",
        ["exploitdb", "sploitus", "packetstorm", "rapid7", "seclists", "githubpoc", "nvd", "vulners"],
    ),
    "exploit": (
        "Alias for pentest profile (exploits, PoCs, Metasploit modules)",
        ["exploitdb", "sploitus", "packetstorm", "rapid7", "seclists", "githubpoc", "nvd", "vulners"],
    ),
    "all": (
        "All registered search engines across all domains",
        [key for _, key, _ in ENGINES],
    ),
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

    # Priority order: LibreWolf -> Firefox -> Brave -> Chrome -> Chromium -> First available
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


def list_engines() -> None:
    """Displays the list of supported search engines."""
    print("Supported search engines:\n")
    print(f"  {'Identifier':<16} {'Name':<18} {'Base URL'}")
    print(f"  {'-'*14:<16} {'-'*16:<18} {'-'*40}")
    for name, key, tpl in ENGINES:
        print(f"  {key:<16} {name:<18} {tpl}")

    print("\nShortcuts accepted in -e/--engines:")
    print("  ddg -> duckduckgo, sp -> startpage, perp -> perplexity, wb -> wayback,")
    print("  at -> archive-today, gh -> github, grep -> grepapp, vt -> virustotal,")
    print("  edb -> exploitdb, sploit -> sploitus, ps -> packetstorm, msf -> rapid7, poc -> githubpoc")


def list_categories() -> None:
    """Displays available search category presets."""
    print("Available category presets (-c / --category):\n")
    print(f"  {'Category':<12} {'Engines Count':<15} {'Description'}")
    print(f"  {'-'*10:<12} {'-'*13:<15} {'-'*50}")
    for cat_name, (desc, engines) in CATEGORIES.items():
        print(f"  {cat_name:<12} {len(engines):<15} {desc}")
        engines_str = ", ".join(engines)
        print(f"  {'':<12} Engines: {engines_str}\n")


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


def get_engines_by_category(category: str) -> list[tuple[str, str, str]]:
    """Returns engines corresponding to a category preset."""
    cat_lower = category.strip().lower()
    if cat_lower not in CATEGORIES:
        valid_cats = ", ".join(CATEGORIES.keys())
        print(f"Error: Unknown category '{category}'. Available categories: {valid_cats}", file=sys.stderr)
        sys.exit(2)

    _, keys = CATEGORIES[cat_lower]
    key_set = set(keys)
    return [e for e in ENGINES if e[1] in key_set]


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


def main() -> int:
    default_browser = detect_default_browser()

    p = argparse.ArgumentParser(
        description="Multi-Search: Opens multiple browser tabs across search engines and OSINT sources.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Examples:\n"
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
        "-c", "--category",
        default="web",
        help="Category preset to search (default: 'web'). Options: web, osint, infra, code, archive, all.",
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

    if args.list_categories:
        list_categories()
        return 0

    if args.list_engines:
        list_engines()
        return 0

    if args.list_browsers:
        list_browsers()
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

    # Human simulation presets
    if args.human:
        args.shuffle = True
        if args.delay == DEFAULT_TAB_DELAY:
            args.delay = 1.8
        if args.jitter == 0.0:
            args.jitter = 0.8
        if args.initial_delay == DEFAULT_INITIAL_DELAY:
            args.initial_delay = 2.2

    # Resolve target engines
    if args.engines:
        engines = filter_engines([args.engines])
        active_preset = f"custom ({len(engines)} engines)"
    else:
        engines = get_engines_by_category(args.category)
        active_preset = f"category '{args.category}'"

    searches = build_searches(term, engines)
    if args.shuffle:
        random.shuffle(searches)

    cmd_display = " ".join(browser_cmd)
    if args.dry_run:
        print(f"\n🔍 Search Query: \"{term}\"")
        print(f"🏷️  Profile: {active_preset}")
        print(f"🌐 Browser: {cmd_display} ({'Chromium-based' if is_chromium else 'Firefox-based'})")
        if args.human:
            print("👤 Human Simulation: Enabled (shuffled order, dynamic jitter 1.0s-2.6s)")
        elif args.shuffle:
            print("🔀 Shuffled Order: Enabled")
        print(f"📑 Total engines: {len(searches)}\n")
        for name, url in searches:
            print(f"  [{name:<16}] {url}")
        print()
        return 0

    mode_label = "private/incognito" if args.private else "standard"
    human_tag = " | Human Simulation: ON" if args.human else ""
    print(f"🔍 Multi-Search | Query: \"{term}\" | Profile: {active_preset} | Browser: {cmd_display} | Mode: {mode_label}{human_tag}")

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
            init_wait = calculate_delay(args.initial_delay, 0.4 if args.human else 0.0)
            time.sleep(init_wait)

            # 2) Open subsequent URLs in new tabs
            for idx, (name, url) in enumerate(searches[1:], start=2):
                wait_time = calculate_delay(args.delay, args.jitter)
                delay_info = f" (interval: {wait_time}s)" if (args.human or args.jitter > 0) else ""
                print(f" [{idx}/{len(searches)}] 📄 Opening tab: {name}{delay_info}...")
                if is_chromium:
                    tab_flags = ["--incognito", url] if args.private else [url]
                else:
                    tab_flags = ["--new-tab", url]
                subprocess.Popen(browser_cmd + tab_flags)
                time.sleep(wait_time)

    except KeyboardInterrupt:
        print("\n\n⚠️ Interrupted by user.", file=sys.stderr)
        return 130

    print("✨ All tabs dispatched successfully!")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
