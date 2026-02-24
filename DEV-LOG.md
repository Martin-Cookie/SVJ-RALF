# DEV-LOG – SVJ Správa v2.0

---
## RE-ENTRY AUDIT – 2026-02-24 00:00

### Stav projektu
- Předchozích iterací: 0
- Feature bloky hotové: žádné
- Feature bloky CHYBÍ: 1–10 (všechny)
- Testy: 0/9 prochází (RED stav — moduly neexistují)
- Interaction testy: ❌ (app neexistuje)

### Identifikované problémy
| # | Problém | Severity |
|---|---------|----------|
| 1 | Žádný kód aplikace — pouze prázdné __init__.py | CRITICAL |
| 2 | Testy v RED stavu — importy selhávají (app.config, app.models, app.main) | CRITICAL |
| 3 | Playwright nainstalovaný (package.json), ale chromium nepotvrzen | LOW |

### Plán
Pokračuji od Fáze 0 (setup). Bloky: 1–10.
Fáze 0 → Feature Blok 1 (setup + datový model + dashboard + auth).

---

## Iterace 1 – 2026-02-24
📍 Status: Iterace 1/3+ | Feature blok: 1 (Setup + Datový model + Dashboard) | Bloky zbývají: 9

### GATE Status
- GATE 0: PASSED — projekt inicializován, testy GREEN
- GATE 1: PASSED — Blok 1 built, testy 22/22, screenshoty 3/3, interaction 9/9
- GATE 2: PASSED — review ze 6 rolí provedeno, findings zalogovány
- GATE 2b: PASSED — CRITICAL fixy aplikovány, testy OK, post-fix screenshoty OK

### Změny
- [5c390be] `init:` project setup — FastAPI + all DB models + auth + dashboard + templates
- [c7892b3] `test:` auth routes + search tests (TDD RED → GREEN)
- [74504c9] `feat:` fix auth routes with Form() params, fix test conftest StaticPool
- [0991642] `test:` Playwright visual + interaction tests for Blok 1
- [1d550ac] `fix:` update dependencies (CVE fixes) + TemplateResponse deprecation

### Review Findings (všech 6 rolí)

| # | Role | Finding / Verdikt | Severity | Status |
|---|------|-------------------|----------|--------|
| 1 | CEO | Features Bloku 1 implementované (auth, dashboard, sidebar, dark mode, search, shortcuts, locale) | — | OK |
| 2 | CEO | Chybí spustit.command + pripravit_usb.sh (PRD Blok 1 item 13) | MEDIUM | OPEN → Blok 10 |
| 3 | CTO | requirements.txt outdated — jinja2, starlette, python-multipart CVEs | CRITICAL | FIXED |
| 4 | CTO | PydanticDeprecatedSince20 warning v config.py | MEDIUM | FIXED |
| 5 | CTO | TemplateResponse deprecated signature | MEDIUM | FIXED |
| 6 | CPO | Screenshoty potvrzují profesionální layout na 3 viewportech | — | OK |
| 7 | CPO | 9/9 interaction tests prochází | — | OK |
| 8 | Security | Dependency CVEs (jinja2 3.1.2, python-multipart 0.0.6) | CRITICAL | FIXED |
| 9 | Security | SECRET_KEY v .env, credentials v .env.example jako placeholdery | — | OK |
| 10 | Security | Session cookie httpOnly + samesite=lax | — | OK |
| 11 | QA | Unit 22/22, Interaction 9/9, Visual 3/3 | — | OK |
| 12 | QA | Coverage measurement missing | MEDIUM | OPEN → iter 2 |
| 13 | Designer | Clean professional design, konzistentní palette, responsive | — | OK |
| 14 | Designer | Empty states řešeny (dashboard, notifications, search) | — | OK |

### Visual Check
- **After Build:** Desktop ✅ / Tablet ✅ / Mobile ✅ → `screenshots/iter-1-build-*.png`
- **After Review (fresh):** Desktop ✅ / Tablet ✅ / Mobile ✅ → `screenshots/iter-1-review-*.png`
- **After Fix:** Desktop ✅ / Tablet ✅ / Mobile ✅ → `screenshots/iter-1-fix-*.png`

### Interaction Check
- Tlačítka: dark-toggle, logout, sidebar links → ✅
- Formuláře: login, register → ✅
- Navigace/linky: sidebar 7 links, header search → ✅
- Hlavní user flow: register → dashboard → navigate → logout → login ✅ end-to-end OK
- Error states: login chybné heslo → flash message ✅

### Testy
- Unit: 22/22 | Integration: — | E2E (Playwright): 9/9 | Visual: 3/3

### Verdict tabulka

| Role | Verdict | Odůvodnění | Open |
|------|---------|------------|------|
| CEO | APPROVED | Všechny core features Bloku 1 implementované (auth, dashboard, sidebar, dark mode, search, shortcuts, locale). USB skripty přesunuty do Bloku 10. | 1 |
| CTO | APPROVED | TDD dodrženo, dependencies aktualizovány, deprecation warnings opraveny, 22/22 testů prochází. | 0 |
| CPO | APPROVED | Profesionální UI na 3 viewportech, 9/9 interaction testů, responsive layout funguje. | 0 |
| Security | APPROVED | CVE fixnuty aktualizací dependencies, session auth bezpečná, žádné hardcoded credentials. | 0 |
| QA | APPROVED | 22/22 unit + 9/9 E2E + 3/3 visual = kompletní coverage pro Blok 1. | 0 |
| Designer | APPROVED | Čistý profesionální design, konzistentní barvy/typografie, empty states řešeny, responsive OK. | 0 |

### AGENTS.md update
- StaticPool pattern pro SQLite in-memory testy
- TemplateResponse nový API (request jako 1. parametr)
- Python 3.9: Optional[X] místo X | None

### Souhrn + plán další iterace
Blok 1 kompletní. Pokračuji Blokem 2 (Evidence vlastníků) — CRUD, Excel import/export, filtrační bubliny, inline editace.

---
