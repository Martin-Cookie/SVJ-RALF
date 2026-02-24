# HANDOFF – SVJ Správa v2.0

## Jak spustit

### Požadavky
- Python 3.9+
- Node.js (pro Playwright testy)

### Instalace

```bash
# Backend dependencies
pip install -r requirements.txt

# Playwright (pro E2E testy)
npm install
npx playwright install chromium
```

### Konfigurace

```bash
cp .env.example .env
# Upravte SECRET_KEY na náhodný řetězec
# Volitelně: nastavte SMTP pro email
```

### Spuštění

```bash
python -m uvicorn app.main:app --port 8000 --reload
```

Otevřete http://localhost:8000 — při prvním spuštění se zobrazí registrace.

### Testy

```bash
# Unit testy (81 testů)
python -m pytest tests/ -v

# E2E interaction testy (48 testů) — vyžaduje běžící server
npx playwright test tests/interaction-check.spec.ts

# Visual screenshoty (3 viewporty)
ITER=X PHASE=Y npx playwright test tests/visual-check.spec.ts
```

## Implementované features

### Fáze 1: Základ + Evidence
- **Blok 1:** Dashboard, autentizace (login/registrace/logout), sidebar navigace, dark mode, global search, klávesové zkratky, české locale filtry
- **Blok 2:** Evidence vlastníků — CRUD, Excel import/export, filtrační bubliny (fyzické/právnické), HTMX inline editace, ownership history
- **Blok 3:** Evidence jednotek — CRUD, search, building filter, bidirectional owner↔unit links

### Fáze 2: Hlasování
- **Blok 4:** Hlasování — vytvoření, body, .docx šablona upload, PDF lístky, status workflow (koncept→aktivní→uzavřené/zrušené)
- **Blok 5:** Zpracování lístků — ballot detail, single/bulk processing, neodevzdané lístky, výsledky s kvórem

### Fáze 3: Daně + Sync
- **Blok 6:** Rozúčtování příjmů — PDF upload, pdfplumber name extraction, fuzzy matching (difflib), confirm/reject, delete
- **Blok 7:** Synchronizace — CSV upload s BOM stripping, delimiter auto-detection, column mapping, comparison (shoda/částečná/přeházená/rozdílní/chybí), filter bubbles

### Fáze 4: Administrace
- **Blok 8-9:** Správa SVJ — SVJ info CRUD, členové výboru + kontrolního orgánu (add/delete), collapsible sections, datalist autocomplete
- **Blok 10:** Nastavení — app info, email log placeholder, keyboard shortcuts reference

## Known Issues / TODO

### Nice-to-have (neimplementované PRD features)
- Email odesílání (SMTP integration) — PRD "Hromadné rozeslání emailem" v Daních
- spustit.command + pripravit_usb.sh — USB deployment skripty
- Excel import hlasovacích lístků (4-krokový flow)
- Hlasování v zastoupení (plné moci/Proxy)
- Pokročilé filtry vlastníků (sekce, typ vlastnictví)
- Column sorting by click v tabulkách
- Auto-zálohy, obnova dat
- Hromadné úpravy, tisk
- Smazání dat (danger zone)

### Dependency vulnerabilities
Pinned by FastAPI 0.115.0 (medium priority):
- python-multipart 0.0.18 → 0.0.22 (GHSA-wp53-j4wj-2cfg)
- pdfminer-six 20231228 → 20251107+ (2 CVEs)
- starlette 0.38.6 → 0.40.0+ (2 CVEs)
- pillow 11.3.0 → 12.1.1 (1 CVE)

**Fix:** Upgrade FastAPI to latest version which unpins starlette. Test thoroughly after upgrade.

### Minor warnings
- `Query.get()` deprecation in test_owners.py → use `Session.get()`
- `import multipart` PendingDeprecationWarning → will resolve with python-multipart upgrade

## Tech Stack
- Python 3.9.6, FastAPI 0.115.0, SQLAlchemy 2.0.35, SQLite
- Jinja2 templates + HTMX 1.9.10 + Tailwind CSS CDN
- Starlette SessionMiddleware (cookie-based auth, bcrypt passwords)
- Playwright + Chromium (E2E tests + visual screenshots)

## Test Coverage
- **Unit tests:** 81 passing (auth, dashboard, search, owners, units, voting, voting processing, tax, sync, admin, settings)
- **E2E interaction tests:** 48 passing (Playwright across all 10 feature blocks)
- **Visual checks:** 3 viewports (mobile 375px, tablet 768px, desktop 1440px)
- **RALF iterations:** 7 complete with 6-role review panels

## Data
- Database: `data/svj.db` (SQLite, auto-created)
- Uploads: `data/uploads/` (PDF documents)
- Generated: `data/generated/` (ballot PDFs)
- Backups: `data/backups/` (placeholder)
