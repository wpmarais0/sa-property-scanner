# SA Property Scanner

![CI](https://github.com/wpmarais0/sa-property-scanner/actions/workflows/ci.yml/badge.svg)

Autonomous property scanner for South African real estate, targeting the **Western Cape / Garden Route** market. Monitors major portals and agency sites, filters by your criteria, and pushes instant alerts to Telegram or Discord.

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Sources                                                    │
│  ├── Property24        (Playwright + API intercept)         │
│  ├── Private Property  (Playwright + API intercept)         │
│  ├── Pam Golding       (Static HTML scraping)               │
│  ├── Seeff             (Static HTML scraping)               │
│  ├── Sotheby's         (Static HTML scraping)               │
│  ├── Just Property     (Static HTML scraping)               │
│  ├── Harcourts         (Static HTML scraping)               │
│  └── Rawson            (Static HTML scraping)               │
└────────────────────────┬────────────────────────────────────┘
                         ▼
              ┌─────────────────────┐
              │  Unified Extractor  │
              │  Pydantic validation│
              │  Retry + backoff    │
              └──────────┬──────────┘
                         ▼
              ┌─────────────────────┐
              │  PostgreSQL / SQLite│
              │  Deduplication      │
              │  Price drop tracking│
              └──────────┬──────────┘
                         ▼
              ┌─────────────────────┐
              │  Notification Router│
              │  Telegram / Discord │
              └─────────────────────┘
```

---

## 🚀 Quick Start

### 1. Prerequisites

- Python 3.11+
- [Poetry](https://python-poetry.org/docs/#installation)
- (Optional) Docker & Docker Compose

### 2. Install

```bash
cd sa_property_scanner
poetry install
poetry shell
```

### 3. Configure

```bash
cp .env.example .env
# Edit .env with your Telegram token, chat ID, and target URLs
```

### 4. Initialise Database

```bash
property-scanner init-db
property-scanner migrate
```

### 5. Run a Scan

```bash
property-scanner scan
```

---

## 🐳 Docker

```bash
# Start PostgreSQL + scanner
docker-compose up --build

# Or run scanner only against SQLite
docker build -t sa-property-scanner .
docker run --env-file .env sa-property-scanner
```

---

## 📅 Scheduling

### Local / VPS (Recommended)

Add to your crontab (`crontab -e`):

```cron
# Run every 30 minutes
*/30 * * * * cd /path/to/sa_property_scanner && poetry run property-scanner scan >> /var/log/property_scanner.log 2>&1
```

### GitHub Actions (Free tier)

The included `.github/workflows/scanner.yml` runs on a cron schedule every 30 minutes.

1. Make sure your local `.env` has the values you want to use.
2. Push your `.env` values to GitHub secrets/variables:

   ```bash
   # Review what will be uploaded
   scripts/export-github-env.sh

   # Actually upload (requires the GitHub CLI and repo write access)
   scripts/export-github-env.sh --apply
   ```

   Sensitive values (`DISCORD_WEBHOOK_URL`, `TELEGRAM_BOT_TOKEN`, etc.) are stored as **encrypted secrets**. Source URLs, filters, and enabled flags are stored as **repository variables**.

3. Trigger the workflow manually from the Actions tab to verify it works.

**Notes:**
- Property24 and Private Property may block GitHub's Azure IP ranges. Agency-only mode (Pam Golding, Seeff, Sotheby's, Just Property, Harcourts, Rawson) is more reliable here.
- The workflow caches `properties.db` between runs so only new/updated listings trigger notifications.
- If you want to use PostgreSQL instead of SQLite, set `DATABASE_URL` to a connection string (e.g. from a managed Postgres provider).

---

## 🔌 Adding a New Source

1. Create `src/sa_property_scanner/sources/my_site.py`
2. Subclass `SourceAdapter` and implement `fetch()` and `parse()`
3. Register in `src/sa_property_scanner/sources/__init__.py`
4. Add env vars in `.env.example`

Example:

```python
from .base import SourceAdapter

class MySiteSource(SourceAdapter):
    name = "my_site"
    mode = "static"  # or "playwright"

    def fetch(self, url: str) -> str:
        return self._http_get(url)

    def parse(self, html: str) -> list[RawListing]:
        # ... parsing logic ...
        pass
```

---

## 🧪 Testing

```bash
pytest
```

---

## ⚠️ Legal & Ethical Notice

This tool is for **personal use only**. Respect the `robots.txt` and Terms of Service of target websites. Do not hammer servers with excessive requests. The default `SLEEP_BETWEEN_REQUESTS=2` is designed to be polite.

---

## 📄 License

MIT
