# Multi-Search (`msearch`)

A lightning-fast command-line productivity tool that triggers simultaneous searches across multiple web search engines in browser tabs (LibreWolf, Firefox, or any browser of choice).

---

## ⚡ Features

- **Multi-Engine Orchestration**: Dispatches queries across 11 major search engines simultaneously:
  - Google, Bing, DuckDuckGo, Startpage, Ecosia, Qwant, Yahoo, Yandex, Mojeek, Perplexity, and Brave Search.
- **Smart Browser Detection**: Automatically detects native LibreWolf, Flatpak LibreWolf (`io.gitlab.librewolf-community`), or standard Firefox.
- **Engine Filtering (`-e` / `--engines`)**: Run searches only on your preferred engines (e.g. `-e google,brave,ddg`).
- **Private Browsing Mode (`-p` / `--private`)**: Launches queries in an isolated private window.
- **Pacing Control (`-d` / `--delay`)**: Spaced tab dispatching to prevent browser throttling, dropped tabs, or search engine rate-limiting.
- **Dry-Run Inspection (`--dry-run`)**: Preview generated URLs directly in your terminal without opening browser windows.
- **Graceful Execution**: Live progress indicators in the terminal with clean `Ctrl+C` interrupt handling.

---

## 📦 Dependencies

Ensure you have **Python 3.8+** and a supported web browser installed:

### Debian / Ubuntu / Kali / Pop!_OS
```bash
# Python 3 is typically pre-installed
sudo apt update && sudo apt install -y python3
```

### Supported Browsers
By default, `msearch` will automatically detect and use:
1. Native `librewolf` (if installed and in PATH)
2. Flatpak `io.gitlab.librewolf-community`
3. Native `firefox` (if installed)
4. Any custom browser via the `-b` / `--browser` flag (e.g., `google-chrome`, `brave-browser`, `chromium`)

To install LibreWolf via Flatpak:
```bash
flatpak install flathub io.gitlab.librewolf-community
```

---

## 🚀 Usage & Examples

### Basic Usage
Quotes around multi-word queries are optional:
```bash
# Search across all 11 engines
msearch python web scraping

# Or using the script directly:
./multi_search.py cybersecurity threat modeling
```

### Filtering Search Engines (`-e` / `--engines`)
Search only on specific engines using their names or shortcuts (`ddg`, `sp`, `perp`):
```bash
# Search only on Google, Brave, and DuckDuckGo
msearch -e google,brave,ddg reverse engineering

# Search on Perplexity and Startpage
msearch -e perp,sp fast api tutorial
```

### Private Browsing (`-p` / `--private`)
Open all search results inside a new private browsing window:
```bash
msearch -p osint investigation techniques
```

### Preview URLs without Opening Browser (`--dry-run`)
```bash
msearch --dry-run open source intelligence
```

### List Available Engines (`-l` / `--list-engines`)
```bash
msearch --list-engines
```

### List Detected Browsers (`-lb` / `--list-browsers`)
Scan and display all web browsers currently installed on your system (Native, Flatpak, and Snap):
```bash
msearch --list-browsers
```

### Choose Browser with Aliases (`-b` / `--browser`)
Easily switch browsers using short aliases or custom commands:
```bash
# Use Brave Browser (Flatpak or Native)
msearch -b brave open source tools

# Use Google Chrome or Firefox
msearch -b chrome kubernetes architecture
msearch -b firefox reverse engineering
```

---

## 🛠️ Command-Line Options

| Flag | Argument | Description |
| :--- | :--- | :--- |
| `QUERY` | `[string...]` | Search query (multiple words are joined automatically) |
| `-e`, `--engines` | `<list>` | Comma-separated list of engines to query (e.g. `google,brave,ddg`) |
| `-l`, `--list-engines` | None | Display supported search engines and exit |
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

Ensure `~/.local/bin` is present in your `PATH` environment variable:
```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc   # For Bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc    # For Zsh
```

### Shell Alias (Optional)
Alternatively, add an alias to `~/.bashrc` or `~/.zshrc`:
```bash
alias ms='/path/to/projects/multi_search/multi_search.py'
```

---

## 📄 License

Distributed under the [MIT](LICENSE) License. Copyright (c) 2026 Carlos Dias.
