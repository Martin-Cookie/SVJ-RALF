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
# Unit testy (113 testů)
python3 -m pytest tests/ -v

# E2E interaction testy (48 testů) — vyžaduje běžící server
npx playwright test tests/interaction-check.spec.ts

# Visual screenshoty (3 viewporty × 9 stránek)
ITER=X PHASE=Y npx playwright test tests/visual-check.spec.ts
```

### Import vlastníků z Excelu

1. Otevřete `/vlastnici/import`
2. Nahrajte Excel soubor (formát: sheet "Vlastnici_SVJ", 31 sloupců, pozice 0-30)
3. Preview zobrazí parsovaná data, deduplikaci a chyby
4. Klikněte "Potvrdit import"
5. Výsledek: vlastníci, jednotky a vazby vytvořeny

Referenční Excel: project SVJ, `data/SVJ_Evidence_Vlastniku_CLEAN.xlsx`

## Implementované features (10 bloků)

### Fáze 1: Základ + Evidence
- **Blok 1:** Dashboard, autentizace (login/registrace/logout), sidebar navigace, dark mode, global search, klávesové zkratky, české locale filtry
- **Blok 2:** Evidence vlastníků — CRUD, Excel import/export, filtrační bubliny (fyzické/právnické), HTMX inline editace, ownership history, birth number masking
- **Blok 3:** Evidence jednotek — CRUD, search, building filter, bidirectional owner<>unit links

### Fáze 2: Hlasování
- **Blok 4:** Hlasování — vytvoření, body, .docx šablona upload, PDF lístky, status workflow (koncept→aktivní→uzavřené/zrušené)
- **Blok 5:** Zpracování lístků — ballot detail, single/bulk processing, neodevzdané lístky, výsledky s kvórem

### Fáze 3: Daně + Sync
- **Blok 6:** Rozúčtování příjmů — PDF upload, pdfplumber name extraction, fuzzy matching (difflib), confirm/reject, delete
- **Blok 7:** Synchronizace — CSV upload s BOM stripping, delimiter auto-detection, column mapping, comparison (shoda/částečná/přeházená/rozdílní/chybí), filter bubbles

### Fáze 4: Administrace
- **Blok 8-9:** Správa SVJ — SVJ info CRUD, členové výboru + kontrolního orgánu (add/delete), collapsible sections, datalist autocomplete
- **Blok 10:** Nastavení — app info, email log placeholder, keyboard shortcuts reference

### Excel Import (Blok 10b)
- 31-sloupcový parser (pozice 0-30, sheet "Vlastnici_SVJ")
- Owner deduplication: group by birth_number/IČ, then by normalized name
- Name cleaning: strip trailing fractions ("Zich 1/3" → "Zich"), deduplicate legal entity names
- File-based temp storage (UUID4 token → .xlsx na disku)
- Transaction management: service uses flush(), caller commits
- 32 dedicated unit tests

## Known Issues / TODO

### MEDIUM (upgrade path existuje)
- **pip-audit: 6 vulnerabilities** v 4 balíčcích:
  - `starlette 0.38.6` → upgrade FastAPI na 0.119+ (vyžaduje `starlette >=0.40`)
  - `python-multipart 0.0.18` → `pip install python-multipart>=0.0.22`
  - `pdfminer-six 20231228` → `pip install pdfminer.six>=20251230`
  - `pillow 11.3.0` → `pip install pillow>=12.1.1`
- **CSRF ochrana** chybí (omezení Starlette SessionMiddleware) — pro produkci přidat CSRF token middleware

**Fix:** Upgrade FastAPI to latest version which unpins starlette. Test thoroughly after upgrade.

### LOW (minor)
- `OwnerUnit.share` vždy 1.0 — vlastnický podíl neextrahován z Excelu
- Loading indikátor chybí při importu (770 řádků trvá pár sekund)
- Temp file cleanup pouze v finally bloku (bez periodic cleanup pro crash scénáře)
- `Query.get()` deprecation warning → use `Session.get()`
- Rate limiting na login endpoint chybí
- Test coverage measurement (pytest-cov) není nastaveno
- `datetime.utcnow` deprecation (Python 3.12+, ale projekt běží na 3.9)

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

## Tech Stack

| Komponenta | Verze |
|-----------|-------|
| Python | 3.9.6 |
| FastAPI | 0.115.0 |
| SQLAlchemy | 2.0.35 |
| Starlette | 0.38.6 |
| SQLite | lokální (data/svj.db) |
| Tailwind CSS | CDN (ne CLI build) |
| HTMX | 1.9.10 |
| Playwright | 1.58.2 |

## Test Coverage
- **Unit tests:** 113 passing (14 test files: auth, config, database, owners, units, voting, voting_processing, tax, sync, admin, search, settings, excel_import)
- **E2E interaction tests:** 48 passing (Playwright across all 10 feature blocks)
- **Visual checks:** 3 viewports (mobile 375px, tablet 768px, desktop 1440px) × 9 stránek = 27 screenshots
- **RALF iterations:** 9 complete with 6-role review panels

## Data
- Database: `data/svj.db` (SQLite, auto-created)
- Uploads: `data/uploads/` (PDF documents)
- Import temp: `data/uploads/_import_temp/` (UUID4.xlsx, cleaned after confirm)
- Generated: `data/generated/` (ballot PDFs)
- Backups: `data/backups/` (placeholder)

## RALF Loop Summary
- **9 iterací** provedeno (3+ požadováno)
- **Všech 6 rolí APPROVED** (CEO, CTO, CPO, Security, QA, Designer)
- **CRITICAL = 0, HIGH = 0**
- **161 testů** (113 unit + 48 E2E) — všechny prochází
- **Reálná data** ověřena: 430 vlastníků, 508 jednotek, 767 vazeb
