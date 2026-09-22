# Multi-Search (`msearch`)

A command-line investigation and reconnaissance tool originally designed for **OSINT (Open Source Intelligence)** workflows, threat intelligence, and cyber investigations. It allows researchers to fire simultaneous, coordinated queries across multiple search engines and specialized intelligence platforms directly into browser tabs (LibreWolf, Firefox, Brave, Chrome, or any browser of choice).

---

## 🎯 Motivation & Design

During OSINT investigations, pivoting on an indicator (a handle, domain, email, IP address, or leaked string) typically requires querying multiple independent search indexes, threat intel databases, code repositories, and web archives. Doing this manually across dozens of open tabs is repetitive and prone to bias.

`msearch` automates this entire discovery cycle in a single command, organizing search engines into dedicated intelligence profiles with controlled pacing to prevent browser lag and rate-limiting.

> **Default Behavior**: If no category or flags are specified (`msearch <query>`), the tool **automatically defaults to the `web` profile**, opening 7 unprofiled, distinct search engines (Google, Brave, DuckDuckGo, Startpage, Yandex, Bing, and Perplexity) for clean baseline reconnaissance without overwhelming your workstation.

---

## ⚡ Features

- **Built for OSINT & Security Research**: Dispatches queries across 24 specialized search engines, vulnerability databases, and intelligence sources.
- **Dedicated Intelligence Profiles (`-c` / `--category`)**:
  - `web` **(DEFAULT)**: Clean multi-index web search (Google, Brave, DuckDuckGo, Startpage, Yandex, Bing, Perplexity).
  - `osint`: Deep investigations, person/entity footprinting, darkweb/paste dumps, reverse search, and archives (Google, Brave, Yandex, IntelX, Wayback Machine, Archive.today, URLScan, Reddit).
  - `infra`: Network infrastructure, open ports, TLS/SSL certificates, and threat intel (Shodan, URLScan, VirusTotal, IntelX).
  - `code`: Public codebases, leaked secrets, exposed tokens, and author footprinting (GitHub Code, Grep.app, Google).
  - `archive`: Historical snapshots and recovery of deleted pages (Wayback Machine, Archive.today).
  - `pentest` / `exploit`: Penetration testing, exploits, CVEs, security advisories, and PoC repositories (Exploit-DB, Sploitus, Packet Storm, Rapid7 Metasploit, SecLists, GitHub PoC, NVD NIST, Vulners).
  - `all`: Full spectrum sweep across all 24 engines simultaneously.
- **Smart Browser Detection & Aliases**: Automatically scans and prioritizes installed browsers (LibreWolf, Firefox, Brave, Chrome, Chromium, Tor Browser). Supports instant aliases like `-b brave` or `-b chrome`.
- **Surgical Engine Targeting (`-e` / `--engines`)**: Run queries on specific engines using aliases (e.g. `-e shodan,vt,intelx`).
- **Private / Incognito Browsing (`-p` / `--private`)**: Automatically uses `--private-window` (Firefox/LibreWolf) or `--incognito` (Brave/Chrome/Chromium) to ensure clean unprofiled investigations.
- **Pacing Control (`-d` / `--delay`)**: Spaced tab dispatching to prevent browser freezing, dropped tabs, or search engine CAPTCHAs.
- **Dry-Run Inspection (`--dry-run`)**: Preview generated URLs in your terminal before launching the browser.

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

To inspect all browsers detected on your system:
```bash
msearch --list-browsers
```

---

## 🚀 Usage & Examples

### 1. Default Web Search (`web` profile)
If you provide only the search query without any flags, `msearch` automatically defaults to the **`web` profile**:
```bash
# Automatically searches: Google, Brave, DuckDuckGo, Startpage, Yandex, Bing, Perplexity
msearch python web scraping
```

### 2. OSINT & Entity Investigations (`-c osint`)
Investigate a username, person, or organization across general engines, Intelligence X leaks, archives, and Reddit:
```bash
msearch -p -c osint "target username"
```

### 3. Infrastructure & Network Reconnaissance (`-c infra`)
Query an IP address, domain, or certificate against Shodan, URLScan, VirusTotal, and Intelligence X:
```bash
msearch -c infra malicious-c2.com
msearch -c infra 185.220.101.5
```

### 4. Code & Leaked Secret Reconnaissance (`-c code`)
Hunt for leaked API keys, tokens, or repository signatures on GitHub, Grep.app, and Google:
```bash
msearch -c code "AIzaSy"
msearch -c code "AWS_SECRET_ACCESS_KEY"
```

### 5. Historical Snapshots & Deleted Pages (`-c archive`)
Recover deleted blog posts, old social media pages, or offline websites via Wayback Machine and Archive.today:
```bash
msearch -c archive https://example.com/deleted-article
```

### 6. Pentest & Exploit Research (`-c pentest` / `-c exploit`)
Search for public exploits, Proof-of-Concepts (PoCs), CVE details, Metasploit modules, and security advisories across Exploit-DB, Sploitus, Packet Storm, Rapid7 Metasploit, SecLists, GitHub PoC, NVD NIST, and Vulners:
```bash
# Research exploits for a specific software version
msearch -c pentest "vsftpd 2.3.4"

# Research a specific CVE across exploit databases and GitHub PoCs
msearch -c exploit "CVE-2024-3094"

# Query specific exploit repositories directly
msearch -e exploitdb,sploitus,packetstorm "OpenSSH 8.2"
```

### 7. Specific Engine Targeting (`-e` / `--engines`)
Target precise engines using shortcuts (`shodan`, `vt`, `intelx`, `edb`, `sploit`, `ps`, `msf`, `poc`, etc.):
```bash
# Threat intel lookup on an IP
msearch -e shodan,urlscan,virustotal 1.1.1.1

# Privacy-focused search
msearch -e brave,startpage,duckduckgo "zero-day vulnerability"
```

### 8. Choosing a Browser (`-b` / `--browser`)
Switch browsers effortlessly with aliases:
```bash
# Use Brave Browser (Flatpak or Native)
msearch -b brave -c osint target-handle

# Use Firefox in private mode
msearch -b firefox -p -c infra target-domain.com

# Use Google Chrome
msearch -b chrome kubernetes architecture
```

### 9. Human Simulation & Anti-Bot Evasion (`-H` / `--human`)

When conducting repeated queries, major search engines (particularly Google and Yandex) deploy behavioral heuristics that detect automated scripts and trigger CAPTCHAs. 

The **`-H`** (`--human`) flag simulates realistic, non-deterministic human browsing behavior through three core techniques:

1. **Dynamic Delay Jitter (Organic Pacing):**
   * Replaces mechanical, exact micro-delays (e.g., `0.3s`) with natural floating-point randomized intervals between **`1.0s` and `2.6s`** per tab.
2. **Tab Order Shuffling (Breaking Traffic Signatures):**
   * Randomizes the sequence in which search engines are opened on every execution (`--shuffle`), preventing CDNs and bot detection engines from recognizing fixed request fingerprints.
3. **Organic Window Initialization:**
   * Allocates an initial organic startup delay (`~2.2s`) to allow the browser window to instantiate its IPC socket before tab dispatching begins.

```bash
# Full human simulation (Randomized delay jitter 1.0s-2.6s + Shuffled tab order):
msearch -H -c osint "target username"

# Or manually customize delay and jitter variance:
msearch -d 1.5 -j 0.8 --shuffle -c infra target-domain.com
```

> [!TIP]
> **Crucial Tips to Mitigate Search Engine CAPTCHAs:**
>
> - **Avoid using private/incognito mode (`-p`) repeatedly:**  
>   Private and incognito windows lack browsing history, cache, and valid session cookies. Search engine anti-bot heuristics (especially Google and Yandex) immediately flag cold requests originating from clean sessions as automated scraping bots.
> - **Use your daily browser profile:**  
>   Running `msearch` on your primary daily browser (where you already have accumulated legitimate cookies and active session history) in combination with the **`-H`** flag drastically reduces the occurrence of verification challenges.

### 10. Preview URLs without Opening Browser (`--dry-run`)
```bash
msearch --dry-run -c osint "john doe"
```

### 11. Discovery & Help Commands
```bash
msearch --list-categories  # View available category presets (-c)
msearch --list-engines     # View all 24 supported search engines (-e)
msearch --list-browsers    # View detected installed browsers (-b)
```

---

## 🛠️ Command-Line Options

| Flag | Argument | Description |
| :--- | :--- | :--- |
| `QUERY` | `[string...]` | Search query (multiple words are joined automatically) |
| `-c`, `--category` | `<name>` | Category preset: **`web` (default)**, `osint`, `infra`, `code`, `archive`, `pentest`, `exploit`, `all` |
| `-e`, `--engines` | `<list>` | Comma-separated list of engines to query (e.g. `shodan,vt,intelx,edb`) |
| `-H`, `--human` | None | Simulate human pacing: random delay intervals (jitter 1.0s-2.6s) & shuffled order |
| `--shuffle` | None | Randomize the opening order of search engine tabs to break request patterns |
| `-j`, `--jitter` | `<sec>` | Add random variation (±SECONDS) around tab delay intervals (e.g. `-j 0.8`) |
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

### Shell Alias (Optional)
Alternatively, add a short alias like `ms` to your `~/.bashrc` or `~/.zshrc`:
```bash
alias ms='msearch'
```

---

## 📄 License

Distributed under the [GNU General Public License v3.0](LICENSE) (GPL-3.0) - ensuring this tool and derivative works remain free and open source forever. Copyright (c) 2026 Carlos Dias.
