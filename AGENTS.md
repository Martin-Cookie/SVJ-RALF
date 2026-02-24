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
- [iter 7] Playwright strict mode: input[name="name"] matchuje více elementů na admin page → scope with section locator
- [iter 7] Collapsible `<details>`: po redirect se zavřou → v E2E testech znovu otevřít summary po page load
- [iter 7] Playwright data persistence: pro board member add testy použij unique name s Date.now()
- [iter 8] Excel import: service functions MUSÍ mít dedicated unit testy — production data parsing je příliš kritický pro route-only testing
- [iter 8] Personal data (RČ): VŽDY maskovat v UI, omezit v search, zvážit encryption at rest
- [iter 8] Transaction management: service functions NESMÍ commitovat — nechej callera řídit transakci
- [iter 8] Name cleaning: stripuj trailing fraction patterns (např. "Zich 1/3" → "Zich") přes regex
- [iter 8] Import flow: file-based temp storage (UUID4 token → .xlsx na disku) místo session cookie (4KB limit!)
- [iter 9] Playwright strict mode: `.first()` pro locátory které matchují víc elementů (např. username v headeru)
- [iter 9] Interaction testy: regex `/\d+/` v assertions pro hodnoty které závisí na stavu DB (počty vlastníků apod.)
- [iter 9] pip-audit: 6 known vulns (starlette, python-multipart, pdfminer-six, pillow) — dokumentovat upgrade path v HANDOFF.md

## Patterns (co funguje dobře v tomto projektu)
- [iter 1] FastAPI Form() params místo asyncio.new_event_loop() hacku pro form data
- [iter 1] conftest.py: db_engine (StaticPool) → db_session → client (override get_db) → auth_client chain
- [iter 1] Playwright visual-check: loginOrRegister() helper s URL-based branching (registrace/login/dashboard)
- [iter 1] Tailwind CDN + HTMX + Jinja2 = rychlý prototyping bez build stepu
- [iter 2] Excel import: openpyxl load_workbook(read_only=True) + column mapping dict → flexibilní parsing
- [iter 2→8] Import preview: file-based temp storage (UUID token → .xlsx) — session cookie příliš malý pro reálná data
- [iter 8] Owner deduplication: group by birth_number/IČ first, pak by normalized name — testovat s reálnými daty!
- [iter 8] Test fixtures: openpyxl Workbook() → temp file → pytest fixture = spolehlivé testování import service
- [iter 2] Collapsible sections: `<details><summary>` element pro ownership history

## Known Issues (problémy které ještě nejsou vyřešené)
- [RESOLVED iter 7] Sidebar linky na neexistující routes — nyní všechny routes implementované
- [DEFERRED → HANDOFF] spustit.command + pripravit_usb.sh — nice-to-have
- [DEFERRED → HANDOFF] Test coverage measurement — nice-to-have
- [DEFERRED → HANDOFF] starlette 0.38.6 CVE — pinned by FastAPI 0.115.0, upgrade FastAPI to fix
- [DEFERRED → HANDOFF] Pokročilé filtry vlastníků — nice-to-have
- [RESOLVED iter 8] Import flow test — nyní 32 dedicated unit testů + route integration test
- [MINOR] Query.get() deprecation warning v testu — use Session.get()
- [MINOR] OwnerUnit.share vždy 1.0 — ownership fraction neextrahována z Excelu
- [MINOR] Loading indicator chybí při importu (770 rows trvá pár sekund)
- [MINOR] Temp files: cleanup v finally bloku, ale bez periodic cleanup pro crash scenarios

## Tech Notes (specifika tech stacku tohoto projektu)
- Python 3.9.6, FastAPI 0.115.0, SQLAlchemy 2.0.35, Starlette 0.38.6
- SQLite lokální DB (data/svj.db), in-memory pro testy
- Session auth přes Starlette SessionMiddleware (cookie-based, httpOnly, samesite=lax)
- Tailwind CDN (ne CLI build), custom.css pro overrides
- HTMX 1.9.10 pro inline editace
- Playwright + Chromium pro E2E testy a screenshoty
- Excel import: positional column indices (0-30), sheet "Vlastnici_SVJ"
- Owner model: owner_type = "physical"/"legal" (ne "fyzická"/"právnická")
- Unit model: unit_number = Integer (parsed from "1098/X" → X)
- Birth numbers (RČ): masked in UI, excluded from search
- Import temp files: data/uploads/_import_temp/{uuid4}.xlsx
