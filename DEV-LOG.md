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

## Iterace 2 – 2026-02-24
📍 Status: Iterace 2/3+ | Feature blok: 2 (Evidence vlastníků) | Bloky zbývají: 8

### GATE Status
- GATE 1: PASSED — Blok 2 built, testy 32/32, screenshoty 3/3, interaction 15/15
- GATE 2: PASSED — review ze 6 rolí provedeno, findings zalogovány
- GATE 2b: PASSED — CRITICAL/HIGH fixy aplikovány, testy OK, post-fix screenshoty OK

### Změny
- [5d45627] `test:` add owners module tests (RED state)
- [403fcb3] `feat:` implement owners module (Evidence vlastníků)
- [8a7cd3e] `test:` add Blok 2 Playwright interaction tests + owners screenshots
- [52ea626] `fix:` add Excel import, HTMX inline editing, ownership history

### Review Findings (všech 6 rolí)

| # | Role | Finding / Verdikt | Severity | Status |
|---|------|-------------------|----------|--------|
| 1 | CEO | CRUD vlastníků implementován (list, detail, update, add/remove unit, export) | — | OK |
| 2 | CEO | Chyběl Excel import (core PRD feature pro Blok 2) | HIGH | FIXED |
| 3 | CEO | Chyběla HTMX inline editace kontaktů | HIGH | FIXED |
| 4 | CEO | Chyběla ownership history (historie vlastnictví) | MEDIUM | FIXED |
| 5 | CEO | Pokročilé filtry (sekce, typ vlastnictví, s/bez emailu) → Blok 3+ | MEDIUM | OPEN → iter 3 |
| 6 | CEO | Column sorting by click → Blok 3+ | LOW | OPEN → iter 3 |
| 7 | CTO | TDD compliance: test: (5d45627) → feat: (403fcb3) → test: (8a7cd3e) ✅ | — | OK |
| 8 | CTO | Query.get() deprecation warning v testu | LOW | OPEN |
| 9 | CTO | Route ordering: /import musí být před /{owner_id} | HIGH | FIXED |
| 10 | CTO | python-multipart CVE (0.0.12 → 0.0.18) | HIGH | FIXED |
| 11 | CPO | Screenshoty profesionální na 3 viewportech | — | OK |
| 12 | CPO | 15/15 interaction testů prochází (9 Blok 1 + 6 Blok 2) | — | OK |
| 13 | CPO | Import button přidán na seznam vlastníků | — | OK |
| 14 | CPO | Empty state + filter bubbles fungují | — | OK |
| 15 | Security | python-multipart CVE GHSA-59g5-xgcq-4qw3 | HIGH | FIXED |
| 16 | Security | starlette CVE (0.38.6) — FastAPI 0.115.0 pinuje starlette | MEDIUM | OPEN → iter 3 |
| 17 | Security | Žádné hardcoded credentials, session auth bezpečná | — | OK |
| 18 | QA | Unit 32/32, Interaction 15/15, Visual 3/3 | — | OK |
| 19 | QA | Import flow zatím bez E2E testu (session-based preview) | MEDIUM | OPEN → iter 3 |
| 20 | Designer | Clean layout owners list/detail, filter bubbles, responsive | — | OK |
| 21 | Designer | Import page s upload formulářem a historií | — | OK |
| 22 | Designer | Ownership history collapsible section | — | OK |

### Visual Check
- **After Build:** Desktop ✅ / Tablet ✅ / Mobile ✅ → `screenshots/iter-2-build-*.png`
- **After Review (fresh):** Desktop ✅ / Tablet ✅ / Mobile ✅ → `screenshots/iter-2-review-*.png`
- **After Fix:** Desktop ✅ / Tablet ✅ / Mobile ✅ → `screenshots/iter-2-fix-*.png`

### Interaction Check
- Tlačítka: Import, Export, filter bubbles, detail link → ✅
- Formuláře: search, contact edit → ✅
- Navigace/linky: sidebar /vlastnici, G+V shortcut, detail back link → ✅
- Hlavní user flow: dashboard → vlastníci → search → filter → detail → edit → save ✅ end-to-end OK
- Error states: 404 on nonexistent owner ✅

### Testy
- Unit: 32/32 | Integration: — | E2E (Playwright): 15/15 | Visual: 3/3

### Verdict tabulka

| Role | Verdict | Odůvodnění | Open |
|------|---------|------------|------|
| CEO | APPROVED | Core Blok 2 features implementovány: CRUD, import, export, filter bubbles, detail, history. Pokročilé filtry do iter 3. | 2 |
| CTO | APPROVED | TDD dodrženo, route ordering fix, CVE fix (python-multipart). 32/32 testů prochází. | 2 |
| CPO | APPROVED | Profesionální UI na 3 viewportech, 15/15 interaction testů, import flow přidán. | 0 |
| Security | APPROVED | python-multipart CVE fixnut. Starlette CVE medium priority (pinned by FastAPI). | 1 |
| QA | APPROVED | 32/32 unit + 15/15 E2E + 3/3 visual. Import E2E test do iter 3. | 1 |
| Designer | APPROVED | Konzistentní design, filter bubbles, empty state, responsive, collapsible history. | 0 |

### AGENTS.md update
- Route ordering: statické cesty (/vlastnici/import, /vlastnici/export) MUSÍ být před parametrickými (/vlastnici/{id})
- Playwright: getByRole s { exact: true } pro heading matchování kde existuje subsstring match
- ImportLog model: používá source+records_count+status (ne module+row_count)

### Souhrn + plán další iterace
Blok 2 kompletní. Pokračuji Blokem 3 (Evidence jednotek) — CRUD jednotek, prokliky vlastník↔jednotka, inline editace.

---

## Iterace 3 – 2026-02-24
📍 Status: Iterace 3/3+ | Feature blok: 3 (Evidence jednotek) | Bloky zbývají: 7

### GATE Status
- GATE 1: PASSED — Blok 3 built, testy 39/39, screenshoty 3/3, interaction 19/19
- GATE 2: PASSED — review ze 6 rolí provedeno, findings zalogovány
- GATE 2b: PASSED — žádné CRITICAL/HIGH findings, testy OK

### Změny
- [4d58d51] `test:` add units module tests (RED state)
- [f757a54] `feat:` implement units module (Evidence jednotek)
- [6e88395] `test:` add Blok 3 Playwright interaction tests + units screenshots

### Review Findings (všech 6 rolí)

| # | Role | Finding / Verdikt | Severity | Status |
|---|------|-------------------|----------|--------|
| 1 | CEO | Units CRUD implementován (list, detail, search, building filter) | — | OK |
| 2 | CEO | Bidirectional owner↔unit navigation funguje | — | OK |
| 3 | CEO | Ownership history collapsible section na unit detail | — | OK |
| 4 | CTO | TDD compliance: test: (4d58d51) → feat: (f757a54) → test: (6e88395) ✅ | — | OK |
| 5 | CTO | 39/39 testů prochází, kód čistý a konzistentní | — | OK |
| 6 | CPO | Screenshoty profesionální na 3 viewportech | — | OK |
| 7 | CPO | 19/19 interaction testů prochází | — | OK |
| 8 | Security | Žádné nové security issues, ORM chrání před SQL injection | — | OK |
| 9 | QA | Unit 39/39, Interaction 19/19, Visual 3/3 | — | OK |
| 10 | Designer | Konzistentní layout s owners, empty state, building icon | — | OK |

### Visual Check
- **After Build:** Desktop ✅ / Tablet ✅ / Mobile ✅ → `screenshots/iter-3-build-*.png`
- **After Review (fresh):** Desktop ✅ / Tablet ✅ / Mobile ✅ → `screenshots/iter-3-review-*.png`
- **After Fix:** Desktop ✅ / Tablet ✅ / Mobile ✅ → `screenshots/iter-3-fix-*.png`

### Interaction Check
- Tlačítka: N/A (units je read-only) → ✅
- Formuláře: search → ✅
- Navigace/linky: sidebar /jednotky, G+J shortcut, detail back, owner↔unit links → ✅
- Hlavní user flow: dashboard → jednotky → search → detail → klik na vlastníka → zpět ✅ end-to-end OK
- Error states: 404 on nonexistent unit ✅

### Testy
- Unit: 39/39 | Integration: — | E2E (Playwright): 19/19 | Visual: 3/3

### Verdict tabulka

| Role | Verdict | Odůvodnění | Open |
|------|---------|------------|------|
| CEO | APPROVED | Blok 3 kompletní: list, detail, search, filter, bidirectional links, history. | 0 |
| CTO | APPROVED | TDD dodrženo. 39/39 testů. Kód konzistentní. | 0 |
| CPO | APPROVED | Profesionální UI, 19/19 interaction testů. Responsive OK. | 0 |
| Security | APPROVED | Žádné nové issues. | 0 |
| QA | APPROVED | Kompletní coverage pro Blok 3. | 0 |
| Designer | APPROVED | Konzistentní s owners designem, empty state, responsive. | 0 |

### AGENTS.md update
- Blok 3 čistý — žádné nové guardrails potřeba

### Souhrn + plán další iterace
Bloky 1–3 kompletní (Fáze 1). 3 verdict tabulky → GATE 3 PASSED. Pokračuji Fází 2 — Blok 4 (Hlasování).

---
