#!/usr/bin/env python3
"""Локалізація MustDie: таблиця Google Sheets `[MD]Localization` (лист Strings) <-> localization/strings.csv.

Запуск з кореня репозиторію:
  python3 tools/localization_sheet.py import IN.json   # рядки листа -> localization/strings.csv
  python3 tools/localization_sheet.py export OUT.json  # localization/strings.csv -> рядки листа
  python3 tools/localization_sheet.py check            # перевірка CSV + export -> import без втрат

Імпорт пише і localization/strings.csv, і runtime-файли lobby/localization.json та rooms/shared/localization.json
(їх читає гра через ConfigService; копії ідентичні, validate.py це перевіряє), і localization/LocFallback.lua —
англійські тексти, вшиті в гру (Core.Shared.LocFallback): їх видно, поки таблиця не завантажилась або якщо GitHub недоступний.
Після зміни таблиці вміст LocFallback.lua вставляємо в модуль Core.Shared.LocFallback (Packages) і публікуємо Core.

IN.json: відповідь get_values ({"values": [[...]]}) або просто [[...]]; xlsx-експорт можна перегнати в той самий список.

Лист Strings: Key | Context | en | de | fr | it | es | pt-pt | pt-br | uk (перший рядок = заголовки).
strings.csv: формат LocalizationTable Roblox (Key, Source, Context, Example, <локалі>), UTF-8, імпортується
в Studio (Localization Tools / LocalizationTable:SetEntries). Source = текст en.

Правила перевірки:
- Key унікальний, формат a.b.c (малі літери, цифри, _), не порожній;
- є всі мови; порожній переклад = помилка (гра покаже en, але в релізі такого бути не має);
- плейсхолдери {x}, теги RichText <b>..</b> і кількість переносів \\n у перекладі такі самі, як в en;
- клітинки без пробілів на краях;
- немає значень помилок Google Sheets (#ERROR!, #NAME? ...): текст, що починається з + = -, таблиця вважає формулою,
  такі клітинки вводимо з апострофом ('+{delta} ...).
"""
import csv
import io
import json
import os
import re
import sys
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_PATH = os.path.join(ROOT, "localization", "strings.csv")
JSON_PATHS = [os.path.join(ROOT, "lobby", "localization.json"), os.path.join(ROOT, "rooms", "shared", "localization.json")]
LUA_PATH = os.path.join(ROOT, "localization", "LocFallback.lua")
SOURCE = "en"
LOCALES = ["de", "fr", "it", "es", "pt-pt", "pt-br", "uk"]
SHEET_HEADER = ["Key", "Context", SOURCE] + LOCALES
CSV_HEADER = ["Key", "Source", "Context", "Example"] + LOCALES
KEY_RE = re.compile(r"^[a-z0-9_]+(\.[a-z0-9_]+)+$")
PH_RE = re.compile(r"\{[a-z_]+\}")
TAG_RE = re.compile(r"</?[a-z]+>")
SHEET_ERROR_RE = re.compile(r"^#(ERROR!|NAME\?|VALUE!|REF!|DIV/0!|N/A|NUM!|NULL!)")


def read_csv(path=CSV_PATH):
    with open(path, encoding="utf-8", newline="") as fh:
        rows = list(csv.reader(fh))
    if not rows or rows[0] != CSV_HEADER:
        raise SystemExit(f"{path}: заголовок має бути {CSV_HEADER}")
    out = []
    for r in rows[1:]:
        d = dict(zip(CSV_HEADER, r + [""] * (len(CSV_HEADER) - len(r))))
        out.append({"key": d["Key"], "context": d["Context"], SOURCE: d["Source"],
                    **{loc: d[loc] for loc in LOCALES}})
    return out


def write_csv(entries, path=CSV_PATH):
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n", quoting=csv.QUOTE_MINIMAL)
    w.writerow(CSV_HEADER)
    for e in entries:
        w.writerow([e["key"], e[SOURCE], e["context"], ""] + [e[loc] for loc in LOCALES])
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(buf.getvalue())


def build_runtime_json(entries):
    """Текст runtime-файлу для гри: {"languages": [...], "strings": {ключ: {мова: текст}}}. Детермінований (без дат)."""
    data = {"languages": [SOURCE] + LOCALES,
            "strings": {e["key"]: {loc: e[loc] for loc in [SOURCE] + LOCALES} for e in entries}}
    return json.dumps(data, ensure_ascii=False, indent=1) + "\n"


def write_runtime_json(entries):
    text = build_runtime_json(entries)
    for path in JSON_PATHS:
        with open(path, "w", encoding="utf-8", newline="") as fh:
            fh.write(text)


def lua_string(text):
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n") + '"'


def build_fallback_lua(entries):
    """ModuleScript Core.Shared.LocFallback: {ключ = англійський текст}. Детермінований."""
    lines = ["--!strict",
             "-- ЗГЕНЕРОВАНО tools/localization_sheet.py з localization/strings.csv. Не редагувати вручну.",
             "-- Англійські тексти, вшиті в гру: Loc / LocalizationServer беруть їх, поки таблиця не прийшла з GitHub.",
             "",
             "local strings: { [string]: string } = {"]
    for e in entries:
        lines.append(f"\t[{lua_string(e['key'])}] = {lua_string(e[SOURCE])},")
    lines += ["}", "", "return table.freeze(strings)", ""]
    return "\n".join(lines)


def write_fallback_lua(entries):
    with open(LUA_PATH, "w", encoding="utf-8", newline="") as fh:
        fh.write(build_fallback_lua(entries))


def sheet_to_entries(rows):
    if isinstance(rows, dict):
        rows = rows.get("values", rows)
    if not rows or [str(c).strip() for c in rows[0]] != SHEET_HEADER:
        raise SystemExit(f"лист: заголовок має бути {SHEET_HEADER}, зараз {rows[0] if rows else None}")
    out = []
    for r in rows[1:]:
        r = [("" if c is None else str(c)) for c in r] + [""] * (len(SHEET_HEADER) - len(r))
        if not any(c.strip() for c in r):
            continue  # порожні рядки-розділювачі в таблиці пропускаємо
        d = dict(zip(SHEET_HEADER, r))
        out.append({"key": d["Key"], "context": d["Context"], SOURCE: d[SOURCE],
                    **{loc: d[loc] for loc in LOCALES}})
    return out


def entries_to_sheet(entries):
    return [SHEET_HEADER] + [[e["key"], e["context"], e[SOURCE]] + [e[loc] for loc in LOCALES] for e in entries]


def validate(entries):
    errs = []
    counts = Counter(e["key"] for e in entries)
    for k, n in counts.items():
        if n > 1:
            errs.append(f"{k}: ключ повторюється {n} разів")
    for e in entries:
        k = e["key"]
        if not KEY_RE.match(k):
            errs.append(f"{k!r}: ключ має бути a.b.c (малі літери, цифри, _)")
        src = e[SOURCE]
        if not src:
            errs.append(f"{k}: порожній текст {SOURCE}")
            continue
        sp, st, sn = sorted(PH_RE.findall(src)), Counter(TAG_RE.findall(src)), src.count("\n")
        for loc in [SOURCE] + LOCALES:
            t = e[loc]
            if t != t.strip():
                errs.append(f"{k} [{loc}]: пробіли на краях")
            if SHEET_ERROR_RE.match(t):
                errs.append(f"{k} [{loc}]: у клітинці помилка таблиці {t!r} (текст з + = - на початку вводимо з апострофом)")
            if loc == SOURCE:
                continue
            if not t:
                errs.append(f"{k} [{loc}]: немає перекладу")
                continue
            if sorted(PH_RE.findall(t)) != sp:
                errs.append(f"{k} [{loc}]: плейсхолдери {sorted(PH_RE.findall(t))} != {sp}")
            if Counter(TAG_RE.findall(t)) != st:
                errs.append(f"{k} [{loc}]: теги RichText не збігаються з {SOURCE}")
            if t.count("\n") != sn:
                errs.append(f"{k} [{loc}]: переносів рядка {t.count(chr(10))}, в {SOURCE} {sn}")
    return errs


def main(argv):
    if len(argv) < 2 or argv[1] not in ("import", "export", "check"):
        print(__doc__)
        return 2
    cmd = argv[1]
    if cmd == "import":
        with open(argv[2], encoding="utf-8") as fh:
            entries = sheet_to_entries(json.load(fh))
        errs = validate(entries)
        for e in errs:
            print("ПОМИЛКА", e)
        if errs:
            print(f"{len(errs)} помилок, CSV не записано")
            return 1
        write_csv(entries)
        write_runtime_json(entries)
        write_fallback_lua(entries)
        print(f"OK: {len(entries)} рядків -> {os.path.relpath(CSV_PATH, ROOT)}, {len(JSON_PATHS)} копії localization.json і LocFallback.lua")
        return 0
    entries = read_csv()
    if cmd == "export":
        with open(argv[2], "w", encoding="utf-8") as fh:
            json.dump(entries_to_sheet(entries), fh, ensure_ascii=False)
        print(f"OK: {len(entries)} рядків -> {argv[2]}")
        return 0
    errs = validate(entries)
    back = sheet_to_entries(entries_to_sheet(entries))
    if back != entries:
        errs.append("export -> import змінює дані")
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(CSV_HEADER)
    for e in entries:
        w.writerow([e["key"], e[SOURCE], e["context"], ""] + [e[loc] for loc in LOCALES])
    with open(CSV_PATH, encoding="utf-8", newline="") as fh:
        if fh.read() != buf.getvalue():
            errs.append("strings.csv не в канонічному вигляді (перезапишіть через import)")
    expected = build_runtime_json(entries)
    for path in JSON_PATHS:
        rel = os.path.relpath(path, ROOT)
        if not os.path.exists(path):
            errs.append(f"{rel}: немає файлу (запустіть import)")
        else:
            with open(path, encoding="utf-8", newline="") as fh:
                if fh.read() != expected:
                    errs.append(f"{rel}: не збігається зі strings.csv (запустіть import)")
    if not os.path.exists(LUA_PATH):
        errs.append("localization/LocFallback.lua: немає файлу (запустіть import)")
    else:
        with open(LUA_PATH, encoding="utf-8", newline="") as fh:
            if fh.read() != build_fallback_lua(entries):
                errs.append("localization/LocFallback.lua: не збігається зі strings.csv (запустіть import)")
    for e in errs:
        print("ПОМИЛКА", e)
    print("OK" if not errs else f"{len(errs)} помилок", f"({len(entries)} рядків, {len(LOCALES)} мов + {SOURCE})")
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
