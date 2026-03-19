# -*- coding: utf-8 -*-
"""
Веб-приложение бизнес-игры для франчайзи.
Запуск: python app.py
Участники: регистрация по имени команды, выбор коэффициента в каждом раунде.
Экран: вводные, задания, результаты раундов, карта 4 квадрантов.
"""
import copy
import json
import math
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
    if not DATA.get("common_intro_by_round") and DATA.get("common_intro"):
        common = DATA["common_intro"]
        DATA["common_intro_by_round"] = {str(r): common for r in range(1, 7)}
    # Раунд 6: если в файле нет — подставляем из раунда 5
    cbr = DATA.get("common_intro_by_round") or {}
    if "6" not in cbr and "5" in cbr:
        DATA["common_intro_by_round"]["6"] = cbr["5"]
    ri = DATA.get("rounds_intro") or {}
    if "6" not in ri and "5" in ri:
        DATA["rounds_intro"]["6"] = ri["5"]
    if "6" not in DATA.get("scenarios", {}):
        DATA.setdefault("scenarios", {})["6"] = {}
    # Раунд 6 в JSON часто с 3 сценариями; для остальных комбинаций нужна полная матрица (как в р5)
    _sc = DATA.get("scenarios") or {}
    _r5, _r6 = _sc.get("5"), _sc.get("6")
    if isinstance(_r5, dict) and isinstance(_r6, dict):
        for _k, _v in _r5.items():
            if _k not in _r6:
                _r6[_k] = copy.deepcopy(_v)
    # В файле часто нет исходного DC — это суммарная маржа (заказы × DCPO), не путать с DCPO «на заказ»
    _im0 = DATA.get("initial_metrics") or {}
    for _tk in ("team1", "team2"):
        _s0 = _im0.get(_tk)
        if isinstance(_s0, dict) and _s0.get("DC") is None:
            try:
                _s0["DC"] = round(float(_s0["orders"]) * float(_s0["DCPO"]), 2)
            except (TypeError, ValueError, KeyError):
                pass
except FileNotFoundError:
    print("ERROR: data/scenarios.json not found at", DATA_PATH, file=sys.stderr)
    DATA = {"common_intro_by_round": {str(r): [] for r in range(1, 7)}, "rounds_intro": {}, "scenarios": {}, "coefficients": [], "initial_metrics": {}}
except Exception as e:
    print("ERROR loading scenarios.json:", e, file=sys.stderr)
    DATA = {"common_intro_by_round": {str(r): [] for r in range(1, 7)}, "rounds_intro": {}, "scenarios": {}, "coefficients": [], "initial_metrics": {}}

# In-memory state (для одного мероприятия)
# Всегда 10 команд: слоты 1…10, названия задаются на экране ведущего
FIXED_TEAM_NAMES = [f"Команда {i}" for i in range(1, 11)]
NUM_TEAMS = 10
slot_display_names = {}  # {1: "Название", 2: "", ...} — отображаемые имена слотов 1…10
teams = []  # [{"id": 1, "name": "Команда 1", "role": 1|2, "pair_id": 0}, ...]
pairs = []  # 5 пар: (1,2), (3,4), (5,6), (7,8), (9,10); слоты могут быть None при удалении
choices = {}  # {(team_id, round): coefficient}
current_round = 1
max_rounds = 6
expected_teams = 10  # всегда 10


def team_display_name(t):
    """Имя команды для отображения: из карточки «Названия команд» на экране или «Команда N»."""
    s = (slot_display_names.get(t["id"]) or "").strip()
    return s if s else t["name"]


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


def scenario_pair_key(coef1, coef2):
    """Ключ сценария как в scenarios.json: «0», не «0.0»; совпадает с выгрузкой из СВОД."""
    def part(v):
        x = float(v)
        if math.isclose(x, 0.0, abs_tol=1e-12):
            return "0"
        if math.isclose(x, round(x), rel_tol=0, abs_tol=1e-9):
            return str(int(round(x)))
        return "%g" % x

    return f"{part(coef1)}_{part(coef2)}"


def get_scenario_result(r, coef1, coef2):
    c1, c2 = float(coef1), float(coef2)
    scenarios = DATA.get("scenarios", {}).get(str(r), {})
    # Порядок важен: сначала канонический ключ JSON, затем «сырой» float (0.0_0.4 и т.д.)
    keys_try = [
        scenario_pair_key(c1, c2),
        f"{c1}_{c2}",
        f"{c1}_{c2}".replace("_0.0", "_0").replace("0.0_", "0_"),
    ]
    seen = set()
    res = None
    for key in keys_try:
        if not key or key in seen:
            continue
        seen.add(key)
        res = scenarios.get(key)
        if res is not None:
            break
    # Раунд 6: в данных часто не все пары коэффициентов — подставляем сценарий раунда 5
    if res is None and r == 6:
        res = get_scenario_result(5, coef1, coef2)
    return res


def _coerce_metric_number(x):
    """Привести к float для расчёта заказов/OPH (JSON/СВОД иногда дают строку)."""
    if x is None:
        return None
    if isinstance(x, bool):
        return None
    if isinstance(x, (int, float)):
        if isinstance(x, float) and (math.isnan(x) or math.isinf(x)):
            return None
        return float(x)
    if isinstance(x, str):
        s = x.strip().replace(" ", "").replace(",", ".")
        if not s:
            return None
        try:
            return float(s)
        except ValueError:
            return None
    return None


def _enrich_side_sh_orders_oph(side, role):
    """
    В выгрузке svod_full.txt слоты 10–12 (SH, заказы, OPH) часто пустые — тогда как на сводной Excel:
    заказы ≈ DC/DCPO; SH = исходный_SH (часы смены не пересчитываем от объёма); OPH = заказы/SH.
    Пример 0%/0%: заказы 1260/1332, SH 300, OPH 4.2 / 4.4. Одна и та же логика для раундов 1–6 (номер раунда не меняет формулу).
    Если в JSON заданы все три поля — не трогаем (как вручную заполненные ячейки Excel).
    """
    if not isinstance(side, dict):
        return
    if side.get("SH") is not None and side.get("orders") is not None and side.get("OPH") is not None:
        return
    im = (DATA.get("initial_metrics") or {}).get("team%d" % int(role), {})
    if not im:
        return

    orders = side.get("orders")
    if orders is None:
        cur_dc = _coerce_metric_number(side.get("DC"))
        cur_dcpo = _coerce_metric_number(side.get("DCPO"))
        if cur_dc is not None and cur_dcpo is not None and abs(cur_dcpo) > 1e-12:
            orders = round(cur_dc / cur_dcpo)
        else:
            orders = _coerce_metric_number(im.get("orders"))
    else:
        orders = _coerce_metric_number(orders)

    sh_in = side.get("SH")
    if sh_in is not None:
        sh = _coerce_metric_number(sh_in)
    else:
        # Без масштабирования на заказы — иначе OPH «залипает» на исходном 3.5/3.7 вместо 4.2/4.4 как в Excel
        sh = _coerce_metric_number(im.get("SH"))

    oph = side.get("OPH")
    if oph is None:
        if sh is not None and sh != 0 and orders is not None:
            try:
                # Как в сводной Excel: обычно один знак после запятой (4.2; 4.4)
                oph = round(float(orders) / float(sh), 1)
            except (ValueError, ZeroDivisionError):
                oph = _coerce_metric_number(im.get("OPH"))
        else:
            oph = _coerce_metric_number(im.get("OPH"))
    else:
        oph = _coerce_metric_number(oph)

    if side.get("SH") is None and sh is not None:
        side["SH"] = sh
    if side.get("orders") is None and orders is not None:
        side["orders"] = orders
    if side.get("OPH") is None and oph is not None:
        side["OPH"] = oph


@app.route("/health")
def health():
    """Проверка для Render и отладки: сервер отвечает без загрузки данных."""
    return jsonify({"status": "ok", "data_loaded": bool(DATA.get("scenarios"))}), 200


@app.route("/")
def index():
    try:
        return send_from_directory(app.static_folder, "index.html")
    except Exception as e:
        print("ERROR serving index.html:", e, file=sys.stderr)
        return f"Error: {e}", 500


@app.route("/team/<int:n>")
def team_page(n):
    """Отдельный экран для команды N (1…10). Один URL — одна команда, без путаницы."""
    if n < 1 or n > NUM_TEAMS:
        return "Недопустимый номер команды", 404
    try:
        return send_from_directory(app.static_folder, "index.html")
    except Exception as e:
        print("ERROR serving index.html:", e, file=sys.stderr)
        return f"Error: {e}", 500


@app.route("/screen")
def screen():
    try:
        return send_from_directory(app.static_folder, "screen.html")
    except Exception as e:
        print("ERROR serving screen.html:", e, file=sys.stderr)
        return f"Error: {e}", 500


def _format_intro_bold(items):
    """Добавляет жирное выделение в пункты вводных по правилам из ТЗ."""
    out = []
    for s in items:
        if not isinstance(s, str):
            out.append(s)
            continue
        s = s.replace("больше курьеров нет, мы можем", "больше курьеров <strong>в городе</strong> нет, мы можем")
        s = s.replace("В стране санкции, поэтому пользователи не могут", "В стране санкции, поэтому <strong>в этом раунде</strong> пользователи не могут")
        s = s.replace("за выполнение CTE", "за <strong>выполнение CTE</strong>")
        s = s.replace("за выполнения CTE", "за <strong>выполнение CTE</strong>")
        out.append(s)
    return out

def _format_round_intro_bold(round_num, items):
    """Жирное в доп. вводных по раундам: раунд 4, 5."""
    out = []
    for s in items:
        if not isinstance(s, str):
            out.append(s)
            continue
        if round_num == 4 and "Отключили санкции" in s and "перетекать" in s:
            s = "<strong>Отключили санкции, и пользователи теперь могут скачать приложение конкурента и перетекать к нему.</strong>"
        if round_num == 5 and "не бесконечный склад" in s:
            s = s.replace("У нас не бесконечный склад", "У нас <strong>больше</strong> не бесконечный склад")
        out.append(s)
    return out

@app.route("/api/data")
def api_data():
    """Общие данные: вводные, коэффициенты, количество раундов, ожидаемое количество команд, исходные метрики."""
    intro_by_round_raw = DATA.get("common_intro_by_round") or {}
    intro_by_round = {r: _format_intro_bold(lst) for r, lst in intro_by_round_raw.items()}
    rounds_intro_raw = DATA.get("rounds_intro") or {}
    rounds_intro = {}
    for r, lst in rounds_intro_raw.items():
        try:
            rn = int(r)
        except ValueError:
            rn = 1
        rounds_intro[r] = _format_round_intro_bold(rn, lst)
    return jsonify({
        "common_intro_by_round": intro_by_round,
        "common_intro": intro_by_round.get("1", _format_intro_bold(DATA.get("common_intro", []))),
        "rounds_intro": rounds_intro,
        "coefficients": DATA.get("coefficients", []),
        "initial_metrics": DATA.get("initial_metrics", {}),
        "max_rounds": max_rounds,
        "expected_teams": expected_teams,
        "teams_count": len(teams),
    })


@app.route("/api/settings", methods=["GET", "POST"])
def api_settings():
    """Получить или задать настройки (ожидаемое количество команд)."""
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
    """Регистрация: только «Команда 1» … «Команда 10». По имени попадаем в команду без дублей."""
    name = (request.get_json() or {}).get("name", "").strip()
    if not name:
        return jsonify({"error": "Укажите название команды"}), 400
    if name not in FIXED_TEAM_NAMES:
        return jsonify({"error": "Допустимые названия: Команда 1, Команда 2, … Команда 10"}), 400
    team_id = FIXED_TEAM_NAMES.index(name) + 1  # 1..10
    existing = next((t for t in teams if t["id"] == team_id), None)
    if existing:
        return jsonify({
            "team_id": existing["id"],
            "name": existing["name"],
            "role": existing["role"],
            "pair_id": existing["pair_id"],
            "reentered": True,
        })

    pair_id = (team_id - 1) // 2
    role = 1 if team_id % 2 == 1 else 2
    while len(pairs) <= pair_id:
        pairs.append({"team1_id": None, "team2_id": None})
    if role == 1:
        pairs[pair_id]["team1_id"] = team_id
    else:
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
            if pid is not None:
                p = pairs[pid]
                c1 = choices.get((p["team1_id"], current_round))
                c2 = choices.get((p["team2_id"], current_round))
                if c1 is not None and c2 is not None:
                    res = get_scenario_result(current_round, c1, c2)
                    if res is not None:
                        raw = res["team1"] if t["role"] == 1 else res["team2"]
                        result = copy.deepcopy(raw)
                        if result.get("DC") in ("+", "-"):
                            result["DC"] = None
                        _enrich_side_sh_orders_oph(result, t["role"])
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
                        if sr is not None:
                            raw_r = sr["team1"] if t["role"] == 1 else sr["team2"]
                            res_r = copy.deepcopy(raw_r)
                            if res_r.get("DC") in ("+", "-"):
                                res_r["DC"] = None
                            _enrich_side_sh_orders_oph(res_r, t["role"])
            results_by_round.append({
                "round": r,
                "my_choice": my_c,
                "opponent_choice": opp_c,
                "result": res_r,
            })
        return jsonify({
            "team_id": team_id,
            "name": team_display_name(t),
            "role": t["role"],
            "current_round": current_round,
            "my_choice": my_choice,
            "opponent_choice": opp_choice,
            "result": result,
            "results_by_round": results_by_round,
            "rounds_done": [r for r in range(1, current_round) if (team_id, r) in choices],
        })
    # Экран: общее состояние
    # Все ли пары (с двумя командами) ответили в текущем раунде
    round_complete = True
    if pairs:
        for p in pairs:
            t1, t2 = p.get("team1_id"), p.get("team2_id")
            if not t1 or not t2:
                continue
            c1 = choices.get((t1, current_round))
            c2 = choices.get((t2, current_round))
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
        "teams": [{"id": t["id"], "name": team_display_name(t), "role": t["role"]} for t in teams],
        "pairs": [{"team1_id": p["team1_id"], "team2_id": p["team2_id"]} for p in pairs],
        "choices": {f"{tid}_{r}": c for (tid, r), c in choices.items()},
        "slot_display_names": {str(i): (slot_display_names.get(i) or "") for i in range(1, NUM_TEAMS + 1)},
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


@app.route("/api/teams/<int:team_id>", methods=["DELETE"])
def api_remove_team(team_id):
    """Удалить команду. Слот в паре обнуляется; при повторном входе под тем же именем — одна команда."""
    global teams, pairs, choices
    t = next((x for x in teams if x["id"] == team_id), None)
    if not t:
        return jsonify({"error": "Команда не найдена"}), 404
    teams = [x for x in teams if x["id"] != team_id]
    choices = {k: v for k, v in choices.items() if k[0] != team_id}
    for p in pairs:
        if p.get("team1_id") == team_id:
            p["team1_id"] = None
            break
        if p.get("team2_id") == team_id:
            p["team2_id"] = None
            break
    return jsonify({"ok": True, "message": "Команда удалена", "teams_count": len(teams)})


@app.route("/api/teams/<int:team_id>", methods=["PATCH"])
def api_patch_team(team_id):
    """Задать отображаемое название слота 1…10 (на экране ведущего). Команда может ещё не войти."""
    global slot_display_names
    if team_id < 1 or team_id > NUM_TEAMS:
        return jsonify({"error": "Номер команды от 1 до 10"}), 400
    body = request.get_json() or {}
    display_name = body.get("display_name")
    if display_name is not None:
        val = str(display_name).strip() or None
        slot_display_names[team_id] = val
    name = (slot_display_names.get(team_id) or "").strip() or FIXED_TEAM_NAMES[team_id - 1]
    return jsonify({"ok": True, "name": name})


@app.route("/api/reset", methods=["POST"])
def api_reset():
    """Сбросить игру: очистить команды, пары, ответы, раунд 1. Названия слотов сохраняются."""
    global teams, pairs, choices, current_round
    teams = []
    pairs = []
    choices = {}
    current_round = 1
    # slot_display_names не сбрасываем — ведущий задал названия один раз
    return jsonify({"ok": True, "message": "Игра сброшена. Попросите участников нажать «Войти заново» на телефонах."})


@app.route("/api/round", methods=["POST"])
def api_round():
    """Переключить раунд (для ведущего с экрана)."""
    global current_round
    r = (request.get_json() or {}).get("round")
    if r is not None and 1 <= r <= max_rounds:
        current_round = r
        return jsonify({"current_round": current_round})
    return jsonify({"error": "round от 1 до " + str(max_rounds)}), 400


@app.route("/api/results")
def api_results():
    """Итоги: пораундовые DC/CTE; сумма DC; прирост к исх. для карты; сумма ΔDC по этапам для сводки; квадранты по приросту."""
    up_to_round = request.args.get("round", type=int)
    if up_to_round is None or up_to_round < 1 or up_to_round > max_rounds:
        up_to_round = max_rounds
    rounds_consider = list(range(1, up_to_round + 1))
    initial_metrics = DATA.get("initial_metrics", {})
    results = []
    for t in teams:
        im = initial_metrics.get("team" + str(t["role"]), {})
        # Исходный DC — суммарная маржа; не подставлять DCPO (маржа на заказ) — другая размерность
        initial_dc = im.get("DC")
        if initial_dc is None and isinstance(im, dict):
            try:
                initial_dc = round(float(im["orders"]) * float(im["DCPO"]), 2)
            except (TypeError, ValueError, KeyError):
                initial_dc = None
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
            if res is None:
                continue
            side = res["team1"] if t["role"] == 1 else res["team2"]
            dc = side.get("DC")
            if isinstance(dc, (int, float)):
                total_dc += dc
                dc_by_round[r] = dc
            cte_ok = side.get("CTE_in_target", False)
            if cte_ok:
                cte_ok_count += 1
            side_disp = copy.deepcopy(side)
            if side_disp.get("DC") in ("+", "-"):
                side_disp["DC"] = None
            _enrich_side_sh_orders_oph(side_disp, t["role"])
            per_round.append({
                "round": r,
                "dc": round(dc, 0) if isinstance(dc, (int, float)) else None,
                "cte_ok": cte_ok,
                "sh": side_disp.get("SH"),
                "orders": side_disp.get("orders"),
                "oph": side_disp.get("OPH"),
            })
        rounds_played = sum(1 for r in rounds_consider if (t["id"], r) in choices)
        show_total = up_to_round == max_rounds and rounds_played >= 1
        # Последний раунд с рассчитанным DC в диапазоне 1…up_to (если для N нет сценария — берём предыдущий)
        effective_dc_round = None
        if dc_by_round:
            for er in range(up_to_round, 0, -1):
                if er in dc_by_round:
                    effective_dc_round = er
                    break
        # Прирост маржи к исходному: DC после effective_dc_round − исходный (для карты по раунду / квадрантов)
        dc_growth = None
        if effective_dc_round is not None and initial_dc is not None:
            dc_growth = dc_by_round[effective_dc_round] - (initial_dc if isinstance(initial_dc, (int, float)) else 0)
        elif effective_dc_round is not None and 1 in dc_by_round and initial_dc is None:
            dc_growth = dc_by_round[effective_dc_round] - dc_by_round[1]
        # Сумма изменений маржи между соседними сыгранными этапами: (DC_r1−I)+(DC_r2−DC_r1)+… = DC_last−I
        dc_growth_sum_round_deltas = None
        _ordered = sorted(dc_by_round.keys())
        if _ordered:
            _prev = float(initial_dc) if isinstance(initial_dc, (int, float)) else None
            _acc = 0.0
            for _rk in _ordered:
                _cur = dc_by_round[_rk]
                if not isinstance(_cur, (int, float)):
                    continue
                _fv = float(_cur)
                if _prev is not None:
                    _acc += _fv - _prev
                _prev = _fv
            dc_growth_sum_round_deltas = _acc
        # SH / Заказы / OPH — по последнему раунду с данными ≤ up_to, не только строго N
        pr_up = None
        for p in reversed(per_round):
            if p["round"] <= up_to_round:
                pr_up = p
                break
        results.append({
            "team_id": t["id"],
            "name": team_display_name(t),
            "role": t["role"],
            "per_round": per_round,
            "total_dc": round(total_dc, 0) if show_total else None,
            "cte_ok_rounds": cte_ok_count,
            "rounds_played": rounds_played,
            "dc_growth": round(dc_growth, 0) if dc_growth is not None else None,
            "dc_growth_sum_round_deltas": round(dc_growth_sum_round_deltas, 0) if dc_growth_sum_round_deltas is not None else None,
            "rounds_with_result": len(per_round),
            "initial_dc": round(initial_dc, 0) if isinstance(initial_dc, (int, float)) else initial_dc,
            "initial_sh": im.get("SH"),
            "initial_orders": im.get("orders"),
            "initial_oph": im.get("OPH"),
            "result_sh": pr_up.get("sh") if pr_up else None,
            "result_orders": pr_up.get("orders") if pr_up else None,
            "result_oph": pr_up.get("oph") if pr_up else None,
        })
    # Квадранты: ось «прирост маржи» = прирост к исходному DC (и для раунда 1 тоже, не абсолютный DC)
    def _growth_for_axis(row):
        g = row.get("dc_growth_sum_round_deltas")
        if g is None:
            g = row.get("dc_growth")
        return g

    for x in results:
        x["quadrant"] = None
        if x["rounds_played"] < 1:
            continue
        # CTE в таргете в том же «эффективном» раунде, что и для прироста (последний с данными ≤ N)
        pr_sel = None
        for p in reversed(x.get("per_round", [])):
            if p["round"] <= up_to_round:
                pr_sel = p
                break
        cte_ok = pr_sel.get("cte_ok", False) if pr_sel else False
        gx = _growth_for_axis(x)
        # Верхние квадранты: любой положительный прирост маржи (без сравнения с медианой)
        high = gx is not None and gx > 0
        if high and cte_ok:
            x["quadrant"] = "top_right"
        elif high and not cte_ok:
            x["quadrant"] = "top_left"
        elif not high and cte_ok:
            x["quadrant"] = "bottom_right"
        else:
            x["quadrant"] = "bottom_left"
    return jsonify({
        "results": results,
        "median_dc_growth": None,
        "up_to_round": up_to_round,
        "show_total_only_after_round_5": True,
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    app.run(host="0.0.0.0", port=port, debug=os.environ.get("FLASK_DEBUG") == "1")
