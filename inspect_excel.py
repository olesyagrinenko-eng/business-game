#!/usr/bin/env python3
"""Просмотр структуры листа СВОД: заголовки и несколько строк данных раунда 1."""
import openpyxl
import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
EXCEL = os.path.join(os.path.dirname(BASE), "Страт.сессия_бизнес кейс_03.03.26.xlsx")
if len(sys.argv) > 1:
    EXCEL = sys.argv[1]

if not os.path.isfile(EXCEL):
    print("Файл не найден:", EXCEL)
    sys.exit(1)

wb = openpyxl.load_workbook(EXCEL, read_only=True, data_only=True)
ws = wb["СВОД"]
rows = list(ws.iter_rows(values_only=True))
wb.close()

# Строка заголовков таблицы (часто за 1-2 строки до данных раунда 1)
# Раунд 1 данные обычно с строки 33 (индекс 32)
for start in [30, 31, 32]:
    if start >= len(rows): continue
    print("=== Строка", start + 1, "(индекс", start, ") ===")
    row = rows[start]
    for i, v in enumerate(row[:35]):
        if v is not None and str(v).strip():
            print("  col[%d] = %s" % (i, repr(v)[:60]))
    print()

# Ищем строки с коэффициентами в колонках 1 и 2
for start in range(32, min(60, len(rows))):
    row = rows[start]
    if not row or len(row) < 3: continue
    v1, v2 = row[1], row[2]
    if v1 in (-0.1, 0, 0.2, 0.4) and v2 in (-0.1, 0, 0.2, 0.4):
        print("=== Строка", start + 1, "(индекс %d), c1=%s c2=%s ===" % (start, v1, v2))
        for i in range(min(50, len(row))):
            v = row[i] if i < len(row) else None
            if v is not None and str(v).strip() != "":
                print("  [%2d] %s" % (i, repr(v)[:55]))
        print("--- Следующие строки (сценарии) ---")
        for j in range(start + 1, min(start + 5, len(rows))):
            r = rows[j]
            if not r or len(r) < 5: continue
            print("  Строка %d: c1=%s c2=%s  team1 DC=%s  team2 DC=%s" % (j+1, r[1], r[2], r[17] if len(r)>17 else '-', r[41] if len(r)>41 else '-'))
        break

# Заголовок таблицы — на 1–2 строки выше первой строки с коэф.
for head_row in range(max(0, 32 - 3), 36):
    if head_row >= len(rows): break
    row = rows[head_row]
    nonempty = [(i, v) for i, v in enumerate(row[:40]) if v is not None and str(v).strip()]
    if len(nonempty) > 5:
        print("=== Возможный заголовок: строка", head_row + 1, "===")
        for i, v in nonempty[:25]:
            print("  [%2d] %s" % (i, str(v)[:50]))
        print()
