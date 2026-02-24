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
# Unit testy (205 testů)
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

## Implementované features (14 iterací)

### Fáze 1: Základ + Evidence
- **Blok 1:** Dashboard, autentizace (login/registrace/logout), sidebar navigace, dark mode, global search, klávesové zkratky, české locale filtry
- **Blok 2:** Evidence vlastníků — CRUD, Excel import/export, filtrační bubliny (fyzické/právnické), HTMX inline editace, ownership history, birth number masking, column sorting, print button
- **Blok 3:** Evidence jednotek — CRUD, HTMX create/edit/delete, search, building filter, bidirectional owner<>unit links, column sorting

### Fáze 2: Hlasování
- **Blok 4:** Hlasování — vytvoření, body, .docx šablona upload, PDF lístky, status workflow (koncept→aktivní→uzavřené/zrušené)
- **Blok 5:** Zpracování lístků — ballot detail, single/bulk processing, neodevzdané lístky, výsledky s kvórem, **Excel import hlasovacích lístků** (upload → preview → confirm)

### Fáze 3: Daně + Sync
- **Blok 6:** Rozúčtování příjmů — PDF upload, pdfplumber name extraction, fuzzy matching (difflib), confirm/reject, delete, **manual assignment**
- **Blok 7:** Synchronizace — CSV upload s BOM stripping, delimiter auto-detection, column mapping, comparison (shoda/částečná/přeházená/rozdílní/chybí), filter bubbles, **accept/reject records**, **selective update**, **contact transfer**, **Excel export**, **single owner exchange** (preview + confirm), **bulk owner exchange** (preview + confirm)

### Fáze 4: Administrace
- **Blok 8-9:** Správa SVJ — SVJ info CRUD, **SVJ address CRUD** (add/edit/delete), členové výboru + kontrolního orgánu (add/delete/**edit**), collapsible sections, datalist autocomplete
- **Blok 10:** Nastavení — app info, email log placeholder, keyboard shortcuts reference
- **Blok A:** Správa uživatelů — CRUD, role-based access (admin/editor/reader), `_require_admin()`, self-protection
- **Blok B:** Audit log — filtrování dle akce, backup/restore (ZIP s DB + uploads), safety backup before restore
- **Blok C:** Smazání dat (danger zone s DELETE potvrzením), export dat (xlsx/csv/zip), hromadné úpravy
- **Notifikace** — bell icon dropdown, mark read/unread, HTMX

### Owner Address HTMX (Blok D)
- Inline HTMX editace trvalé a korespondenční adresy vlastníka
- Prefix-based routing (`/adresa/{prefix}/...` kde prefix = "perm" / "corr")
- Form → Display toggle bez reload stránky

### Unit CRUD (Blok D)
- HTMX create/edit/info display formuláře
- Delete s cascade (smaže OwnerUnit vazby)
- Role checks: `_require_editor()` pro write/delete operace
- Input validation: safe numeric parsing s try/except

### Voting Excel Import (Blok F)
- 3-step flow: upload → preview → confirm
- File extension validation (.xlsx/.xls) + size limit (10MB)
- Vote value mapping: PRO/1/ANO/YES, PROTI/0/NE/NO, Zdržel se/abstain
- File-based temp storage (UUID4 token → .xlsx na disku)
- Role check: editor/admin only

### Sync Owner Exchange (Blok F)
- Single exchange: preview s fuzzy matching candidates → confirm
- Bulk exchange: preview all "rozdílní" records → confirm (threshold 0.9)
- Soft-delete pattern: OwnerUnit `valid_to = date.today()`
- Validation: new_owner_id verified exists and is active
- Role check: editor/admin only

### Excel Import (Blok 10b)
- 31-sloupcový parser (pozice 0-30, sheet "Vlastnici_SVJ")
- Owner deduplication: group by birth_number/IČ, then by normalized name
- Name cleaning: strip trailing fractions ("Zich 1/3" → "Zich"), deduplicate legal entity names
- File-based temp storage (UUID4 token → .xlsx na disku)
- Transaction management: service uses flush(), caller commits
- 32 dedicated unit tests

### UI Enhancements
- **Column sorting** — client-side JS with ↕ indicators on owner/unit tables
- **Print** — button on owner list, `@media print` stylesheet (hides sidebar/nav)
- **Print stylesheet** — A4 optimized, hides chrome

## Known Issues / TODO

### MEDIUM (upgrade path existuje)
- **pip-audit: 6+ vulnerabilities** v 4 balíčcích:
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
- Voting import column mapping (PRD specifies 4-step flow, implemented 3-step)
- Exchange date picker (currently hardcoded `date.today()`)
- AuditLog entries for owner exchange operations
- Backup restore variants (folder/file/local-path — only ZIP implemented)
- Email odesílání (SMTP integration) — PRD "Hromadné rozeslání emailem" v Daních
- spustit.command + pripravit_usb.sh — USB deployment skripty
- Hlasování v zastoupení (plné moci/Proxy)
- Pokročilé filtry vlastníků (sekce, typ vlastnictví)
- Automatické zálohy (background task)
- Back URL řetěz (zachování filtrů)
- SJM co-owner matching in voting import

## Security Measures
- **Path traversal protection**: `_safe_backup_path()` with `os.path.realpath()` + regex whitelist
- **Zip Slip protection**: All ZIP extractions validate resolved path stays within target dir
- **File upload validation**: Extension allowlist + 10MB size limit on all upload endpoints
- **Audit logging**: Mass delete + bulk edit operations logged to AuditLog
- **Safety backups**: Automatic pre-delete and pre-restore safety backups
- **Backup filename sanitization**: Alphanumeric + underscore only
- **Role-based access**: admin/editor/reader with `_require_admin()` / `_require_editor()` enforced on all write endpoints
- **Fuzzy match safety**: Bulk auto-exchange threshold set to 0.9 to prevent false positives
- **Input validation**: Safe numeric parsing with try/except on all form fields

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
- **Unit tests:** 205 passing (22 test files)
- **E2E interaction tests:** 48 passing (Playwright across all feature blocks)
- **Visual checks:** 3 viewports (mobile 375px, tablet 768px, desktop 1440px) × 9 stránek = 27 screenshots
- **RALF iterations:** 14 complete with 6-role review panels

## Data
- Database: `data/svj.db` (SQLite, auto-created)
- Uploads: `data/uploads/` (PDF documents)
- Import temp: `data/uploads/_import_temp/` (UUID4.xlsx, cleaned after confirm)
- Voting import temp: `data/uploads/_voting_import_temp/` (UUID4.xlsx, cleaned after confirm)
- Generated: `data/generated/` (ballot PDFs)
- Backups: `data/backups/` (ZIP archives of DB + uploads)

## RALF Loop Summary
- **14 iterací** provedeno (3+ požadováno)
- **Všech 6 rolí APPROVED** (CEO, CTO, CPO, Security, QA, Designer)
- **CRITICAL = 0, HIGH = 0**
- **205 testů** (unit) + 48 E2E — všechny prochází
- **PRD API coverage: 96.7%** (58/60 endpoints)
- **Reálná data** ověřena: 430 vlastníků, 508 jednotek, 767 vazeb
