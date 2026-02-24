"""Tests for excel_import service — helper functions, preview, and import."""
import io
import os
import tempfile

import pytest
from openpyxl import Workbook


# ---- Helper function tests ----

def test_cell_returns_stripped_string():
    from app.services.excel_import import _cell
    row = ("  hello  ", None, "", 42)
    assert _cell(row, 0) == "hello"
    assert _cell(row, 1) is None
    assert _cell(row, 2) is None
    assert _cell(row, 3) == "42"


def test_cell_out_of_range():
    from app.services.excel_import import _cell
    row = ("a",)
    assert _cell(row, 5) is None


def test_cell_int():
    from app.services.excel_import import _cell_int
    row = ("12212", "3.7", "abc", None)
    assert _cell_int(row, 0) == 12212
    assert _cell_int(row, 1) == 3
    assert _cell_int(row, 2) is None
    assert _cell_int(row, 3) is None


def test_cell_float():
    from app.services.excel_import import _cell_float
    row = ("185.56", "abc", None)
    assert _cell_float(row, 0) == 185.56
    assert _cell_float(row, 1) is None
    assert _cell_float(row, 2) is None


def test_clean_name_strips_fraction():
    from app.services.excel_import import _clean_name
    assert _clean_name("Zich   1/3") == "Zich"
    assert _clean_name("Zichová   2/3") == "Zichová"
    assert _clean_name("Novák") == "Novák"
    assert _clean_name(None) is None
    assert _clean_name("") == ""


def test_clean_name_keeps_normal_slash():
    """Slash in the middle of a name should not be stripped."""
    from app.services.excel_import import _clean_name
    assert _clean_name("s.r.o.") == "s.r.o."
    assert _clean_name("O'Brien") == "O'Brien"


def test_normalize_name():
    from app.services.excel_import import _normalize_name
    assert _normalize_name("Novák Jan") == "novak jan"
    assert _normalize_name("  Šťastný   Petr  ") == "stastny petr"
    assert _normalize_name("VELKÝ") == "velky"


def test_is_birth_number():
    from app.services.excel_import import _is_birth_number
    assert _is_birth_number("711128/9911") is True
    assert _is_birth_number("326129/053") is True
    assert _is_birth_number("7111289911") is True  # 10 digits no slash
    assert _is_birth_number("45277991") is False  # 8 digits = IČ
    assert _is_birth_number("abc") is False
    assert _is_birth_number("123/456/789") is False


def test_is_company_id():
    from app.services.excel_import import _is_company_id
    assert _is_company_id("45277991") is True
    assert _is_company_id("12345678") is True
    assert _is_company_id("711128/9911") is False  # has slash
    assert _is_company_id("1234567") is False  # 7 digits
    assert _is_company_id("123456789") is False  # 9 digits
    assert _is_company_id("abcdefgh") is False


def test_detect_owner_type():
    from app.services.excel_import import _detect_owner_type
    assert _detect_owner_type("711128/9911") == "physical"
    assert _detect_owner_type("45277991") == "legal"
    assert _detect_owner_type(None) == "physical"
    assert _detect_owner_type("") == "physical"


def test_normalize_ownership_type():
    from app.services.excel_import import _normalize_ownership_type
    assert _normalize_ownership_type("ANO") == "SJM"
    assert _normalize_ownership_type("ano") == "SJM"
    assert _normalize_ownership_type("VL") == "VL"
    assert _normalize_ownership_type("SJVL") == "SJVL"
    assert _normalize_ownership_type(None) is None
    assert _normalize_ownership_type("") is None


def test_build_name_with_titles():
    from app.services.excel_import import _build_name_with_titles
    assert _build_name_with_titles("Ing.", "Jan", "Novák") == "Ing. Novák Jan"
    assert _build_name_with_titles(None, "Jan", "Novák") == "Novák Jan"
    assert _build_name_with_titles(None, "Jan", None) == "Jan"
    # Dedup: first_name == last_name (legal entities)
    assert _build_name_with_titles(None, "ICC s.r.o.", "ICC s.r.o.") == "ICC s.r.o."


def test_build_name_normalized():
    from app.services.excel_import import _build_name_normalized
    assert _build_name_normalized("Jan", "Novák") == "novak jan"
    assert _build_name_normalized("Jan", None) == "jan"
    assert _build_name_normalized("Šťastný", "Velký") == "velky stastny"


def test_owner_group_key_by_birth_number():
    from app.services.excel_import import _owner_group_key
    key = _owner_group_key("Jan", "Novák", "711128/9911")
    assert key == "id:711128/9911"


def test_owner_group_key_by_company_id():
    from app.services.excel_import import _owner_group_key
    key = _owner_group_key("ICC", "ICC", "45277991")
    assert key == "id:45277991"


def test_owner_group_key_by_name():
    from app.services.excel_import import _owner_group_key
    key = _owner_group_key("Jan", "Novák", None)
    assert key == "name:novak|jan"


def test_owner_group_key_empty():
    from app.services.excel_import import _owner_group_key
    key = _owner_group_key(None, None, None)
    assert key == "name:|"


def test_parse_unit_number():
    from app.services.excel_import import _parse_unit_number
    assert _parse_unit_number("1098/1") == 1
    assert _parse_unit_number("1098/353") == 353
    assert _parse_unit_number("115") == 115
    assert _parse_unit_number("abc") is None


def test_parse_row_valid():
    from app.services.excel_import import _parse_row
    # Build a 31-column row
    row = [None] * 31
    row[0] = "1098/1"  # unit KN
    row[1] = "A 111"  # building
    row[2] = 12212  # podil
    row[3] = 185.56  # area
    row[11] = "Jan"  # first name
    row[12] = "Novák"  # last name
    row[13] = "Ing."  # title
    row[14] = "711128/9911"  # birth number
    row[27] = "jan@test.cz"  # email

    result = _parse_row(tuple(row), 2)
    assert result is not None
    assert result["unit_kn"] == 1
    assert result["first_name"] == "Jan"
    assert result["last_name"] == "Novák"
    assert result["title"] == "Ing."
    assert result["email_evidence"] == "jan@test.cz"


def test_parse_row_missing_unit():
    from app.services.excel_import import _parse_row
    row = [None] * 31
    row[11] = "Jan"
    assert _parse_row(tuple(row), 2) is None


def test_parse_row_missing_first_name():
    from app.services.excel_import import _parse_row
    row = [None] * 31
    row[0] = "1098/1"
    assert _parse_row(tuple(row), 2) is None


# ---- Integration tests with Excel fixtures ----

def _create_test_workbook(rows):
    """Create an in-memory Excel workbook with given rows."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Vlastnici_SVJ"
    # Header row
    headers = ["Číslo jednotky (KN)", "Číslo prostoru", "Podíl na SČD",
               "Podlahová plocha", "Počet místností", "Druh prostoru",
               "Sekce domu", "Číslo orientační", "Adresa", "LV číslo",
               "Typ vlastnictví", "Jméno", "Příjmení", "Titul",
               "Rodné číslo / IČ", "Trvalá ulice", "Trvalá část obce",
               "Trvalá město", "Trvalá PSČ", "Trvalá stát",
               "Koresp ulice", "Koresp část obce", "Koresp město",
               "Koresp PSČ", "Koresp stát", "Telefon GSM", "Telefon pevný",
               "Email Evidence", "Email Kontakty", "Vlastník od", "Poznámka"]
    ws.append(headers)
    for row in rows:
        # Pad to 31 columns
        padded = list(row) + [None] * (31 - len(row))
        ws.append(padded)
    # Save to temp file
    tmp = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False)
    wb.save(tmp.name)
    wb.close()
    return tmp.name


@pytest.fixture
def simple_excel():
    """Create a simple Excel file with 2 owners and 2 units."""
    rows = [
        # unit_kn, building, podil, area, rooms, type, section, orient, addr, lv,
        # ownership, first, last, title, birth_ic, ...
        ["1098/1", "A 111", 12212, 185.56, "3+1", "byt", "A", 22, "Štěpařská", 3504,
         "ANO", "Jan", "Novák", "Ing.", "711128/9911",
         "Hlavní 1", "Praha 1", "Praha", "11000", "ČR",
         None, None, None, None, None,
         "602123456", None, "jan@test.cz", None, None, None],
        ["1098/2", "A 112", 8000, 120.0, "2+kk", "byt", "A", 22, "Štěpařská", 3505,
         "VL", "Eva", "Malá", None, "826015/1234",
         "Boční 5", None, "Brno", "60200", "ČR",
         None, None, None, None, None,
         None, None, None, "eva@kontakt.cz", None, None],
    ]
    path = _create_test_workbook(rows)
    yield path
    os.unlink(path)


@pytest.fixture
def dedup_excel():
    """Excel with same owner appearing twice (different units, same birth number)."""
    rows = [
        ["1098/1", "A 111", 12212, 185.56, "3+1", "byt", "A", 22, "Štěpařská", 3504,
         "ANO", "Jan", "Novák", "Ing.", "711128/9911",
         None, None, None, None, None,
         None, None, None, None, None,
         None, None, "jan@test.cz", None, None, None],
        ["1098/2", "A 112", 8000, 120.0, None, None, None, None, None, None,
         "ANO", "Jan", "Novák", "Ing.", "711128/9911",
         None, None, None, None, None,
         None, None, None, None, None,
         None, None, None, None, None, None],
    ]
    path = _create_test_workbook(rows)
    yield path
    os.unlink(path)


@pytest.fixture
def legal_entity_excel():
    """Excel with a legal entity (IČ, company name in both columns)."""
    rows = [
        ["1098/5", "B 201", 5000, 50.0, None, "nebyt", "B", None, None, None,
         "VL", "ICC, spol. s .r.o.", "ICC, spol. s .r.o.", None, "45277991",
         None, None, None, None, None,
         None, None, None, None, None,
         None, None, "icc@test.cz", None, None, None],
    ]
    path = _create_test_workbook(rows)
    yield path
    os.unlink(path)


def test_preview_basic(simple_excel):
    """Preview should return correct counts and preview rows."""
    from app.services.excel_import import preview_owners_from_excel
    result = preview_owners_from_excel(simple_excel)
    assert result["rows_processed"] == 2
    assert result["owners_count"] == 2
    assert result["units_count"] == 2
    assert len(result["preview_rows"]) == 2
    assert len(result["errors"]) == 0


def test_preview_dedup(dedup_excel):
    """Preview should count deduplicated owners."""
    from app.services.excel_import import preview_owners_from_excel
    result = preview_owners_from_excel(dedup_excel)
    assert result["rows_processed"] == 2
    assert result["owners_count"] == 1  # same birth number
    assert result["units_count"] == 2


def test_preview_legal_entity(legal_entity_excel):
    """Preview should detect legal entity type."""
    from app.services.excel_import import preview_owners_from_excel
    result = preview_owners_from_excel(legal_entity_excel)
    assert result["owners_count"] == 1
    row = result["preview_rows"][0]
    assert row["owner_type"] == "legal"
    assert row["name"] == "ICC, spol. s .r.o."  # not doubled


def test_preview_row_content(simple_excel):
    """Preview rows should have correct structure."""
    from app.services.excel_import import preview_owners_from_excel
    result = preview_owners_from_excel(simple_excel)
    row = result["preview_rows"][0]
    assert row["name"] == "Ing. Novák Jan"
    assert row["owner_type"] == "physical"
    assert row["unit_number"] == 1
    assert row["ownership_type"] == "SJM"  # ANO -> SJM
    assert row["email"] == "jan@test.cz"


def test_preview_fallback_email(simple_excel):
    """Preview should use email_contacts when email_evidence is missing."""
    from app.services.excel_import import preview_owners_from_excel
    result = preview_owners_from_excel(simple_excel)
    row_eva = result["preview_rows"][1]
    assert row_eva["email"] == "eva@kontakt.cz"


def test_import_creates_records(simple_excel, db_engine):
    """Import should create Owner, Unit, OwnerUnit records."""
    from sqlalchemy.orm import Session as SASession
    from app.services.excel_import import import_owners_from_excel
    from app.models.owner import Owner, Unit, OwnerUnit

    db = SASession(bind=db_engine)
    result = import_owners_from_excel(db, simple_excel)
    db.commit()

    assert result["owners_created"] == 2
    assert result["units_created"] == 2
    assert result["links_created"] == 2
    assert result["rows_processed"] == 2
    assert len(result["errors"]) == 0

    # Verify DB
    assert db.query(Owner).count() == 2
    assert db.query(Unit).count() == 2
    assert db.query(OwnerUnit).count() == 2

    # Check owner details
    jan = db.query(Owner).filter(Owner.last_name == "Novák").first()
    assert jan.first_name == "Jan"
    assert jan.title == "Ing."
    assert jan.birth_number == "711128/9911"
    assert jan.owner_type == "physical"
    assert jan.email == "jan@test.cz"
    assert jan.name_with_titles == "Ing. Novák Jan"
    assert jan.name_normalized == "novak jan"
    assert jan.perm_street == "Hlavní 1"
    assert jan.perm_city == "Praha"

    # Check unit details
    unit1 = db.query(Unit).filter(Unit.unit_number == 1).first()
    assert unit1.building_number == "A 111"
    assert unit1.podil_scd == 12212
    assert unit1.floor_area == 185.56
    assert unit1.room_count == "3+1"

    db.close()


def test_import_dedup(dedup_excel, db_engine):
    """Import should deduplicate owners with same birth number."""
    from sqlalchemy.orm import Session as SASession
    from app.services.excel_import import import_owners_from_excel
    from app.models.owner import Owner, Unit, OwnerUnit

    db = SASession(bind=db_engine)
    result = import_owners_from_excel(db, dedup_excel)
    db.commit()

    assert result["owners_created"] == 1
    assert result["units_created"] == 2
    assert result["links_created"] == 2

    # One owner, two units, two links
    jan = db.query(Owner).first()
    assert jan.last_name == "Novák"

    links = db.query(OwnerUnit).filter(OwnerUnit.owner_id == jan.id).all()
    assert len(links) == 2

    db.close()


def test_import_legal_entity(legal_entity_excel, db_engine):
    """Import should correctly handle legal entities."""
    from sqlalchemy.orm import Session as SASession
    from app.services.excel_import import import_owners_from_excel
    from app.models.owner import Owner

    db = SASession(bind=db_engine)
    import_owners_from_excel(db, legal_entity_excel)
    db.commit()

    owner = db.query(Owner).first()
    assert owner.owner_type == "legal"
    assert owner.company_id == "45277991"
    assert owner.birth_number is None or owner.birth_number == ""
    assert owner.name_with_titles == "ICC, spol. s .r.o."  # not doubled

    db.close()


def test_import_skips_invalid_rows(db_engine):
    """Import should skip rows missing unit number or first name."""
    from sqlalchemy.orm import Session as SASession
    from app.services.excel_import import import_owners_from_excel
    from app.models.owner import Owner

    rows = [
        # Valid row
        ["1098/1", "A", 100, 50.0, None, None, None, None, None, None,
         None, "Jan", "Novák", None, None] + [None] * 16,
        # Missing unit number
        [None, None, None, None, None, None, None, None, None, None,
         None, "Eva", "Malá", None, None] + [None] * 16,
        # Missing first name
        ["1098/2", None, None, None, None, None, None, None, None, None,
         None, None, "Velký", None, None] + [None] * 16,
    ]
    path = _create_test_workbook(rows)

    db = SASession(bind=db_engine)
    result = import_owners_from_excel(db, path)
    db.commit()

    assert result["owners_created"] == 1
    assert len(result["errors"]) == 2  # two invalid rows

    os.unlink(path)
    db.close()


def test_import_confirm_flow(auth_client, db_engine):
    """Full import flow: upload -> preview -> confirm."""
    rows = [
        ["1098/1", "A", 100, 50.0, None, None, None, None, None, None,
         "VL", "Jan", "Novák", None, "711128/9911"] + [None] * 16,
    ]
    path = _create_test_workbook(rows)

    with open(path, "rb") as f:
        resp = auth_client.post(
            "/vlastnici/import",
            files=[("file", ("test.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"))],
        )
    assert resp.status_code == 200
    assert "Novák" in resp.text

    # Confirm
    resp = auth_client.post("/vlastnici/import/potvrdit")
    assert resp.status_code == 303 or resp.status_code == 200

    # Verify data in DB
    from sqlalchemy.orm import Session as SASession
    from app.models.owner import Owner
    session = SASession(bind=db_engine)
    assert session.query(Owner).count() == 1
    owner = session.query(Owner).first()
    assert owner.last_name == "Novák"
    session.close()

    os.unlink(path)


def test_import_confirm_no_token(auth_client):
    """Confirm without prior upload should flash error."""
    resp = auth_client.post("/vlastnici/import/potvrdit", follow_redirects=True)
    assert resp.status_code == 200
    assert "Žádná data" in resp.text or "import" in resp.text.lower()
