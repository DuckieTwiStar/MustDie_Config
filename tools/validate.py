#!/usr/bin/env python3
"""Перевірка конфігів MustDie перед комітом.

Запуск з кореня репозиторію:  python3 tools/validate.py
Код виходу 0 = усе чисто, 1 = є помилки (коміт не робимо).

Що перевіряється:
- кожен *.json парситься, корінь це об'єкт, немає null;
- у файлах rooms/shared/ і rooms/<кімната>/ є meta (version, exported_at, note);
- колекції це масиви об'єктів з полем id у snake_case, id унікальні
  (у пастках унікальна пара id + level);
- обов'язкові поля, типи і діапазони за схемою нижче;
- посилання між файлами: waves -> enemies і спавнери кімнати, weapon_upgrades -> weapons;
- у кожній кімнаті є всі файли кімнати;
- wave_delay однаковий у всіх рядках однієї хвилі (гра бере його з першого рядка);
- копії leaderboards.json і items.json (lobby/, rooms/shared/) побайтно однакові;
- каталог items.json: кожна зброя й пастка має запис (і навпаки), icon це rbxassetid://<число> або порожньо,
  плейсхолдери {x} в description мають значення в values, reward.id у магазинах лобі є в каталозі.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ROOMS = ROOT / "rooms"
SHARED = ROOMS / "shared"
ID_RE = re.compile(r"^[a-z0-9_]+$")

NUM = (int, float)
# поле: (тип, обов'язкове, мін, макс)  None = без межі
SCHEMA = {
    "rules": {
        "_object": True,
        "start_coins": (int, True, 0, None),
        "refund_share": (NUM, True, 0, 1),
        "reward_mode": (str, True, None, None),
        "ricochet_falloff": (NUM, True, 0, 1),
        "cell_size": (NUM, True, 0.1, None),
        "restart_delay": (NUM, True, 0, None),
    },
    "enemies": {
        "id": (str, True, None, None), "name_en": (str, True, None, None), "name_uk": (str, True, None, None),
        "size": (str, True, None, None), "hp": (NUM, True, 1, None), "speed": (NUM, True, 0.1, None),
        "armor": (NUM, True, 0, 0.95), "damage_to_base": (NUM, True, 0, None), "reward": (int, True, 0, None),
    },
    "traps": {
        "id": (str, True, None, None), "level": (int, True, 1, 10), "order": (int, True, 0, None),
        "name_en": (str, True, None, None), "name_uk": (str, True, None, None),
        "mechanic": (str, True, None, None), "placement": (str, True, None, None),
        "cost": (int, True, 0, None), "damage": (NUM, True, 0, None),
        "cooldown": (NUM, False, 0, None), "hold_time": (NUM, False, 0, None),
        "fire_interval": (NUM, False, 0.01, None), "range": (NUM, False, 0, None),
        "default_owned": (bool, False, None, None),
    },
    "weapons": {
        "id": (str, True, None, None), "order": (int, True, 0, None), "default_owned": (bool, False, None, None),
        "name_en": (str, True, None, None), "name_uk": (str, True, None, None),
        "damage": (NUM, True, 0, None), "attack_interval": (NUM, True, 0.01, None), "range": (NUM, True, 0, None),
        "projectile_speed": (NUM, False, 0.1, None), "gravity": (NUM, False, 0, None),
        "ricochet": (int, False, 0, None), "multishot": (int, False, 1, None),
        "crit_chance": (NUM, False, 0, 1), "crit_mult": (NUM, False, 1, None),
        "pellets": (int, False, 1, None), "spread": (NUM, False, 0, 90),
        "falloff_start": (NUM, False, 0, None), "falloff_min": (NUM, False, 0, 1),
    },
    "weapon_upgrades": {
        "id": (str, True, None, None), "weapon_id": (str, True, None, None), "upgrade": (str, True, None, None),
        "order": (int, True, 0, None), "level": (int, True, 1, 10), "cost": (int, True, 0, None), "value": (NUM, True, None, None),
    },
    "run_rewards": {
        "_object": True,
        "damage_per_soft": (NUM, True, 0.01, None), "wisps_per_soft": (NUM, True, 0.01, None),
        "base_hp_per_soft": (NUM, True, 0.01, None), "results_delay": (NUM, True, 0, 30),
        "results_timer": (NUM, True, 5, 300), "damage_dealer_min_players": (int, True, 1, 4),
        "wave_soft": (list, True, None, None),
    },
    "room": {
        "_object": True,
        "id": (str, True, None, None), "name_en": (str, True, None, None), "name_uk": (str, True, None, None),
        "base_hp": (NUM, True, 1, None), "door_timer": (NUM, True, 0, None), "spawners": (list, True, None, None),
    },
    "zones": {
        "id": (str, True, None, None), "order": (int, True, 0, None), "name_en": (str, True, None, None),
        "name_uk": (str, True, None, None), "length": (NUM, True, 0, None),
        "spawner_id": (str, False, None, None),
    },
    "waves": {
        "id": (str, True, None, None), "wave": (int, True, 1, None), "spawner_id": (str, True, None, None),
        "enemy_id": (str, True, None, None), "count": (int, True, 1, None),
        "spawn_interval": (NUM, True, 0, None), "wave_delay": (NUM, True, 0, None),
        "min_players": (int, False, 1, 4),
    },
    "players": {
        "id": (str, True, None, None), "players": (int, True, 1, 4), "hp_mult": (NUM, True, 0.1, None),
        "count_mult": (NUM, True, 0.1, None), "reward_mult": (NUM, True, 0, None),
    },
    "items": {
        "id": (str, True, None, None), "kind": (str, True, None, None), "icon": (str, True, None, None),
        "title": (str, True, None, None), "description": (str, True, None, None), "values": (dict, False, None, None),
    },
}
ENUMS = {
    ("items", "kind"): {"currency", "weapon", "trap", "booster", "item"},
    ("rules", "reward_mode"): {"each", "split", "killer"},
    ("enemies", "size"): {"small", "medium", "large"},
    ("traps", "mechanic"): {"snare", "wall", "turret"},
    ("traps", "placement"): {"floor", "wall"},
    ("weapon_upgrades", "upgrade"): {"damage", "attack_interval", "ricochet", "multishot", "crit", "pellets"},
}
SHARED_FILES = ["rules", "enemies", "traps", "weapons", "weapon_upgrades", "run_rewards", "items"]
ICON_RE = re.compile(r"^(rbxassetid://[0-9]+)?$")
PLACEHOLDER_RE = re.compile(r"\{([a-z0-9_]+)\}")
ROOM_FILES = ["room", "zones", "waves", "players"]
ROOM_OPTIONAL_FILES = ["run_rewards"]  # перекриває rooms/shared цілим файлом (ConfigService не зливає ключі)
SKIP = {"leaderboards"}  # формат лідербордів веде сторона Жені

errors = []


def err(path, msg):
    errors.append(f"{path.relative_to(ROOT)}: {msg}")


def has_null(v):
    if v is None:
        return True
    if isinstance(v, dict):
        return any(has_null(x) for x in v.values())
    if isinstance(v, list):
        return any(has_null(x) for x in v)
    return False


def load(path):
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:  # noqa: BLE001
        err(path, f"не JSON: {e}")
        return None
    if not isinstance(data, dict):
        err(path, "корінь має бути об'єктом")
        return None
    if has_null(data):
        err(path, "є null: відсутнє значення = відсутній ключ")
    return data


def type_ok(v, t):
    if t is int:
        return isinstance(v, int) and not isinstance(v, bool)
    if t == NUM:
        return isinstance(v, (int, float)) and not isinstance(v, bool)
    return isinstance(v, t)


def check_fields(path, name, row, where):
    schema = SCHEMA[name]
    for key, spec in schema.items():
        if key.startswith("_"):
            continue
        t, req, lo, hi = spec
        if key not in row:
            if req:
                err(path, f"{where}: немає поля {key}")
            continue
        v = row[key]
        if not type_ok(v, t):
            err(path, f"{where}: {key} має неправильний тип ({v!r})")
            continue
        if lo is not None and v < lo:
            err(path, f"{where}: {key}={v} менше за {lo}")
        if hi is not None and v > hi:
            err(path, f"{where}: {key}={v} більше за {hi}")
        if (name, key) in ENUMS and v not in ENUMS[(name, key)]:
            err(path, f"{where}: {key}={v!r} не з {sorted(ENUMS[(name, key)])}")
    for key in row:
        if key not in schema or key.startswith("_"):
            err(path, f"{where}: невідоме поле {key} (додай його в схему і README)")


def check_file(path, name):
    data = load(path)
    if data is None:
        return None
    meta = data.get("meta")
    if not isinstance(meta, dict) or not all(isinstance(meta.get(k), str) and meta.get(k) for k in ("version", "exported_at", "note")):
        err(path, "meta має містити рядки version, exported_at, note")
    if name not in data:
        err(path, f"немає ключа {name}")
        return None
    body = data[name]
    if SCHEMA[name].get("_object"):
        if not isinstance(body, dict):
            err(path, f"{name} має бути об'єктом")
            return None
        check_fields(path, name, body, name)
        if "id" in body and not ID_RE.match(str(body["id"])):
            err(path, f"id {body['id']!r} не snake_case")
        return body
    if not isinstance(body, list) or not body:
        err(path, f"{name} має бути непорожнім масивом")
        return None
    seen = set()
    for i, row in enumerate(body):
        where = f"{name}[{i}]"
        if not isinstance(row, dict):
            err(path, f"{where}: не об'єкт")
            continue
        check_fields(path, name, row, where)
        rid = row.get("id")
        if isinstance(rid, str) and not ID_RE.match(rid):
            err(path, f"{where}: id {rid!r} не snake_case")
        key = (rid, row.get("level")) if name == "traps" else rid
        if key in seen:
            err(path, f"{where}: повторний id {key}")
        seen.add(key)
    return body


def check_items(items, weapon_ids, trap_ids):
    """items.json: каталог предметів (іконка, назва, опис) для лобі й кімнат."""
    path = SHARED / "items.json"
    by_id = {}
    for i, it in enumerate(items):
        if not isinstance(it, dict):
            continue
        where = f"items[{i}] ({it.get('id')})"
        by_id[it.get("id")] = it
        icon = it.get("icon")
        if isinstance(icon, str) and not ICON_RE.match(icon):
            err(path, f"{where}: icon має бути порожнім або rbxassetid://<число>, зараз {icon!r}")
        for key in ("title", "description"):
            if isinstance(it.get(key), str) and not it[key].strip():
                err(path, f"{where}: {key} порожній")
        values = it.get("values") if isinstance(it.get("values"), dict) else {}
        used = set(PLACEHOLDER_RE.findall(it.get("description") or ""))
        for name in sorted(used - set(values)):
            err(path, f"{where}: у description є {{{name}}}, а в values немає ключа {name}")
        for name in sorted(set(values) - used):
            err(path, f"{where}: values.{name} не використано в description")
    for kind, ids in (("weapon", weapon_ids), ("trap", trap_ids)):
        have = {i for i, it in by_id.items() if it.get("kind") == kind}
        for i in sorted(ids - have):
            err(path, f"немає запису kind={kind} для id {i!r} (він є в {kind}s.json)")
        for i in sorted(have - ids):
            err(path, f"запис {i!r} має kind={kind}, але такого id немає в {kind}s.json")
    for cur in ("soft", "hard", "wisps"):
        if by_id.get(cur, {}).get("kind") != "currency":
            err(path, f"немає запису kind=currency для {cur!r}")
    # предмети, які магазини лобі видають як нагороду
    for shop in ("shop_soft", "shop_hard"):
        sp = ROOT / "lobby" / f"{shop}.json"
        if not sp.exists():
            continue
        try:
            rows = json.loads(sp.read_text(encoding="utf-8")).get("items") or []
        except Exception:  # noqa: BLE001
            continue  # синтаксис перевірить load() нижче
        for r in rows:
            rw = r.get("reward") if isinstance(r, dict) else None
            if isinstance(rw, dict) and rw.get("kind") in ("Item", "Booster") and rw.get("id") not in by_id:
                err(sp, f"reward.id {rw.get('id')!r} немає в items.json")


def check_portals(path):
    """lobby/portals.json: порталі лобі (id = ContentId порталу в Studio), Place ID кімнат."""
    if not path.exists():
        err(path, "файлу немає")
        return
    body = load(path)
    if not isinstance(body, dict):
        return
    for key, lo, hi in (("maxPlayers", 1, 4), ("autoJoinRadius", 1, 200)):
        v = body.get(key)
        if not isinstance(v, (int, float)) or isinstance(v, bool) or not (lo <= v <= hi):
            err(path, f"{key}: потрібне число {lo}..{hi}")
    portals = body.get("portals")
    if not isinstance(portals, list) or not portals:
        err(path, "portals: потрібен непорожній масив")
        return
    seen = set()
    for i, row in enumerate(portals):
        where = f"portals[{i}]"
        if not isinstance(row, dict):
            err(path, f"{where}: не об'єкт")
            continue
        pid = row.get("id")
        if not isinstance(pid, str) or not pid or pid in seen:
            err(path, f"{where}: id (рядок, збігається з ContentId порталу) має бути унікальним, зараз {pid!r}")
        seen.add(pid)
        if not isinstance(row.get("title"), str) or not row["title"]:
            err(path, f"{where}: потрібен title")
        place = row.get("placeId")
        if not isinstance(place, int) or isinstance(place, bool) or place < 0:
            err(path, f"{where}: placeId має бути цілим числом >= 0")
        if not isinstance(row.get("enabled"), bool):
            err(path, f"{where}: enabled має бути true/false")
        elif row["enabled"] and not place:
            err(path, f"{where}: enabled=true потребує placeId > 0")
        mp = row.get("maxPlayers")
        if mp is not None and (not isinstance(mp, int) or isinstance(mp, bool) or not 1 <= mp <= 4):
            err(path, f"{where}: maxPlayers 1..4")


def check_debug(path):
    """rules.json -> debug: { enabled: bool, user_ids: [UserId...] }. Ключа може не бути (= дебаг вимкнений)."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return
    block = data.get("debug")
    if block is None:
        return
    if not isinstance(block, dict):
        err(path, "debug має бути об'єктом")
        return
    for key in block:
        if key not in ("enabled", "user_ids"):
            err(path, f"debug: невідоме поле {key}")
    if not isinstance(block.get("enabled"), bool):
        err(path, "debug.enabled має бути true/false")
    ids = block.get("user_ids")
    if not isinstance(ids, list):
        err(path, "debug.user_ids має бути масивом чисел")
        return
    for i, uid in enumerate(ids):
        if not isinstance(uid, int) or isinstance(uid, bool) or uid <= 0:
            err(path, f"debug.user_ids[{i}]: потрібен додатний цілий UserId")
    if len(set(ids)) != len(ids):
        err(path, "debug.user_ids: є дублі")
    if block.get("enabled") is True and not ids:
        err(path, "debug.enabled=true, але user_ids порожній")


def main():
    shared = {}
    for n in SHARED_FILES:
        p = SHARED / f"{n}.json"
        if not p.exists():
            err(p, "файлу немає")
            continue
        shared[n] = check_file(p, n)
        if n == "rules":
            check_debug(p)

    enemy_ids = {e["id"] for e in (shared.get("enemies") or []) if isinstance(e, dict)}
    weapon_ids = {w["id"] for w in (shared.get("weapons") or []) if isinstance(w, dict)}
    for i, u in enumerate(shared.get("weapon_upgrades") or []):
        if isinstance(u, dict) and u.get("weapon_id") not in weapon_ids:
            err(SHARED / "weapon_upgrades.json", f"weapon_upgrades[{i}]: weapon_id {u.get('weapon_id')!r} немає в weapons")
    traps = shared.get("traps") or []
    by_trap = {}
    for t in traps:
        if isinstance(t, dict):
            by_trap.setdefault(t.get("id"), []).append(t.get("level"))
    for tid, levels in by_trap.items():
        if sorted(levels) != list(range(1, len(levels) + 1)):
            err(SHARED / "traps.json", f"пастка {tid}: рівні мають іти 1..N без пропусків, зараз {sorted(levels)}")
    if not any(isinstance(w, dict) and w.get("default_owned") for w in (shared.get("weapons") or [])):
        err(SHARED / "weapons.json", "жодна зброя не default_owned: гравцю не буде з чим грати")
    check_items(shared.get("items") or [], weapon_ids, set(by_trap))

    for room_dir in sorted(p for p in ROOMS.iterdir() if p.is_dir() and p.name != "shared"):
        if not ID_RE.match(room_dir.name):
            err(room_dir, "назва папки кімнати має бути snake_case")
        files = {}
        for n in ROOM_FILES:
            p = room_dir / f"{n}.json"
            if not p.exists():
                err(p, "файлу немає (кожна кімната має всі файли кімнати)")
                continue
            files[n] = check_file(p, n)
        for n in ROOM_OPTIONAL_FILES:
            p = room_dir / f"{n}.json"
            if p.exists():
                files[n] = check_file(p, n)
        room = files.get("room") or {}
        spawner_ids = set()
        for i, s in enumerate(room.get("spawners") or []):
            if not isinstance(s, dict) or not isinstance(s.get("id"), str) or not ID_RE.match(s["id"]):
                err(room_dir / "room.json", f"spawners[{i}]: потрібен id у snake_case")
                continue
            spawner_ids.add(s["id"])
        if room and room.get("id") != room_dir.name:
            err(room_dir / "room.json", f"room.id {room.get('id')!r} має збігатися з назвою папки {room_dir.name!r}")
        delays = {}
        for i, wv in enumerate(files.get("waves") or []):
            if not isinstance(wv, dict):
                continue
            if wv.get("enemy_id") not in enemy_ids:
                err(room_dir / "waves.json", f"waves[{i}]: enemy_id {wv.get('enemy_id')!r} немає в shared/enemies")
            if wv.get("spawner_id") not in spawner_ids:
                err(room_dir / "waves.json", f"waves[{i}]: spawner_id {wv.get('spawner_id')!r} немає в room.spawners")
            d = delays.setdefault(wv.get("wave"), wv.get("wave_delay"))
            if d != wv.get("wave_delay"):
                err(room_dir / "waves.json", f"waves[{i}]: wave_delay у хвилі {wv.get('wave')} має бути однаковим у всіх рядках")
        branch_spawners = set()
        for i, z in enumerate(files.get("zones") or []):
            if isinstance(z, dict) and "spawner_id" in z:
                if z["spawner_id"] not in spawner_ids:
                    err(room_dir / "zones.json", f"zones[{i}]: spawner_id {z['spawner_id']!r} немає в room.spawners")
                branch_spawners.add(z["spawner_id"])
        if len(spawner_ids) > 1 and branch_spawners != spawner_ids:
            err(room_dir / "zones.json", f"при кількох спавнерах кожен має свою гілку зон (spawner_id), зараз {sorted(branch_spawners)}")
        rewards = files.get("run_rewards") or shared.get("run_rewards") or {}
        wave_nums = {wv.get("wave") for wv in (files.get("waves") or []) if isinstance(wv, dict)}
        soft = rewards.get("wave_soft") if isinstance(rewards, dict) else None
        if isinstance(soft, list) and wave_nums:
            if len(soft) < max(wave_nums):
                err(room_dir / "waves.json", f"хвиль {max(wave_nums)}, а wave_soft у run_rewards має лише {len(soft)} значень: за зайві хвилі гравець не отримає софт")
            for i, v in enumerate(soft):
                if not isinstance(v, int) or isinstance(v, bool) or v < 0:
                    err(room_dir / "waves.json", f"run_rewards.wave_soft[{i}]: ціле >= 0")
        counts = sorted(p.get("players") for p in (files.get("players") or []) if isinstance(p, dict))
        if counts and counts != [1, 2, 3, 4]:
            err(room_dir / "players.json", f"потрібні рядки для 1, 2, 3, 4 гравців, зараз {counts}")

    check_portals(ROOT / "lobby" / "portals.json")

    # leaderboards.json і items.json лежать у кількох місцях, бо різні частини гри читають різні адреси: копії мають бути ідентичними
    for fname in ("leaderboards.json", "items.json"):
        copies = [ROOT / "lobby" / fname, SHARED / fname]
        copies = [p for p in copies if p.exists()]
        if len(copies) > 1:
            base = copies[0].read_bytes()
            for p in copies[1:]:
                if p.read_bytes() != base:
                    err(p, f"не збігається з {copies[0].relative_to(ROOT)}: копії {fname} мають бути ідентичними")

    # решта JSON (лобі, лідерборди): лише синтаксис
    for p in sorted(ROOT.rglob("*.json")):
        if ".git" in p.parts:
            continue
        rel = p.relative_to(ROOMS) if ROOMS in p.parents else None
        managed = rel is not None and len(rel.parts) == 2 and p.stem in SCHEMA
        if not managed:
            load(p)

    if errors:
        print(f"ПОМИЛКИ ({len(errors)}):")
        for e in errors:
            print("  -", e)
        return 1
    print("OK: усі конфіги валідні")
    return 0


if __name__ == "__main__":
    sys.exit(main())
