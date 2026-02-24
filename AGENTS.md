# AGENTS.md – Operational Learnings

## Guardrails (přidávej když narazíš na problém)
- [iter 1] Python 3.9: NEPOUŽÍVAT `X | None` syntax → použít `Optional[X]` z typing
- [iter 1] SQLite in-memory testy: VŽDY použít `StaticPool` v engine, jinak každá connection = jiná DB
- [iter 1] Playwright: po `pkill uvicorn` ČEKAT 2s než se port uvolní, jinak "address already in use"
- [iter 1] Playwright: `waitForURL('/')` nefunguje spolehlivě po redirect chain → použít `waitForURL('**/')` nebo `waitForLoadState`
- [iter 1] TemplateResponse: NOVÝ API od Starlette 0.38+ → `TemplateResponse(request, name, ctx)` místo `TemplateResponse(name, {"request": request, ...})`
- [iter 1] Playwright locators: `text=Vlastníků` matchuje i "Import vlastníků" → použít `{ exact: true }` nebo `getByRole`

## Patterns (co funguje dobře v tomto projektu)
- [iter 1] FastAPI Form() params místo asyncio.new_event_loop() hacku pro form data
- [iter 1] conftest.py: db_engine (StaticPool) → db_session → client (override get_db) → auth_client chain
- [iter 1] Playwright visual-check: loginOrRegister() helper s URL-based branching (registrace/login/dashboard)
- [iter 1] Tailwind CDN + HTMX + Jinja2 = rychlý prototyping bez build stepu

## Known Issues (problémy které ještě nejsou vyřešené)
- spustit.command + pripravit_usb.sh ještě nevytvořeny (plán: Blok 10)
- Test coverage measurement neprobíhá (plán: iter 2)
- Sidebar linky na neexistující routes (vlastnici, jednotky, ...) → budou v Bloku 2–3

## Tech Notes (specifika tech stacku tohoto projektu)
- Python 3.9.6, FastAPI 0.115.0, SQLAlchemy 2.0.35, Starlette 0.38.6
- SQLite lokální DB (data/svj.db), in-memory pro testy
- Session auth přes Starlette SessionMiddleware (cookie-based, httpOnly, samesite=lax)
- Tailwind CDN (ne CLI build), custom.css pro overrides
- HTMX 1.9.10 pro inline editace
- Playwright + Chromium pro E2E testy a screenshoty
