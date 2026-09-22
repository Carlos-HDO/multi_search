# Multi-Search (`msearch`)

A lightning-fast command-line productivity tool that triggers simultaneous searches across multiple web search engines and OSINT intelligence sources in browser tabs (LibreWolf, Firefox, Brave, Chrome, or any browser of choice).

---

## ⚡ Features

- **Multi-Engine Orchestration**: Dispatches queries across 16 specialized search engines and intelligence sources.
- **OSINT & Intelligence Profiles (`-c` / `--category`)**:
  - `web`: General independent search (Google, Brave, DuckDuckGo, Startpage, Yandex, Bing, Perplexity).
  - `osint`: Deep open-source investigations, archives, darkweb/paste dumps, and reverse search (Google, Brave, Yandex, IntelX, Wayback Machine, Archive.today, URLScan, Reddit).
  - `infra`: Network infrastructure, open ports, certificates, and threats (Shodan, URLScan, VirusTotal, IntelX).
  - `code`: Public codebases, leaked credentials, API tokens, and developer footprinting (GitHub Code, Grep.app, Google).
  - `archive`: Historical snapshots and recovery of deleted pages (Wayback Machine, Archive.today).
  - `all`: Full spectrum sweep across all 16 engines.
- **Smart Browser Detection & Aliases**: Automatically detects native LibreWolf, Flatpak LibreWolf, Firefox, Chrome, Brave, Chromium, and Tor Browser. Use short aliases like `-b brave` or `-b chrome`.
- **Engine Filtering (`-e` / `--engines`)**: Run searches on specific engines using aliases (e.g. `-e shodan,vt,intelx`).
- **Private / Incognito Mode (`-p` / `--private`)**: Launches queries in isolated private browsing (supports both Firefox `--private-window` and Chromium `--incognito`).
- **Pacing Control (`-d` / `--delay`)**: Spaced tab dispatching to prevent browser freezing, dropped tabs, or search engine rate-limiting.
- **Dry-Run Inspection (`--dry-run`)**: Preview generated URLs directly in your terminal without launching the browser.

---

## 📦 Dependencies

Ensure you have **Python 3.8+** and a supported web browser installed:

### Debian / Ubuntu / Kali / Pop!_OS
```bash
sudo apt update && sudo apt install -y python3
```

### Supported Browsers
By default, `msearch` will automatically detect and prioritize installed browsers:
1. LibreWolf (Native or Flatpak `io.gitlab.librewolf-community`)
2. Firefox (`firefox`)
3. Brave (`brave` or `com.brave.Browser`)
4. Google Chrome (`com.google.Chrome` or native)
5. Chromium (Native or Snap)
6. Tor Browser (`org.torproject.torbrowser-launcher`)

To see all browsers detected on your system:
```bash
msearch --list-browsers
```

---

## 🚀 Usage & Examples

### Basic Web Search
Quotes around multi-word queries are optional:
```bash
# Default category (web: Google, Brave, DDG, Startpage, Yandex, Bing, Perplexity)
msearch python web scraping
```

### OSINT & Intelligence Searches (`-c` / `--category`)
```bash
# General OSINT investigation (Google, Brave, Yandex, IntelX, Wayback, Archive.today, URLScan, Reddit)
msearch -c osint "john doe"

# Network & Infrastructure reconnaissance (Shodan, URLScan, VirusTotal, IntelX)
msearch -c infra target-domain.com

# Leak & credential hunting in public git repositories (GitHub Code, Grep.app, Google)
msearch -c code "AWS_SECRET_ACCESS_KEY"

# Retrieve historical snapshots of a deleted page or profile
msearch -c archive https://example.com/deleted-article
```

### Specific Engine Selection (`-e` / `--engines`)
Target specific engines directly using names or shortcuts (`shodan`, `vt`, `intelx`, `ddg`, `sp`, `gh`, etc.):
```bash
# Threat intel lookup on an IP
msearch -e shodan,urlscan,virustotal 1.1.1.1

# Search only Google, Brave, and DuckDuckGo
msearch -e google,brave,ddg cybersecurity news
```

### Private / Incognito Browsing (`-p` / `--private`)
Opens results in a newly spawned private/incognito window:
```bash
msearch -p -c osint suspicious-actor
```

### Choosing a Browser (`-b` / `--browser`)
Use short aliases or full commands:
```bash
# Use Brave Browser (Flatpak or Native)
msearch -b brave -c osint target-handle

# Use Google Chrome or Firefox
msearch -b chrome kubernetes architecture
msearch -b firefox -p threat modeling
```

### Dry-Run Mode (`--dry-run`)
Preview all generated URLs in the terminal without opening any tabs:
```bash
msearch --dry-run -c infra evil-corp.com
```

### List Categories & Engines
```bash
msearch --list-categories  # View category presets and their engine members
msearch --list-engines     # View all supported engines and aliases
msearch --list-browsers    # View detected browsers on the system
```

---

## 🛠️ Command-Line Options

| Flag | Argument | Description |
| :--- | :--- | :--- |
| `QUERY` | `[string...]` | Search query (multiple words are joined automatically) |
| `-c`, `--category` | `<name>` | Category preset: `web` (default), `osint`, `infra`, `code`, `archive`, `all` |
| `-e`, `--engines` | `<list>` | Comma-separated list of engines to query (e.g. `shodan,vt,intelx`) |
| `-lc`, `--list-categories`| None | Display available category presets and exit |
| `-l`, `--list-engines` | None | Display all supported search engines and exit |
| `-lb`, `--list-browsers` | None | Scan and list detected installed web browsers and exit |
| `-b`, `--browser` | `<alias\|cmd>` | Browser alias (`brave`, `chrome`, `firefox`, etc.) or custom command |
| `-p`, `--private` | None | Open search in a new private/incognito window |
| `-d`, `--delay` | `<sec>` | Delay in seconds between opening tabs (default: `0.3s`) |
| `--initial-delay` | `<sec>` | Delay before opening tabs to allow window startup (default: `1.0s`) |
| `--dry-run` | None | Preview formatted search URLs without launching the browser |
| `-h`, `--help` | None | Display help and usage instructions |

---

## 🔗 Setup & Shell Integration

### Quick Install
Run the installation script to create symlinks in `~/.local/bin/`:
```bash
chmod +x install.sh
./install.sh
```

Ensure `~/.local/bin` is in your `PATH`:
```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc   # For Bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc    # For Zsh
```

---

## 📄 License

Distributed under the [MIT](LICENSE) License. Copyright (c) 2026 Carlos Dias.
