# Негативні тести валідатора: ефекти v2 (docs/effects-v2.md), on_hit, прокачка пасток: python3 tools/test_validate_effects.py
# Копіює репозиторій у тимчасову папку, псує один файл і перевіряє, що validate.py ловить саме цю помилку.
import json, shutil, subprocess, sys, tempfile, pathlib, copy
SRC = pathlib.Path(__file__).resolve().parent.parent
def run(mutate, label, expect):
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="vt_"))
    dst = tmp / "repo"
    shutil.copytree(SRC, dst, ignore=shutil.ignore_patterns(".git"))
    mutate(dst)
    r = subprocess.run([sys.executable, "-I", str(dst / "tools" / "validate.py")], capture_output=True, text=True)
    out = r.stdout + r.stderr
    ok = (expect is None and r.returncode == 0) or (expect is not None and r.returncode != 0 and expect in out)
    print(("PASS" if ok else "FAIL"), label)
    if not ok:
        print("   expected:", expect, "| rc", r.returncode); print("   ", "\n    ".join(out.strip().splitlines()[:6]))
    shutil.rmtree(tmp)
    return ok
def edit(rel, fn):
    def m(dst):
        p = dst / rel
        d = json.loads(p.read_text(encoding="utf-8"))
        fn(d)
        p.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
    return m
def eff(d, i): return {e["id"]: e for e in d["status_effects"]}[i]
SE = "rooms/shared/status_effects.json"
results = []
results.append(run(lambda d: None, "базовий стан без змін", None))
results.append(run(edit(SE, lambda d: eff(d, "chill").update(max_stacks=1)), "chill max_stacks=1 з decay_interval", "decay_interval лише для лічильника"))
results.append(run(edit(SE, lambda d: eff(d, "chill")["modifiers"].append({"stat": "armor_mult", "value": 1})), "невідомий stat", "не зі словника"))
results.append(run(edit(SE, lambda d: eff(d, "frozen_immune").update(on_end={"apply": "chill"})), "цикл chill->frozen->immune->chill", "цикл переходів"))
results.append(run(edit(SE, lambda d: eff(d, "chill").update(requires_tags=["wet"])), "тег, який ніхто не видає", "не видає жоден ефект"))
results.append(run(edit(SE, lambda d: eff(d, "chill")["modifiers"].append({"stat": "damage_taken_mult", "value": 1.2, "per_stack": True})), "per_stack з combine max", "не поєднується з combine"))
results.append(run(edit(SE, lambda d: eff(d, "chill")["on_max_stacks"].update(apply="nope")), "apply невідомого ефекту", "ефекту 'nope' немає"))
results.append(run(edit(SE, lambda d: eff(d, "stun")["modifiers"][0].update(value=5)), "value поза межами стата", "поза межами стата"))
results.append(run(edit(SE, lambda d: eff(d, "ash_curse")["on_death"]["blast"].update(sound="no_such_sound")), "звук вибуху відсутній", "немає в sounds.json"))
results.append(run(edit(SE, lambda d: eff(d, "chill")["on_max_stacks"].update(consume="yes")), "consume не bool", "consume має бути true/false"))
results.append(run(edit(SE, lambda d: d["status_effects"].append({"id": "noop", "name_en": "x", "name_uk": "x", "max_stacks": 1, "duration": 2})), "ефект нічого не робить", "нічого не робить"))
results.append(run(edit(SE, lambda d: d.pop("stats")), "немає секції stats", "потрібна секція stats"))
results.append(run(edit(SE, lambda d: eff(d, "slow").pop("duration")), "таймерний ефект без duration", "потрібне duration"))
results.append(run(edit(SE, lambda d: eff(d, "frozen").update(blocked_by_tags=["frozen_immune"], requires_tags=["nope_tag"])), "requires без видавця", "не видає жоден ефект"))
results.append(run(edit(SE, lambda d: eff(d, "chill").update(max_stacks=3)), "поріг: apply stacks коректний при зміні max_stacks", None))
results.append(run(edit("rooms/shared/weapons.json", lambda d: [w for w in d["weapons"] if w["id"] == "tommy"][0]["on_hit"]["burn"].update(stacks=2)), "stacks для нестекового burn", "невідомий параметр stacks"))
results.append(run(edit("rooms/shared/traps.json", lambda d: [t for t in d["traps"] if t["id"] == "snare"][0]["on_hit"].update(chill={"stacks": 2})), "пастка накладає chill stacks=2 (позитив)", None))
results.append(run(edit("rooms/shared/traps.json", lambda d: [t for t in d["traps"] if t["id"] == "snare"][0]["on_hit"].update(chill={"stacks": 6})), "stacks > max_stacks", "потрібне ціле 1..5"))
results.append(run(edit("rooms/shared/traps.json", lambda d: [t for t in d["traps"] if t["id"] == "snare"][0]["on_hit"].update(chill={"duration": 2})), "duration для лічильника", "невідомий параметр duration"))
results.append(run(edit("rooms/shared/weapon_upgrades.json", lambda d: d["upgrade_types"][0].update(stat="on_hit.burn.stacks")), "прокачка: stat on_hit.burn.stacks", "stacks"))
results.append(run(edit(SE, lambda d: eff(d, "frozen")["modifiers"].append({"stat": "damage_taken_mult.poison", "value": 1.5})), "невідомий тип урону в stat", "не зі словника"))
results.append(run(edit(SE, lambda d: eff(d, "stun").update(damage_type="fire")), "damage_type без dps", "мають сенс лише з модифікаторами dps"))
results.append(run(edit("rooms/shared/weapons.json", lambda d: [w for w in d["weapons"] if w["id"] == "bow"][0].update(knockback=3)), "knockback ще без механіки", "механіки відкидання ще немає"))
results.append(run(edit("rooms/shared/weapons.json", lambda d: [w for w in d["weapons"] if w["id"] == "bow"][0].update(bonus_vs={"stun": 1.5})), "bonus_vs по ефекту (позитив)", None))
TU = "rooms/shared/trap_upgrades.json"
def tu_type(d, i): return {t["id"]: t for t in d["upgrade_types"]}[i]
results.append(run(edit(TU, lambda d: d["trap_upgrades"].append({"id": "nope_damage_1", "trap_id": "nope", "upgrade": "damage", "order": 10, "level": 1, "price_soft": 10, "value": 5})), "прокачка пастки, якої немає", "немає в traps.json"))
results.append(run(edit(TU, lambda d: tu_type(d, "damage").update(stat="cost")), "прокачка поля, яке не качається", "не поле пастки"))
results.append(run(edit(TU, lambda d: [u for u in d["trap_upgrades"] if u["id"] == "snare_damage_1"][0].update(level=3, id="snare_damage_3")), "пропуск рівня прокачки пастки", "рівні мають іти 1..N"))
results.append(run(edit("rooms/shared/traps.json", lambda d: [t for t in d["traps"] if t["id"] == "tar"][0].update(footprint_w=2.5)), "footprint_w дробове", "неправильний тип"))
results.append(run(edit("rooms/shared/traps.json", lambda d: [t for t in d["traps"] if t["id"] == "tar"][0].pop("zone_tick")), "зона без zone_tick", "потрібне поле zone_tick"))
results.append(run(edit(TU, lambda d: d["trap_upgrades"].append({"id": "snare_length_1", "trap_id": "snare", "upgrade": "length", "order": 40, "level": 1, "price_soft": 10, "value": 3})), "прокачка довжини пастки без footprint_l", "немає поля footprint_l"))
results.append(run(edit("rooms/shared/traps.json", lambda d: [t for t in d["traps"] if t["id"] == "frost_fan"][0].pop("active_time")), "аура без active_time", "потрібне поле active_time"))
results.append(run(edit("rooms/shared/traps.json", lambda d: [t for t in d["traps"] if t["id"] == "frost_fan"][0]["on_hit"]["chill"].update(stacks=6)), "chill stacks > 5 у вентиляторі", "потрібне ціле 1..5"))
results.append(run(edit("rooms/shared/traps.json", lambda d: d["traps"][0].update(level=1)), "старе поле level у пастці", "поле level більше не використовується"))
results.append(run(edit(TU, lambda d: tu_type(d, "hold").update(stat="on_hit.slow.duration")), "прокачка on_hit, якого в пастці немає", "немає on_hit.slow"))
results.append(run(edit(TU, lambda d: d["trap_upgrades"].append({"id": "energy_wall_cooldown_1", "trap_id": "energy_wall", "upgrade": "cooldown", "order": 20, "level": 1, "price_soft": 10, "value": 2})), "прокачка поля, якого в пастці немає", "немає поля cooldown"))
print(f"{sum(results)}/{len(results)} passed")
sys.exit(0 if all(results) else 1)
