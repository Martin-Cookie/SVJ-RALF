"""Excel import service for owners."""
from typing import Dict, List, Optional, Tuple

from openpyxl import load_workbook


def parse_owners_xlsx(file_bytes) -> Tuple[List[Dict], List[str]]:
    """Parse an Excel file with owner data.

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

    # Column mapping (Czech headers → field names)
    col_map = {
        "příjmení": "last_name",
        "jméno": "first_name",
        "titul před": "title_before",
        "titul za": "title_after",
        "rodné číslo": "birth_number",
        "rč": "birth_number",
        "ič": "ico",
        "ičo": "ico",
        "typ": "owner_type",
        "email": "email",
        "telefon": "phone",
        "ulice trvalá": "perm_street",
        "město trvalá": "perm_city",
        "psč trvalá": "perm_zip",
        "ulice korespondenční": "corr_street",
        "město korespondenční": "corr_city",
        "psč korespondenční": "corr_zip",
        "číslo jednotky": "unit_number",
        "budova": "building",
        "sekce": "section",
        "typ prostoru": "space_type",
        "typ vlastnictví": "ownership_type",
        "podíl": "ownership_share",
        "hlasovací váha": "voting_weight",
        "plocha": "area",
        "podíl sčd": "share_scd",
        "lv": "land_registry_number",
        "počet místností": "room_count",
        "adresa": "address",
    }

    # Map actual column indices
    field_indices = {}  # type: Dict[str, int]
    for idx, header in enumerate(header_row):
        for czech, field in col_map.items():
            if czech in header:
                field_indices[field] = idx
                break

    if "last_name" not in field_indices and "first_name" not in field_indices:
        # Fallback: assume columns in order
        default_order = ["last_name", "first_name", "title_before", "title_after",
                         "birth_number", "ico", "owner_type", "email", "phone",
                         "perm_street", "perm_city", "perm_zip",
                         "corr_street", "corr_city", "corr_zip",
                         "unit_number", "building"]
        for idx, field in enumerate(default_order):
            if idx < len(header_row):
                field_indices[field] = idx

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

        # Normalize owner type
        ot = data.get("owner_type", "").lower()
        if "práv" in ot or "po" in ot:
            data["owner_type"] = "právnická"
        else:
            data["owner_type"] = "fyzická"

        # Convert numeric fields
        for num_field in ["unit_number", "room_count"]:
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
