#!/usr/bin/env python3
"""Модель балансу v0018_1 (з нуля, середня складність). Пише конфіги в робочу копію репозиторію.
Запуск: python3 -I model.py <repo_root>
"""
import json, math, os, sys

ROOT = sys.argv[1]
VERSION = "BAL-0018_1"
DATE = "2026-11-02"


def load(p):
    with open(os.path.join(ROOT, p), encoding="utf-8") as fh:
        return json.load(fh)


def save(p, doc):
    with open(os.path.join(ROOT, p), "w", encoding="utf-8") as fh:
        json.dump(doc, fh, ensure_ascii=False, indent=2)
        fh.write("\n")


def r5(x):
    return int(max(5, round(x / 5.0) * 5))


def stamp(doc, note=None):
    doc["meta"]["version"] = VERSION
    doc["meta"]["exported_at"] = DATE
    if note:
        doc["meta"]["note"] = note


# ---------------------------------------------------------------- припущення
PLAYERS = 4          # боти добирають команду до 4, тому хвилі рахуємо на 4 учасники
EFF = 0.5            # частка часу, коли учасник реально б'є (як у листі curves)
REF_SPEED = 12       # швидкість ворога для часу маршруту (grunt)
PLAYER_DAMAGE_SHARE = 0.30  # частка урону команди, яку робить живий гравець (решта боти)

# ---------------------------------------------------------------- зброя
WEAPONS = {
    # id: (price_soft, зміни статів)
    "fists": (50, {"damage": 15, "attack_interval": 0.4}),
    "slingshot": (150, {"damage": 14, "attack_interval": 0.55}),
    "bow": (300, {"damage": 45, "attack_interval": 1.0}),
    "revolver": (800, {"damage": 30, "attack_interval": 0.5, "magazine": 6, "reload_time": 2.0}),
    "shotgun": (1200, {"damage": 11, "attack_interval": 0.9, "pellets": 8, "magazine": 5, "reload_time": 0.55}),
    "tommy": (3000, {"damage": 9, "attack_interval": 0.1, "magazine": 50, "reload_time": 2.0}),
    "crossbow": (6000, {"damage": 95, "attack_interval": 1.3}),
    "energygun": (7500, {"damage": 12, "attack_interval": 0.1}),
    "voodoo": (10000, {"damage": 45, "attack_interval": 0.8}),
}
# база для цін прокачки безкоштовної зброї (її price_soft лише бюджет ботів)
UPGRADE_PRICE_BASE = {"fists": 200, "slingshot": 300}

w_doc = load("rooms/shared/weapons.json")
for w in w_doc["weapons"]:
    price, stats = WEAPONS[w["id"]]
    w["price_soft"] = price
    w.update(stats)
stamp(w_doc)
save("rooms/shared/weapons.json", w_doc)
W = {w["id"]: w for w in w_doc["weapons"]}


def dps(w):
    """Та сама формула, що weapons!dps_calc у таблиці."""
    d = w["damage"] * w.get("pellets", 1) * w.get("multishot", 1)
    d *= 1 + w.get("crit_chance", 0) * (w.get("crit_mult", 1) - 1)
    d /= w["attack_interval"]
    mag = w.get("magazine", 0)
    if mag:
        k = w["attack_interval"]
        rt = w.get("reload_time", 0) * (mag if w.get("reload_per_round") else 1)
        d *= mag * k / (mag * k + rt)
    return d


# ---------------------------------------------------------------- прокачка зброї
STD_F = [0.08, 0.13, 0.20]
SPECIAL = {"dual", "multishot", "ricochet", "incendiary", "plasma", "pierce", "ash", "targets", "radius"}
SPEC_F = [0.25, 0.35, 0.45]
u_doc = load("rooms/shared/weapon_upgrades.json")
for u in u_doc["weapon_upgrades"]:
    wid, typ, lv = u["weapon_id"], u["upgrade"], u["level"]
    base_price = UPGRADE_PRICE_BASE.get(wid, W[wid]["price_soft"])
    f = (SPEC_F if typ in SPECIAL else STD_F)[min(lv, 3) - 1]
    u["price_soft"] = r5(base_price * f)
    w = W[wid]
    if typ == "damage":
        v = w["damage"] * (1 + 0.2 * lv)
        u["value"] = int(round(v)) if w["damage"] >= 5 else round(v, 1)
    elif typ == "attack_interval":
        u["value"] = round(w["attack_interval"] * (1 - 0.12 * lv), 3)
# нормалізація: повне дерево прокачки зброї = TREE[w] (відносні ваги рівнів зберігаються)
TREE = {"fists": 120, "slingshot": 200, "bow": 400, "revolver": 900, "shotgun": 1300, "tommy": 3300,
        "crossbow": 6000, "energygun": 7000, "voodoo": 9000}
_tot = {}
for u in u_doc["weapon_upgrades"]:
    _tot[u["weapon_id"]] = _tot.get(u["weapon_id"], 0) + u["price_soft"]
for u in u_doc["weapon_upgrades"]:
    u["price_soft"] = r5(u["price_soft"] * TREE[u["weapon_id"]] / _tot[u["weapon_id"]])
stamp(u_doc)
save("rooms/shared/weapon_upgrades.json", u_doc)

# ---------------------------------------------------------------- пастки
TRAPS = {  # id: (cost віспи, price_soft, база цін прокачки)
    "tar": (100, 0, 300),
    "darts": (150, 0, 300),
    "frost_fan": (200, 500, 600),
    "fire_grate": (150, 1000, 900),
    "tesla": (250, 2200, 1500),
    "snare": (100, 0, 300), "energy_wall": (200, 0, 300), "turret": (250, 0, 300),  # вимкнені, лишаємо узгодженими
}
t_doc = load("rooms/shared/traps.json")
for t in t_doc["traps"]:
    cost, price, _ = TRAPS[t["id"]]
    t["cost"] = cost
    t["price_soft"] = price
stamp(t_doc)
save("rooms/shared/traps.json", t_doc)

TRAP_STD = [0.25, 0.40, 0.60]
TRAP_SPECIAL = {"length", "rear_jets", "jumps", "branch", "poison", "vortex"}
tu_doc = load("rooms/shared/trap_upgrades.json")
for u in tu_doc["trap_upgrades"]:
    if u["trap_id"] in ("snare", "energy_wall", "turret"):
        continue  # вимкнені пастки: ціни не чіпаємо, щоб боти не витрачали на них бюджет
    base = TRAPS[u["trap_id"]][2]
    if u["upgrade"] in TRAP_SPECIAL:
        u["price_soft"] = r5(base * 1.2)
    else:
        u["price_soft"] = r5(base * TRAP_STD[min(u["level"], 3) - 1])
TTREE = {"tar": 900, "darts": 1100, "frost_fan": 2000, "fire_grate": 2500, "tesla": 4000}
_tt = {}
for u in tu_doc["trap_upgrades"]:
    _tt[u["trap_id"]] = _tt.get(u["trap_id"], 0) + u["price_soft"]
for u in tu_doc["trap_upgrades"]:
    if u["trap_id"] in TTREE:
        u["price_soft"] = r5(u["price_soft"] * TTREE[u["trap_id"]] / _tt[u["trap_id"]])
stamp(tu_doc)
save("rooms/shared/trap_upgrades.json", tu_doc)

# ---------------------------------------------------------------- вороги
ENEMY = {  # hp, speed, armor, damage_to_base, reward (віспи кожному учаснику)
    "grunt": (60, 12, 0, 10, 6),
    "runner": (40, 20, 0, 8, 5),
    "toad": (50, 10, 0, 15, 8),
    "warrior": (150, 10, 0.25, 20, 12),
    "brute": (600, 6, 0.1, 60, 35),
}
e_doc = load("rooms/shared/enemies.json")
for e in e_doc["enemies"]:
    hp, sp, ar, dmg, rew = ENEMY[e["id"]]
    e.update({"hp": hp, "speed": sp, "armor": ar, "damage_to_base": dmg, "reward": rew})
stamp(e_doc)
save("rooms/shared/enemies.json", e_doc)

# ---------------------------------------------------------------- кімнати й хвилі
ROOMS = {
    "room1": dict(key="slingshot", hp_mult=1.0, door=45, route=154, split={"s1": 1.0},
                  idx=(0.45, 1.35), win=(14, 30), leak_k=0.32,
                  delays=[0, 18, 18, 20, 20, 22],
                  mix=[{"grunt": 1}, {"grunt": 1}, {"grunt": .7, "warrior": .3},
                       {"grunt": .45, "warrior": .35, "toad": .2}, {"grunt": .4, "warrior": .25, "brute": .35},
                       {"grunt": .3, "warrior": .3, "toad": .15, "brute": .25}]),
    "room2": dict(key="bow", hp_mult=1.2, door=60, route=280, split={"s1": .5, "s2": .5},
                  idx=(0.5, 1.6), win=(16, 34), leak_k=0.25,
                  delays=[0, 18, 20, 20, 22, 22, 25],
                  mix=[{"grunt": 1}, {"grunt": .8, "toad": .2}, {"grunt": .5, "warrior": .35, "toad": .15},
                       {"grunt": .35, "warrior": .35, "brute": .3}, {"grunt": .3, "warrior": .3, "toad": .15, "brute": .25},
                       {"grunt": .3, "warrior": .35, "toad": .1, "brute": .25},
                       {"grunt": .25, "warrior": .3, "toad": .15, "brute": .3}]),
    "room3": dict(key="shotgun", hp_mult=1.6, door=60, route=486, split={"s1": .7, "s2": .3},
                  idx=(0.55, 1.75), win=(16, 36), leak_k=0.22,
                  delays=[0, 18, 20, 20, 22, 22, 25],
                  mix=[{"grunt": .7, "runner": .3}, {"grunt": .45, "runner": .3, "warrior": .25},
                       {"grunt": .3, "runner": .25, "warrior": .25, "toad": .2},
                       {"grunt": .25, "runner": .25, "warrior": .25, "brute": .25},
                       {"grunt": .2, "runner": .25, "warrior": .25, "toad": .1, "brute": .2},
                       {"runner": .3, "warrior": .3, "toad": .1, "brute": .3},
                       {"grunt": .2, "runner": .25, "warrior": .2, "toad": .1, "brute": .25}]),
    "room4": dict(key="tommy", hp_mult=2.0, door=60, route=625, split={"s1": .4, "s2": .35, "s3": .25},
                  idx=(0.55, 1.9), win=(16, 38), leak_k=0.2,
                  delays=[0, 18, 20, 20, 22, 22, 25, 25],
                  mix=[{"grunt": .6, "runner": .4}, {"grunt": .45, "runner": .3, "warrior": .25},
                       {"grunt": .3, "runner": .25, "warrior": .25, "toad": .2},
                       {"grunt": .25, "runner": .2, "warrior": .25, "brute": .3},
                       {"grunt": .2, "runner": .25, "warrior": .25, "toad": .1, "brute": .2},
                       {"runner": .25, "warrior": .3, "toad": .15, "brute": .3},
                       {"grunt": .2, "runner": .25, "warrior": .25, "brute": .3},
                       {"grunt": .15, "runner": .25, "warrior": .25, "toad": .1, "brute": .25}]),
}
ORDER = ["grunt", "runner", "toad", "warrior", "brute"]

WAVE_SOFT = [5, 5, 10, 10, 15, 15, 20, 25]
report = {}


def lerp_curve(a, b, n, i, p=1.3):
    t = 0 if n == 1 else i / (n - 1)
    return a + (b - a) * t ** p


for rid, R in ROOMS.items():
    n = len(R["mix"])
    team = PLAYERS * dps(W[R["key"]]) * EFF
    travel = R["route"] / REF_SPEED
    rows, waves_info = [], []
    tot_hp = tot_base = tot_wisps = 0
    for i in range(n):
        wave = i + 1
        idx = lerp_curve(*R["idx"], n, i)
        win = lerp_curve(*R["win"], n, i, 1.0)
        hp_budget = idx * team * (win + travel) / R["hp_mult"]  # сирий HP (без hp_mult)
        counts = {}
        for eid, share in R["mix"][i].items():
            counts[eid] = max(1, round(hp_budget * share / ENEMY[eid][0]))
        wave_hp = sum(c * ENEMY[e][0] for e, c in counts.items())
        for eid in ORDER:
            if eid not in counts:
                continue
            c = counts[eid]
            # розкладаємо по спавнерах
            spl = R["split"]
            alloc, left = {}, c
            sp_ids = list(spl)
            for j, s in enumerate(sp_ids):
                k = left if j == len(sp_ids) - 1 else round(c * spl[s])
                k = min(k, left)
                alloc[s] = k
                left -= k
            if c < len(sp_ids):  # мало ворогів: віддаємо головному спавнеру
                alloc = {sp_ids[0]: c}
            for s, k in alloc.items():
                if k <= 0:
                    continue
                interval = 0 if k == 1 else round(max(0.3, win / k) * 20) / 20
                rows.append({"id": f"w{wave}_{s}_{eid}", "wave": wave, "spawner_id": s, "enemy_id": eid,
                             "count": k, "spawn_interval": interval, "wave_delay": R["delays"][i]})
        base = sum(c * ENEMY[e][3] for e, c in counts.items())
        wisps = sum(c * ENEMY[e][4] for e, c in counts.items())
        tot_hp += wave_hp
        tot_base += base
        tot_wisps += wisps
        waves_info.append(dict(wave=wave, idx=round(idx, 2), window=round(win, 1), hp=round(wave_hp * R["hp_mult"]),
                               enemies=sum(counts.values()), base_dmg=base, wisps=wisps))
    base_hp = r5(R["leak_k"] * tot_base / 5) * 5 if False else int(round(R["leak_k"] * tot_base / 50.0) * 50)
    R.update(rows=rows, info=waves_info, tot_hp=tot_hp * R["hp_mult"], tot_base=tot_base, tot_wisps=tot_wisps,
             base_hp=base_hp, travel=travel, team=team)
    run_time = R["door"] + sum(R["delays"]) + sum(wi["window"] for wi in waves_info) + travel
    R["run_min"] = run_time / 60

# ---------------------------------------------------------------- софт за забіг
DAMAGE_PER_SOFT = 80
BASE_HP_PER_SOFT = 20
for rid, R in ROOMS.items():
    n = len(R["info"])
    soft = sum(WAVE_SOFT[:n]) + int(R["tot_hp"] * PLAYER_DAMAGE_SHARE // DAMAGE_PER_SOFT) + int(R["base_hp"] * 0.5 // BASE_HP_PER_SOFT)
    R["soft"] = soft

for rid, R in ROOMS.items():
    rm = load(f"rooms/{rid}/room.json")
    rm["room"]["base_hp"] = R["base_hp"]
    rm["room"]["door_timer"] = R["door"]
    stamp(rm)
    save(f"rooms/{rid}/room.json", rm)
    pl = load(f"rooms/{rid}/players.json")
    for p in pl["players"]:
        cm = {1: 0.3, 2: 0.55, 3: 0.8, 4: 1.0}[p["players"]]
        p.update({"hp_mult": R["hp_mult"], "count_mult": cm, "reward_mult": 1, "interval_mult": round(1 / cm, 3)})
    stamp(pl, f"{rid}: хвилі на 4 учасники (боти добирають команду). hp_mult = складність кімнати ({VERSION}). interval_mult = 1/count_mult: хвиля триває однаково")
    save(f"rooms/{rid}/players.json", pl)
    wv = load(f"rooms/{rid}/waves.json")
    wv["waves"] = R["rows"]
    stamp(wv, f"Хвилі {rid} ({VERSION}): згенеровано моделлю з цільової кривої індексу тиску {R['idx'][0]}→{R['idx'][1]}, вікно спавну {R['win'][0]}→{R['win'][1]} с, на 4 учасники")
    save(f"rooms/{rid}/waves.json", wv)

rr = load("rooms/shared/run_rewards.json")
rr["run_rewards"].update({"damage_per_soft": DAMAGE_PER_SOFT, "base_hp_per_soft": BASE_HP_PER_SOFT,
                          "wisps_per_soft": 100, "wave_soft": WAVE_SOFT})
stamp(rr)
save("rooms/shared/run_rewards.json", rr)

ru = load("rooms/shared/rules.json")
ru["rules"]["run"]["start_wisps"] = 400
stamp(ru)
save("rooms/shared/rules.json", ru)

bo = load("rooms/shared/bots.json")
bo["bots"].update({"trap_budget_mult": 1, "upgrade_budget_mult": 0.5})
stamp(bo)
save("rooms/shared/bots.json", bo)

# ---------------------------------------------------------------- звіт
print("DPS (формула листа):", {k: round(dps(v), 1) for k, v in W.items()})
tree = {}
for u in u_doc["weapon_upgrades"]:
    tree[u["weapon_id"]] = tree.get(u["weapon_id"], 0) + u["price_soft"]
print("Повне дерево прокачки зброї:", tree)
ttree = {}
for u in tu_doc["trap_upgrades"]:
    ttree[u["trap_id"]] = ttree.get(u["trap_id"], 0) + u["price_soft"]
print("Повне дерево прокачки пасток:", ttree)
for rid, R in ROOMS.items():
    print(f"\n{rid}: key {R['key']} team_dps {R['team']:.0f}, travel {R['travel']:.0f}s, base_hp {R['base_hp']} (усі вороги б'ють {R['tot_base']}),"
          f" HP забігу {R['tot_hp']:.0f}, віспи кожному {R['tot_wisps']} (+400 старт), софт за перемогу ~{R['soft']}, тривалість ~{R['run_min']:.1f} хв")
    for wi in R["info"]:
        print("   ", wi)
json.dump({rid: {k: R[k] for k in ("soft", "run_min", "base_hp", "tot_hp", "tot_wisps", "info")} for rid, R in ROOMS.items()},
          open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "report.json"), "w"), ensure_ascii=False, indent=1)
