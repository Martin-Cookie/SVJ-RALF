"""Parse voting items from .docx template files."""
import re
from typing import List

from docx import Document


def parse_voting_items(file_path: str) -> List[str]:
    """Extract numbered voting items from a .docx file.

    Looks for paragraphs starting with a number followed by a period or parenthesis,
    and returns the text of each item.
    """
    doc = Document(file_path)
    items = []
    pattern = re.compile(r"^\s*(\d+)\s*[.)]\s*(.+)")

    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            continue
        match = pattern.match(text)
        if match:
            items.append(match.group(2).strip())

    return items
