#!/usr/bin/env python3
"""
Проверка: для всех сценариев 1–6, где в JSON нет SH/заказов/OPH, после _enrich_side_sh_orders_oph
должно выполняться: заказы = round(DC/DCPO), SH = исходный SH роли, OPH = round(заказы/SH, 1).

Запуск из каталога game-web: python3 scripts/verify_excel_enrich.py
"""
import copy
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import app as m  # noqa: E402


def main():
    im1 = m.DATA["initial_metrics"]["team1"]
    im2 = m.DATA["initial_metrics"]["team2"]
    ish1, ish2 = im1.get("SH"), im2.get("SH")
    fails = []
    explicit = 0
    checked = 0
    for rnd in "123456":
        sc = m.DATA["scenarios"].get(rnd, {})
        for key, pair in sc.items():
            for role, im, ish in ((1, im1, ish1), (2, im2, ish2)):
                raw = pair["team%d" % role]
                has_any = (
                    raw.get("SH") is not None
                    or raw.get("orders") is not None
                    or raw.get("OPH") is not None
                )
                if has_any:
                    explicit += 1
                    continue
                checked += 1
                side = copy.deepcopy(raw)
                m._enrich_side_sh_orders_oph(side, role)
                dc, dcpo = side.get("DC"), side.get("DCPO")
                if not (
                    isinstance(dc, (int, float))
                    and isinstance(dcpo, (int, float))
                    and abs(dcpo) > 1e-12
                ):
                    continue
                exp_o = round(dc / dcpo)
                exp_oph = round(float(exp_o) / float(ish), 1)
                if side.get("SH") != ish:
                    fails.append((rnd, key, role, "SH", side.get("SH"), ish))
                if side.get("orders") != exp_o:
                    fails.append((rnd, key, role, "orders", side.get("orders"), exp_o))
                if side.get("OPH") != exp_oph:
                    fails.append((rnd, key, role, "OPH", side.get("OPH"), exp_oph))
    print("Проверено ячеек (пустые SH/заказы/OPH в JSON):", checked)
    print("Пропущено (явно заданы в JSON, как в Excel):", explicit)
    if fails:
        print("ОШИБКИ:", len(fails))
        for f in fails[:20]:
            print(" ", f)
        sys.exit(1)
    print("OK: логика совпадает со сводной Excel для всех раундов.")


if __name__ == "__main__":
    main()
