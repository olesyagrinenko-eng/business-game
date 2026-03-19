#!/usr/bin/env python3
"""Импорт scenarios.json напрямую из Excel (лист СВОД) без openpyxl.

Причина: в окружении openpyxl может падать на некоторых xlsx (segfault),
поэтому читаем OOXML как zip/xml.

Использование:
  python3 scripts/import_svod_xlsx.py "/abs/path/to/СВОД.xlsx"
"""
import json
import re
import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

NS = {
    "m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "pr": "http://schemas.openxmlformats.org/package/2006/relationships",
}

COEFS = {-0.1, 0, 0.2, 0.4}


def _num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _tf(v):
    if v == "+":
        return True
    if v == "-":
        return False
    return bool(v)


def _key_of(a, b):
    def part(x):
        x = float(x)
        if abs(x) < 1e-12:
            return "0.0"
        return str(round(x, 1))

    return f"{part(a)}_{part(b)}"


def _load_sheet_rows(xlsx_path, sheet_name="СВОД"):
    with zipfile.ZipFile(xlsx_path) as zf:
        wb = ET.fromstring(zf.read("xl/workbook.xml"))
        rels = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
        rid_to_target = {
            rel.attrib["Id"]: rel.attrib["Target"]
            for rel in rels.findall("pr:Relationship", NS)
        }

        target = None
        for sh in wb.findall("m:sheets/m:sheet", NS):
            if sh.attrib.get("name") == sheet_name:
                rid = sh.attrib.get(
                    "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
                )
                target = "xl/" + rid_to_target[rid]
                break
        if not target:
            raise RuntimeError(f"Лист '{sheet_name}' не найден")

        sst = []
        if "xl/sharedStrings.xml" in zf.namelist():
            sr = ET.fromstring(zf.read("xl/sharedStrings.xml"))
            for si in sr.findall("m:si", NS):
                sst.append("".join((t.text or "") for t in si.findall(".//m:t", NS)))

        sheet = ET.fromstring(zf.read(target))

        def cell_value(c):
            t = c.attrib.get("t")
            v = c.find("m:v", NS)
            if v is None:
                return None
            raw = v.text
            if t == "s":
                return sst[int(raw)] if raw is not None else None
            if t == "b":
                return raw == "1"
            try:
                x = float(raw)
                return int(x) if abs(x - round(x)) < 1e-9 else round(x, 2)
            except Exception:
                return raw

        rows = []
        for row in sheet.findall("m:sheetData/m:row", NS):
            rnum = int(row.attrib["r"])
            d = {}
            for c in row.findall("m:c", NS):
                col = re.sub(r"\d+", "", c.attrib.get("r", ""))
                d[col] = cell_value(c)
            rows.append((rnum, d))
        return rows


def build_from_xlsx(xlsx_path, scenarios_json_path):
    with open(scenarios_json_path, "r", encoding="utf-8") as f:
        out = json.load(f)

    rows = _load_sheet_rows(xlsx_path, sheet_name="СВОД")

    initial = None
    scenario_rows = []
    for _, d in rows:
        a, b, c = d.get("A"), d.get("B"), d.get("C")
        if isinstance(a, str) and "Прошлая неделя" in a and _num(b) and _num(c):
            initial = d
        if _num(b) and _num(c) and float(b) in COEFS and float(c) in COEFS and _num(d.get("R")) and _num(d.get("AP")):
            if isinstance(a, str) and "Прошлая неделя" in a:
                continue
            scenario_rows.append(d)

    if len(scenario_rows) < 96:
        raise RuntimeError(f"Найдено сценариев {len(scenario_rows)}, ожидалось >=96")
    scenario_rows = scenario_rows[:96]

    scenarios = {str(r): {} for r in range(1, 7)}
    for i, d in enumerate(scenario_rows):
        rnd = i // 16 + 1
        b, c = float(d["B"]), float(d["C"])
        key = _key_of(b, c)
        scenarios[str(rnd)][key] = {
            "team1": {
                "SH": d.get("E"),
                "orders": d.get("F"),
                "OPH": d.get("G"),
                "CTE": d.get("H"),
                "CPO": d.get("K"),
                "DCPO": d.get("Q"),
                "DC": d.get("R"),
                "CTE_in_target": _tf(d.get("T")),
                "place_DC": d.get("U"),
                "surge_prev": d.get("I"),
                "surge_curr": d.get("I"),
                "fallback_share": d.get("L"),
                "cpo_total": d.get("M"),
                "writeoffs": d.get("N"),
            },
            "team2": {
                "SH": d.get("AC"),
                "orders": d.get("AD"),
                "OPH": d.get("AE"),
                "CTE": d.get("AF"),
                "CPO": d.get("AI"),
                "DCPO": d.get("AO"),
                "DC": d.get("AP"),
                "CTE_in_target": _tf(d.get("AR")),
                "place_DC": d.get("AS"),
                "surge_prev": d.get("AG"),
                "surge_curr": d.get("AG"),
                "fallback_share": d.get("AJ"),
                "cpo_total": d.get("AK"),
                "writeoffs": d.get("AL"),
            },
        }

    if initial:
        im = out.get("initial_metrics", {})
        t1 = im.get("team1", {})
        t2 = im.get("team2", {})
        t1.update({
            "SH": initial.get("E"),
            "orders": initial.get("F"),
            "OPH": round(float(initial.get("G")), 1) if _num(initial.get("G")) else initial.get("G"),
            "CTE": initial.get("H"),
            "CPO": initial.get("K"),
            "DCPO": initial.get("Q"),
            "DC": initial.get("R"),
            "avg_check": initial.get("J"),
            "margin": initial.get("P"),
        })
        t2.update({
            "SH": initial.get("AC"),
            "orders": initial.get("AD"),
            "OPH": round(float(initial.get("AE")), 1) if _num(initial.get("AE")) else initial.get("AE"),
            "CTE": initial.get("AF"),
            "CPO": initial.get("AI"),
            "DCPO": initial.get("AO"),
            "DC": initial.get("AP"),
            "avg_check": initial.get("AH"),
            "margin": initial.get("AN"),
        })
        im["team1"] = t1
        im["team2"] = t2
        out["initial_metrics"] = im

    out["scenarios"] = scenarios

    with open(scenarios_json_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 scripts/import_svod_xlsx.py /abs/path/to/file.xlsx")
        sys.exit(2)
    xlsx_path = Path(sys.argv[1])
    base = Path(__file__).resolve().parents[1]
    json_path = base / "data" / "scenarios.json"
    build_from_xlsx(str(xlsx_path), str(json_path))
    print(f"OK: updated {json_path} from {xlsx_path}")
