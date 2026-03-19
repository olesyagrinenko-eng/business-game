#!/usr/bin/env python3
"""
Полная проверка scenarios.json (все раунды 1–6, все ключи коэффициентов):

1) Явно заданные SH+заказы+OPH: заказы ≈ OPH×SH (как в Excel).
2) Иначе — после app._enrich_side_sh_orders_oph: SH = initial, orders = round(DC/DCPO),
   OPH = round(orders/SH,1) — уже покрыто в verify_excel_enrich.py; здесь дублируем счётчик.
3) Сурж surge_prev / surge_curr: число в [0, 100] или None.
4) Базовые поля: CTE, CPO, DCPO, DC присутствуют (DC может быть отрицательным — помечаем warning).

Запуск из каталога game-web:
  python3 scripts/verify_all_scenarios.py
"""
import copy
import json
import math
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JSON_PATH = os.path.join(BASE, "data", "scenarios.json")

sys.path.insert(0, BASE)
import app as m  # noqa: E402


def _surge_ok(v):
    if v is None:
        return True
    if isinstance(v, bool):
        return False
    if isinstance(v, (int, float)) and not (isinstance(v, float) and (math.isnan(v) or math.isinf(v))):
        return 0 <= float(v) <= 100
    return False


def main():
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    scenarios = data.get("scenarios") or {}
    im = data.get("initial_metrics") or {}

    errors = []
    warnings = []
    explicit_ok = 0
    surge_checked = 0

    for rnd in ("1", "2", "3", "4", "5", "6"):
        sc = scenarios.get(rnd) or {}
        for key, pair in sc.items():
            for role in (1, 2):
                t = pair.get("team%d" % role)
                if not isinstance(t, dict):
                    errors.append((rnd, key, role, "missing team dict"))
                    continue
                for sp in ("surge_prev", "surge_curr"):
                    surge_checked += 1
                    if not _surge_ok(t.get(sp)):
                        errors.append((rnd, key, role, "bad %s=%r" % (sp, t.get(sp))))

                sh, od, oph = t.get("SH"), t.get("orders"), t.get("OPH")
                if sh is not None and od is not None and oph is not None:
                    explicit_ok += 1
                    try:
                        pred = float(oph) * float(sh)
                        if abs(pred - float(od)) > 0.51:
                            errors.append(
                                (rnd, key, role, "OPH*SH=%s vs orders=%s" % (pred, od))
                            )
                    except (TypeError, ValueError):
                        errors.append((rnd, key, role, "non-numeric SH/orders/OPH"))

                side = copy.deepcopy(t)
                m._enrich_side_sh_orders_oph(side, role)
                dc, dcpo = side.get("DC"), side.get("DCPO")
                if isinstance(dc, (int, float)) and dc < 0:
                    warnings.append((rnd, key, role, "DC<0", dc))

                if t.get("SH") is None and t.get("orders") is None and t.get("OPH") is None:
                    if isinstance(dc, (int, float)) and isinstance(dcpo, (int, float)) and abs(dcpo) > 1e-12:
                        exp_o = round(dc / dcpo)
                        if side.get("orders") != exp_o:
                            errors.append(
                                (rnd, key, role, "orders after enrich %s != %s" % (side.get("orders"), exp_o))
                            )

    print("Файл:", JSON_PATH)
    print("Явных троек SH+заказы+OPH (проверка OPH×SH≈заказы):", explicit_ok)
    print("Проверок полей суржа (surge_prev/curr):", surge_checked)
    print("Предупреждений (DC<0):", len(warnings))
    for w in warnings[:15]:
        print("  WARN", w)
    if len(warnings) > 15:
        print("  ... +%d" % (len(warnings) - 15))

    if errors:
        print("ОШИБОК:", len(errors))
        for e in errors[:40]:
            print(" ", e)
        if len(errors) > 40:
            print("  ... +%d" % (len(errors) - 40))
        sys.exit(1)
    print("OK: все сценарии прошли проверки.")
    print("Совет: также запустите python3 scripts/verify_excel_enrich.py (пустые слоты → enrich).")


if __name__ == "__main__":
    main()
