"""Excel import service for owners."""
from typing import Dict, List, Tuple

from openpyxl import load_workbook


def parse_owners_xlsx(file_bytes) -> Tuple[List[Dict], List[str]]:
    """Parse an Excel file with owner data (31-column SVJ format).

    Returns (rows, errors) where rows is a list of dicts
    and errors is a list of validation error messages.
    """
    errors = []
    rows = []

    try:
        wb = load_workbook(file_bytes, read_only=True, data_only=True)
    except Exception as e:
        return [], [f"Nelze otevřít soubor: {e}"]

    # Try to find the right sheet
    ws = None
    for name in ["Vlastnici_SVJ", "Vlastnici", "Sheet1", "List1"]:
        if name in wb.sheetnames:
            ws = wb[name]
            break
    if ws is None:
        ws = wb.active

    if ws is None:
        return [], ["Soubor neobsahuje žádný list."]

    # Read header row to map columns
    header_row = []
    for cell in next(ws.iter_rows(min_row=1, max_row=1)):
        header_row.append(str(cell.value or "").strip().lower())

    # Column mapping: longer patterns first to avoid false matches
    # (e.g., "podíl na sčd" must match before "podíl")
    # Each entry: (pattern_to_find_in_header, field_name)
    col_map_ordered = [
        # Unit fields
        ("číslo jednotky", "unit_number"),
        ("číslo prostoru", "building"),
        ("podíl na sčd", "share_scd"),
        ("podlahová plocha", "area"),
        ("počet místností", "room_count"),
        ("druh prostoru", "space_type"),
        ("sekce", "section"),
        ("číslo orientační", "orientation_number"),
        ("adresa jednotky", "address"),
        ("lv", "land_registry_number"),
        # Ownership
        ("typ vlastnictví", "ownership_type"),
        # Owner fields
        ("jméno", "first_name"),
        ("příjmení", "last_name"),
        ("titul", "title_before"),
        ("rodné číslo", "birth_number"),
        # Permanent address
        ("trvalá adresa – ulice", "perm_street"),
        ("trvalá adresa – část obce", "perm_district"),
        ("trvalá adresa – město", "perm_city"),
        ("trvalá adresa – psč", "perm_zip"),
        ("trvalá adresa – stát", "perm_country"),
        # Correspondence address
        ("koresp. adresa – ulice", "corr_street"),
        ("koresp. adresa – část obce", "corr_district"),
        ("koresp. adresa – město", "corr_city"),
        ("koresp. adresa – psč", "corr_zip"),
        ("koresp. adresa – stát", "corr_country"),
        # Contact
        ("telefon gsm", "phone"),
        ("telefon pevný", "phone_landline"),
        ("email", "email"),
        # Metadata
        ("vlastník od", "owner_since"),
        ("poznámka", "note"),
    ]

    # Map actual column indices
    field_indices = {}  # type: Dict[str, int]
    used_cols = set()  # track which columns are already matched
    for pattern, field in col_map_ordered:
        for idx, header in enumerate(header_row):
            if idx not in used_cols and pattern in header:
                field_indices[field] = idx
                used_cols.add(idx)
                break

    # Handle dual email columns: prefer "email (evidence" over "email (kontakty)"
    # If we have two email columns, pick the first one (Evidence)
    email_cols = []
    for idx, header in enumerate(header_row):
        if "email" in header:
            email_cols.append((idx, header))
    if len(email_cols) >= 2:
        # Use Evidence email as primary, Kontakty as secondary
        for idx, header in email_cols:
            if "evidence" in header:
                field_indices["email"] = idx
                break

    if "last_name" not in field_indices and "first_name" not in field_indices:
        return [], ["Nelze identifikovat sloupce – chybí 'Jméno' a 'Příjmení'."]

    # Parse data rows
    for row_idx, row in enumerate(ws.iter_rows(min_row=2), start=2):
        cells = [cell.value for cell in row]

        # Skip empty rows
        if all(c is None or str(c).strip() == "" for c in cells):
            continue

        data = {}
        for field, col_idx in field_indices.items():
            if col_idx < len(cells):
                val = cells[col_idx]
                data[field] = str(val).strip() if val is not None else ""
            else:
                data[field] = ""

        # Validate required fields
        if not data.get("last_name") and not data.get("first_name"):
            errors.append(f"Řádek {row_idx}: chybí jméno nebo příjmení")
            continue

        # Normalize owner type from ownership_type field
        # The Excel has "Typ vlastnictví" (SJM, VL, etc.), not owner type (fyzická/právnická)
        # Detect právnická by IČ presence
        birth_or_ico = data.get("birth_number", "")
        if birth_or_ico and "/" not in birth_or_ico and birth_or_ico.isdigit() and len(birth_or_ico) <= 8:
            data["ico"] = birth_or_ico
            data["birth_number"] = ""
            data["owner_type"] = "právnická"
        else:
            data["ico"] = ""
            data["owner_type"] = "fyzická"

        # unit_number stays as string (e.g., "1098/1")
        # Convert numeric fields
        for num_field in ["room_count"]:
            try:
                data[num_field] = int(float(data.get(num_field, "") or "0"))
            except (ValueError, TypeError):
                data[num_field] = 0

        for float_field in ["area", "share_scd", "voting_weight"]:
            try:
                data[float_field] = float(data.get(float_field, "") or "0")
            except (ValueError, TypeError):
                data[float_field] = 0.0

        rows.append(data)

    wb.close()
    return rows, errors
