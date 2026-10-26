#!/usr/bin/env python3
"""Перевірка конфігів MustDie перед комітом.

Запуск з кореня репозиторію:  python3 tools/validate.py
Код виходу 0 = усе чисто, 1 = є помилки (коміт не робимо).

Що перевіряється:
- кожен *.json парситься, корінь це об'єкт, немає null;
- у файлах rooms/shared/ і rooms/<кімната>/ є meta (version, exported_at, note);
- колекції це масиви об'єктів з полем id у snake_case, id унікальні
  (пастка: один рядок на id, як зброя);
- обов'язкові поля, типи і діапазони за схемою нижче;
- посилання між файлами: waves -> enemies і спавнери кімнати, weapon_upgrades -> weapons, trap_upgrades -> traps;
- у кожній кімнаті є всі файли кімнати;
- wave_delay однаковий у всіх рядках однієї хвилі (гра бере його з першого рядка);
- копії leaderboards.json і items.json (lobby/, rooms/shared/) побайтно однакові;
- зброя (контракт 23.10.2026, docs/combat-config-contract.md): `defaults` має всі DEFAULT_KEYS, поля за fire_mode задані, on_hit/bonus_vs посилаються на ефекти з status_effects;
- прокачка: upgrade_types (stat = поле зброї / пастки або on_hit.<ефект>.<параметр>, item_id з items.json), рядки weapon_upgrades і trap_upgrades мають рівні 1..N, значення за типом і межами поля;
- зброя: tier (прогрес), price_soft у всіх базових (розблокування в лобі; у default_owned це бюджет ботів), модифікація = base_id + tier бази + order бази+1..9;
- пастки: price_soft = 0 у default_owned, інакше > 0 (розблокування в лобі); room.json: unlock_weapon існує, базова, tier не спадає з номером кімнати;
- bots.json: пул зброї ботів та бюджет на пастки (розблокування й прокачки); симулятор: python3 tools/validate.py --economy;
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
    "rules": {"_object": True, "_sections": True},  # поля в RULES_SCHEMA
    "enemies": {
        "id": (str, True, None, None), "name_en": (str, True, None, None), "name_uk": (str, True, None, None),
        "size": (str, True, None, None), "hp": (NUM, True, 1, None), "speed": (NUM, True, 0.1, None),
        "armor": (NUM, True, 0, 0.95), "damage_to_base": (NUM, True, 0, None), "reward": (int, True, 0, None),
        # контракт 23.10.2026, етап 1в: те, що було лише в Config.lua
        "hitbox": (list, True, None, None), "color": (str, True, None, None),
        "visual": (str, False, None, None), "visual_scale": (NUM, False, 0.1, 10),
    },
    "traps": {
        "id": (str, True, None, None), "order": (int, True, 0, None),
        "name_en": (str, True, None, None), "name_uk": (str, True, None, None),
        "mechanic": (str, True, None, None), "placement": (str, True, None, None),
        "cost": (int, True, 0, None), "price_soft": (int, True, 0, None), "damage": (NUM, True, 0, None),
        "cooldown": (NUM, False, 0, None),
        "fire_interval": (NUM, False, 0.01, None), "range": (NUM, False, 0, None),
        "default_owned": (bool, False, None, None), "enabled": (bool, False, None, None),
        # контракт 23.10.2026, етап 1в
        "damage_type": (str, False, None, None), "armor_pierce": (NUM, False, 0, 1), "on_hit": (dict, False, None, None),
        "trigger_radius": (NUM, False, 0.1, None), "hit_margin": (NUM, False, 0, None),
        "wall_height": (NUM, False, 0.1, None), "wall_span_max": (NUM, False, 1, None),
        # пастки v2 (docs/traps-v2.md): прямокутник у клітинках (ширина впоперек, довжина вздовж маршруту), крок зони
        "footprint_w": (int, False, 1, 32), "footprint_l": (int, False, 1, 32), "zone_tick": (NUM, False, 0.05, 5),
        "active_time": (NUM, False, 0.1, 60), "aura_tick": (NUM, False, 0.1, 5),
    },
    "weapons": {
        "id": (str, True, None, None), "order": (int, True, 0, None), "default_owned": (bool, False, None, None),
        "tier": (int, True, 1, 20), "price_soft": (int, False, 1, None), "base_id": (str, False, None, None),
        "name_en": (str, True, None, None), "name_uk": (str, True, None, None),
        "damage": (NUM, True, 0, None), "attack_interval": (NUM, True, 0.01, None), "range": (NUM, True, 0, None),
        "projectile_speed": (NUM, False, 0.1, None), "gravity": (NUM, False, 0, None),
        "ricochet": (int, False, 0, None), "multishot": (int, False, 1, None),
        "crit_chance": (NUM, False, 0, 1), "crit_mult": (NUM, False, 1, None),
        "pellets": (int, False, 1, None), "spread": (NUM, False, 0, 90),
        "falloff_start": (NUM, False, 0, None), "falloff_min": (NUM, False, 0, 1),
        # арсенал 19.10.2026
        "rarity": (str, True, None, None), "fire_mode": (str, True, None, None),
        "pierce": (int, False, 0, None), "multishot_spread": (NUM, False, 0, 45),
        "dual_rate": (NUM, False, 1, None), "dual_spread": (NUM, False, 0, 90), "dual_magazine_mult": (NUM, False, 1, None),
        "spread_max": (NUM, False, 0, 90), "spread_grow": (NUM, False, 0, 90), "spread_recover": (NUM, False, 0, None),
        "beam_time": (NUM, False, 0.1, None), "cooldown": (NUM, False, 0, None),
        "plasma_interval": (NUM, False, 0.1, None), "plasma_radius": (NUM, False, 0, None),
        "cone": (NUM, False, 1, 90), "splash_share": (NUM, False, 0, 1),
        # контракт конфігів бою 23.10.2026
        "auto": (bool, False, None, None), "damage_type": (str, False, None, None),
        "projectile_style": (str, False, None, None), "stick": (bool, False, None, None),
        "volley_delay": (NUM, False, 0, 1), "ricochet_range": (NUM, False, 0, None),
        "ricochet_damage_mult": (NUM, False, 0, 1), "dual": (int, False, 0, 1),
        "magazine": (int, False, 0, None), "reload_time": (NUM, False, 0, None),
        "reload_per_round": (bool, False, None, None), "reload_interruptible": (bool, False, None, None),
        "plasma_damage": (NUM, False, 0, None), "plasma_speed": (NUM, False, 1, None),
        "targets": (int, False, 1, None), "splash_radius": (NUM, False, 0, None),
        "armor_pierce": (NUM, False, 0, 1), "knockback": (NUM, False, 0, None),
        "bonus_vs": (dict, False, None, None), "on_hit": (dict, False, None, None),
    },
    "weapon_upgrades": {
        "id": (str, True, None, None), "weapon_id": (str, True, None, None), "upgrade": (str, True, None, None),
        "order": (int, True, 0, None), "level": (int, True, 1, 10), "price_soft": (int, True, 1, None), "value": (NUM, True, None, None),
    },
    # прокачка пасток (25.10.2026): як weapon_upgrades, власник trap_id
    "trap_upgrades": {
        "id": (str, True, None, None), "trap_id": (str, True, None, None), "upgrade": (str, True, None, None),
        "order": (int, True, 0, None), "level": (int, True, 1, 10), "price_soft": (int, True, 1, None), "value": (NUM, True, None, None),
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
        "unlock_weapon": (str, True, None, None),
        "base_hp": (NUM, True, 1, None), "door_timer": (NUM, True, 0, None), "spawners": (list, True, None, None),
    },
    "bots": {
        "_object": True,
        "weapon_pool_exclude": (list, True, None, None), "include_premium": (bool, True, None, None),
        "trap_budget_mult": (NUM, True, 0, 100), "upgrade_budget_mult": (NUM, True, 0, 100),
    },
    "zones": {
        "id": (str, True, None, None), "order": (int, True, 0, None), "name_en": (str, True, None, None),
        "name_uk": (str, True, None, None), "length": (NUM, True, 0, None),
        "lanes": (int, True, 1, 64),
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
    # ефекти на ворогах (EffectService v2, docs/effects-v2.md): стеки, модифікатори, теги, переходи; новий id = новий ефект без коду
    "status_effects": {
        "id": (str, True, None, None), "name_en": (str, True, None, None), "name_uk": (str, True, None, None),
        "max_stacks": (int, False, 1, 50), "duration": (NUM, False, 0, None), "decay_interval": (NUM, False, 0, None),
        "reapply": (str, False, None, None), "tick": (NUM, False, 0.05, 5),
        "modifiers": (list, False, None, None), "damage_type": (str, False, None, None), "armor_pierce": (NUM, False, 0, 1),
        "grants_tags": (list, False, None, None), "requires_tags": (list, False, None, None), "blocked_by_tags": (list, False, None, None),
        "on_max_stacks": (dict, False, None, None), "on_end": (dict, False, None, None), "on_death": (dict, False, None, None),
        "visual": (str, False, None, None),
    },
    "sounds": {
        "id": (str, True, None, None), "asset": (str, True, None, None),
        "volume": (NUM, True, 0, 2), "pitch": (NUM, True, 0.1, 4),
    },
    "items": {
        "id": (str, True, None, None), "kind": (str, True, None, None), "icon": (str, True, None, None),
        "title": (str, True, None, None), "description": (str, True, None, None), "values": (dict, False, None, None),
    },
}
# Той самий перелік у грі: ConfigLoader.DAMAGE_TYPES. Змінюєш тут — зміни і там, і запусти tools/studio/config_parity_test.luau
DAMAGE_TYPES = {"physical", "fire", "shock", "ice"}
ENUMS = {
    ("items", "kind"): {"currency", "weapon", "trap", "booster", "item", "enemy", "upgrade"},
    ("enemies", "size"): {"small", "medium", "large"},
    ("traps", "mechanic"): {"snare", "wall", "turret", "zone", "aura"},
    ("traps", "placement"): {"floor", "wall"},
    ("traps", "damage_type"): DAMAGE_TYPES,
    ("status_effects", "damage_type"): DAMAGE_TYPES,
    ("status_effects", "reapply"): {"refresh", "ignore"},
    ("status_effects", "visual"): {"fire"},
    ("weapons", "rarity"): {"common", "uncommon", "rare", "epic", "legendary"},
    ("weapons", "fire_mode"): {"melee", "projectile", "hitscan", "pellets", "beam", "curse"},
    ("weapons", "damage_type"): DAMAGE_TYPES,
    ("weapons", "projectile_style"): {"arrow", "bolt", "pebble"},
}
# поля зброї, які не мають дефолту (ідентифікація і базові стати)
WEAPON_IDENTITY = {"id", "order", "default_owned", "tier", "price_soft", "base_id", "name_en", "name_uk",
                   "rarity", "fire_mode", "damage", "attack_interval", "range"}
# поля, які код читає без запасного значення: defaults мусить містити всі
DEFAULT_KEYS = (
    "auto", "damage_type", "armor_pierce", "knockback", "gravity", "stick", "pierce",
    "multishot", "multishot_spread", "volley_delay", "ricochet", "ricochet_range", "ricochet_damage_mult",
    "crit_chance", "crit_mult", "spread", "pellets", "falloff_min", "dual", "dual_rate", "dual_magazine_mult",
    "magazine", "reload_time", "reload_per_round", "reload_interruptible",
    "plasma_damage", "plasma_interval", "plasma_radius", "plasma_speed", "targets", "splash_radius", "splash_share",
)
# що обов'язково має бути в рядку зброї (або в defaults) для механіки fire_mode
MODE_REQUIRED = {
    "melee": ("cone",), "projectile": ("projectile_speed",), "hitscan": (),
    "pellets": ("projectile_speed",), "beam": ("beam_time", "cooldown"), "curse": ("cone",),
}
# Словник модифікаторів, який розуміє код (docs/effects-v2.md); combine, базове значення й межі задає секція stats у status_effects.json
STAT_IDS = ("speed_mult", "damage_taken_mult", "dps", "hp_pct_per_sec")
COMBINES = {"add", "mul", "max", "min"}
EFFECT_INFO = {}  # id ефекту -> {"max_stacks": n, "params": {параметр джерела: (мін, макс, лише ціле)}}; заповнює check_effects


def effect_params(eid):
    """Які числа джерело (on_hit зброї чи пастки, прокачка) може передати цьому ефекту."""
    return (EFFECT_INFO.get(eid) or {}).get("params") or {}


UPGRADE_OPS = {"set", "add", "mul"}
TYPE_FIELDS = {"id": (str, True, None, None), "stat": (str, True, None, None), "name_en": (str, True, None, None),
               "name_uk": (str, True, None, None), "desc_en": (str, True, None, None), "item_id": (str, False, None, None), "op": (str, False, None, None),
               "display_mult": (NUM, False, 0.001, 1000)}
SHARED_FILES = ["rules", "enemies", "traps", "trap_upgrades", "weapons", "weapon_upgrades", "run_rewards", "items", "bots", "status_effects", "sounds"]
GENERATED_REWARD_KINDS = {"Weapon", "TrapLevel", "WeaponUpgrade", "TrapUpgrade"}
HEX_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")
REWARD_MODES = {"each", "split", "killer"}
# rules.json -> rules: секції (поле: (тип, мін, макс)); усі поля обов'язкові, запасних значень у коді немає
RULES_SCHEMA = {
    "run": {
        "start_wisps": (int, 0, None), "reward_mode": (str, None, None), "start_weapon": (str, None, None),
        "restart_delay": (NUM, 0, 600), "weapon_select_seconds": (NUM, 1, 120), "weapon_select_delay": (NUM, 0, 10),
    },
    "player": {"walk_speed": (NUM, 1, 200), "sprint_speed": (NUM, 1, 300)},
    "traps": {
        "cell_size": (NUM, 0.1, None), "place_reach": (NUM, 1, 2000), "reach": (NUM, 1, 200),
        "reach_slack": (NUM, 0, 100), "refund_share": (NUM, 0, 1),
    },
    "enemies": {
        "corridor_lanes": (int, 1, 64), "turn_radius": (NUM, 0, 200), "speed_jitter": (NUM, 0, 1),
        "spawn_jitter": (NUM, 0, 1), "drift_amplitude": (NUM, 0, 100), "drift_scale": (NUM, 1, 1000),
    },
    "combat": {"max_live_shots": (int, 1, 1000), "net_tolerance": (NUM, 0, 1)},
}
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


def check_value(path, name, key, v, spec, where):
    """Тип, межі й enum одного значення за специфікацією (тип, обов'язкове, мін, макс). True = значення придатне."""
    t, _req, lo, hi = spec
    if not type_ok(v, t):
        err(path, f"{where}: {key} має неправильний тип ({v!r})")
        return False
    ok = True
    if lo is not None and v < lo:
        err(path, f"{where}: {key}={v} менше за {lo}")
        ok = False
    if hi is not None and v > hi:
        err(path, f"{where}: {key}={v} більше за {hi}")
        ok = False
    if (name, key) in ENUMS and v not in ENUMS[(name, key)]:
        err(path, f"{where}: {key}={v!r} не з {sorted(ENUMS[(name, key)])}")
        ok = False
    return ok


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
        check_value(path, name, key, row[key], spec, where)
    for key in row:
        if key not in schema or key.startswith("_"):
            err(path, f"{where}: невідоме поле {key} (додай його в схему і README)")


def check_rules(path, body):
    """rules.json -> rules: секції run / player / traps / enemies / combat, усі поля обов'язкові."""
    for section, fields in RULES_SCHEMA.items():
        block = body.get(section)
        if not isinstance(block, dict):
            err(path, f"rules.{section}: потрібен об'єкт")
            continue
        for key, (t, lo, hi) in fields.items():
            if key not in block:
                err(path, f"rules.{section}: немає поля {key}")
                continue
            check_value(path, "rules", key, block[key], (t, True, lo, hi), f"rules.{section}")
        for key in block:
            if key not in fields:
                err(path, f"rules.{section}: невідоме поле {key} (додай його в схему і README)")
    for section in body:
        if section not in RULES_SCHEMA:
            err(path, f"rules: невідома секція {section} (є {sorted(RULES_SCHEMA)})")
    mode = (body.get("run") or {}).get("reward_mode")
    if isinstance(mode, str) and mode not in REWARD_MODES:
        err(path, f"rules.run: reward_mode={mode!r} не з {sorted(REWARD_MODES)}")
    walk, sprint = (body.get("player") or {}).get("walk_speed"), (body.get("player") or {}).get("sprint_speed")
    if type_ok(walk, NUM) and type_ok(sprint, NUM) and sprint < walk:
        err(path, "rules.player: sprint_speed менша за walk_speed")


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
    if SCHEMA[name].get("_sections"):
        if not isinstance(body, dict):
            err(path, f"{name} має бути об'єктом")
            return None
        check_rules(path, body)
        return body
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
        key = rid
        if key in seen:
            err(path, f"{where}: повторний id {key}")
        seen.add(key)
    return body


def load_raw(path):
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}
    return data if isinstance(data, dict) else {}


def check_effects(effects, stats_raw):
    """status_effects.json (docs/effects-v2.md): секція stats, стекінг, модифікатори, теги, переходи, цикли. Заповнює EFFECT_INFO."""
    path = SHARED / "status_effects.json"
    EFFECT_INFO.clear()
    # --- секція stats: combine, базове значення й межі кожного стата зі словника
    stats = {}
    if not isinstance(stats_raw, list) or not stats_raw:
        err(path, "потрібна секція stats: масив зі статами " + ", ".join(STAT_IDS))
        stats_raw = []
    for i, st in enumerate(stats_raw):
        where = f"stats[{i}]"
        if not isinstance(st, dict) or not isinstance(st.get("id"), str):
            err(path, f"{where}: потрібен об'єкт з id")
            continue
        sid = st["id"]
        where = f"stats[{sid}]"
        if sid not in STAT_IDS:
            err(path, f"{where}: код не знає стата {sid!r} (є {list(STAT_IDS)})")
            continue
        if sid in stats:
            err(path, f"{where}: стат описано двічі")
            continue
        for key in st:
            if key not in ("id", "combine", "base", "min", "max"):
                err(path, f"{where}: невідоме поле {key}")
        if st.get("combine") not in COMBINES:
            err(path, f"{where}: combine має бути одним з {sorted(COMBINES)}")
        if not type_ok(st.get("base"), NUM):
            err(path, f"{where}: base має бути числом")
        for key in ("min", "max"):
            if key in st and not type_ok(st[key], NUM):
                err(path, f"{where}: {key} має бути числом")
        if all(type_ok(st.get(k), NUM) for k in ("min", "max")) and st["min"] > st["max"]:
            err(path, f"{where}: min більше за max")
        stats[sid] = st
    for sid in STAT_IDS:
        if stats_raw and sid not in stats:
            err(path, f"stats: немає опису стата {sid!r}")

    by_id = {e["id"]: e for e in effects if isinstance(e, dict) and isinstance(e.get("id"), str)}
    granted = set()
    for e in by_id.values():
        if isinstance(e.get("grants_tags"), list):
            granted |= {t for t in e["grants_tags"] if isinstance(t, str)}

    def tag_list(where, key, row):
        vals = row.get(key)
        if vals is None:
            return
        if not isinstance(vals, list) or not vals:
            err(path, f"{where}: {key} має бути непорожнім масивом тегів")
            return
        seen = set()
        for t in vals:
            if not isinstance(t, str) or not ID_RE.match(t):
                err(path, f"{where}: тег {t!r} не snake_case")
            elif t in seen:
                err(path, f"{where}: тег {t!r} повторюється в {key}")
            elif key != "grants_tags" and t not in granted:
                err(path, f"{where}: тег {t!r} ({key}) не видає жоден ефект (теги ворогів з'являться на етапі 7)")
            seen.add(t)

    edges = {}
    for eid, e in by_id.items():
        where = f"status_effects[{eid}]"
        n = e.get("max_stacks", 1) if type_ok(e.get("max_stacks", 1), int) else 1
        stackable = n > 1
        # --- таймер чи лічильник
        if stackable:
            for bad in ("duration", "reapply"):
                if bad in e:
                    err(path, f"{where}: {bad} не для лічильника (max_stacks > 1); час життя задає decay_interval")
        else:
            if "duration" not in e:
                err(path, f"{where}: для max_stacks = 1 потрібне duration (0 = до зняття або смерті)")
            if "decay_interval" in e:
                err(path, f"{where}: decay_interval лише для лічильника (max_stacks > 1)")
        # --- модифікатори
        params = {"chance": (0, 1, False)}
        mods = e.get("modifiers")
        has_mod = False
        if mods is not None:
            if not isinstance(mods, list) or not mods:
                err(path, f"{where}: modifiers має бути непорожнім масивом")
                mods = []
            used = set()
            for j, m in enumerate(mods):
                mw = f"{where}.modifiers[{j}]"
                if not isinstance(m, dict):
                    err(path, f"{mw}: не об'єкт")
                    continue
                for key in m:
                    if key not in ("stat", "value", "per_stack", "requires_tags"):
                        err(path, f"{mw}: невідоме поле {key}")
                stat = m.get("stat")
                if not isinstance(stat, str):
                    err(path, f"{mw}: потрібне поле stat")
                    continue
                base, _, typ = stat.partition(".")
                if base not in STAT_IDS or (typ and (base != "damage_taken_mult" or typ not in DAMAGE_TYPES)):
                    err(path, f"{mw}: stat {stat!r} не зі словника ({list(STAT_IDS)}; для damage_taken_mult можна .<тип урону>)")
                    continue
                has_mod = True
                if stat in used:
                    err(path, f"{mw}: stat {stat!r} повторюється в одному ефекті")
                used.add(stat)
                spec = stats.get(base)
                if not type_ok(m.get("value"), NUM):
                    err(path, f"{mw}: value має бути числом")
                elif spec:
                    lo, hi = spec.get("min"), spec.get("max")
                    if (lo is not None and m["value"] < lo) or (hi is not None and m["value"] > hi):
                        err(path, f"{mw}: value={m['value']} поза межами стата {base} ({lo}..{hi})")
                if "per_stack" in m:
                    if not isinstance(m["per_stack"], bool):
                        err(path, f"{mw}: per_stack має бути true/false")
                    elif m["per_stack"] and not stackable:
                        err(path, f"{mw}: per_stack має сенс лише для max_stacks > 1")
                    elif m["per_stack"] and spec and spec.get("combine") in ("max", "min"):
                        err(path, f"{mw}: per_stack не поєднується з combine {spec['combine']} стата {base}")
                if "requires_tags" in m:
                    tag_list(mw, "requires_tags", m)
                if not stackable and "." not in stat:
                    lo = spec.get("min", 0) if spec else 0
                    params[stat] = (lo if type_ok(lo, NUM) else 0, spec.get("max") if spec else None, False)
        # --- теги й умови
        for key in ("grants_tags", "requires_tags", "blocked_by_tags"):
            tag_list(where, key, e)
        # --- переходи
        for ev in ("on_max_stacks", "on_end", "on_death"):
            block = e.get(ev)
            if block is None:
                continue
            ew = f"{where}.{ev}"
            if not block:
                err(path, f"{ew}: порожній об'єкт")
                continue
            if ev == "on_max_stacks" and not stackable:
                err(path, f"{ew}: лише для лічильника (max_stacks > 1)")
            allowed = {"on_max_stacks": ("consume", "apply", "stacks", "duration"),
                       "on_end": ("apply", "stacks", "duration"), "on_death": ("blast",)}[ev]
            for key in block:
                if key not in allowed:
                    err(path, f"{ew}: невідоме поле {key} (є {list(allowed)})")
            if "consume" in block and not isinstance(block["consume"], bool):
                err(path, f"{ew}.consume має бути true/false")
            if "apply" in block:
                target = block["apply"]
                if target not in by_id:
                    err(path, f"{ew}.apply: ефекту {target!r} немає")
                else:
                    edges.setdefault(eid, set()).add(target)
                    tn = by_id[target].get("max_stacks", 1)
                    if "stacks" in block and (not type_ok(block["stacks"], int) or not 1 <= block["stacks"] <= (tn if type_ok(tn, int) else 1)):
                        err(path, f"{ew}.stacks: ціле 1..{tn} (max_stacks ефекту {target})")
                    if "duration" in block and (not type_ok(block["duration"], NUM) or block["duration"] <= 0):
                        err(path, f"{ew}.duration: число > 0")
            elif "stacks" in block or "duration" in block:
                err(path, f"{ew}: stacks/duration мають сенс лише разом з apply")
            if ev == "on_death":
                blast = block.get("blast")
                if not isinstance(blast, dict):
                    err(path, f"{ew}.blast: потрібен об'єкт {{damage, radius, ...}}")
                else:
                    bspec = {"damage": (NUM, True, 0, None), "radius": (NUM, True, 0.1, None),
                             "damage_type": (str, False, None, None), "armor_pierce": (NUM, False, 0, 1),
                             "fx": (str, False, None, None), "sound": (str, False, None, None)}
                    for key, sp in bspec.items():
                        if key not in blast:
                            if sp[1]:
                                err(path, f"{ew}.blast: немає поля {key}")
                            continue
                        if check_value(path, "status_effects", key, blast[key], sp, f"{ew}.blast") is False:
                            continue
                    for key in blast:
                        if key not in bspec:
                            err(path, f"{ew}.blast: невідоме поле {key}")
                    if not stackable:
                        params["damage"] = (0, None, False)
                        params["radius"] = (0.1, None, False)
        # --- що можна передати з джерела
        if stackable:
            params["stacks"] = (1, n, True)
        else:
            params["duration"] = (0, None, False)
        EFFECT_INFO[eid] = {"max_stacks": n, "params": params}
        if not (has_mod or e.get("grants_tags") or e.get("on_death") or e.get("on_end") or e.get("on_max_stacks")):
            err(path, f"{where}: ефект нічого не робить (потрібні modifiers, grants_tags або події)")
        if e.get("damage_type") and not any(isinstance(m, dict) and str(m.get("stat")) in ("dps", "hp_pct_per_sec") for m in (mods or [])):
            err(path, f"{where}: damage_type/armor_pierce/tick мають сенс лише з модифікаторами dps або hp_pct_per_sec")

    # --- цикли в apply (A -> B -> A)
    state = {}

    def visit(node, trail):
        state[node] = 1
        for nxt in sorted(edges.get(node, ())):
            if state.get(nxt) == 1:
                err(path, "цикл переходів: " + " -> ".join(trail + [node, nxt]))
            elif nxt not in state:
                visit(nxt, trail + [node])
        state[node] = 2

    for eid in sorted(edges):
        if eid not in state:
            visit(eid, [])


def check_effect_map(path, where, block, effect_ids, params=True):
    """on_hit: {effect_id: {chance, stacks, duration, <число модифікатора>, ...}}; bonus_vs: {effect_id: множник}."""
    if not isinstance(block, dict):
        return
    for eid, val in block.items():
        if eid not in effect_ids:
            err(path, f"{where}: ефекту {eid!r} немає в status_effects.json")
        if not params:
            if not type_ok(val, NUM) or not 0 <= val <= 10:
                err(path, f"{where}.{eid}: множник має бути числом 0..10")
            continue
        if not isinstance(val, dict) or not val:
            err(path, f"{where}.{eid}: потрібен непорожній об'єкт з числами (chance, stacks, duration, ...)")
            continue
        allowed = effect_params(eid)
        for pk, pv in val.items():
            if pk not in allowed:
                err(path, f"{where}.{eid}: невідомий параметр {pk} (для цього ефекту є {sorted(allowed)})")
                continue
            lo, hi, whole = allowed[pk]
            if not type_ok(pv, int if whole else NUM) or pv < lo or (hi is not None and pv > hi):
                err(path, f"{where}.{eid}.{pk}: потрібне {'ціле' if whole else 'число'} {lo}..{hi if hi is not None else '∞'}")


TRAP_REQUIRED = {
    "snare": ("cooldown", "trigger_radius", "on_hit"),
    "wall": ("hit_margin", "wall_height", "wall_span_max"),
    "turret": ("fire_interval", "range"),
    "zone": ("zone_tick", "on_hit"),
    "aura": ("cooldown", "range", "active_time", "aura_tick", "on_hit"),
}


def check_enemy_extras(enemies):
    path = SHARED / "enemies.json"
    for i, e in enumerate(enemies):
        if not isinstance(e, dict):
            continue
        where = f"enemies[{i}] {e.get('id')!r}"
        hb = e.get("hitbox")
        if isinstance(hb, list) and (len(hb) != 3 or not all(type_ok(v, NUM) and 0.1 <= v <= 100 for v in hb)):
            err(path, f"{where}: hitbox має бути [x, y, z] студів, числа 0.1..100")
        col = e.get("color")
        if isinstance(col, str) and not HEX_RE.match(col):
            err(path, f"{where}: color має бути hex #RRGGBB, зараз {col!r}")
        if "visual_scale" in e and "visual" not in e:
            err(path, f"{where}: visual_scale без visual")


def check_trap_extras(traps, effect_ids):
    path = SHARED / "traps.json"
    for i, t in enumerate(traps):
        if not isinstance(t, dict):
            continue
        where = f"traps[{i}] {t.get('id')!r}"
        for key in TRAP_REQUIRED.get(t.get("mechanic"), ()):
            if key not in t:
                err(path, f"{where}: для mechanic={t.get('mechanic')} потрібне поле {key}")
        if "on_hit" in t:
            check_effect_map(path, f"{where}.on_hit", t["on_hit"], effect_ids)
        if t.get("mechanic") == "snare":
            stun = (t.get("on_hit") or {}).get("stun") if isinstance(t.get("on_hit"), dict) else None
            if not isinstance(stun, dict) or not type_ok(stun.get("duration"), NUM) or stun["duration"] <= 0:
                err(path, f"{where}: капкан тримає ворога через on_hit.stun.duration > 0")


def check_sound_refs(sounds, effects, rules, weapons):
    path = SHARED / "sounds.json"
    ids = {x["id"] for x in sounds if isinstance(x, dict) and isinstance(x.get("id"), str)}
    for e in effects:
        blast = ((e.get("on_death") or {}).get("blast") or {}) if isinstance(e, dict) and isinstance(e.get("on_death"), dict) else {}
        if isinstance(blast, dict) and "sound" in blast and blast["sound"] not in ids:
            err(SHARED / "status_effects.json", f"status_effects {e.get('id')!r}: on_death.blast.sound {blast['sound']!r} немає в sounds.json")
    for need in ("music", "enemy_hit", "enemy_death", "click"):
        if need not in ids:
            err(path, f"немає звуку {need!r}, який грає код")
    start = ((rules or {}).get("run") or {}).get("start_weapon")
    by = {w["id"]: w for w in weapons if isinstance(w, dict) and isinstance(w.get("id"), str)}
    if isinstance(start, str):
        if start not in by:
            err(SHARED / "rules.json", f"rules.run.start_weapon {start!r} немає в weapons.json")
        elif not by[start].get("default_owned"):
            err(SHARED / "rules.json", f"rules.run.start_weapon {start!r} не default_owned: гравець може її не мати")


def check_weapon_extras(weapons, effect_ids):
    """weapons.json: блок defaults, обов'язкові поля за fire_mode, on_hit і bonus_vs."""
    path = SHARED / "weapons.json"
    defaults = load_raw(path).get("defaults")
    if not isinstance(defaults, dict):
        err(path, "потрібен об'єкт defaults: значення пропущених необов'язкових полів (код не має запасних значень)")
        defaults = {}
    for key in DEFAULT_KEYS:
        if key not in defaults:
            err(path, f"defaults: немає {key}")
    for key, v in defaults.items():
        spec = SCHEMA["weapons"].get(key)
        if spec is None or key in WEAPON_IDENTITY or key in ("on_hit", "bonus_vs"):
            err(path, f"defaults.{key}: це поле не має дефолту")
            continue
        check_value(path, "weapons", key, v, spec, f"defaults.{key}")
    # knockback зарезервовано контрактом, механіки в коді ще немає: не 0 = дизайнер чекає ефекту, якого не буде
    if type_ok(defaults.get("knockback", 0), NUM) and defaults.get("knockback", 0) != 0:
        err(path, "defaults.knockback: механіки відкидання ще немає в коді, лиши 0 (docs/combat-config-contract.md)")
    for i, w in enumerate(weapons):
        if not isinstance(w, dict):
            continue
        where = f"weapons[{i}] ({w.get('id')})"
        if type_ok(w.get("knockback", 0), NUM) and w.get("knockback", 0) != 0:
            err(path, f"{where}.knockback: механіки відкидання ще немає в коді, лиши 0")
        check_effect_map(path, f"{where}.on_hit", w.get("on_hit"), effect_ids)
        check_effect_map(path, f"{where}.bonus_vs", w.get("bonus_vs"), effect_ids, params=False)
        for key in MODE_REQUIRED.get(w.get("fire_mode"), ()):
            if key not in w and key not in defaults:
                err(path, f"{where}: для fire_mode={w['fire_mode']} потрібне поле {key}")


# Поля пастки, які можна качати (решта: каталог, механіка, розміщення)
TRAP_UPGRADABLE = {"damage", "cooldown", "fire_interval", "range", "trigger_radius", "hit_margin", "wall_span_max", "armor_pierce", "footprint_l", "active_time"}


def resolve_stat(stat, effect_ids, owner="weapons"):
    """stat прокачки: ('field', key, spec) | ('on_hit', ефект, параметр, spec) | рядок з поясненням помилки."""
    parts = stat.split(".")
    if len(parts) == 1:
        spec = SCHEMA[owner].get(stat)
        if owner == "traps":
            if spec is None or stat not in TRAP_UPGRADABLE:
                return f"stat {stat!r} це не поле пастки, яке можна качати ({sorted(TRAP_UPGRADABLE)})"
        elif spec is None or stat in WEAPON_IDENTITY - {"damage", "attack_interval", "range"}:
            return f"stat {stat!r} це не поле зброї, яке можна качати"
        if spec[0] not in (int, NUM):
            return f"stat {stat!r} не числове поле"
        return ("field", stat, spec)
    if len(parts) == 3 and parts[0] == "on_hit":
        _, eid, param = parts
        if eid not in effect_ids:
            return f"stat {stat!r}: ефекту {eid!r} немає в status_effects.json"
        allowed = effect_params(eid)
        if param not in allowed:
            return f"stat {stat!r}: параметр {param!r} не з {sorted(allowed)}"
        lo, hi, whole = allowed[param]
        return ("on_hit", eid, param, (int if whole else NUM, True, lo, hi))
    return f"stat {stat!r}: очікується поле {'пастки' if owner == 'traps' else 'зброї'} або on_hit.<ефект>.<параметр>"


def check_upgrades(rows, weapons, effect_ids, items, file="weapon_upgrades", owner="weapons", owner_key="weapon_id", other_items=frozenset()):
    """upgrade_types (що змінює кожна прокачка) і рядки weapon_upgrades / trap_upgrades. Повертає item_id, які використано.
    other_items: item_id з іншого файлу прокачок (предмет kind=upgrade має бути прив'язаний хоча б в одному)."""
    path = SHARED / f"{file}.json"
    raw_types = load_raw(path).get("upgrade_types")
    if not isinstance(raw_types, list) or not raw_types:
        err(path, "потрібен непорожній масив upgrade_types")
        return set()
    by_type = {}
    for i, t in enumerate(raw_types):
        where = f"upgrade_types[{i}]"
        if not isinstance(t, dict):
            err(path, f"{where}: не об'єкт")
            continue
        for key, spec in TYPE_FIELDS.items():
            if key in t:
                check_value(path, "upgrade_types", key, t[key], spec, where)
            elif spec[1]:
                err(path, f"{where}: немає поля {key}")
        for key in t:
            if key not in TYPE_FIELDS:
                err(path, f"{where}: невідоме поле {key}")
        for name in PLACEHOLDER_RE.findall(t.get("desc_en") or ""):
            if name not in ("new", "delta"):
                err(path, f"{where}: desc_en містить {{{name}}}, дозволено лише {{new}} і {{delta}}")
        tid = t.get("id")
        if isinstance(tid, str):
            if not ID_RE.match(tid):
                err(path, f"{where}: id {tid!r} не snake_case")
            if tid in by_type:
                err(path, f"{where}: повторний id {tid}")
            by_type[tid] = t
        if t.get("op", "set") not in UPGRADE_OPS:
            err(path, f"{where}: op має бути з {sorted(UPGRADE_OPS)}")
        if isinstance(t.get("stat"), str):
            r = resolve_stat(t["stat"], effect_ids, owner)
            if isinstance(r, str):
                err(path, f"{where}: {r}")
            else:
                t["_resolved"] = r
    # item_id <-> items.json (kind=upgrade)
    upgrade_items = {it["id"] for it in items if isinstance(it, dict) and it.get("kind") == "upgrade"}
    used_items = [t["item_id"] for t in by_type.values() if "item_id" in t]
    for iid in used_items:
        if iid not in upgrade_items:
            err(path, f"item_id {iid!r} немає в items.json з kind=upgrade")
    for iid in sorted(upgrade_items - set(used_items) - set(other_items)):
        err(path, f"предмет {iid!r} (kind=upgrade) не прив'язаний до жодного upgrade_types.item_id")
    if len(set(used_items)) != len(used_items):
        err(path, "item_id повторюється в upgrade_types")
    # рядки рівнів
    wby = {w["id"]: w for w in weapons if isinstance(w, dict) and isinstance(w.get("id"), str)}
    levels = {}
    for i, u in enumerate(rows):
        if not isinstance(u, dict):
            continue
        where = f"{file}[{i}] ({u.get('id')})"
        t = by_type.get(u.get("upgrade"))
        if t is None:
            err(path, f"{where}: upgrade {u.get('upgrade')!r} немає в upgrade_types")
            continue
        if u.get(owner_key) not in wby:
            err(path, f"{where}: {owner_key} {u.get(owner_key)!r} немає в {owner}.json")
        if u.get("id") != f"{u.get(owner_key)}_{u.get('upgrade')}_{u.get('level')}":
            err(path, f"{where}: id має бути <{owner_key}>_<upgrade>_<level>")
        levels.setdefault((u.get(owner_key), u.get("upgrade")), []).append(u.get("level"))
        r = t.get("_resolved")
        w = wby.get(u.get(owner_key))
        if r is None or w is None or not type_ok(u.get("value"), NUM):
            continue
        if t.get("op", "set") == "set":
            spec = r[-1]
            if spec[0] is int and not type_ok(u["value"], int):
                err(path, f"{where}: поле {t['stat']} ціле, а value={u['value']!r}")
            else:
                lo, hi = spec[2], spec[3]
                if (lo is not None and u["value"] < lo) or (hi is not None and u["value"] > hi):
                    err(path, f"{where}: value={u['value']} поза межами {t['stat']} ({lo}..{hi})")
        if r[0] == "on_hit" and r[1] not in (w.get("on_hit") or {}):
            err(path, f"{where}: прокачка змінює {t['stat']}, а в {w['id']} немає on_hit.{r[1]} (додай запис з нульовим головним числом або chance 0)")
        if r[0] == "field" and owner == "traps" and r[1] not in w:
            err(path, f"{where}: прокачка змінює {t['stat']}, а в пастці {w['id']} немає поля {r[1]}")
    for (wid, up), lv in levels.items():
        if sorted(lv) != list(range(1, len(lv) + 1)):
            err(path, f"{wid}/{up}: рівні мають іти 1..N без пропусків, зараз {sorted(lv)}")
    for t in by_type.values():
        t.pop("_resolved", None)
    return set(used_items)


def check_items(items, weapon_ids, trap_ids, enemy_ids=frozenset()):
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
    # вороги: перевірка вмикається з першим записом kind=enemy (до публікації пакета Core з типом enemy рядків додавати не можна)
    have_enemy = {i for i, it in by_id.items() if it.get("kind") == "enemy"}
    if have_enemy:
        for i in sorted(enemy_ids - have_enemy):
            err(path, f"немає запису kind=enemy для id {i!r} (він є в enemies.json)")
        for i in sorted(have_enemy - enemy_ids):
            err(path, f"запис {i!r} має kind=enemy, але такого id немає в enemies.json")
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


def check_economy(weapons, traps, bots, room_unlocks):
    """3.1: tier/order/ціни зброї й пасток, зброя що відкриває кімнату, пул і бюджет ботів."""
    wpath, tpath = SHARED / "weapons.json", SHARED / "traps.json"
    by_id = {w["id"]: w for w in weapons if isinstance(w, dict) and isinstance(w.get("id"), str)}
    orders = {}
    for w in by_id.values():
        wid = w["id"]
        o = w.get("order")
        if o in orders:
            err(wpath, f"{wid}: order {o} вже має {orders[o]}")
        orders[o] = wid
        base_id = w.get("base_id")
        if base_id is not None:
            base = by_id.get(base_id)
            if base is None:
                err(wpath, f"{wid}: base_id {base_id!r} немає в weapons")
                continue
            if base.get("base_id") is not None:
                err(wpath, f"{wid}: base_id має вказувати на базову зброю, а {base_id!r} сама модифікація")
            if w.get("tier") != base.get("tier"):
                err(wpath, f"{wid}: модифікація успадковує tier бази ({base.get('tier')}), зараз {w.get('tier')}")
            if isinstance(o, int) and isinstance(base.get("order"), int) and not (base["order"] < o < base["order"] + 10):
                err(wpath, f"{wid}: order модифікації = order бази ({base['order']}) + 1..9, зараз {o}")
            if "price_soft" in w:
                err(wpath, f"{wid}: модифікація не продається за софт (price_soft), її видають нагородою або в hard-магазині")
            if w.get("default_owned"):
                err(wpath, f"{wid}: модифікація не може бути default_owned")
        elif "price_soft" not in w:
            err(wpath, f"{wid}: базова зброя потребує price_soft (для default_owned це бюджет ботів, гравець не платить)")
    # tier не спадає з order серед базової зброї
    bases = sorted((w for w in by_id.values() if w.get("base_id") is None), key=lambda w: w.get("order", 0))
    for a, b in zip(bases, bases[1:]):
        if isinstance(a.get("tier"), int) and isinstance(b.get("tier"), int) and b["tier"] < a["tier"]:
            err(wpath, f"tier не має спадати з order: {a['id']} (tier {a['tier']}) нижче за {b['id']} (tier {b['tier']})")
    # пастки: ціна розблокування (прокачки в trap_upgrades.json, їхні ціни > 0 перевіряє схема)
    for t in traps:
        if not isinstance(t, dict):
            continue
        where = f"{t.get('id')}"
        price = t.get("price_soft")
        if not isinstance(price, int):
            continue
        if t.get("default_owned") and price != 0:
            err(tpath, f"{where}: default_owned, ціна має бути 0")
        if not t.get("default_owned") and price <= 0:
            err(tpath, f"{where}: не default_owned, потрібна price_soft > 0 (розблокування в лобі)")
    # кімнати: зброя, що відкриває кімнату
    prev_tier, prev_room = 0, None
    for room_id, wid in room_unlocks:
        w = by_id.get(wid)
        rpath = ROOMS / room_id / "room.json"
        if w is None:
            err(rpath, f"unlock_weapon {wid!r} немає в weapons")
            continue
        if w.get("base_id") is not None:
            err(rpath, f"unlock_weapon {wid!r} це модифікація: кімнату відкриває базова зброя")
        m = re.fullmatch(r"room(\d+)", room_id)
        if m and isinstance(w.get("tier"), int):
            if w["tier"] < prev_tier:
                err(rpath, f"tier зброї {wid!r} ({w['tier']}) нижчий, ніж у {prev_room} ({prev_tier}): кімнати мають відкриватися зростаючою зброєю")
            prev_tier, prev_room = w["tier"], room_id
    # боти
    if isinstance(bots, dict):
        for x in bots.get("weapon_pool_exclude") or []:
            if x not in by_id:
                err(SHARED / "bots.json", f"weapon_pool_exclude: {x!r} немає в weapons")
        for room_id, wid in room_unlocks:
            if not bot_pool(by_id, bots, wid):
                err(ROOMS / room_id / "room.json", "пул зброї ботів порожній (усе в weapon_pool_exclude)")


def bot_pool(by_id, bots, unlock_id):
    """Зброя, яку може взяти бот: unlock_weapon кімнати і все, що нижче за order; без виключень і (за налаштуванням) без модифікацій."""
    top = by_id.get(unlock_id)
    if top is None:
        return []
    excl = set(bots.get("weapon_pool_exclude") or [])
    out = []
    for w in sorted(by_id.values(), key=lambda w: w.get("order", 0)):
        if w["id"] in excl or w.get("order", 0) > top.get("order", 0):
            continue
        if w.get("base_id") is not None and not bots.get("include_premium"):
            continue
        out.append(w["id"])
    return out


def trap_upgrades(traps, upgrades=()):
    """{trap_id: {"unlock": ціна або None (default_owned), "ups": {прокачка: [ціна рівня 1, 2, ...]}}}."""
    by = {}
    for t in traps:
        if isinstance(t, dict) and isinstance(t.get("id"), str):
            by[t["id"]] = {"unlock": None if t.get("default_owned") else t.get("price_soft", 0), "ups": {}}
    for u in upgrades:
        if isinstance(u, dict) and u.get("trap_id") in by and isinstance(u.get("level"), int):
            prices = by[u["trap_id"]]["ups"].setdefault(u.get("upgrade"), {})
            prices[u["level"]] = u.get("price_soft", 0)
    for b in by.values():
        b["ups"] = {k: [v[lv] for lv in sorted(v)] for k, v in b["ups"].items()}
    return by


def spend_budget(by, budget, rng):
    """Бот витрачає бюджет випадково: розблокування пастки або наступний рівень прокачки пастки, яка вже є
    (те саме робить LoadoutService.rollBot). Повертає ({пастка: 0/1}, {пастка: сума рівнів прокачок}, залишок)."""
    owned = {tid: b["unlock"] is None for tid, b in by.items()}
    ups = {tid: {k: 0 for k in b["ups"]} for tid, b in by.items()}
    while True:
        options = []
        for tid, b in sorted(by.items()):
            if not owned[tid]:
                if b["unlock"] <= budget:
                    options.append((tid, None, b["unlock"]))
                continue
            for k, prices in sorted(b["ups"].items()):
                lv = ups[tid][k]
                if lv < len(prices) and prices[lv] <= budget:
                    options.append((tid, k, prices[lv]))
        if not options:
            return {t: int(o) for t, o in owned.items()}, {t: sum(v.values()) for t, v in ups.items()}, budget
        tid, k, price = rng.choice(options)
        budget -= price
        if k is None:
            owned[tid] = True
        else:
            ups[tid][k] += 1


BASE_HP_LEFT = 0.5  # типовий виграшний забіг: база доживає з такою часткою HP


def run_soft(rewards, waves, enemies, base_hp):
    """Софт за типовий виграшний забіг однієї кімнати: хвилі + урон усіма ворогами + HP бази. Віспи, що лишились, не рахуємо."""
    wave_soft = rewards.get("wave_soft") or []
    n = max((wv.get("wave", 0) for wv in waves if isinstance(wv, dict)), default=0)
    total_hp = sum(enemies.get(wv.get("enemy_id"), {}).get("hp", 0) * wv.get("count", 0) for wv in waves if isinstance(wv, dict))
    soft = sum(v for v in wave_soft[:n] if isinstance(v, int))
    soft += int(total_hp // rewards.get("damage_per_soft", 100))
    soft += int(base_hp * BASE_HP_LEFT // rewards.get("base_hp_per_soft", 10))
    return soft


def economy_report(weapons, traps, bots, room_unlocks, run_values=None, runs=2000, trap_ups=()):
    """Таблиця для людини: що отримають боти в кожній кімнаті. Не помилка, а підказка для налаштування цін."""
    import random
    by_id = {w["id"]: w for w in weapons if isinstance(w, dict) and isinstance(w.get("id"), str)}
    by = trap_upgrades(traps, trap_ups)
    cheapest = min((p for b in by.values() for prices in b["ups"].values() for p in prices if isinstance(p, int)), default=0)
    lines, warns = [], []
    run_values = run_values or {}
    for wid2, w2 in by_id.items():
        if w2.get("base_id") is None and isinstance(w2.get("price_soft"), int):
            owned = " (отримана одразу)" if w2.get("default_owned") else ""
            lines.append(f"  ціна {wid2}: {w2['price_soft']}{owned}")
    for room_id, run in sorted(run_values.items()):
        lines.append(f"  забіг {room_id}: ~{run} софту (хвилі + урон + база {int(BASE_HP_LEFT * 100)}%); на лук {by_id.get('bow', {}).get('price_soft', 0) / run:.1f} забігів, на дробовик {by_id.get('shotgun', {}).get('price_soft', 0) / run:.1f}")
    for room_id, wid in room_unlocks:
        w = by_id.get(wid) or {}
        budget = (w.get("price_soft") or 0) * bots.get("trap_budget_mult", 1)
        pool = bot_pool(by_id, bots, wid)
        rng = random.Random(room_id)
        owned_tot, up_tot, left = {tid: 0 for tid in by}, {tid: 0 for tid in by}, 0
        for _ in range(runs):
            owned, ups, rest = spend_budget(by, budget, rng)
            for tid in by:
                owned_tot[tid] += owned[tid]
                up_tot[tid] += ups[tid]
            left += rest
        avg = ", ".join(f"{tid} {owned_tot[tid] / runs:.2f}/{up_tot[tid] / runs:.2f}" for tid in by)
        lines.append(f"  {room_id}: зброя {wid} (tier {w.get('tier')}), пул ботів {pool}, бюджет {budget:g}, пастки (є / сер. рівнів прокачок): {avg}, не витрачено в середньому {left / runs:.0f}; бюджет прокачки зброї {(w.get('price_soft') or 0) * bots.get('upgrade_budget_mult', 0):g}")
        if 0 < budget < cheapest:
            warns.append(f"{room_id}: бюджет ботів {budget:g} менший за найдешевшу прокачку ({cheapest}): боти лишаться на базових пастках")
    return lines, warns


def check_shop_soft(path, weapons, traps):
    """lobby/shop_soft.json: тут лише звичайні предмети (бустери, косметика). Зброя, пастки і прокачки зброї й пасток
    не прописуються рядками: лобі збирає їх у картки з weapons.json, traps.json, weapon_upgrades.json і trap_upgrades.json (ціни лише там)."""
    if not path.exists():
        return
    try:
        rows = json.loads(path.read_text(encoding="utf-8")).get("items") or []
    except Exception:  # noqa: BLE001
        return
    for r in rows:
        rw = r.get("reward") if isinstance(r, dict) else None
        if isinstance(rw, dict) and rw.get("kind") in GENERATED_REWARD_KINDS:
            err(path, f"shop_soft {r.get('id')}: нагорода {rw.get('kind')} збирається з weapons/traps/weapon_upgrades/trap_upgrades, рядок прибрати")


def check_portals(path, weapons=(), room_unlocks=()):
    """lobby/portals.json: порталі лобі (id = ContentId порталу в Studio), Place ID кімнат.
    requires = зброя (id з weapons.json), потрібна для входу (tier не нижчий за tier цієї зброї). Для порталу N кімната rooms/roomN:
    її unlock_weapon має збігатися з requires, а якщо tier зброї кімнати вищий за 1, requires обов'язковий."""
    wby = {w["id"]: w for w in weapons if isinstance(w, dict) and isinstance(w.get("id"), str)}
    unlocks = dict(room_unlocks)
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
        req = row.get("requires")
        if req is not None:
            if req not in wby:
                err(path, f"{where}: requires {req!r} немає в weapons.json")
            elif wby[req].get("default_owned"):
                err(path, f"{where}: requires {req!r} це зброя default_owned, замок нічого не закриє")
        unlock = unlocks.get(f"room{pid}")
        if unlock is not None and unlock in wby:
            need = wby[unlock].get("tier", 1)
            if req is None and need > 1:
                err(path, f"{where}: кімната room{pid} відкривається зброєю {unlock} (tier {need}), а requires не заданий")
            if req is not None and req in wby and req != unlock:
                err(path, f"{where}: requires {req!r} не збігається з unlock_weapon кімнати room{pid} ({unlock!r})")


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
    economy = "--economy" in sys.argv
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
    by_trap = {t.get("id"): t for t in traps if isinstance(t, dict)}
    for t in traps:
        if isinstance(t, dict) and "level" in t:
            err(SHARED / "traps.json", f"пастка {t.get('id')}: поле level більше не використовується (рівні = прокачки в trap_upgrades.json)")
    if not any(isinstance(w, dict) and w.get("default_owned") for w in (shared.get("weapons") or [])):
        err(SHARED / "weapons.json", "жодна зброя не default_owned: гравцю не буде з чим грати")
    effect_ids = {e["id"] for e in (shared.get("status_effects") or []) if isinstance(e, dict) and isinstance(e.get("id"), str)}
    check_effects(shared.get("status_effects") or [], load_raw(SHARED / "status_effects.json").get("stats"))
    check_weapon_extras(shared.get("weapons") or [], effect_ids)
    check_enemy_extras(shared.get("enemies") or [])
    check_trap_extras(traps, effect_ids)
    check_sound_refs(shared.get("sounds") or [], shared.get("status_effects") or [], shared.get("rules"), shared.get("weapons") or [])
    trap_items = check_upgrades(shared.get("trap_upgrades") or [], traps, effect_ids, shared.get("items") or [],
                                file="trap_upgrades", owner="traps", owner_key="trap_id",
                                other_items={it.get("id") for it in (shared.get("items") or []) if isinstance(it, dict)})  # «не прив'язаний» перевіряємо раз, нижче
    check_upgrades(shared.get("weapon_upgrades") or [], shared.get("weapons") or [], effect_ids, shared.get("items") or [],
                   other_items=trap_items)
    check_items(shared.get("items") or [], weapon_ids, set(by_trap), enemy_ids)
    room_unlocks = []
    run_values = {}

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
        if isinstance(room.get("unlock_weapon"), str):
            room_unlocks.append((room_dir.name, room["unlock_weapon"]))
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
        if isinstance(rewards, dict) and isinstance(room.get("base_hp"), (int, float)):
            enemies_by_id = {e["id"]: e for e in (shared.get("enemies") or []) if isinstance(e, dict) and "id" in e}
            run_values[room_dir.name] = run_soft(rewards, [wv for wv in (files.get("waves") or [])], enemies_by_id, room["base_hp"])
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

    room_unlocks.sort(key=lambda x: (x[0] == "template", int(re.sub(r"\D", "", x[0]) or 0)))
    check_economy(shared.get("weapons") or [], shared.get("traps") or [], shared.get("bots") or {}, room_unlocks)

    check_portals(ROOT / "lobby" / "portals.json", shared.get("weapons") or [], room_unlocks)
    check_shop_soft(ROOT / "lobby" / "shop_soft.json", shared.get("weapons") or [], shared.get("traps") or [])

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
    lines, warns = economy_report(shared.get("weapons") or [], shared.get("traps") or [], shared.get("bots") or {}, room_unlocks, run_values,
                                  trap_ups=shared.get("trap_upgrades") or [])
    if economy:
        print("Економіка ботів (бюджет = ціна зброї кімнати x trap_budget_mult):")
        print("\n".join(lines))
    for w in warns:
        print("  УВАГА:", w)
    return 0


if __name__ == "__main__":
    sys.exit(main())
