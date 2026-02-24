# ARCHITECTURE.md – SVJ Správa v2.0

## Tech Stack

| Vrstva | Technologie | Verze |
|--------|-------------|-------|
| Backend | FastAPI + SQLAlchemy ORM + SQLite | Python 3.9+ |
| Frontend | Jinja2 + HTMX + Tailwind CSS (CDN) | |
| Dokumenty | openpyxl, docxtpl, pdfplumber | |
| Email | SMTP s TLS | |
| PDF | LibreOffice (volitelné) | |
| Server | Uvicorn | |
| Autentizace | bcrypt, session cookie | |
| Testing | pytest, playwright | |

## Architektura

```
app/
├── main.py              # FastAPI app, mount static, include routers, startup events
├── config.py            # Pydantic Settings (.env)
├── database.py          # SQLAlchemy engine + session (SQLite)
├── auth.py              # Auth dependencies (get_current_user, require_role)
├── models/              # SQLAlchemy ORM modely
│   ├── __init__.py
│   ├── user.py          # User (auth)
│   ├── owner.py         # Owner, Unit, OwnerUnit, Proxy
│   ├── voting.py        # Voting, VotingItem, Ballot, BallotVote
│   ├── tax.py           # TaxSession, TaxDocument, TaxDistribution
│   ├── sync.py          # SyncSession, SyncRecord
│   ├── common.py        # EmailLog, ImportLog, AuditLog, Notification
│   └── administration.py # SvjInfo, SvjAddress, BoardMember, AutoBackupConfig
├── routers/             # FastAPI routers
│   ├── __init__.py
│   ├── auth.py          # /login, /logout, /registrace
│   ├── dashboard.py     # GET /
│   ├── owners.py        # /vlastnici
│   ├── units.py         # /jednotky
│   ├── voting.py        # /hlasovani
│   ├── tax.py           # /dane
│   ├── sync.py          # /synchronizace
│   ├── administration.py # /sprava
│   ├── settings_page.py # /nastaveni
│   ├── search.py        # /hledani
│   └── notifications.py # /notifikace
├── services/            # Business logika
│   ├── __init__.py
│   ├── excel_import.py
│   ├── excel_export.py
│   ├── word_parser.py
│   ├── pdf_generator.py
│   ├── pdf_extractor.py
│   ├── owner_matcher.py
│   ├── voting_import.py
│   ├── csv_comparator.py
│   ├── owner_exchange.py
│   ├── backup_service.py
│   ├── data_export.py
│   ├── email_service.py
│   └── audit_service.py
├── templates/           # Jinja2
│   ├── base.html
│   ├── login.html
│   ├── register.html
│   ├── dashboard.html
│   ├── settings.html
│   ├── search.html
│   ├── owners/
│   ├── units/
│   ├── voting/
│   ├── tax/
│   ├── sync/
│   ├── administration/
│   └── partials/
└── static/
    ├── css/custom.css
    └── js/app.js
data/
├── svj.db
├── uploads/
├── generated/
└── backups/
```

## Feature bloky (10 bloků, 5 fází)

### Fáze 1: Základ + Evidence
| # | Blok | Obsah |
|---|------|-------|
| 1 | Projekt setup + Datový model + Dashboard | FastAPI init, všechny DB modely, autentizace, base layout, dashboard, dark mode, search, klávesové zkratky, lokalizace |
| 2 | Evidence vlastníků | CRUD vlastníků, Excel import/export, filtrační bubliny, inline editace, back URL |
| 3 | Evidence jednotek | CRUD jednotek, prokliky vlastník↔jednotka, inline editace |

### Fáze 2: Hlasování
| # | Blok | Obsah |
|---|------|-------|
| 4 | Hlasování — vytvoření, body, lístky | Vytvoření hlasování, .docx šablona, body, PDF generování, stavy |
| 5 | Hlasování — zpracování, import, výsledky | Zpracování lístků, hromadné operace, Excel import, kvórum |

### Fáze 3: Daně + Sync
| # | Blok | Obsah |
|---|------|-------|
| 6 | Rozúčtování příjmů (Daně) | PDF upload, extrakce jmen, fuzzy matching, email |
| 7 | Kontrola vlastníků (Synchronizace) | CSV upload, porovnání, selektivní aktualizace, výměna |

### Fáze 4: Administrace
| # | Blok | Obsah |
|---|------|-------|
| 8 | Administrace — info, členové, zálohy | SVJ info, výbor, zálohy, obnova, uživatelé, audit, notifikace |
| 9 | Administrace — smazání, export, hromadné | Smazání dat, export, hromadné úpravy, auto-zálohy, tisk |

### Fáze 5: Finalizace
| # | Blok | Obsah |
|---|------|-------|
| 10 | Nastavení + USB + Visual polish | Email log, USB deployment, vizuální polish |

## Key Decisions

- **SQLite** — single-user lokální app, žádný DB server
- **Session auth** — cookie-based, bcrypt pro hesla
- **HTMX** — inline editace bez custom JS AJAX
- **Tailwind CDN** — rychlý setup, custom.css pro overrides
- **Playwright** — E2E testy + vizuální screenshoty + interaction testy
- **TDD** — test: → feat: → refactor: → style: commit flow
