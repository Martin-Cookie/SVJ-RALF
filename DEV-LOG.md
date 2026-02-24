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
