"""Planning source parity and drift checks; no competition data access."""

import html
import importlib.util
import re
import shutil
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "timeline_export", ROOT / "scripts/timeline.py"
)
timeline = importlib.util.module_from_spec(spec)
spec.loader.exec_module(timeline)


def test_current_docx_export_preserves_text_links_tables_and_image():
    result = timeline.check(ROOT)
    assert result["status"] == "current"
    content, assets, counts = timeline.reading_copy(ROOT)
    plain = re.sub(r"\[([^\]]*)\]\(<[^>]*>\)", r"\1", content)
    plain = html.unescape(plain).replace("<br>", " ")
    with zipfile.ZipFile(ROOT / timeline.SOURCE) as archive:
        doc = ET.fromstring(archive.read("word/document.xml"))
        paragraphs = doc.findall(".//w:body//w:p", timeline.NS)
        for paragraph in paragraphs:
            text = "".join(
                t.text or "" for t in paragraph.findall(".//w:t", timeline.NS)
            ).strip()
            if text:
                assert text in plain
        rels = ET.fromstring(archive.read("word/_rels/document.xml.rels"))
        for rel in rels:
            if rel.get("Type", "").endswith("/hyperlink"):
                assert rel.get("Target") in content
    assert counts["tables"] == len(doc.findall(".//w:tbl", timeline.NS))
    assert counts["images"] == len(assets) > 0


def test_check_refuses_stale_export_or_obsolete_asset(tmp_path):
    for name in ("Research", "manifests"):
        shutil.copytree(ROOT / name, tmp_path / name)
    assert timeline.check(tmp_path)["status"] == "current"
    old = tmp_path / "Research/timeline_assets/obsolete.png"
    old.write_bytes(b"obsolete synthetic asset")
    with pytest.raises(ValueError, match="obsolete"):
        timeline.check(tmp_path)
    old.unlink()
    (tmp_path / timeline.WEB).write_text("stale", encoding="utf-8")
    with pytest.raises(ValueError, match="stale"):
        timeline.check(tmp_path)
