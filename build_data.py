#!/usr/bin/env python3
"""Сборка scenarios.json из svod_full.txt (без Excel)."""
import json
import os
import re

BASE = os.path.dirname(os.path.abspath(__file__))
TXT = os.path.join(os.path.dirname(BASE), "svod_full.txt")
OUT = os.path.join(BASE, "data", "scenarios.json")

    # Индексы строк в svod_full.txt (0-based). Данные раунда 1: строки 33-48, раунд 2: 58-73, и т.д.
ROUNDS = {
    1: list(range(33, 33 + 16)),
    2: list(range(58, 58 + 16)),
    3: list(range(84, 84 + 16)),
    4: list(range(111, 111 + 16)),
    5: list(range(140, 140 + 16)),
}

ROUNDS_INTRO = {
    1: ["На след.неделе прогнозируют проливные дожди и рост спроса"],
    2: [
        "На след.неделе прогнозируют проливные дожди и рост спроса",
        "Вы с конкурентом одновременно изобрели механизм суржа, который обрезает заказы, но растит чек",
    ],
    3: [
        "На след.неделе прогнозируют проливные дожди и рост спроса",
        "Вы с конкурентом одновременно изобрели механизм суржа, который обрезает заказы, но растит чек",
        "На рынке появился сервис Доставки заказов, который вывозит заказы с неоптимальным CTE (макс возможность вывоза - 500 заказов)",
    ],
    4: [
        "На след.неделе прогнозируют проливные дожди и рост спроса",
        "Вы с конкурентом одновременно изобрели механизм суржа, который обрезает заказы, но растит чек",
        "На рынке появился сервис Доставки заказов, который вывозит заказы с неоптимальным CTE (макс возможность вывоза - 500 заказов)",
        "Отключили санкции и пользователи теперь могут скачать приложение конкурента и перетекать",
    ],
    5: [
        "На след.неделе прогнозируют проливные дожди и рост спроса",
        "Вы с конкурентом одновременно изобрели механизм суржа, который обрезает заказы, но растит чек",
        "На рынке появился сервис Доставки заказов, который вывозит заказы с неоптимальным CTE (макс возможность вывоза - 500 заказов)",
        "Отключили санкции и пользователи теперь могут скачать приложение конкурента и перетекать",
        "У нас не бесконечный склад (АЗ привез сток под прогноз заказов) + мы продаем скоропортящиеся товары, которые списываются",
    ],
}


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
            scenarios[str(r)][key] = {
                "team1": {
                    "CTE": rv(parts[4]),
                    "CPO": rv(parts[5]),
                    "DCPO": rv(parts[6]),
                    "DC": rv(parts[7]),
                    "CTE_in_target": parts[8] == "+",
                    "place_DC": int(parts[9]) if parts[9] is not None else None,
                },
                "team2": {
                    "CTE": rv(parts[18]),
                    "CPO": rv(parts[19]),
                    "DCPO": rv(parts[20]),
                    "DC": rv(parts[21]),
                    "CTE_in_target": parts[22] == "+",
                    "place_DC": int(parts[23]) if len(parts) > 23 and parts[23] is not None else None,
                },
            }

    out = {
        "common_intro": [
            "В городе 2 конкурента (Команда 1 и Команда 2)",
            "У каждого конкурента одинаковое кол-во курьеров, больше курьеров нет",
            "Мы живем в идеальном мире, где нет перетока курьеров, нет суржа и пр.",
            "В стране санкции, поэтому пользователи не могут скачать приложение конкурента и сделать заказ там",
            "Задача: удержать CTE в таргете при максимальной марже (DC = Direct Contribution)",
        ],
        "rounds_intro": ROUNDS_INTRO,
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
