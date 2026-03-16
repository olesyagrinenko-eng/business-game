#!/usr/bin/env python3
"""Экспорт сценариев из Excel (лист СВОД) в JSON для веб-игры."""
import openpyxl
import json
import os

BASE = os.path.dirname(os.path.abspath(__file__))
# Путь к Excel: задайте через аргумент или положите файл в родительскую папку
DEFAULT_EXCEL = os.path.join(os.path.dirname(BASE), "Страт.сессия_бизнес кейс_03.03.26.xlsx")

# Раунды 1-6: индекс первой строки сценариев (0-based). Строка «Прошлая неделя» — на 1 выше, не включаем.
# Колонки по листу СВОД: team1 [4]=SH [5]=orders [6]=OPH [7]=CTE [10]=CPO [16]=DCPO [17]=DC [19]=+/-
# team2 [28]=SH [29]=orders [30]=OPH [31]=CTE [34]=CPO [40]=DCPO [41]=DC [43]=+/-
ROUND_DATA_START = {
    1: 38,   # первая строка сценариев раунда 1 (после «Прошлая неделя»)
    2: 62,
    3: 88,
    4: 114,
    5: 144,
    6: 170,
}

def round_value(v):
    if v is None: return None
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        if abs(v - round(v)) < 1e-6: return int(round(v))
        return round(v, 2)
    return v

def main():
    import sys
    excel_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_EXCEL
    if not os.path.isfile(excel_path):
        print("Файл не найден:", excel_path)
        print("Использование: python export_scenarios.py [путь/к/файлу.xlsx]")
        sys.exit(1)
    wb = openpyxl.load_workbook(excel_path, read_only=True, data_only=True)
    ws = wb["СВОД"]
    rows = list(ws.iter_rows(values_only=True))
    wb.close()

    # Доп. вводные по раундам (собираем строки между "Доп. вводные N раунда" и "Коэф.изм.")
    rounds_intro = {}
    for r in ROUND_DATA_START:
        start = ROUND_DATA_START[r] - 6  # примерно где "Доп. вводные"
        intro = []
        for i in range(start, start + 6):
            if i < 0: continue
            row = rows[i]
            if row and len(row) > 1 and row[1] and isinstance(row[1], str):
                if "Коэф" in str(row[1]): break
                if "Доп. вводные" in str(row[1]) or (isinstance(row[0], (int, float)) and row[1]):
                    intro.append(str(row[1]).strip())
        rounds_intro[r] = [x for x in intro if x and "Доп. вводные" not in x]

    scenarios = {}
    coefs = [-0.1, 0, 0.2, 0.4]

    for round_num in ROUND_DATA_START:
        scenarios[str(round_num)] = {}
        start = ROUND_DATA_START[round_num]
        for i in range(16):
            row = rows[start + i]
            if not row or row[1] is None: continue
            c1, c2 = row[1], row[2]
            if c1 not in coefs or c2 not in coefs: continue
            key = f"{c1}_{c2}"
            def opt_row(rw, idx):
                if not rw or len(rw) <= idx or rw[idx] is None: return None
                return round_value(rw[idx])
            scenarios[str(round_num)][key] = {
                "team1": {
                    "SH": opt_row(row, 4),
                    "orders": opt_row(row, 5),
                    "OPH": opt_row(row, 6),
                    "CTE": round_value(row[7]),
                    "CPO": round_value(row[10]),
                    "DCPO": round_value(row[16]),
                    "DC": round_value(row[17]),
                    "CTE_in_target": row[19] == "+" if len(row) > 19 else False,
                    "place_DC": int(row[20]) if len(row) > 20 and row[20] is not None and isinstance(row[20], (int, float)) else None,
                },
                "team2": {
                    "SH": opt_row(row, 28),
                    "orders": opt_row(row, 29),
                    "OPH": opt_row(row, 30),
                    "CTE": round_value(row[31]),
                    "CPO": round_value(row[34]),
                    "DCPO": round_value(row[40]),
                    "DC": round_value(row[41]),
                    "CTE_in_target": row[43] == "+" if len(row) > 43 else False,
                    "place_DC": int(row[44]) if len(row) > 44 and row[44] is not None and isinstance(row[44], (int, float)) else None,
                },
            }

    out = {
        "rounds_intro": rounds_intro,
        "scenarios": scenarios,
        "common_intro": [
            "В городе 2 конкурента (Команда 1 и Команда 2)",
            "У каждого конкурента одинаковое кол-во курьеров, больше курьеров нет",
            "Мы живем в идеальном мире, где нет перетока курьеров, нет суржа и пр.",
            "В стране санкции, поэтому пользователи не могут скачать приложение конкурента и сделать заказ там",
            "Задача: удержать CTE в таргете при максимальной марже (DC = Direct Contribution)",
        ],
        "coefficients": [
            {"value": -0.1, "label": "-10%"},
            {"value": 0, "label": "0%"},
            {"value": 0.2, "label": "+20%"},
            {"value": 0.4, "label": "+40%"},
        ],
    }

    out_path = os.path.join(BASE, "data", "scenarios.json")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    # Сохраняем initial_metrics и common_intro_by_round из текущего JSON, если есть
    if os.path.isfile(out_path):
        try:
            with open(out_path, "r", encoding="utf-8") as f:
                existing = json.load(f)
            out["initial_metrics"] = existing.get("initial_metrics", {})
            out["common_intro_by_round"] = existing.get("common_intro_by_round", {})
        except Exception:
            pass
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print("Exported to", out_path)

if __name__ == "__main__":
    main()
