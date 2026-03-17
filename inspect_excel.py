#!/usr/bin/env python3
"""Найти индексы первых строк сценариев для раундов 1-6 (строка с коэф. в col 1,2)."""
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

coefs = (-0.1, 0, 0.2, 0.4)
data_rows = []
for idx in range(len(rows)):
    row = rows[idx]
    if not row or len(row) < 20: continue
    v1, v2 = row[1], row[2]
    dc1 = row[17] if len(row) > 17 else None
    if v1 in coefs and v2 in coefs and isinstance(dc1, (int, float)) and dc1 and dc1 > 10000:
        data_rows.append((idx, v1, v2, dc1))
print("Всего строк с данными сценариев:", len(data_rows))
print("Первые 20: индекс, c1, c2, DC1")
for t in data_rows[:20]:
    print("  ", t)
print("...")
print("Строки 17-25:", data_rows[16:25] if len(data_rows) >= 25 else data_rows[16:])
# Раунд 1 = 16 строк (индексы 38..53), раунд 2 = след. 16 и т.д.
if len(data_rows) >= 32:
    print("\nПредполагаемые старты раундов (каждые 16 сценариев):")
    for r in range(6):
        i = r * 16
        if i < len(data_rows):
            print("  Раунд %d: индекс строки %d" % (r + 1, data_rows[i][0]))

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
