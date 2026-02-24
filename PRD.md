# PRD – SVJ Správa v2.0

## Přehled projektu

**Název:** SVJ Správa
**Účel:** Webová aplikace pro automatizaci správy SVJ (Společenství vlastníků jednotek). Spravuje evidenci vlastníků a jednotek, hlasování per rollam, rozúčtování daní, synchronizaci dat s externími zdroji a administraci SVJ.
**Cílový uživatel:** Předseda/výbor SVJ, správce domu. Jeden uživatel, bez autentizace.
**Platforma:** Lokální webová aplikace (localhost), možnost spuštění z USB na jiném Macu.

---

## Tech Stack

| Vrstva | Technologie | Poznámka |
|--------|-------------|----------|
| Backend | FastAPI + SQLAlchemy ORM + SQLite | Python 3.9+ |
| Frontend | Jinja2 šablony + HTMX + Tailwind CSS | Tailwind přes CDN (nebo CLI pro produkci) |
| Dokumenty | openpyxl (Excel), docxtpl (Word), pdfplumber (PDF), Tesseract (OCR) | |
| Email | SMTP s TLS | |
| PDF generování | LibreOffice (volitelné) | Konverze .docx → .pdf |
| Server | Uvicorn | `uvicorn app.main:app --reload --port 8000` |

---

## Konfigurace (.env)

```env
DATABASE_PATH=data/svj.db
UPLOAD_DIR=data/uploads
GENERATED_DIR=data/generated
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
SMTP_FROM_EMAIL=svj@example.com
SMTP_FROM_NAME=SVJ
LIBREOFFICE_PATH=/Applications/LibreOffice.app/Contents/MacOS/soffice
```

---

## Adresářová struktura

```
app/
├── main.py                    # FastAPI aplikace, mount static, include routers
├── config.py                  # Pydantic Settings (čte .env)
├── database.py                # SQLAlchemy engine + session (SQLite)
├── models/                    # SQLAlchemy modely
│   ├── owner.py               # Owner, Unit, OwnerUnit, Proxy
│   ├── voting.py              # Voting, VotingItem, Ballot, BallotVote
│   ├── tax.py                 # TaxSession, TaxDocument, TaxDistribution
│   ├── sync.py                # SyncSession, SyncRecord
│   ├── common.py              # EmailLog, ImportLog
│   └── administration.py      # SvjInfo, SvjAddress, BoardMember
├── routers/                   # FastAPI routers (HTTP endpointy)
│   ├── dashboard.py           # GET /
│   ├── owners.py              # /vlastnici
│   ├── units.py               # /jednotky
│   ├── voting.py              # /hlasovani
│   ├── tax.py                 # /dane
│   ├── sync.py                # /synchronizace
│   ├── administration.py      # /sprava
│   └── settings_page.py       # /nastaveni
├── services/                  # Business logika (čistá, testovatelná)
│   ├── excel_import.py        # Import z 31-sloupcového Excelu
│   ├── excel_export.py        # Export do Excelu
│   ├── word_parser.py         # Extrakce bodů z .docx šablony
│   ├── pdf_generator.py       # Generování PDF lístků
│   ├── pdf_extractor.py       # Extrakce textu z PDF
│   ├── owner_matcher.py       # Fuzzy párování jmen
│   ├── voting_import.py       # Import výsledků hlasování z Excelu
│   ├── csv_comparator.py      # Porovnání CSV vs DB
│   ├── owner_exchange.py      # Výměna vlastníků při synchronizaci
│   ├── backup_service.py      # Zálohování a obnova dat (ZIP)
│   ├── data_export.py         # Export dat do Excel/CSV
│   └── email_service.py       # SMTP odesílání emailů
├── templates/                 # Jinja2 šablony
│   ├── base.html              # Layout se sidebar navigací
│   ├── dashboard.html
│   ├── settings.html
│   ├── owners/                # Šablony pro vlastníky
│   ├── units/                 # Šablony pro jednotky
│   ├── voting/                # Šablony pro hlasování
│   ├── tax/                   # Šablony pro daně
│   ├── sync/                  # Šablony pro synchronizaci
│   ├── administration/        # Šablony pro administraci
│   └── partials/              # HTMX partial komponenty
└── static/
    ├── css/custom.css
    └── js/app.js
data/
├── svj.db                     # SQLite databáze
├── uploads/                   # Nahrané soubory
├── generated/                 # Generované dokumenty
└── backups/                   # ZIP zálohy
```

---

## Datový model

### Owner (Vlastník)
- `id`, `first_name`, `last_name`, `title_before`, `title_after`
- `birth_number` (RČ), `ico` (IČ), `owner_type` (fyzická/právnická)
- `email`, `phone`
- `perm_street`, `perm_city`, `perm_zip` (trvalá adresa)
- `corr_street`, `corr_city`, `corr_zip` (korespondenční adresa)
- `is_active` (soft delete)
- Property `display_name`: formát „příjmení jméno" s titulem

### Unit (Jednotka)
- `id`, `unit_number` (INTEGER), `building`, `section`, `space_type`
- `address`, `land_registry_number` (LV)
- `room_count`, `area` (plocha), `share_scd` (podíl SČD)

### OwnerUnit (Vazba vlastník-jednotka)
- `id`, `owner_id`, `unit_id`
- `ownership_type` (SJM, VL, SJVL, Výhradní, Podílové, Neuvedeno)
- `ownership_share` (podíl vlastnictví)
- `voting_weight` (hlasovací váha)
- `valid_from`, `valid_to` (NULL = aktuálně platný, datum = historický)

### Proxy (Plná moc)
- `id`, `voting_id`, `grantor_id`, `grantee_id`

### Voting (Hlasování)
- `id`, `name`, `status` (koncept/aktivní/uzavřené/zrušené)
- `start_date`, `end_date`, `quorum`
- `template_path` (cesta k .docx šabloně)

### VotingItem (Bod hlasování)
- `id`, `voting_id`, `number`, `text`

### Ballot (Hlasovací lístek)
- `id`, `voting_id`, `owner_id`, `unit_id`
- `status` (vygenerován/odesláno/zpracován/neodevzdán)
- `pdf_path`

### BallotVote (Hlas)
- `id`, `ballot_id`, `voting_item_id`
- `vote` (PRO/PROTI/Zdržel se)

### TaxSession, TaxDocument, TaxDistribution
- Session → Documents (PDF soubory) → Distribution (párování na vlastníky)

### SyncSession, SyncRecord
- Session → Records (porovnání CSV vs DB, cascade delete)

### SvjInfo, SvjAddress
- Info o SVJ (název, typ budovy, celkový počet podílů)
- Adresy SVJ (více adres)

### BoardMember
- Člen výboru nebo kontrolního orgánu
- `group` (board/control), `name`, `role`, `email`, `phone`

### EmailLog, ImportLog
- Systémové logy (odesílání emailů, importy, změny)

### AuditLog
- `id`, `user_id`, `action` (create/update/delete), `model_name`, `record_id`
- `field_name`, `old_value`, `new_value`, `timestamp`
- Automaticky zapisován při každé změně dat

### Notification
- `id`, `user_id`, `type` (voting_created/voting_status/import_done/sync_done/backup_done)
- `message`, `link` (URL), `is_read`, `created_at`

### AutoBackupConfig
- `id`, `frequency` (daily/weekly), `time` (HH:MM), `max_backups` (kolik uchovat)
- `last_run`, `next_run`, `is_enabled`

---

## Autentizace a role

### Přihlášení
- Login stránka (`/login`) — uživatelské jméno + heslo
- Hesla hashovaná (bcrypt)
- Session-based autentizace (cookie)
- Po přihlášení redirect na dashboard
- Odhlášení (`/logout`) — smazání session

### První spuštění
- Při prvním spuštění (žádný uživatel v DB) se zobrazí registrační formulář
- První registrovaný uživatel automaticky dostane roli **admin**
- Další uživatele vytváří pouze admin

### Role

| Oprávnění | Čtenář | Editor | Admin |
|-----------|--------|--------|-------|
| Prohlížení všech dat (seznamy, detaily, dashboard) | ✅ | ✅ | ✅ |
| Vyhledávání, filtrování, řazení | ✅ | ✅ | ✅ |
| Export dat (Excel, CSV) | ✅ | ✅ | ✅ |
| Přidávání/editace vlastníků a jednotek | ❌ | ✅ | ✅ |
| Import dat (Excel, CSV) | ❌ | ✅ | ✅ |
| Zpracování hlasování (zadávání hlasů) | ❌ | ✅ | ✅ |
| Import výsledků hlasování | ❌ | ✅ | ✅ |
| Synchronizace — aktualizace a výměna vlastníků | ❌ | ✅ | ✅ |
| Rozúčtování — párování, odesílání emailů | ❌ | ✅ | ✅ |
| Hromadné úpravy | ❌ | ✅ | ✅ |
| Vytváření a správa hlasování (nové, body, generování, mazání) | ❌ | ❌ | ✅ |
| Administrace SVJ (info, adresy, členové výboru) | ❌ | ❌ | ✅ |
| Zálohování a obnova dat | ❌ | ❌ | ✅ |
| Mazání dat (kategorie, cascade) | ❌ | ❌ | ✅ |
| Správa uživatelů (vytvoření, změna role, reset hesla, smazání) | ❌ | ❌ | ✅ |

### Datový model — User
- `id`, `username` (unikátní), `password_hash` (bcrypt)
- `role` (enum: admin / editor / reader)
- `display_name` (zobrazované jméno)
- `is_active` (soft delete)
- `created_at`, `last_login`

### UI chování dle role
- Tlačítka a akce, na které uživatel nemá oprávnění, se **nezobrazují** (ne disabled, ale skryté)
- Při pokusu o přímý přístup na chráněnou URL → redirect na dashboard s flash message „Nemáte oprávnění"
- V sidebar se zobrazují pouze sekce, ke kterým má uživatel přístup
- V hlavičce aplikace: jméno přihlášeného uživatele + role + odkaz na odhlášení

### Správa uživatelů (pouze admin)
- Stránka `/sprava/uzivatele` v rámci administrace
- Seznam uživatelů (jméno, login, role, poslední přihlášení, stav)
- Vytvoření nového uživatele (username, heslo, role, display_name)
- Změna role existujícího uživatele
- Reset hesla
- Deaktivace/aktivace uživatele (soft delete)
- Admin nemůže smazat/deaktivovat sám sebe
- Minimálně jeden admin musí vždy existovat

---

## Globální UI pravidla

### Layout
- **Sidebar navigace** — fixní levý panel (w-44) s ikonami a sekcemi: Dashboard, Vlastníci, Jednotky, Hlasování, Daně, Synchronizace, Správa, Nastavení
- **Flex layout** — `height:calc(100vh - 48px)` pro stránky kde scrolluje jen tělo tabulky
- **Responsive** — sidebar se na mobilech skryje, tabulky horizontálně scrollovatelné

### Společné UI vzory
- **Filtrační bubliny** — klikací filtry nad tabulkou s počty záznamů, dynamicky roztažené na celou šířku (flex-1), aktivní bublina zvýrazněna
- **Back URL řetěz** — zachování filtrů při navigaci seznam → detail → zpět. Parametr `back` propagován přes bubliny, hledání, řazení, HTMX a detailové odkazy
- **Sticky hlavičky** — záhlaví tabulek zůstává viditelné při scrollu
- **HTMX inline editace** — formuláře se přepínají bez reloadu stránky
- **Řazení sloupců** — kliknutí na hlavičku → řazení vzestupně/sestupně
- **Vyhledávání** — full-text search nad relevantními poli
- **Dvousloupcový layout** — formulář vlevo + historie vpravo (import, kontrola)
- **Potvrzovací dialogy** — u destruktivních akcí (smazání)
- **Flash messages** — úspěch (zelená), chyba (červená), info (modrá)

### Design principy
- Profesionální, čistý design — NE generický AI look
- Konzistentní color palette, typografie, spacing
- Všechny states: loading, empty, error, success
- WCAG AA accessibility
- **Tmavý režim (dark mode)** — přepínač v hlavičce, preference uložena v cookie/localStorage, Tailwind `dark:` třídy

### Audit log
- Každá změna dat (vytvoření, editace, smazání) se zaloguje s: kdo (user), co (model + id + pole), kdy (timestamp), stará hodnota → nová hodnota
- Model `AuditLog`: `user_id`, `action` (create/update/delete), `model_name`, `record_id`, `field_name`, `old_value`, `new_value`, `timestamp`
- Prohlížení audit logu v administraci (`/sprava/audit`) — filtrování dle uživatele, modelu, akce, datumu
- Pouze admin vidí audit log

### Notifikace v aplikaci
- Zvonečkový indikátor v hlavičce s počtem nepřečtených
- Notifikace při: nové hlasování vytvořeno, hlasování změnilo stav, import dokončen, synchronizace provedena, záloha vytvořena
- Model `Notification`: `user_id`, `type`, `message`, `link` (URL kam vede), `is_read`, `created_at`
- Dropdown s posledními notifikacemi, odkaz „Zobrazit vše" → `/notifikace`
- Označení jako přečtené (jednotlivě i hromadně)

### Automatické zálohy
- Nastavení v administraci: frekvence (denní/týdenní), čas spuštění, počet uchovávaných záloh
- Spouštěno při startu aplikace přes background task (FastAPI `on_startup` + asyncio)
- Kontrola při každém requestu zda je čas na zálohu (alternativa k cronu pro lokální app)
- Zálohy ukládány do `data/backups/auto/` s timestampem
- Automatické mazání starých záloh dle nastaveného limitu
- Stav automatických záloh viditelný v administraci (poslední záloha, další plánovaná)

### Fulltextové hledání napříč moduly
- Globální search bar v hlavičce (klávesová zkratka `/` nebo `Ctrl+K`)
- Hledá napříč: vlastníci (jméno, email, RČ/IČ), jednotky (číslo, adresa), hlasování (název), synchronizace
- Výsledky seskupené dle modulu s prokliky
- HTMX live search (debounce 300ms)
- Endpoint `GET /hledani?q=...`

### Klávesové zkratky
- `/` nebo `Ctrl+K` — focus na globální hledání
- `G` + `D` — přejít na dashboard
- `G` + `V` — přejít na vlastníky
- `G` + `J` — přejít na jednotky
- `G` + `H` — přejít na hlasování
- `Escape` — zavřít modal/dropdown/search
- `?` — zobrazit nápovědu klávesových zkratek (modal)
- Implementováno v `app.js`, nesmí kolidovat s inputy (deaktivace při focusu na input/textarea)

### Tisk sestav
- Tlačítko „Tisk" / „Export PDF" na klíčových stránkách:
  - Seznam vlastníků (filtrovaný pohled)
  - Detail vlastníka
  - Výsledky hlasování (souhrn + detailní po bodech)
  - Porovnání synchronizace
- CSS print stylesheet (`@media print`) — skryje sidebar, navigaci, tlačítka; optimalizuje layout pro A4
- Alternativně generování PDF přes server (WeasyPrint nebo LibreOffice)

### Česká lokalizace
- Formát data: `DD.MM.YYYY` (ne ISO, ne americký)
- Formát času: `HH:MM` (24h)
- Čísla: mezera jako oddělovač tisíců, čárka jako desetinný oddělovač (1 234,56)
- Měna: Kč za číslem (1 234,56 Kč)
- Jinja2 filtry: `|datum`, `|cas`, `|cislo`, `|mena` pro konzistentní formátování
- Všechny texty v češtině (flash messages, labels, placeholders, error messages)

---

## FÁZE VÝVOJE

Projekt je rozdělen do 5 fází. Každá fáze obsahuje feature bloky pro RALF loop.

---

## FÁZE 1: Základ + Evidence (Feature bloky 1–3)

### Feature blok 1: Projekt setup + Datový model + Dashboard

**Cíl:** Funkční aplikace s databází, layoutem a dashboardem.

**Úkoly:**
1. Inicializace FastAPI projektu s konfigurací (Pydantic Settings, .env)
2. SQLAlchemy engine + session (SQLite)
3. VŠECHNY databázové modely (Owner, Unit, OwnerUnit, Proxy, Voting, VotingItem, Ballot, BallotVote, TaxSession, TaxDocument, TaxDistribution, SyncSession, SyncRecord, SvjInfo, SvjAddress, BoardMember, EmailLog, ImportLog, **User**)
4. Automatická migrace (vytvoření tabulek, přidání chybějících sloupců/indexů)
5. **Autentizace:**
   - Login stránka (`/login`) — username + heslo
   - Bcrypt hashování hesel
   - Session-based auth (cookie)
   - Middleware/dependency pro ověření přihlášení na všech chráněných cestách
   - Role-based access control (admin/editor/reader) — decorator/dependency pro kontrolu oprávnění
   - První spuštění: pokud žádný User v DB → registrační formulář → první user = admin
   - Odhlášení (`/logout`)
6. Base template (`base.html`) se sidebar navigací (w-44, fixní, ikony + sekce)
   - Sidebar zobrazuje pouze sekce dle role přihlášeného uživatele
   - Header: jméno uživatele + role + odhlášení
7. Dashboard (`GET /`) — přehled s klikacími bublinami (vlastníci, jednotky, hlasování) a modulovými kartami, vše dynamicky roztažené na šířku
8. Statické soubory (CSS, JS), Tailwind CDN
9. **Dark mode** — přepínač v hlavičce, Tailwind `dark:` třídy, preference v cookie
10. **Globální search bar** v hlavičce (`Ctrl+K`) — fulltextové hledání napříč moduly (HTMX live search)
11. **Klávesové zkratky** — navigace (`G+D`, `G+V`...), search (`/`, `Ctrl+K`), nápověda (`?`)
12. **Česká lokalizace** — Jinja2 filtry `|datum`, `|cas`, `|cislo`, `|mena`, český formát dat a čísel
13. `spustit.command` a `pripravit_usb.sh` pro USB nasazení

**User stories:**
- Uživatel otevře aplikaci poprvé → vidí registrační formulář → vytvoří admin účet
- Uživatel otevře aplikaci → vidí login → přihlásí se → vidí dashboard
- Čtenář nevidí tlačítka pro editaci, editor ano, admin vidí vše
- Uživatel spustí aplikaci → vidí dashboard s přehledem statistik
- Dashboard zobrazuje: počet vlastníků, jednotek, aktivních hlasování
- Bublina hlasování zobrazuje seznam aktivních/konceptových hlasování se stavem a názvem (truncate + tooltip)
- Sidebar umožňuje navigaci do všech modulů

**Akceptační kritéria:**
- Aplikace se spustí na `localhost:8000`
- Všechny tabulky se vytvoří v SQLite
- Dashboard zobrazuje statistiky (0 záznamů = empty state)
- Sidebar navigace funguje, aktivní sekce zvýrazněna

---

### Feature blok 2: Evidence vlastníků

**Cíl:** Kompletní CRUD pro vlastníky včetně importu z Excelu.

**Úkoly:**
1. Router `/vlastnici` se všemi endpointy (viz API sekce)
2. Seznam vlastníků s vyhledáváním (jméno, email, telefon, RČ, IČ, č. jednotky)
3. Filtrační bubliny: typ vlastníka (fyzická/právnická), sekce domu, typ vlastnictví (SJM, VL, SJVL, Výhradní, Podílové, Neuvedeno), kontakty (s/bez emailu, s/bez telefonu — rozdělené bubliny)
4. Řazení kliknutím na hlavičky sloupců (jméno, typ, email, telefon, podíl, jednotky, sekce)
5. Sticky hlavička tabulky
6. RČ/IČ viditelné v seznamu i detailu
7. Detail vlastníka:
   - Inline editace kontaktů (email, telefon) přes HTMX
   - Inline editace trvalé a korespondenční adresy přes HTMX
   - Správa přiřazených jednotek (přidat z dropdownu, odebrat s valid_to datem)
   - Sloupec Podíl % (podíl SČD / celkový počet podílů z administrace)
   - Souhrnný řádek Celkem (podíl SČD, podíl %, plocha)
   - Proklik na detail jednotky
   - Kolapsovatelná sekce „Historie vlastnictví" — předchozí jednotky s daty od/do
8. Import z Excelu (31 sloupců, sheet `Vlastnici_SVJ`):
   - Upload souboru → náhled dat s potvrzením
   - Service `excel_import.py` parsuje 31 sloupců
   - Vytvoření Owner + Unit + OwnerUnit záznamů
   - Historie importů s možností smazání (cascade smaže vlastníky, jednotky i přiřazení)
9. Export vlastníků do Excelu
10. Porovnání podílů: prohlášení vlastníka vs evidence s barevným rozdílem a %
11. Back URL řetěz: zachování filtrů při navigaci seznam → detail → detail → zpět

**User stories:**
- Uživatel nahraje Excel → vidí náhled → potvrdí → vlastníci jsou v systému
- Uživatel vyhledá vlastníka podle jména → klikne → vidí detail
- V detailu klikne na email → edituje inline → uloží bez reloadu
- Uživatel přidá jednotku vlastníkovi z dropdownu
- Uživatel smaže import → smažou se všechna navázaná data

**Akceptační kritéria:**
- Import 31-sloupcového Excelu funguje end-to-end
- Vyhledávání filtruje v reálném čase
- Filtrační bubliny zobrazují správné počty
- Inline editace přes HTMX funguje bez reloadu
- Back URL řetěz zachovává filtry přes celou navigaci

---

### Feature blok 3: Evidence jednotek

**Cíl:** Kompletní CRUD pro jednotky s prokliky na vlastníky.

**Úkoly:**
1. Router `/jednotky` se všemi endpointy
2. Seznam jednotek s vyhledáváním (číslo, budova, typ, sekce, adresa, vlastník)
3. Filtrační bubliny: typ prostoru, sekce domu (dynamicky roztažené)
4. Řazení kliknutím na hlavičky sloupců
5. Porovnání podílů: prohlášení vlastníka vs evidence s barevným rozdílem a %
6. Vytvoření nové jednotky (inline HTMX formulář)
7. Detail jednotky:
   - Inline editace všech polí přes HTMX (číslo, budova, typ, sekce, adresa, LV, místnosti, plocha, podíl)
   - Seznam vlastníků s prokliky
   - Kolapsovatelná sekce „Předchozí vlastníci" — historické záznamy s daty od/do
   - Smazání jednotky (cascade smaže přiřazení)
8. Číslo jednotky uloženo a řazeno jako INTEGER
9. Back URL řetěz

**Akceptační kritéria:**
- CRUD jednotek funguje kompletně
- Prokliky vlastník ↔ jednotka fungují obousměrně
- Inline editace přes HTMX funguje
- Cascade smazání funguje správně

---

## FÁZE 2: Hlasování (Feature bloky 4–5)

### Feature blok 4: Hlasování — vytvoření, body, generování lístků

**Cíl:** Vytvořit hlasování, extrahovat body z šablony, generovat PDF lístky.

**Úkoly:**
1. Router `/hlasovani` — základní endpointy
2. Vytvoření hlasování (název, termíny, kvórum)
3. Nahrání šablony hlasovacího lístku (.docx)
4. Automatická extrakce bodů hlasování z šablony (`word_parser.py`)
5. Přidání a smazání jednotlivých bodů (pouze ve stavu koncept)
6. Generování personalizovaných PDF lístků (`pdf_generator.py` + LibreOffice)
7. Stavy hlasování: koncept → aktivní → uzavřené / zrušené
8. Smazání hlasování z přehledu (cascade smaže body, lístky, hlasy + soubory) s potvrzovacím dialogem
9. Seznam hlasování s výsledky po bodech (PRO/PROTI/Zdržel se s procenty)
10. Filtrační bubliny dle stavu (vše, koncept, aktivní, uzavřeno, zrušeno)
11. Sdílený header na všech stránkách hlasování (partial `_voting_header.html`)
12. Status bubliny fixně nahoře — nescrollují se
13. Viditelnost UI dle stavu: koncept = správa bodů + generování; po generování = výsledky + zpracování

**Akceptační kritéria:**
- Vytvoření hlasování s .docx šablonou funguje
- Body se extrahují automaticky z šablony
- PDF lístky se generují pro všechny vlastníky
- Stavy se správně přepínají
- Cascade smazání funguje (body, lístky, hlasy, soubory)

---

### Feature blok 5: Hlasování — zpracování, import, výsledky

**Cíl:** Zpracování lístků, hromadné operace, import z Excelu, výpočet kvóra.

**Úkoly:**
1. Detail hlasování: vyhledávání v bodech + řazení sloupců (HTMX partial)
2. Seznam lístků s vyhledáváním vlastníka a řazením sloupců
3. Detail hlasovacího lístku s prokliky na vlastníka
4. Zpracování lístků: zadání hlasů (PRO/PROTI/Zdržel se) s vyhledáváním
5. Neodevzdané lístky s vyhledáváním
6. Sčítání hlasů a výpočet kvóra
7. Podpora hlasování v zastoupení (plné moci — Proxy model)
8. Hromadné zpracování: checkboxy, select all, batch zadání hlasů
9. Import výsledků hlasování z Excelu:
   - 4-krokový flow: upload → mapování sloupců → náhled → potvrzení
   - Mapování sloupců na role (vlastník, jednotka, bod hlasování) s předvyplněním
   - Konfigurovatelné hodnoty PRO/PROTI (výchozí 1,ANO / 0,NE)
   - Nastavitelný počáteční řádek dat
   - Režim importu: doplnit / vyčistit a přepsat
   - Automatické párování spoluvlastníků (SJM)
   - Náhled s filtračními bublinami (přiřazeno/nepřiřazeno/chyby)
   - Výsledek s prokliky
10. Aktivní bublina zvýrazněna ring-2 dle aktuální stránky/filtru
11. Zpracování lístků: řazení dle vlastníka/jednotek/hlasů

**Akceptační kritéria:**
- Kompletní user flow: vytvoření → generování → zpracování → výsledky
- Import z Excelu funguje end-to-end (4 kroky)
- Kvórum se počítá správně
- Hromadné zpracování funguje
- Plné moci se správně aplikují

---

## FÁZE 3: Daně + Synchronizace (Feature bloky 6–7)

### Feature blok 6: Rozúčtování příjmů (Daně)

**Cíl:** Nahrání daňových PDF, extrakce jmen, párování, rozeslání emailem.

**Úkoly:**
1. Router `/dane` se všemi endpointy
2. Vytvoření rozúčtování s nahráním PDF dokumentů
3. Extrakce jmen z PDF (`pdf_extractor.py` + pdfplumber)
4. Fuzzy párování jmen na vlastníky (`owner_matcher.py`):
   - Práh 0.6 pro párování v rámci jednotky
   - Práh 0.75 pro globální párování
5. Ruční ověření a oprava párování
6. Hromadné rozeslání emailem s přílohami (`email_service.py`)
7. Seznam rozúčtování, detail s párováním

**Akceptační kritéria:**
- Upload PDF → extrakce jmen → automatické párování funguje
- Fuzzy matching správně páruje české jména (háčky, čárky)
- Ruční oprava párování funguje
- Email odesílání funguje (nebo mock pro testování)

---

### Feature blok 7: Kontrola vlastníků (Synchronizace)

**Cíl:** Nahrání CSV, porovnání s DB, selektivní aktualizace, výměna vlastníků.

**Úkoly:**
1. Router `/synchronizace` se všemi endpointy
2. Nahrání CSV exportu (sousede.cz nebo interní export)
3. Automatická detekce formátu CSV, BOM stripping
4. Sloučení spoluvlastníků z interního exportu
5. Historie kontrol s možností smazání (cascade)
6. Porovnání s DB (`csv_comparator.py`):
   - Rozlišení: úplná shoda / částečná shoda / přeházená jména / rozdílní vlastníci / rozdílné podíly / chybí
7. Filtrační bubliny s dynamickými počty a souhrny podílů:
   - Každá bublina zobrazuje podíly v evidenci, CSV a rozdíl
   - Bublina „Vše" zobrazuje katastrální podíl (4 103 391) s procentuálními rozdíly
   - Bublina „Rozdílné podíly" filtruje záznamy kde se liší pouze podíl SČD
8. Třídění kliknutím na hlavičky sloupců
9. Selektivní aktualizace dat z CSV:
   - Checkboxy u lišících se polí
   - Řádkový checkbox pro hromadné zaškrtnutí
   - Toolbar: Vybrat vše / Zrušit výběr / počítadlo / Aktualizovat vybrané
   - Po aktualizaci přepočet statusu a počítadel
10. Aktualizace vlastníků: matchování CSV → DB (fuzzy ≥75%), přidání nových, soft-delete
11. Logování změn (zdrojový CSV, čas)
12. Proklik na detail vlastníka s návratem zpět
13. Export filtrovaného pohledu do Excelu (zvýraznění rozdílů)
14. Přenos kontaktů z CSV
15. Výměna vlastníků:
    - Preview výměny (přeškrtnutí → zelené badge)
    - Inteligentní párování: existující (přesná shoda), možná shoda (fuzzy ≥90%), nový
    - Rovnoměrné rozdělení hlasů mezi spoluvlastníky
    - Změny typu prostoru a druhu vlastnictví
    - Hromadná výměna všech rozdílných najednou
    - Date picker pro datum výměny
    - Soft-delete: nepárované OwnerUnit dostanou valid_to
    - Vlastníci bez jednotek = zešedlý řádek (opacity-50)
    - Zachování filtru a scroll pozice (#sync-{id} anchor)
    - Logování do ImportLog

**Akceptační kritéria:**
- CSV upload → porovnání → filtrace → aktualizace funguje end-to-end
- Oba CSV formáty (sousede.cz i interní) se správně parsují
- Výměna vlastníků zachovává historii (soft-delete)
- Export do Excelu obsahuje zvýraznění rozdílů

---

## FÁZE 4: Administrace (Feature bloky 8–9)

### Feature blok 8: Administrace — info, členové, zálohy

**Cíl:** Správa SVJ info, členů výboru, zálohování a obnova.

**Úkoly:**
1. Router `/sprava` se všemi endpointy
2. Informace o SVJ (název, typ budovy, celkový počet podílů) — read-only + inline editace
3. Správa adres SVJ — přidání, editace, smazání, řazení abecedně
4. Členové výboru — přidání, inline editace, smazání
5. Členové kontrolního orgánu — stejná funkcionalita
6. Autocomplete rolí přes `<datalist>` (Předseda/Místopředseda/Člen)
7. Řazení členů: předsedové → místopředsedové → ostatní, abecedně
8. **Správa uživatelů** (`/sprava/uzivatele`):
   - Seznam uživatelů (jméno, login, role, poslední přihlášení, stav)
   - Vytvoření nového uživatele (username, heslo, role, display_name)
   - Změna role existujícího uživatele
   - Reset hesla
   - Deaktivace/aktivace uživatele (soft delete)
   - Admin nemůže smazat/deaktivovat sám sebe
   - Minimálně jeden admin musí vždy existovat
9. **Audit log** (`/sprava/audit`):
   - Prohlížení všech změn (kdo, co, kdy, stará → nová hodnota)
   - Filtrování dle uživatele, modelu, akce, datumu
   - Pouze admin
10. **Notifikace**:
    - Model Notification, zvonečkový indikátor v hlavičce
    - Dropdown s posledními, označení jako přečtené
    - Notifikace při: nové hlasování, změna stavu, import, sync, záloha
11. Zálohování:
   - Vytvoření zálohy (ZIP: DB + uploads + generated) s vlastním názvem
   - Ochrana proti prázdným zálohám
   - Seznam záloh s datem, velikostí, stažením, smazáním
9. Obnova ze zálohy — tři způsoby:
   - Upload ZIP
   - Upload složky z Finderu (webkitdirectory)
   - Upload souboru svj.db
10. Před obnovou automatická pojistná záloha
11. Po obnově automatická migrace (engine.dispose + přidání chybějících sloupců/indexů)
12. `application/octet-stream` pro stahování (Safari kompatibilita)
13. Sekce zůstává otevřená po akcích (query param `sekce=zalohy`)
14. Side-by-side layout: vytvořit vlevo, obnovit vpravo
15. Všechny sekce v skládacích `<details>` blocích

**Akceptační kritéria:**
- CRUD pro SVJ info, adresy, členy funguje
- Záloha vytvoří validní ZIP s DB + soubory
- Obnova funguje všemi třemi způsoby
- Po obnově server nepadá (migrace proběhne)

---

### Feature blok 9: Administrace — smazání, export, hromadné úpravy

**Cíl:** Smazání dat, export, hromadné úpravy hodnot.

**Úkoly:**
1. Smazání dat:
   - Výběr kategorií (vlastníci, hlasování, daně, synchronizace, logy, administrace, zálohy, historie obnovení)
   - Checkbox „Vybrat/Zrušit vše"
   - Počet záznamů a popis u každé kategorie
   - Potvrzení zadáním slova DELETE
   - Cascade smazání v bezpečném pořadí
2. Export dat:
   - Výběr kategorií s checkboxy
   - Formát Excel (xlsx) nebo CSV (UTF-8 s BOM)
   - Hromadný export: jedna kategorie = soubor, více = ZIP
   - 6 kategorií: vlastníci a jednotky, hlasování, daně, synchronizace, logy, administrace
3. Hromadné úpravy (`/sprava/hromadne-upravy`):
   - Výběr pole (typ prostoru, sekce, počet místností, vlastnictví druh, vlastnictví/podíl, adresa, orientační číslo)
   - Tabulka unikátních hodnot s počtem výskytů
   - Rozkliknutí → všechny záznamy s detaily
   - Prokliky na detail jednotky a vlastníka
   - Třídění sloupců (klientské řazení)
   - Checkboxy pro selektivní opravu — vybrat/zrušit vše + počítadlo + indeterminate
   - Persistence výběru přes sessionStorage
   - Inline oprava s datalist napovídáním
4. **Automatické zálohy**:
   - Nastavení v administraci: frekvence (denní/týdenní), čas, počet uchovávaných
   - Background task při startu aplikace
   - Automatické mazání starých záloh
   - Stav viditelný v administraci (poslední záloha, další plánovaná)
5. **Tisk sestav**:
   - Tlačítko „Tisk" na: seznam vlastníků, detail vlastníka, výsledky hlasování, porovnání synchronizace
   - CSS print stylesheet (`@media print`) — skryje sidebar, navigaci; optimalizuje pro A4

**Akceptační kritéria:**
- Smazání dat funguje s cascade v bezpečném pořadí
- Export generuje validní Excel/CSV/ZIP
- Hromadné úpravy umožňují opravu hodnot across záznamy
- SessionStorage zachová výběr při navigaci

---

## FÁZE 5: Nastavení + Polish (Feature blok 10)

### Feature blok 10: Nastavení + USB nasazení + Visual polish

**Cíl:** Modul nastavení, USB deployment skripty, finální vizuální polish.

**Úkoly:**
1. Router `/nastaveni` — přehled odeslaných emailů (posledních 50)
2. `spustit.command` — macOS spouštěcí skript:
   - Automatické vytvoření venv
   - Instalace závislostí (offline z wheels nebo online)
   - Spuštění aplikace
3. `pripravit_usb.sh` — příprava offline wheels
4. Vizuální polish celé aplikace:
   - Konzistentní typografie, barvy, spacing
   - Loading states, empty states, error states, success states
   - Micro-interactions (hover, focus, transitions)
   - Responsivita (mobile-friendly sidebar, tabulky)
   - WCAG AA accessibility check

**Akceptační kritéria:**
- Nastavení zobrazuje email log
- USB deployment funguje na čistém Macu s Python 3.9+
- Všechny stránky vizuálně konzistentní
- Žádné broken layouts na mobilu

---

## API Endpointy — kompletní reference

### Dashboard
| Metoda | Cesta | Popis |
|--------|-------|-------|
| GET | `/` | Dashboard s přehledem statistik |

### Autentizace
| Metoda | Cesta | Popis |
|--------|-------|-------|
| GET | `/login` | Přihlašovací stránka |
| POST | `/login` | Přihlášení (username + heslo) |
| GET | `/logout` | Odhlášení |
| GET | `/registrace` | Registrace prvního uživatele (pouze pokud 0 users) |
| POST | `/registrace` | Vytvoření prvního admin účtu |

### Vlastníci (`/vlastnici`)
| Metoda | Cesta | Popis |
|--------|-------|-------|
| GET | `/vlastnici` | Seznam vlastníků (search, filtr, řazení) |
| GET | `/vlastnici/import` | Import stránka + historie |
| POST | `/vlastnici/import` | Upload Excel → náhled |
| POST | `/vlastnici/import/potvrdit` | Potvrzení importu |
| POST | `/vlastnici/import/{log_id}/smazat` | Smazání importu (cascade) |
| GET | `/vlastnici/{id}` | Detail vlastníka |
| GET | `/vlastnici/{id}/upravit-formular` | HTMX: formulář kontaktů |
| GET | `/vlastnici/{id}/info` | HTMX: zobrazení kontaktů |
| POST | `/vlastnici/{id}/upravit` | Uložení kontaktů |
| GET | `/vlastnici/{id}/adresa/{prefix}/upravit-formular` | HTMX: formulář adresy |
| GET | `/vlastnici/{id}/adresa/{prefix}/info` | HTMX: zobrazení adresy |
| POST | `/vlastnici/{id}/adresa/{prefix}/upravit` | Uložení adresy |
| POST | `/vlastnici/{id}/jednotky/pridat` | Přidat jednotku |
| POST | `/vlastnici/{id}/jednotky/{ou_id}/odebrat` | Odebrat jednotku |

### Jednotky (`/jednotky`)
| Metoda | Cesta | Popis |
|--------|-------|-------|
| GET | `/jednotky` | Seznam jednotek |
| GET | `/jednotky/nova-formular` | HTMX: formulář nové jednotky |
| POST | `/jednotky/nova` | Vytvoření jednotky |
| GET | `/jednotky/{id}` | Detail jednotky |
| GET | `/jednotky/{id}/upravit-formular` | HTMX: formulář editace |
| GET | `/jednotky/{id}/info` | HTMX: zobrazení údajů |
| POST | `/jednotky/{id}/upravit` | Uložení údajů |

### Hlasování (`/hlasovani`)
| Metoda | Cesta | Popis |
|--------|-------|-------|
| GET | `/hlasovani` | Seznam hlasování |
| GET | `/hlasovani/nova` | Formulář nového hlasování |
| POST | `/hlasovani/nova` | Vytvoření hlasování |
| GET | `/hlasovani/{id}` | Detail s výsledky |
| POST | `/hlasovani/{id}/smazat` | Smazání (cascade) |
| POST | `/hlasovani/{id}/stav` | Změna stavu |
| POST | `/hlasovani/{id}/pridat-bod` | Přidání bodu |
| POST | `/hlasovani/{id}/smazat-bod/{item_id}` | Smazání bodu |
| POST | `/hlasovani/{id}/generovat` | Generování PDF |
| GET | `/hlasovani/{id}/listky` | Seznam lístků |
| GET | `/hlasovani/{id}/listek/{ballot_id}` | Detail lístku |
| GET | `/hlasovani/{id}/zpracovani` | Zpracování lístků |
| POST | `/hlasovani/{id}/zpracovat/{ballot_id}` | Zpracování jednoho |
| POST | `/hlasovani/{id}/zpracovat-hromadne` | Hromadné zpracování |
| GET | `/hlasovani/{id}/neodevzdane` | Neodevzdané lístky |
| GET | `/hlasovani/{id}/import` | Import stránka |
| POST | `/hlasovani/{id}/import` | Upload Excel |
| POST | `/hlasovani/{id}/import/nahled` | Náhled importu |
| POST | `/hlasovani/{id}/import/potvrdit` | Potvrzení importu |

### Rozúčtování (`/dane`)
| Metoda | Cesta | Popis |
|--------|-------|-------|
| GET | `/dane` | Seznam rozúčtování |
| GET | `/dane/nova` | Formulář nového |
| POST | `/dane/nova` | Vytvoření s PDF |
| GET | `/dane/{id}` | Detail s párováním |
| POST | `/dane/{id}/potvrdit/{dist_id}` | Potvrzení párování |
| POST | `/dane/{id}/prirazeni/{doc_id}` | Ruční přiřazení |

### Synchronizace (`/synchronizace`)
| Metoda | Cesta | Popis |
|--------|-------|-------|
| GET | `/synchronizace` | Upload CSV + historie |
| POST | `/synchronizace/nova` | Nahrání a porovnání |
| POST | `/synchronizace/{id}/smazat` | Smazání kontroly |
| GET | `/synchronizace/{id}` | Porovnání s filtry |
| POST | `/synchronizace/{id}/aktualizovat` | Aplikace změn |
| POST | `/synchronizace/{id}/aplikovat-kontakty` | Přenos kontaktů |
| POST | `/synchronizace/{id}/exportovat` | Export do Excelu |
| GET | `/synchronizace/{id}/vymena/{rec_id}` | Preview výměny |
| POST | `/synchronizace/{id}/vymena/{rec_id}/potvrdit` | Potvrzení výměny |
| POST | `/synchronizace/{id}/vymena-hromadna` | Preview hromadné výměny |
| POST | `/synchronizace/{id}/vymena-hromadna/potvrdit` | Potvrzení hromadné |
| POST | `/synchronizace/{id}/prijmout/{rec_id}` | Přijetí změny |
| POST | `/synchronizace/{id}/odmitnout/{rec_id}` | Odmítnutí změny |
| POST | `/synchronizace/{id}/upravit/{rec_id}` | Ruční úprava |

### Administrace (`/sprava`)
| Metoda | Cesta | Popis |
|--------|-------|-------|
| GET | `/sprava` | Stránka administrace |
| POST | `/sprava/info` | Uložení info SVJ |
| POST | `/sprava/adresa/pridat` | Přidání adresy |
| POST | `/sprava/adresa/{id}/upravit` | Editace adresy |
| POST | `/sprava/adresa/{id}/smazat` | Smazání adresy |
| POST | `/sprava/clen/pridat` | Přidání člena |
| POST | `/sprava/clen/{id}/upravit` | Editace člena |
| POST | `/sprava/clen/{id}/smazat` | Smazání člena |
| GET | `/sprava/uzivatele` | Seznam uživatelů (pouze admin) |
| POST | `/sprava/uzivatele/novy` | Vytvoření uživatele (pouze admin) |
| POST | `/sprava/uzivatele/{id}/role` | Změna role (pouze admin) |
| POST | `/sprava/uzivatele/{id}/heslo` | Reset hesla (pouze admin) |
| POST | `/sprava/uzivatele/{id}/stav` | Aktivace/deaktivace (pouze admin) |
| POST | `/sprava/zaloha/vytvorit` | Vytvoření zálohy |
| GET | `/sprava/zaloha/{filename}/stahnout` | Stažení zálohy |
| POST | `/sprava/zaloha/{filename}/smazat` | Smazání zálohy |
| POST | `/sprava/zaloha/obnovit` | Obnova z ZIP |
| POST | `/sprava/zaloha/obnovit-slozku` | Obnova ze složky |
| POST | `/sprava/zaloha/obnovit-soubor` | Obnova z DB souboru |
| POST | `/sprava/zaloha/obnovit-adresar` | Obnova z lokální cesty |
| POST | `/sprava/smazat-data` | Smazání dat (DELETE) |
| GET | `/sprava/export/{category}/{fmt}` | Export kategorie |
| POST | `/sprava/export/hromadny` | Hromadný export |
| GET | `/sprava/hromadne-upravy` | Hromadné úpravy |
| GET | `/sprava/hromadne-upravy/hodnoty` | HTMX: unikátní hodnoty |
| GET | `/sprava/hromadne-upravy/zaznamy` | HTMX: záznamy |
| POST | `/sprava/hromadne-upravy/opravit` | Hromadná oprava |

### Nastavení (`/nastaveni`)
| Metoda | Cesta | Popis |
|--------|-------|-------|
| GET | `/nastaveni` | Přehled emailů |

### Globální hledání
| Metoda | Cesta | Popis |
|--------|-------|-------|
| GET | `/hledani?q=...` | Fulltextové hledání napříč moduly |

### Notifikace
| Metoda | Cesta | Popis |
|--------|-------|-------|
| GET | `/notifikace` | Seznam všech notifikací |
| GET | `/notifikace/neprecetene` | HTMX: dropdown nepřečtených |
| POST | `/notifikace/{id}/precist` | Označit jako přečtenou |
| POST | `/notifikace/precist-vse` | Označit vše jako přečtené |

### Audit log (pouze admin)
| Metoda | Cesta | Popis |
|--------|-------|-------|
| GET | `/sprava/audit` | Prohlížení audit logu s filtry |

---

## Priorita implementace (shrnutí)

| Fáze | Bloky | Obsah | Odhad |
|------|-------|-------|-------|
| 1 | 1–3 | Setup + Vlastníci + Jednotky | Základ aplikace |
| 2 | 4–5 | Hlasování komplet | Klíčový modul |
| 3 | 6–7 | Daně + Synchronizace | Import/export data |
| 4 | 8–9 | Administrace komplet | Správa + zálohy |
| 5 | 10 | Nastavení + USB + Polish | Finalizace |

---

## Poznámky pro vývojáře

- **Jazyk UI:** Čeština (URL cesty, popisky, flash messages)
- **Číslo jednotky:** Vždy INTEGER (řazení numerické, ne abecední)
- **Soft delete:** OwnerUnit používá valid_to datum, nikdy se nemaže fyzicky
- **Cascade delete:** Při mazání importu/hlasování/kontroly se mažou všechna navázaná data
- **Excel import:** 31 sloupců, sheet pojmenovaný `Vlastnici_SVJ`
- **CSV formáty:** Dva formáty — sousede.cz (sloupec „Vlastníci jednotky") a interní export (sloupce „Příjmení" + „Jméno")
- **Fuzzy matching:** Používat pro česká jména s diakritikou, prahy: 0.6 (jednotka), 0.75 (globální), 0.9 (výměna)
- **HTMX:** Veškerá inline editace přes HTMX, žádný custom JavaScript pro AJAX
- **Tailwind:** Přes CDN, custom styly v `static/css/custom.css`
- **Flash messages:** Po každé akci zobrazit feedback (úspěch/chyba)
