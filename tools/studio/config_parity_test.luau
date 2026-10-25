--!strict
-- Тест паритету валідаторів: tools/validate.py (CI) ↔ ConfigLoader у грі. Ревʼю 25.10.2026, H1.
-- Навіщо: якщо гра суворіша за CI, файл проходить CI, а в грі відкидається цілком
-- (traps.json -> вбудований рівень 1, weapons.json -> кулаки й рогатка) лише з warn у консолі.
-- Як запустити: Studio, place «MustDie - Packages», режим Edit, вставити цей файл у Command Bar (або execute_luau).
-- Читає JSON з гілки BRANCH через HttpService, валідує клоном ConfigLoader (кеш require не заважає), клон видаляє.
-- Кожен новий позитивний кейс у tools/test_validate_effects.py, що стосується on_hit / damage_type, додавай і сюди.
local HttpService = game:GetService("HttpService")
local BRANCH = "main"
local BASE = `https://raw.githubusercontent.com/DuckieTwiStar/MustDie_Config/{BRANCH}/rooms/shared/`

local parent = game:GetService("ServerStorage").TowerDefenseServer
local clone = parent.ConfigLoader:Clone()
clone.Name = "ConfigLoaderParityTmp"
clone.Parent = parent
local ok, mod = pcall(require, clone)
if not ok then
	clone:Destroy()
	error(`require ConfigLoader: {mod}`)
end
local T = (mod :: any)._test
local lines: { string } = {}
local pass, fail = 0, 0

local function check(label: string, value: any, expect: boolean)
	local good = (value == true) == expect
	if good then pass += 1 else fail += 1 end
	table.insert(lines, `{if good then "PASS" else "FAIL"} {label}`)
end

local function get(name: string): any
	return HttpService:JSONDecode(HttpService:GetAsync(BASE .. name .. ".json", true))
end

local function copy(v: any): any
	return HttpService:JSONDecode(HttpService:JSONEncode(v))
end

local files: { [string]: (any) -> (boolean, string?) } = {
	rules = T.validateRules, enemies = T.validateEnemies, weapon_upgrades = T.validateUpgrades,
	weapons = T.validateWeapons, traps = T.validateTraps, sounds = T.validateSounds, status_effects = T.validateEffects,
}
local data: { [string]: any } = {}
for name, fn in files do
	data[name] = get(name)
	local valid, why = fn(data[name])
	check(`{BRANCH}/{name}.json як є ({why or "ok"})`, valid, true)
end

local function snare1(d: any): any
	for _, r in d.traps do
		if r.id == "snare" and r.level == 1 then return r end
	end
	return nil
end
local function weapon(d: any, id: string): any
	for _, r in d.weapons do
		if r.id == id then return r end
	end
	return nil
end
local function effect(d: any, id: string): any
	for _, r in d.status_effects do
		if r.id == id then return r end
	end
	return nil
end

-- позитивні: CI пропускає, гра має прийняти
local d = copy(data.traps); snare1(d).on_hit.chill = { stacks = 2 }
check("пастка on_hit chill.stacks=2", T.validateTraps(d), true)
d = copy(data.traps); snare1(d).damage_type = "ice"
check("пастка damage_type ice", T.validateTraps(d), true)
d = copy(data.traps); snare1(d).on_hit.slow = { speed_mult = 0.3, duration = 2, chance = 0.5 }
check("пастка on_hit slow.speed_mult", T.validateTraps(d), true)
d = copy(data.weapons); weapon(d, "bow").damage_type = "ice"
check("зброя damage_type ice", T.validateWeapons(d), true)
d = copy(data.weapons); weapon(d, "bow").on_hit = { chill = { stacks = 1, chance = 0.3 } }
check("зброя on_hit chill", T.validateWeapons(d), true)
d = copy(data.status_effects); effect(d, "chill").max_stacks = 3
check("chill max_stacks=3", T.validateEffects(d), true)

-- негативні: гра має відхилити (безпека коду)
d = copy(data.traps); snare1(d).on_hit.chill = { stacks = 0 }
check("stacks=0", T.validateTraps(d), false)
d = copy(data.traps); snare1(d).on_hit.chill = { stacks = 1.5 }
check("stacks=1.5", T.validateTraps(d), false)
d = copy(data.traps); snare1(d).on_hit.stun.chance = 2
check("chance=2", T.validateTraps(d), false)
d = copy(data.traps); snare1(d).on_hit.slow = { speed_mult = -1 }
check("від'ємне число", T.validateTraps(d), false)
d = copy(data.traps); snare1(d).on_hit.slow = { ["Bad-Name"] = 1 }
check("ім'я Bad-Name", T.validateTraps(d), false)
d = copy(data.traps); snare1(d).on_hit.slow = { speed_mult = "x" }
check("рядок замість числа", T.validateTraps(d), false)
d = copy(data.traps); snare1(d).damage_type = "poison"
check("пастка damage_type poison", T.validateTraps(d), false)
d = copy(data.weapons); weapon(d, "bow").damage_type = "Ice"
check("зброя damage_type Ice", T.validateWeapons(d), false)
d = copy(data.status_effects); d.stats[1].min = "0"
check("stats.min рядок", T.validateEffects(d), false)
d = copy(data.status_effects); effect(d, "chill").modifiers[2].per_stack = "yes"
check("per_stack рядок", T.validateEffects(d), false)
d = copy(data.status_effects); effect(d, "burn").damage_type = "poison"
check("ефект damage_type poison", T.validateEffects(d), false)
d = copy(data.status_effects); effect(d, "burn").kind = "dot"
check("старий формат kind", T.validateEffects(d), false)

-- збірка: параметри on_hit доходять до Config.traps у camelCase
d = copy(data.traps); snare1(d).on_hit.chill = { stacks = 2 }; snare1(d).on_hit.slow = { speed_mult = 0.3 }
local onHit = T.buildTraps(d).snare.levels[1].onHit
check("buildTraps: chill.stacks=2, slow.speedMult=0.3", onHit.chill ~= nil and onHit.chill.stacks == 2 and onHit.slow ~= nil and onHit.slow.speedMult == 0.3, true)

clone:Destroy()
table.insert(lines, `{pass}/{pass + fail} passed`)
print(table.concat(lines, "\n"))
return table.concat(lines, "\n")
