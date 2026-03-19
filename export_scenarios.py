#!/usr/bin/env python3
"""Экспорт сценариев из Excel (лист СВОД) в JSON для веб-игры."""
import openpyxl
import json
import os

BASE = os.path.dirname(os.path.abspath(__file__))
# Путь к Excel: задайте через аргумент или положите файл в родительскую папку
DEFAULT_EXCEL = os.path.join(os.path.dirname(BASE), "Страт.сессия_бизнес кейс_03.03.26.xlsx")

# Колонки по листу СВОД: team1 [4]=SH [5]=orders [6]=OPH [7]=CTE [10]=CPO [16]=DCPO [17]=DC [19]=+/-
# team2 [28]=SH [29]=orders [30]=OPH [31]=CTE [34]=CPO [40]=DCPO [41]=DC [43]=+/-
# Собираем все строки с коэф. и числовым DC, затем по 16 штук на раунд (пропуская «Прошлая неделя»).

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

    # Собираем все строки с коэффициентами и числовым DC (исключаем «Прошлая неделя» по row[0])
    coefs = [-0.1, 0, 0.2, 0.4]
    data_rows = []
    for idx, row in enumerate(rows):
        if not row or len(row) < 44: continue
        v0 = row[0]
        if v0 and isinstance(v0, str) and "Прошлая неделя" in str(v0):
            continue
        c1, c2 = row[1], row[2]
        dc1 = row[17] if len(row) > 17 else None
        if c1 not in coefs or c2 not in coefs: continue
        if not isinstance(dc1, (int, float)) or not dc1 or dc1 < 1000:
            continue
        data_rows.append(row)

    print("Найдено строк сценариев: %d (нужно 96 для 6 раундов по 16)" % len(data_rows))
    if len(data_rows) < 16 * 6:
        print("Внимание: данных меньше 96 — проверьте структуру листа СВОД.")

    # По 16 сценариев на раунд
    scenarios = {}
    def opt_row(rw, idx):
        if not rw or len(rw) <= idx or rw[idx] is None: return None
        return round_value(rw[idx])
    for round_num in range(1, 7):
        scenarios[str(round_num)] = {}
        start_idx = (round_num - 1) * 16
        for i in range(16):
            if start_idx + i >= len(data_rows):
                break
            row = data_rows[start_idx + i]
            c1, c2 = row[1], row[2]
            key = f"{c1}_{c2}"
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

    # Доп. вводные по раундам (ищем блоки «Доп. вводные N раунда» по листу)
    rounds_intro = {str(r): [] for r in range(1, 7)}
    for idx, row in enumerate(rows):
        if not row or len(row) < 2: continue
        v1 = row[1]
        if not v1 or not isinstance(v1, str): continue
        if "Доп. вводные" in v1 and "раунда" in v1.lower():
            intro = []
            for j in range(idx + 1, min(idx + 8, len(rows))):
                rw = rows[j]
                if not rw or len(rw) < 2: continue
                if rw[1] and "Коэф" in str(rw[1]): break
                if rw[1] and isinstance(rw[1], str) and "Доп. вводные" not in rw[1]:
                    intro.append(str(rw[1]).strip())
            try:
                rn = int("".join(c for c in v1 if c.isdigit()) or "1")
                if 1 <= rn <= 6:
                    rounds_intro[str(rn)] = [x for x in intro if x]
            except ValueError:
                pass

    out = {
        "rounds_intro": rounds_intro,
        "scenarios": scenarios,
        "common_intro": [
            "В городе 2 конкурента (Команда 1 и Команда 2)",
            "У каждого конкурента одинаковое количество курьеров, больше курьеров нет",
            "Мы живем в идеальном мире, где нет перетока курьеров, нет суржа и прочего подобного",
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
