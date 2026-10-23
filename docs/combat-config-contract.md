# Контракт конфігів бою (зброя, вороги, пастки, ефекти, правила)

Дата: 23.10.2026. Автор: Агент J. Рішення Жені. Задача `Ж-002`, етап 1 плану `docs/combat-v2-plan.md`. Статус: **затверджено Женею**. Етап 1а (зброя й прокачки), 1б (магазин і перезарядка), 1в (правила, вороги, пастки, ефекти, звуки): дані й валідатор у `main`, код у Packages **не опубліковано**.

## Правила

1. **Число чи логіка.** Дизайнер міняє число заради балансу чи відчуття: конфіг. Зміна потребує нової поведінки: код. Тип поведінки вибирає enum (`fire_mode`, `mechanic`), числа йдуть з конфігу.
2. **Одне джерело правди.** JSON плюс блок `defaults` у `weapons.json` (перелік ключів у `DEFAULT_KEYS` валідатора). Запасні значення в `Config.lua` і `def.x or 100` у коді прибираємо (лишається мінімальний безпечний режим: кулаки й рогатка при збої завантаження). Обов'язкове поле відсутнє: помилка завантаження. Необов'язкове: дефолт зі схеми.
3. **Прокачка сама каже, що міняє.** Масив `upgrade_types` у `weapon_upgrades.json`: `id`, `stat` (шлях до поля зброї, наприклад `crit_mult`, `on_hit.burn.dps`), `op` (`set` за замовчуванням, `add`, `mul`), `name_en`/`name_uk`, `item_id` (іконка й опис в `items.json`). Рядки рівнів посилаються на тип через `upgrade`; порядок у вікні з `order`. Таблиці `BASE_FIELD`/`BASE_DEFAULT` у `WeaponStats`, `Config.upgradeNames`, `weaponUpgradeOrder` зникають. Старі ключі без аліасів: переходимо одразу.
4. **Ефект = запис із числами**, а не тег.
5. **Документація поля одна:** опис, тип, діапазон, дефолт, одиниця у схемі `validate.py`; таблицю для README генеруємо зі схеми.

## Зброя (`weapons.json`)

Усі числові поля можна прокачувати. **Жирним** нові; решта вже є.

**Ідентифікація:** `id`, `order`, `tier`, `rarity`, `price_soft`, `default_owned`, `name_en`, `name_uk`, `fire_mode` (`melee`, `projectile`, `hitscan`, `pellets`, `beam`, `curse`), `auto` (тримати кнопку), **`damage_type`** (`physical` за замовчуванням, далі `fire`, `shock`), **`projectile_style`** (`arrow`, `bolt`, `pebble`).

**Базові:** `damage`, `attack_interval`, `range`.

**Снаряд:** `projectile_speed`, `gravity`, **`stick`**, `pierce`, `multishot`, `multishot_spread`, **`volley_delay`** (0.09 с), `ricochet`, **`ricochet_range`** (30), **`ricochet_damage_mult`** (0.5).

**Крит (для всіх режимів):** `crit_chance` (0..1, прокачується), `crit_mult` (множник: 1.5 = +50%; UI показує відсотки). Ключ прокачки `crit` → `crit_damage` (stat `crit_mult`), додається `crit_chance`.

**Розкид і дробовик:** `spread`, `spread_max`, `spread_grow`, `spread_recover`, `pellets`, `falloff_start`, `falloff_min`. **Револьвер:** **`dual`** (0/1), `dual_rate`, `dual_spread`.

**Магазин і перезарядка (нове):** `magazine` (0 = без ліміту), `reload_time` (с; для `reload_per_round` на один патрон), `reload_per_round` (дробовик), `reload_interruptible` (револьвер, дробовик: так; томмі: ні). Старт: револьвер 6, дробовик 4 (по одному), томмі 30. Патрони не зберігаються: при зміні зброї магазин повний. Перервана повна перезарядка скасовується; у `reload_per_round` вже заряджені патрони лишаються. Енергогармата лишає свою модель `beam_time`/`cooldown`.

**Промінь і плазма:** `beam_time`, `cooldown`, **`plasma_damage`** (0 = немає), `plasma_interval`, `plasma_radius`, **`plasma_speed`** (120).

**Конус і вуду:** `cone` (градуси; кулаки теж, замість `punchCone`), **`targets`** (1), **`splash_radius`** (0), `splash_share`.

**Зв'язки з ворогами, пастками, ефектами:**
- **`armor_pierce`** (0..1) замість bool `ignore_armor` (вуду = 1).
- **`bonus_vs`**: мапа «id ефекту або тег ворога → множник урону», напр. `{"stun": 1.5, "burn": 1.2}`.
- **`knockback`**: відкидання по маршруту; поле резервуємо (0), механіку робимо після етапу 4.
- **`on_hit`**: мапа «id ефекту → числа»; `on_crit`, `on_kill` додаємо, коли знадобляться.

```json
{ "id": "voodoo", "armor_pierce": 1, "on_hit": {
    "burn":      { "chance": 1, "dps": 10, "duration": 3 },
    "ash_curse": { "chance": 1, "damage": 0, "radius": 8 } } }
{ "id": "tommy", "on_hit": { "burn": { "chance": 1, "dps": 0, "duration": 2 } } }
```

- Ключ запису = `id` з `status_effects.json`; числа запису важливіші за числа типу.
- Ефект із нульовим головним числом (`dps`, `damage`) не накладається: прокачка «вмикає» його, піднявши число з 0.
- Старі поля `burn_dps`, `burn_time`, `ash_radius`, `ignore_armor` зникають.

### Прокачки: `upgrade` → `stat`

damage → `damage`; attack_interval → `attack_interval`; ricochet → `ricochet`; multishot → `multishot`; crit_damage → `crit_mult`; crit_chance → `crit_chance`; pellets → `pellets`; choke → `spread` (дробовик); stability → `spread_max` (томмі); beam_time, cooldown → однойменні; pierce → `pierce`; dual → `dual`; incendiary → `on_hit.burn.dps` (томмі); burn → `on_hit.burn.dps` (вуду); plasma → `plasma_damage`; radius → `splash_radius`; targets → `targets`; ash → `on_hit.ash_curse.damage`; нові без коду: `magazine`, `reload_time`, `range`, `projectile_speed`, тривалість горіння, радіус попелу.

## Вороги (`enemies.json`)

Зараз: `id`, `name_*`, `size` (мітка), `hp`, `speed`, `armor`, `damage_to_base`, `reward`. Додаємо:

| Поле | Тип, дефолт | Зараз |
|---|---|---|
| `hitbox` | [x, y, z] студи | лише `Config.lua` |
| `color`, `visual`, `visual_scale` | hex, назва моделі, масштаб | лише `Config.lua` |
| `speed_jitter`, `drift_amplitude`, `drift_scale` | з `rules.enemies` | `gameplay` |
| `tags` | список: `ground`, `armored`, `large`, `boss` | нове |
| `resist` | мапа `damage_type → множник` | нове |
| `immune` | список id ефектів | нове |
| `effect_resist` | мапа `id ефекту → множник тривалості` | нове |
| `knockback_resist` | 0..1 | нове (з `knockback`) |
| `on_death` | мапа ефектів, як `on_hit` | пізніше |

## Пастки (`traps.json`)

Зараз: `mechanic`, `placement`, `cost`, `damage`, `cooldown`, `hold_time`, `fire_interval`, `range`, `price_soft`. Додаємо:

| Поле | Тип, дефолт | Зараз |
|---|---|---|
| `damage_type`, `armor_pierce` | `physical`, 0 (стіна `shock`) | `"shock"` у коді |
| `on_hit` | мапа ефектів (капкан `stun`, стіна `slow`, турель `burn`) | `EnemyService.hold` у коді |
| `footprint` | [x, z] клітинок, [1, 1]; пастки будуть різних форм і розмірів | 1 клітинка, стіна 2 ключі |
| `trigger_radius`, `hit_margin`, `hit_once` | студи; капкан 2.4, стіна 0.6, bool | у коді |
| `wall_height`, `wall_span_max` | 4 і 30 | `WALL_HEIGHT`, `gameplay.wallSpan` |
| `target_priority` | `nearest`, `first`, `last`, `strongest` (турель) | `nearest` у коді |
| `reach`, `refund_share` | з `rules.traps`, можна перекрити | `gameplay.trapReach`, `rules.refundShare` |
| `max_per_player` | 0 = без ліміту | нове |
| `model` | назва моделі або порожньо | розміри й кольори в `TrapService.build` |

Розмір, що змінює ігровий результат, іде в конфіг; моделі й кольори лишаються в коді, доки арт не замінить їх. Список нових пасток і їхні форми обговорюємо окремо.

## Ефекти (`status_effects.json`)

Зараз: `kind`, `duration`, `dps`, `tick`, `mult`, `ignore_armor`, `visual`, `fx`, `sound`. Додаємо `stacking` (`none` зараз, `refresh`, `stack`), `max_stacks`, `damage_type`, `tags`, `armor_pierce` (замість `ignore_armor`). Повну систему ефектів (стакання, опори, теги, синергії) проговорюємо окремо перед реалізацією на етапі 5.

## Правила

| Секція | Поля | Зараз |
|---|---|---|
| `rules.player` | `walk_speed` 16, `sprint_speed` 24 | `gameplay` |
| `rules.traps` | `place_reach` 300, `reach` 14, `reach_slack` 6, `refund_share` **0.5** | `gameplay`, `REACH_SLACK`, `rules` |
| `rules.enemies` | `turn_radius` 12, `speed_jitter`, `spawn_jitter`, `drift_*` | `gameplay` |
| `rules.combat` | `max_live_shots` 60, `net_tolerance` 0.05, правило повного магазину | `CombatService` |
| `rules.run` | `restart_delay` 10, `start_weapon`, `start_wisps` (замість `start_coins`) | `gameplay`, `Config.startWeapon`, `rules` |
| `zones.json` | `lanes` на зону (ширина коридору з даних рівня) | `rules.corridorLanes` |

Ліміти частоти запитів (8/12, 10/15 на секунду) лишаються в коді як захист.

## Подання

- `sounds.json`: id, гучність, висота тону для всіх звуків (зараз `Config.sounds`).
- Назви й іконки прокачок: у рядках `weapon_upgrades.json`. Порядок зброї й прокачок з поля `order`.
- Кольори рарності: окремий розділ UI-конфіга (вітрина лобі, рішення за Васею).

## Лишається в коді

Алгоритми: політ снаряда, пробиття, рикошет, кільце дробин, наростання розкиду, нагрів променя, вибір цілей у конусі, чергування рук, побудова моделей, візуальні ефекти, внутрішні допуски.

## Узгодження

Контракт змінює формат JSON і код `WeaponStats`, `ConfigLoader`, `CombatService`, `UpgradeClient`, `TrapService`, `EnemyService`. Ці модулі в зоні бойового ядра (Женя + Агент J). Вася з Агентом Коричневим: ширина коридору з рівня (`lanes` у `zones.json`), вітрина лобі, моделі й анімації ворогів.

## Статус етапу 1 (23.10.2026)

**Зроблено і в даних, і в коді (Packages):**
- Зброя, прокачки, магазин і перезарядка (1а, 1б), див. вище.
- `rules.json` по секціях `run` / `player` / `traps` / `enemies` / `combat`; `start_coins` став `start_wisps`; `refund_share` у `rules.traps` (0.5).
- `enemies.json`: `hitbox`, `color`, `visual`, `visual_scale`. Новий ворог з JSON створюється без правки коду.
- `traps.json`: усі стати рівнів читає код (`cost`, `damage`, `damage_type`, `armor_pierce`, `on_hit`, `cooldown`, `fire_interval`, `range`, `trigger_radius`, `hit_margin`, `wall_height`, `wall_span_max`). Капкан тримає ворога через `on_hit.stun.duration` (поле `hold_time` зникло, `EnemyService.hold` прибрано). Поведінку вибирає `mechanic`, не `id` пастки.
- `status_effects.json`: `armor_pierce` (частка 0..1) замість `ignore_armor`; id звуку в `sound` у snake_case.
- `sounds.json`: усі звуки; клієнт отримує їх зі знімком конфігу.
- `lanes` у кожній зоні `zones.json` (дані й валідатор).

**Свідомо відкладено (немає механіки в коді, зробимо з відповідним етапом):**
- Вороги: `tags`, `resist`, `immune`, `effect_resist`, `knockback_resist`, `on_death` (етап 7).
- Пастки: `footprint`, `max_per_player`, `model`, `target_priority`, `hit_once`, перекриття `reach` / `refund_share` по пастці (етап 4).
- Ефекти: `stacking`, `max_stacks`, `damage_type`, `tags` (етап 5, окреме обговорення).
- Ширина коридору по зонах: код поки читає одне `rules.enemies.corridor_lanes`; `lanes` із `zones.json` підключимо, коли рівень Васі буде готовий (потрібне зіставлення відстані по маршруту із зоною).
- Клієнт показує висоту й довжину стіни при розстановці за рівнем 1 пастки.

**Лишається в коді як безпечний режим** (`Config.lua`, діє лише при збої завантаження): кулаки й рогатка, рівень 1 пасток, прості правила, три ворога, чотири ефекти, без звуків.
