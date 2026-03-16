# -*- coding: utf-8 -*-
"""
Веб-приложение бизнес-игры для франчайзи.
Запуск: python app.py
Участники: регистрация по имени команды, выбор коэффициента в каждом раунде.
Экран: вводные, задания, результаты раундов, карта 4 квадрантов.
"""
import json
import os
import sys
from flask import Flask, request, jsonify, send_from_directory

# Корень приложения (каталог, где лежит app.py) — так же работает на Render
APP_ROOT = os.path.abspath(os.path.dirname(__file__))
app = Flask(__name__, static_folder=os.path.join(APP_ROOT, "static"), static_url_path="")
DATA_PATH = os.path.join(APP_ROOT, "data", "scenarios.json")

try:
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        DATA = json.load(f)
except FileNotFoundError:
    print("ERROR: data/scenarios.json not found at", DATA_PATH, file=sys.stderr)
    DATA = {"common_intro": [], "rounds_intro": {}, "scenarios": {}, "coefficients": [], "initial_metrics": {}}
except Exception as e:
    print("ERROR loading scenarios.json:", e, file=sys.stderr)
    DATA = {"common_intro": [], "rounds_intro": {}, "scenarios": {}, "coefficients": [], "initial_metrics": {}}

# In-memory state (для одного мероприятия)
teams = []  # [{"id": 1, "name": "Команда А", "role": 1|2, "pair_id": 0}, ...]
pairs = []  # [{"team1_id": 1, "team2_id": 2}, ...]
choices = {}  # {(team_id, round): coefficient}
current_round = 1
max_rounds = 5
expected_teams = None  # ожидаемое кол-во команд (задаёт ведущий), None = не задано


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


@app.route("/health")
def health():
    """Проверка для Render и отладки: сервер отвечает без загрузки данных."""
    return jsonify({"status": "ok", "data_loaded": bool(DATA.get("scenarios"))}), 200


@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.route("/screen")
def screen():
    return send_from_directory(app.static_folder, "screen.html")


@app.route("/api/data")
def api_data():
    """Общие данные: вводные, коэффициенты, количество раундов, ожидаемое кол-во команд, исходные метрики."""
    return jsonify({
        "common_intro": DATA.get("common_intro", []),
        "rounds_intro": DATA.get("rounds_intro", {}),
        "coefficients": DATA.get("coefficients", []),
        "initial_metrics": DATA.get("initial_metrics", {}),
        "max_rounds": max_rounds,
        "expected_teams": expected_teams,
        "teams_count": len(teams),
    })


@app.route("/api/settings", methods=["GET", "POST"])
def api_settings():
    """Получить или задать настройки (ожидаемое кол-во команд)."""
    global expected_teams
    if request.method == "POST":
        body = request.get_json() or {}
        n = body.get("expected_teams")
        if n is not None:
            n = int(n) if n else None
            if n is not None and (n < 2 or n > 50):
                return jsonify({"error": "Укажите число от 2 до 50 (чётное для пар)"}), 400
            expected_teams = n
        return jsonify({"expected_teams": expected_teams})
    return jsonify({"expected_teams": expected_teams, "teams_count": len(teams)})


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
                    if result and result.get("DC") in ("+", "-"):
                        result = {**result, "DC": None}
        # История раундов: что делали я и конкурент, результат по каждому
        results_by_round = []
        for r in range(1, current_round + 1):
            my_c = choices.get((team_id, r))
            opp_c = get_opponent_choice(team_id, r)
            res_r = None
            if my_c is not None and opp_c is not None:
                pid = get_pair_id(team_id)
                if pid is not None:
                    p = pairs[pid]
                    c1 = choices.get((p["team1_id"], r))
                    c2 = choices.get((p["team2_id"], r))
                    if c1 is not None and c2 is not None:
                        sr = get_scenario_result(r, c1, c2)
                        if sr:
                            res_r = sr["team1"] if t["role"] == 1 else sr["team2"]
                            if res_r and res_r.get("DC") in ("+", "-"):
                                res_r = {**res_r, "DC": None}
            results_by_round.append({
                "round": r,
                "my_choice": my_c,
                "opponent_choice": opp_c,
                "result": res_r,
            })
        return jsonify({
            "team_id": team_id,
            "name": t["name"],
            "role": t["role"],
            "current_round": current_round,
            "my_choice": my_choice,
            "opponent_choice": opp_choice,
            "result": result,
            "results_by_round": results_by_round,
            "rounds_done": [r for r in range(1, current_round) if (team_id, r) in choices],
        })
    # Экран: общее состояние
    # Все ли пары ответили в текущем раунде
    round_complete = True
    if pairs:
        for p in pairs:
            if p.get("team2_id") is None:
                round_complete = False
                break
            c1 = choices.get((p["team1_id"], current_round))
            c2 = choices.get((p["team2_id"], current_round))
            if c1 is None or c2 is None:
                round_complete = False
                break
    else:
        round_complete = False
    return jsonify({
        "current_round": current_round,
        "round_complete": round_complete,
        "expected_teams": expected_teams,
        "teams_count": len(teams),
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
    """Итоги: по раундам 1–4 только пораундовые DC/CTE; сумма только за 5 раундов. Квадранты по приросту маржи к прошлой неделе (DC_5 - DC_1)."""
    up_to_round = request.args.get("round", type=int)
    if up_to_round is None or up_to_round < 1 or up_to_round > max_rounds:
        up_to_round = max_rounds
    rounds_consider = list(range(1, up_to_round + 1))
    results = []
    for t in teams:
        per_round = []
        total_dc = 0
        cte_ok_count = 0
        dc_by_round = {}
        for r in rounds_consider:
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
                dc_by_round[r] = dc
            cte_ok = side.get("CTE_in_target", False)
            if cte_ok:
                cte_ok_count += 1
            per_round.append({"round": r, "dc": round(dc, 0) if isinstance(dc, (int, float)) else None, "cte_ok": cte_ok})
        rounds_played = sum(1 for r in rounds_consider if (t["id"], r) in choices)
        # Сумма DC показываем только по итогам 5 раундов
        show_total = up_to_round == max_rounds and rounds_played >= 1
        dc_growth = None
        if 1 in dc_by_round and max_rounds in dc_by_round and rounds_played >= max_rounds:
            dc_growth = dc_by_round[max_rounds] - dc_by_round[1]
        results.append({
            "team_id": t["id"],
            "name": t["name"],
            "role": t["role"],
            "per_round": per_round,
            "total_dc": round(total_dc, 0) if show_total else None,
            "cte_ok_rounds": cte_ok_count,
            "rounds_played": rounds_played,
            "dc_growth": round(dc_growth, 0) if dc_growth is not None else None,
        })
    # Квадранты: по приросту маржи (DC_5 - DC_1). Выше медианы прироста = молодцы
    growths = [x["dc_growth"] for x in results if x["dc_growth"] is not None]
    median_growth = sorted(growths)[len(growths) // 2] if growths else 0
    for x in results:
        x["quadrant"] = None
        if x["rounds_played"] < 1 or (up_to_round < max_rounds and x["rounds_played"] < up_to_round):
            continue
        if up_to_round < max_rounds:
            # До 5 раунда квадрант не считаем по приросту (нет DC_5 - DC_1)
            continue
        high_growth = x["dc_growth"] is not None and x["dc_growth"] >= median_growth
        cte_ok = x["cte_ok_rounds"] >= (x["rounds_played"] / 2)
        if high_growth and cte_ok:
            x["quadrant"] = "top_right"
        elif high_growth and not cte_ok:
            x["quadrant"] = "top_left"
        elif not high_growth and cte_ok:
            x["quadrant"] = "bottom_right"
        else:
            x["quadrant"] = "bottom_left"
    return jsonify({
        "results": results,
        "median_dc_growth": median_growth,
        "up_to_round": up_to_round,
        "show_total_only_after_round_5": True,
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    app.run(host="0.0.0.0", port=port, debug=os.environ.get("FLASK_DEBUG") == "1")
