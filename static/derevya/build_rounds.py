#!/usr/bin/env python3
"""Генерация round2.html .. round6.html из scenarios.json."""
import json
import os
import re

BASE = os.path.dirname(os.path.abspath(__file__))
# BASE = .../game-web/static/derevya → data = .../game-web/data/scenarios.json
with open(os.path.join(BASE, "..", "..", "data", "scenarios.json"), "r", encoding="utf-8") as f:
    data = json.load(f)

rounds_intro = data.get("rounds_intro", {})
scenarios = data.get("scenarios", {})

# AOV (средний чек) по раундам — из вкладки Деревья (T18=1100, T61=1210 и т.д.)
AOV_BY_ROUND = {"1": 1100, "2": 1155, "3": 1210, "4": 1210, "5": 1270, "6": 1270}

INTROS = {
    "1": "На след.неделе прогнозируют проливные дожди и рост спроса.",
    "2": "На след.неделе прогнозируют проливные дожди и рост спроса. Вы с конкурентом одновременно изобрели механизм суржа, который обрезает заказы, но растит чек.",
    "3": "На след.неделе прогнозируют проливные дожди и рост спроса. Вы с конкурентом одновременно изобрели механизм суржа. На рынке появился сервис Доставки заказов, который вывозит заказы с неоптимальным CTE (макс возможность вывоза - 500 заказов).",
    "4": "Дожди и рост спроса. Сурж. Сервис доставки заказов. Отключили санкции — пользователи могут скачать приложение конкурента и перетекать.",
    "5": "Дожди, сурж, сервис доставки, санкции сняты. У нас не бесконечный склад (АЗ привёз сток под прогноз заказов) + продаём скоропортящиеся товары, которые списываются.",
    "6": "Раунд 6 — условия как в раунде 5. Данные для расчёта взяты из СВОД (раунд 5).",
}

with open(os.path.join(BASE, "round1.html"), "r", encoding="utf-8") as f:
    template = f.read()

# Extract the part we replace: from "const ROUND = " to "};" at end of SCENARIOS (включая раунд 1 — чтобы SH/OPH из scenarios.json)
for r in ["1", "2", "3", "4", "5", "6"]:
    round_num = int(r)
    intro = INTROS.get(r) or " ".join(rounds_intro.get(r, []))
    sc = scenarios.get(r if r != "6" else "5", {})  # round 6 uses round 5 data
    sc_json = json.dumps(sc, ensure_ascii=False)

    content = template
    content = content.replace("const ROUND = 1;", f"const ROUND = {round_num};")
    content = content.replace("Раунд 1</title>", f"Раунд {round_num}</title>")
    content = content.replace('<div class="num" id="roundNum">1</div>', f'<div class="num" id="roundNum">{round_num}</div>')
    content = content.replace("const AOV = 1100;", f"const AOV = {AOV_BY_ROUND.get(r, 1100)};")
    content = re.sub(
        r"const ROUND_INTRO = .*?;",
        "const ROUND_INTRO = " + json.dumps(intro, ensure_ascii=False) + ";",
        content,
        count=1,
        flags=re.DOTALL,
    )
    # Replace SCENARIOS = {...}; by matching braces
    pos = content.find("const SCENARIOS = ")
    start = pos + len("const SCENARIOS = ")
    depth = 0
    i = start
    while i < len(content):
        if content[i] == "{":
            depth += 1
        elif content[i] == "}":
            depth -= 1
            if depth == 0:
                break
        i += 1
    end = i + 2  # "};"
    content = content[:pos] + "const SCENARIOS = " + sc_json + ";" + content[end:]

    out = os.path.join(BASE, f"round{r}.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(content)
    print("Wrote", out)
