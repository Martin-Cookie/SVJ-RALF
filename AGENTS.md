# AGENTS.md – Operational Learnings

## Guardrails (přidávej když narazíš na problém)
- [iter 1] Python 3.9: NEPOUŽÍVAT `X | None` syntax → použít `Optional[X]` z typing
- [iter 1] SQLite in-memory testy: VŽDY použít `StaticPool` v engine, jinak každá connection = jiná DB
- [iter 1] Playwright: po `pkill uvicorn` ČEKAT 2s než se port uvolní, jinak "address already in use"
- [iter 1] Playwright: `waitForURL('/')` nefunguje spolehlivě po redirect chain → použít `waitForURL('**/')` nebo `waitForLoadState`
- [iter 1] TemplateResponse: NOVÝ API od Starlette 0.38+ → `TemplateResponse(request, name, ctx)` místo `TemplateResponse(name, {"request": request, ...})`
- [iter 1] Playwright locators: `text=Vlastníků` matchuje i "Import vlastníků" → použít `{ exact: true }` nebo `getByRole`
- [iter 2] FastAPI route ordering: statické cesty (/vlastnici/export, /vlastnici/import) MUSÍ být PŘED parametrickými (/vlastnici/{id}), jinak se "import" matchne jako owner_id
- [iter 2] Playwright heading match: pokud stránka má h1 "Vlastníci" a h3 "Žádní vlastníci", getByRole('heading', { name: 'Vlastníci' }) matchne oba → použít { exact: true }
- [iter 2] ImportLog model: pole jsou source, records_count, status (NE module, row_count)
- [iter 4] Playwright strict mode: flash messages contain same text as page elements → use getByRole('heading') or { exact: true } for disambiguation
- [iter 4] FastAPI file upload: async endpoint + UploadFile + File(None) for optional file uploads. Form must have enctype="multipart/form-data"
- [iter 4] Ballot generation: generate_ballot_pdf has fallback — creates simple .docx when no template provided
- [iter 5] Async endpoints: pro dynamické form fields (vote_{id}) použij async def + await request.form() — NIKDY sync body parsing
- [iter 5] Starlette FormData.getlist(): pro multi-value form fields (ballot_ids) použij form.getlist("field_name")
- [iter 6] PDF name extraction: pdfplumber best-effort with filename fallback — nikdy nespoléhej na úspěšnou extrakci
- [iter 6] Fuzzy matching: difflib.SequenceMatcher with bidirectional name comparison (First Last vs Last First)

## Patterns (co funguje dobře v tomto projektu)
- [iter 1] FastAPI Form() params místo asyncio.new_event_loop() hacku pro form data
- [iter 1] conftest.py: db_engine (StaticPool) → db_session → client (override get_db) → auth_client chain
- [iter 1] Playwright visual-check: loginOrRegister() helper s URL-based branching (registrace/login/dashboard)
- [iter 1] Tailwind CDN + HTMX + Jinja2 = rychlý prototyping bez build stepu
- [iter 2] Excel import: openpyxl load_workbook(read_only=True) + column mapping dict → flexibilní parsing
- [iter 2] Session-based import preview: upload → parse → store in session → confirm → create records
- [iter 2] Collapsible sections: `<details><summary>` element pro ownership history

## Known Issues (problémy které ještě nejsou vyřešené)
- spustit.command + pripravit_usb.sh ještě nevytvořeny (plán: Blok 10)
- Test coverage measurement neprobíhá (plán: iter 3)
- Sidebar linky na neexistující routes (dane, synchronizace, sprava, nastaveni) → budou v Bloku 6–10
- starlette 0.38.6 CVE (GHSA-f96h-pmfr-66vw) — pinned by FastAPI 0.115.0, upgrade v Bloku 10
- Pokročilé filtry vlastníků (sekce, typ vlastnictví, s/bez email/telefon) → iter 3
- Import flow E2E test chybí (session-based = těžké testovat v Playwright) → iter 3
- Query.get() deprecation warning v testu → minor, fix v iter 3

## Tech Notes (specifika tech stacku tohoto projektu)
- Python 3.9.6, FastAPI 0.115.0, SQLAlchemy 2.0.35, Starlette 0.38.6
- SQLite lokální DB (data/svj.db), in-memory pro testy
- Session auth přes Starlette SessionMiddleware (cookie-based, httpOnly, samesite=lax)
- Tailwind CDN (ne CLI build), custom.css pro overrides
- HTMX 1.9.10 pro inline editace
- Playwright + Chromium pro E2E testy a screenshoty
