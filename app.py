# -*- coding: utf-8 -*-
"""
Веб-приложение бизнес-игры для франчайзи.
Запуск: python app.py
Участники: регистрация по имени команды, выбор коэффициента в каждом раунде.
Экран: вводные, задания, результаты раундов, карта 4 квадрантов.
"""
import json
import os
from flask import Flask, request, jsonify, send_from_directory

app = Flask(__name__, static_folder="static", static_url_path="")
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
with open(os.path.join(DATA_DIR, "scenarios.json"), "r", encoding="utf-8") as f:
    DATA = json.load(f)

# In-memory state (для одного мероприятия)
teams = []  # [{"id": 1, "name": "Команда А", "role": 1|2, "pair_id": 0}, ...]
pairs = []  # [{"team1_id": 1, "team2_id": 2}, ...]
choices = {}  # {(team_id, round): coefficient}
current_round = 1
max_rounds = 5


def get_pair_id(team_id):
    for i, p in enumerate(pairs):
        if p.get("team1_id") == team_id or p.get("team2_id") == team_id:
            return i
    return None


def get_opponent_choice(team_id, r):
    pid = get_pair_id(team_id)
    if pid is None:
        return None
    p = pairs[pid]
    other_id = p["team2_id"] if p["team1_id"] == team_id else p["team1_id"]
    return choices.get((other_id, r))


def get_scenario_result(r, coef1, coef2):
    # Ключи в JSON вида "0.4_-0.1", "0.0_0.0" — приводим к float для совпадения
    key = f"{float(coef1)}_{float(coef2)}"
    scenarios = DATA.get("scenarios", {}).get(str(r), {})
    return scenarios.get(key)


@app.route("/")
def index():
    return send_from_directory("static", "index.html")


@app.route("/screen")
def screen():
    return send_from_directory("static", "screen.html")


@app.route("/api/data")
def api_data():
    """Общие данные: вводные, коэффициенты, количество раундов."""
    return jsonify({
        "common_intro": DATA.get("common_intro", []),
        "rounds_intro": DATA.get("rounds_intro", {}),
        "coefficients": DATA.get("coefficients", []),
        "max_rounds": max_rounds,
    })


@app.route("/api/register", methods=["POST"])
def api_register():
    """Регистрация команды. Возвращает team_id, role (1 или 2), pair_id."""
    name = (request.get_json() or {}).get("name", "").strip()
    if not name:
        return jsonify({"error": "Укажите название команды"}), 400
    if any(t["name"] == name for t in teams):
        return jsonify({"error": "Такое название уже занято"}), 400

    team_id = len(teams) + 1
    # Чётная команда — Команда 2 в новой паре, нечётная — Команда 1
    if team_id % 2 == 1:
        role = 1
        pairs.append({"team1_id": team_id, "team2_id": None})
        pair_id = len(pairs) - 1
    else:
        role = 2
        pair_id = len(pairs) - 1
        pairs[pair_id]["team2_id"] = team_id

    teams.append({"id": team_id, "name": name, "role": role, "pair_id": pair_id})
    return jsonify({"team_id": team_id, "name": name, "role": role, "pair_id": pair_id})


@app.route("/api/state")
def api_state():
    """Состояние для команды или для экрана."""
    team_id = request.args.get("team_id", type=int)
    if team_id:
        t = next((x for x in teams if x["id"] == team_id), None)
        if not t:
            return jsonify({"error": "Команда не найдена"}), 404
        my_choice = choices.get((team_id, current_round))
        opp_choice = get_opponent_choice(team_id, current_round)
        result = None
        if my_choice is not None and opp_choice is not None:
            pid = get_pair_id(team_id)
            p = pairs[pid]
            c1 = choices.get((p["team1_id"], current_round))
            c2 = choices.get((p["team2_id"], current_round))
            if c1 is not None and c2 is not None:
                res = get_scenario_result(current_round, c1, c2)
                if res:
                    result = res["team1"] if t["role"] == 1 else res["team2"]
        return jsonify({
            "team_id": team_id,
            "name": t["name"],
            "role": t["role"],
            "current_round": current_round,
            "my_choice": my_choice,
            "opponent_choice": opp_choice,
            "result": result,
            "rounds_done": [r for r in range(1, current_round) if (team_id, r) in choices],
        })
    # Экран: общее состояние
    return jsonify({
        "current_round": current_round,
        "teams": [{"id": t["id"], "name": t["name"], "role": t["role"]} for t in teams],
        "pairs": [{"team1_id": p["team1_id"], "team2_id": p["team2_id"]} for p in pairs],
        "choices": {f"{tid}_{r}": c for (tid, r), c in choices.items()},
    })


@app.route("/api/choice", methods=["POST"])
def api_choice():
    """Отправить выбор коэффициента за текущий раунд."""
    body = request.get_json() or {}
    team_id = body.get("team_id")
    value = body.get("value")
    if team_id is None or value is None:
        return jsonify({"error": "Нужны team_id и value"}), 400
    coefs = [c["value"] for c in DATA.get("coefficients", [])]
    if value not in coefs:
        return jsonify({"error": "Недопустимый коэффициент"}), 400
    if not any(t["id"] == team_id for t in teams):
        return jsonify({"error": "Команда не найдена"}), 404
    choices[(team_id, current_round)] = value
    return jsonify({"ok": True, "round": current_round})


@app.route("/api/reset", methods=["POST"])
def api_reset():
    """Сбросить игру: очистить команды, пары, ответы, раунд 1. Для ведущего с экрана."""
    global teams, pairs, choices, current_round
    teams = []
    pairs = []
    choices = {}
    current_round = 1
    return jsonify({"ok": True, "message": "Игра сброшена. Попросите участников нажать «Войти заново» на телефонах."})


@app.route("/api/round", methods=["POST"])
def api_round():
    """Переключить раунд (для ведущего с экрана)."""
    global current_round
    r = (request.get_json() or {}).get("round")
    if r is not None and 1 <= r <= max_rounds:
        current_round = r
        return jsonify({"current_round": current_round})
    return jsonify({"error": "round от 1 до 5"}), 400


@app.route("/api/results")
def api_results():
    """Итоги по всем командам за все раунды: сумма DC, доля раундов в таргете по CTE."""
    results = []
    for t in teams:
        total_dc = 0
        cte_ok_count = 0
        for r in range(1, max_rounds + 1):
            c = choices.get((t["id"], r))
            if c is None:
                continue
            pid = get_pair_id(t["id"])
            if pid is None:
                continue
            p = pairs[pid]
            c1 = choices.get((p["team1_id"], r))
            c2 = choices.get((p["team2_id"], r))
            if c1 is None or c2 is None:
                continue
            res = get_scenario_result(r, c1, c2)
            if not res:
                continue
            side = res["team1"] if t["role"] == 1 else res["team2"]
            dc = side.get("DC")
            if isinstance(dc, (int, float)):
                total_dc += dc
            if side.get("CTE_in_target"):
                cte_ok_count += 1
        results.append({
            "team_id": t["id"],
            "name": t["name"],
            "role": t["role"],
            "total_dc": round(total_dc, 0),
            "cte_ok_rounds": cte_ok_count,
            "rounds_played": sum(1 for r in range(1, max_rounds + 1) if (t["id"], r) in choices),
        })
    # Медиана DC для квадрантов
    dcs = [x["total_dc"] for x in results if x["total_dc"]]
    median_dc = sorted(dcs)[len(dcs) // 2] if dcs else 0
    for x in results:
        x["quadrant"] = None
        if x["rounds_played"] < max_rounds:
            continue
        high_dc = x["total_dc"] >= median_dc
        cte_ok = x["cte_ok_rounds"] >= (max_rounds / 2)
        if high_dc and cte_ok:
            x["quadrant"] = "top_right"
        elif high_dc and not cte_ok:
            x["quadrant"] = "top_left"
        elif not high_dc and cte_ok:
            x["quadrant"] = "bottom_right"
        else:
            x["quadrant"] = "bottom_left"
    return jsonify({"results": results, "median_dc": median_dc})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    app.run(host="0.0.0.0", port=port, debug=os.environ.get("FLASK_DEBUG") == "1")
