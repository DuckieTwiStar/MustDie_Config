#!/usr/bin/env python3
"""Баланс MustDie: конфіги (JSON у git) <-> листи таблиці Google Sheets.

Запуск з кореня репозиторію:
  python3 tools/balance_sheet.py export OUT.json    # git -> {лист: [[рядки]]}
  python3 tools/balance_sheet.py import IN.json DIR # {лист: [[рядки]]} -> JSON-файли в DIR (rooms/..)
  python3 tools/balance_sheet.py check              # export -> import у тимчасову папку -> порівняння з git

Правила перетворення (зворотно сумісні, без втрат):
- файл = кілька «колекцій» (ключів верхнього рівня, крім meta); кожна колекція = один лист;
- колекція-масив об'єктів = таблиця: перший рядок імена колонок, один рядок на запис; вкладені об'єкти
  розгортаються в колонки через крапку (on_hit.stun.chance); масиви (hitbox, modifiers, spawners)
  лежать в одній клітинці як JSON; порожня клітинка = ключа в записі немає;
- колекція-об'єкт (rules, bots, room, run_rewards...) = лист key, value, де key це шлях через крапку;
- колонки з закінченням _calc (і листи waves_summary, README, links, meta) рахуються у таблиці й у JSON не йдуть;
- meta кожного файлу лежить на листі meta (файл, поле, значення).
"""
import json
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOMS = ["room1", "room2", "room3", "room4"]

# (лист, файл відносно кореня, ключ у файлі, тип table | kv)
SPEC = []
for _f, _k, _t, _s in [
    ("rooms/shared/rules.json", "rules", "kv", "rules"),
    ("rooms/shared/rules.json", "debug", "kv", "debug"),
    ("rooms/shared/run_rewards.json", "run_rewards", "kv", "run_rewards"),
    ("rooms/shared/bots.json", "bots", "kv", "bots"),
    ("rooms/shared/enemies.json", "enemies", "table", "enemies"),
    ("rooms/shared/weapons.json", "defaults", "kv", "weapons_defaults"),
    ("rooms/shared/weapons.json", "weapons", "table", "weapons"),
    ("rooms/shared/weapon_upgrades.json", "upgrade_types", "table", "weapon_upgrade_types"),
    ("rooms/shared/weapon_upgrades.json", "weapon_upgrades", "table", "weapon_upgrades"),
    ("rooms/shared/traps.json", "traps", "table", "traps"),
    ("rooms/shared/trap_upgrades.json", "upgrade_types", "table", "trap_upgrade_types"),
    ("rooms/shared/trap_upgrades.json", "trap_upgrades", "table", "trap_upgrades"),
    ("rooms/shared/status_effects.json", "stats", "table", "effect_stats"),
    ("rooms/shared/status_effects.json", "status_effects", "table", "status_effects"),
]:
    SPEC.append((_s, _f, _k, _t))
for _r in ROOMS:
    for _n, _k, _t in [("room", "room", "kv"), ("zones", "zones", "table"), ("players", "players", "table"),
                       ("waves", "waves", "table"), ("run_rewards", "run_rewards", "kv")]:  # run_rewards кімнати: з BAL-0019
        SPEC.append((f"{_r}_{_n}", f"rooms/{_r}/{_n}.json", _k, _t))

META_SHEET = "meta"


def load(path):
    with open(os.path.join(ROOT, path), encoding="utf-8") as fh:
        return json.load(fh)


def jdump(v):
    return json.dumps(v, ensure_ascii=False, separators=(",", ":"))


def is_calc(col):
    return col.endswith("_calc")


def flatten(obj, prefix=""):
    """dict -> [(шлях, лист-значення)]. Масиви і порожні об'єкти йдуть у клітинку як JSON."""
    out = []
    for k, v in obj.items():
        assert "." not in k, f"крапка в ключі {prefix}{k}"
        p = f"{prefix}{k}"
        if isinstance(v, dict) and v:
            out.extend(flatten(v, p + "."))
        elif isinstance(v, (dict, list)):
            out.append((p, "\x00" + jdump(v)))  # маркер: значення це JSON
        else:
            out.append((p, v))
    return out


def to_cell(v):
    if isinstance(v, str) and v.startswith("\x00"):
        return v[1:]
    if isinstance(v, str):
        assert v != "", "порожній рядок у значенні"
        assert not v[0] in "[{", f"рядок схожий на JSON: {v}"
        return v
    return v


def table_rows(records):
    cols = []
    flat = []
    for rec in records:
        f = flatten(rec)
        flat.append(dict(f))
        for k, _ in f:
            if k not in cols:
                cols.append(k)
    rows = [cols]
    for f in flat:
        rows.append([to_cell(f[c]) if c in f else "" for c in cols])
    return rows


def kv_rows(obj):
    rows = [["key", "value"]]
    for k, v in flatten(obj):
        rows.append([k, to_cell(v)])
    return rows


def unflatten_value(v):
    if isinstance(v, str) and v[:1] in "[{":
        return json.loads(v)
    if isinstance(v, float) and v.is_integer():
        return int(v)
    return v


def set_path(d, path, value):
    parts = path.split(".")
    for p in parts[:-1]:
        d = d.setdefault(p, {})
    d[parts[-1]] = value


def reorder_like(new, orig):
    """Порядок ключів як в оригіналі (записи зіставляємо за id або позицією), нові ключі в кінець."""
    if isinstance(new, dict) and isinstance(orig, dict):
        out = {k: reorder_like(new[k], orig[k]) for k in orig if k in new}
        for k in new:
            if k not in out:
                out[k] = new[k]
        return out
    if isinstance(new, list) and isinstance(orig, list):
        byid = {o.get("id"): o for o in orig if isinstance(o, dict) and "id" in o}
        res = []
        for i, n in enumerate(new):
            o = byid.get(n.get("id")) if isinstance(n, dict) and "id" in n else None
            if o is None and i < len(orig) and not byid:
                o = orig[i]
            res.append(reorder_like(n, o) if o is not None else n)
        return res
    # 1.0 у файлі лишається 1.0, хоч таблиця віддає 1
    if isinstance(orig, float) and isinstance(new, int) and not isinstance(new, bool):
        return float(new)
    return new


def dump_inline(v, ind=0):
    """indent 2, але масиви з одних скалярів в один рядок: [3, 5, 3]."""
    p = "  " * ind
    if isinstance(v, dict):
        if not v:
            return "{}"
        body = ",\n".join(f"{p}  {json.dumps(k, ensure_ascii=False)}: {dump_inline(x, ind + 1)}" for k, x in v.items())
        return "{\n" + body + f"\n{p}}}"
    if isinstance(v, list):
        if not v:
            return "[]"
        if all(not isinstance(x, (dict, list)) for x in v):
            return "[" + ", ".join(dump_inline(x) for x in v) + "]"
        body = ",\n".join(f"{p}  {dump_inline(x, ind + 1)}" for x in v)
        return "[\n" + body + f"\n{p}]"
    return json.dumps(v, ensure_ascii=False)


def dump_std(v):
    return json.dumps(v, ensure_ascii=False, indent=2)


def dump_like(doc, orig_text):
    """Пишемо тим стилем, яким записаний оригінал, щоб у git не було шуму."""
    orig = json.loads(orig_text)
    for fn in (dump_inline, dump_std):
        if fn(orig) + "\n" == orig_text:
            return fn(doc) + "\n"
    return dump_std(doc) + "\n"


def from_table(rows):
    cols = rows[0]
    out = []
    for r in rows[1:]:
        rec = {}
        for c, v in zip(cols, r):
            if is_calc(c) or v == "" or v is None:
                continue
            set_path(rec, c, unflatten_value(v))
        if rec:
            out.append(rec)
    return out


def from_kv(rows):
    out = {}
    for r in rows[1:]:
        if len(r) < 2 or r[0] == "" or str(r[0]).endswith("_calc"):
            continue
        set_path(out, r[0], unflatten_value(r[1]))
    return out


def export_all():
    sheets = {}
    metas = [["file", "field", "value"]]
    seen = set()
    for sheet, f, key, kind in SPEC:
        d = load(f)
        sheets[sheet] = table_rows(d[key]) if kind == "table" else kv_rows(d[key])
        if f not in seen:
            seen.add(f)
            for mk, mv in d.get("meta", {}).items():
                metas.append([f, mk, mv])
    sheets[META_SHEET] = metas
    return sheets


def import_all(sheets, outdir):
    files = {}
    for sheet, f, key, kind in SPEC:
        rows = sheets[sheet]
        files.setdefault(f, {})[key] = from_table(rows) if kind == "table" else from_kv(rows)
    metas = {}
    for r in sheets[META_SHEET][1:]:
        metas.setdefault(r[0], {})[r[1]] = r[2]
    for f, parts in files.items():
        with open(os.path.join(ROOT, f), encoding="utf-8") as fh:
            orig_text = fh.read()
        orig = json.loads(orig_text)
        doc = {}
        # порядок ключів файлу як в оригіналі, meta першим, якщо там він був
        for k in orig:
            if k == "meta":
                doc["meta"] = {mk: unflatten_value(mv) if not isinstance(mv, str) else mv for mk, mv in metas.get(f, {}).items()}
            elif k in parts:
                doc[k] = reorder_like(parts[k], orig[k])
        path = os.path.join(outdir, f)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(dump_like(doc, orig_text))
    return list(files)


def same(a, b, path=""):
    """Порівняння з урахуванням порядку ключів; 1 == 1.0 вважаємо однаковими."""
    if isinstance(a, dict) and isinstance(b, dict):
        if list(a.keys()) != list(b.keys()):
            return [f"{path}: порядок/набір ключів {list(a)} != {list(b)}"]
        return [e for k in a for e in same(a[k], b[k], f"{path}.{k}")]
    if isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            return [f"{path}: довжина {len(a)} != {len(b)}"]
        return [e for i, (x, y) in enumerate(zip(a, b)) for e in same(x, y, f"{path}[{i}]")]
    if isinstance(a, bool) != isinstance(b, bool) or a != b:
        return [f"{path}: {a!r} != {b!r}"]
    return []


def check(sheets=None):
    sheets = sheets or export_all()
    errors = []
    with tempfile.TemporaryDirectory() as tmp:
        for f in import_all(sheets, tmp):
            with open(os.path.join(tmp, f), encoding="utf-8") as fh:
                got = json.load(fh)
            errors += [f"{f}{e}" for e in same(load(f), got)]
            with open(os.path.join(tmp, f), encoding="utf-8") as fh, open(os.path.join(ROOT, f), encoding="utf-8") as fo:
                if not errors and fh.read() != fo.read():
                    errors.append(f"{f}: текст файлу відрізняється (форматування)")
    return errors


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "check"
    if cmd == "export":
        with open(sys.argv[2], "w", encoding="utf-8") as fh:
            json.dump(export_all(), fh, ensure_ascii=False)
        print("листів:", len(export_all()))
    elif cmd == "import":
        with open(sys.argv[2], encoding="utf-8") as fh:
            sheets = json.load(fh)
        print("файлів:", import_all(sheets, sys.argv[3]))
    elif cmd == "check":
        errs = check()
        print("ПОМИЛОК:", len(errs))
        for e in errs[:40]:
            print(" ", e)
        sys.exit(1 if errs else 0)
