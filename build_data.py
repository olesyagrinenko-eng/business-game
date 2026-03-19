#!/usr/bin/env python3
"""Сборка scenarios.json из svod_full.txt (без Excel)."""
import json
import os
import re

BASE = os.path.dirname(os.path.abspath(__file__))
TXT = os.path.join(os.path.dirname(BASE), "svod_full.txt")
OUT = os.path.join(BASE, "data", "scenarios.json")

# Индексы строк в svod_full.txt (0-based). Раунд 6: следующий блок после 5 (140+21=161).
ROUNDS = {
    1: list(range(33, 33 + 16)),
    2: list(range(58, 58 + 16)),
    3: list(range(84, 84 + 16)),
    4: list(range(111, 111 + 16)),
    5: list(range(140, 140 + 16)),
    6: list(range(161, 161 + 16)),
}

# Вводные по раундам. Чтобы убрать строку в каком-то раунде — удалите её из списка для этого раунда.
ROUNDS_INTRO = {
    1: ["На следующей неделе прогнозируют проливные дожди и рост спроса"],
    2: [
        "На следующей неделе прогнозируют проливные дожди и рост спроса",
        "Вы с конкурентом одновременно изобрели механизм суржа, который обрезает заказы, но растит чек",
    ],
    3: [
        "На следующей неделе прогнозируют проливные дожди и рост спроса",
        "Вы с конкурентом одновременно изобрели механизм суржа, который обрезает заказы, но растит чек",
        "На рынке появился сервис Доставки заказов, который вывозит заказы с неоптимальным CTE (максимальная возможность вывоза — 500 заказов)",
    ],
    4: [
        "На следующей неделе прогнозируют проливные дожди и рост спроса",
        "Вы с конкурентом одновременно изобрели механизм суржа, который обрезает заказы, но растит чек",
        "На рынке появился сервис Доставки заказов, который вывозит заказы с неоптимальным CTE (максимальная возможность вывоза — 500 заказов)",
        "Отключили санкции и пользователи теперь могут скачать приложение конкурента и перетекать",
    ],
    5: [
        "На следующей неделе прогнозируют проливные дожди и рост спроса",
        "Вы с конкурентом одновременно изобрели механизм суржа, который обрезает заказы, но растит чек",
        "На рынке появился сервис Доставки заказов, который вывозит заказы с неоптимальным CTE (максимальная возможность вывоза — 500 заказов)",
        "Отключили санкции и пользователи теперь могут скачать приложение конкурента и перетекать",
        "У нас не бесконечный склад: автозаказ привёз запас под прогноз заказов. Мы продаём скоропортящиеся товары, которые списываются",
    ],
    6: [
        "На следующей неделе прогнозируют проливные дожди и рост спроса",
        "Вы с конкурентом одновременно изобрели механизм суржа, который обрезает заказы, но растит чек",
        "На рынке появился сервис Доставки заказов, который вывозит заказы с неоптимальным CTE (максимальная возможность вывоза — 500 заказов)",
        "Отключили санкции и пользователи теперь могут скачать приложение конкурента и перетекать",
        "У нас не бесконечный склад: автозаказ привёз запас под прогноз заказов. Мы продаём скоропортящиеся товары, которые списываются",
        "Штрафы за невыполнение CTE (CTE вне таргета)",
    ],
}

# Строки СВОД с исходными метриками на старте: 12–22 — MPH, CPO, CTE target, CTE факт, SH, OPH, заказы, чек, маржа, DCPO, DC
INITIAL_METRICS_ROWS = list(range(12, 23))
METRIC_KEYS = ["MPH", "CPO", "CTE_target", "CTE", "SH", "OPH", "orders", "avg_check", "margin", "DCPO", "DC"]


def parse_line(line):
    # "33 | (None, 0.4, -0.1, 0.5, 11.33, ...)"
    m = re.search(r"\((.+)\)", line)
    if not m:
        return None
    s = m.group(1)
    parts = [p.strip() for p in s.split(",")]
    out = []
    for p in parts:
        if p == "None":
            out.append(None)
        elif p in ("'+'", '"+"', "+"):
            out.append("+")
        elif p in ("'-'", '"-"', "-"):
            out.append("-")
        else:
            try:
                out.append(float(p))
            except ValueError:
                out.append(p)
    return out


def main():
    with open(TXT, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # В файле строка может быть "34:33 | (None, 0.4, ...)" или "33 | (...)" — берём всё после "| "
    def get_content(ln):
        return ln.split("|", 1)[-1].strip() if "|" in ln else ln.strip()

    # Исходные метрики на старте (серая строка)
    initial_metrics = {"team1": {}, "team2": {}}
    for i, row_idx in enumerate(INITIAL_METRICS_ROWS):
        if row_idx >= len(lines):
            break
        parts = parse_line(get_content(lines[row_idx]))
        if not parts or len(parts) < 6:
            continue
        key = METRIC_KEYS[i] if i < len(METRIC_KEYS) else ("m%d" % i)
        v1 = parts[2] if isinstance(parts[2], (int, float)) else None
        v2 = parts[5] if len(parts) > 5 and isinstance(parts[5], (int, float)) else None
        if v1 is not None:
            initial_metrics["team1"][key] = round(v1, 2) if isinstance(v1, float) else v1
        if v2 is not None:
            initial_metrics["team2"][key] = round(v2, 2) if isinstance(v2, float) else v2

    scenarios = {}
    for r, row_indices in ROUNDS.items():
        scenarios[str(r)] = {}
        for idx in row_indices:
            if idx >= len(lines):
                continue
            parts = parse_line(get_content(lines[idx]))
            if not parts or len(parts) < 23:
                continue
            c1, c2 = parts[1], parts[2]
            if c1 is None or c2 is None:
                continue
            key = f"{c1}_{c2}"
            def rv(x):
                if x is None: return None
                if isinstance(x, float) and x == int(x): return int(x)
                return round(x, 2) if isinstance(x, float) else x

            # СВОД: по сценарию есть SH, Заказы, OPH, CTE, ... Общий CPO, DCPO, DC и т.д.
            # Текущая раскладка: 4=CTE1, 5=CPO1, 6=DCPO1, 7=DC1, 8=+/-, 9=place; 17–22=team2.
            # Если в svod_full.txt колонки идут как SH, Заказы, OPH, CTE... — то 3=SH1, 4=orders1, 5=OPH1 или сдвиг; при необходимости поправьте индексы ниже.
            def opt(i):
                return rv(parts[i]) if len(parts) > i and parts[i] is not None else None
            scenarios[str(r)][key] = {
                "team1": {
                    "CTE": rv(parts[4]),
                    "CPO": rv(parts[5]),
                    "DCPO": rv(parts[6]),
                    "DC": rv(parts[7]),
                    "CTE_in_target": parts[8] == "+",
                    "place_DC": int(parts[9]) if parts[9] is not None else None,
                    "SH": opt(10),
                    "orders": opt(11),
                    "OPH": opt(12),
                },
                "team2": {
                    "CTE": rv(parts[17]),
                    "CPO": rv(parts[18]),
                    "DCPO": rv(parts[19]),
                    "DC": rv(parts[20]),
                    "CTE_in_target": parts[21] == "+" if len(parts) > 21 else False,
                    "place_DC": int(parts[22]) if len(parts) > 22 and parts[22] is not None else None,
                    "SH": opt(23),
                    "orders": opt(24),
                    "OPH": opt(25),
                },
            }

    # Общие вводные зависят от раунда: часть пунктов убирается (по правилам из СВОД).
    # hide_from_round = с какого раунда пункт скрывать (2 = показывать только в р1; 3 = в р1–2 и т.д.).
    COMMON_INTRO_ITEMS = [
        ("В городе 2 конкурента (Конкурент 1 и Конкурент 2)", None),
        ("У каждого конкурента одинаковое количество курьеров, больше курьеров нет, мы можем только переманивать их у конкурента", None),
        ("Мы живем в идеальном мире, где нет суржа", 2),   # убрать для раундов 2–6 → показывать только в р1
        ("Мы живем в идеальном мире, где нет фолл-бэка", 3),  # убрать для 3–6 → показывать в р1–2
        ("В стране санкции, поэтому пользователи не могут скачать приложение конкурента и сделать заказ там", 4),  # убрать для 4–6
        ("У нас неограниченный склад (поэтому продажи могут вырасти безлимитно), а списаний нет, так как продаем нескоропортящиеся товары", 5),  # убрать для 5–6
        ("Нет никаких штрафных санкций или поощрений за выполнение CTE", 6),  # убрать для раунда 6
        ("Задача: удержать CTE в таргете при максимальной марже (DC = Direct Contribution)", None),
    ]

    def intro_for_round(r):
        return [text for text, hide_from in COMMON_INTRO_ITEMS if hide_from is None or r < hide_from]

    max_r = max(ROUNDS_INTRO.keys()) if ROUNDS_INTRO else 5
    common_intro_by_round = {str(r): intro_for_round(r) for r in range(1, max_r + 1)}

    out = {
        "common_intro_by_round": common_intro_by_round,
        "rounds_intro": {str(k): v for k, v in ROUNDS_INTRO.items()},
        "initial_metrics": initial_metrics,
        "scenarios": scenarios,
        "coefficients": [
            {"value": -0.1, "label": "-10%"},
            {"value": 0, "label": "0%"},
            {"value": 0.2, "label": "+20%"},
            {"value": 0.4, "label": "+40%"},
        ],
    }

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print("OK:", OUT)


if __name__ == "__main__":
    main()
