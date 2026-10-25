# Ефекти на ворогах (EffectService)

> **АРХІВ (оновлено 25.10.2026).** Описує `EffectService` v1, який **більше не працює в грі**: з 23.10.2026 опубліковано v2 (стеки, модифікатори, теги, переходи), формат `kind` гра відхиляє. Актуальний опис: **`docs/effects-v2.md`** (контракт, API, атрибути для клієнта, debug-команда). Нижче лишається для історії рішень В-001.


Версія 23.10.2026, автор: Агент Смит (агент Васі). Задача `В-001`.

Усі дебафи ворогів (горіння, оглушення, уповільнення, вибух при смерті) винесені зі зброї в окрему систему
`ServerStorage.TowerDefenseServer.EffectService`. Зброя, пастка чи пасивка сцени нічого не рахують самі:
вони лише просять «наклади ефект такого типу від такого гравця».

## Правила

- **Ефекти не стакаються і не оновлюються.** Поки ефект цього типу діє, новий такий самий **не накладається** (`apply` повертає `false`):
  ні числа, ні таймер, ні джерело не змінюються. Наступний можна накласти лише після того, як попередній спав.
  Так ворога не можна тримати в нескінченному горінні чи оглушенні (рішення Васі 23.10.2026).
- **Ефект прив'язаний до гравця, який його наклав.** Урон від ефекту, бали лідерборда, вбивство і нагорода йдуть йому.
  Якщо джерело `nil` (нічий ефект), урон іде без балів і без нагороди.
- **Різні типи працюють одночасно:** ворог може горіти, бути оглушеним і проклятим водночас.
- Якщо гравець вийшов, його ефекти діють далі, але стають нічиїми.

## Типи ефектів

Тип = `id`. Кожен тип має механіку `kind`. Числа за замовчуванням: `rooms/shared/status_effects.json`
(запасні значення в коді: `TowerDefense.Shared.Config.effects`).

| id | kind | що робить | поля |
|---|---|---|---|
| `burn` | `dot` | урон з часом, вогонь на ворогу | `dps`, `duration`, `tick`, `armor_pierce`, `visual: "fire"` |
| `stun` | `stun` | ворог стоїть, грає анімація капкана (атрибут `HeldUntil`) | `duration` |
| `slow` | `slow` | швидкість × `mult` | `mult` (0..1), `duration` |
| `ash_curse` | `death_blast` | при смерті ворог вибухає, урон сусідам | `damage`, `radius`, `armor_pierce`, `fx`, `sound`, `duration` (0 = до смерті) |

Механіки (`kind`): `dot`, `stun`, `slow`, `death_blast`. Нова механіка = код у `EffectService` (наша сторона, пишіть у Slack).
**Новий тип на наявній механіці додається без коду**: рядок у `status_effects.json`, наприклад кислота:

```json
{ "id": "acid", "kind": "dot", "name_en": "Acid", "name_uk": "Кислота", "duration": 4, "dps": 6, "armor_pierce": 1 }
```

## Як підключити (пастки, сцена, будь-що)

```lua
local EffectService = require(ServerStorage.TowerDefenseServer.EffectService)

-- числа з конфігу типу
EffectService.apply(enemy, "burn", trap.owner)
-- свої числа джерела важливіші за конфіг типу
EffectService.apply(enemy, "burn", trap.owner, { dps = stats.burnDps, duration = 2 })
EffectService.apply(enemy, "stun", trap.owner, { duration = stats.holdTime })
EffectService.apply(enemy, "slow", nil, { mult = 0.4, duration = 3 }) -- пасивка сцени: нічий ефект

EffectService.has(enemy, "stun")    -- чи діє
EffectService.remove(enemy, "stun") -- зняти раніше (наприклад, пастку знесли)
EffectService.list(enemy)           -- усі активні (лише читати)
```

- `apply` повертає `true`, якщо ефект накладено (`false`: такий ефект ще діє, ворог мертвий, невідомий тип або `duration <= 0`).
- Ключі в `apply` пишуться camelCase (`armorPierce`), у JSON snake_case (`armor_pierce`, частка броні 0..1, яку ефект ігнорує).

### Капкан і `TrapService` (ваша зона, ми її не чіпали)

- Старий виклик `EnemyService.hold(enemy, seconds)` працює далі: тепер це ефект `stun` (нічий).
  Можна передати власника третім аргументом: `EnemyService.hold(enemy, seconds, trap.owner)`.
- `TrapService` досі читає `enemy.heldUntil` напряму (перевірка «вже тримає»). Це працює, але краще
  `EffectService.has(enemy, "stun")`. Коли пастку зносять і ви скидаєте `heldUntil = 0`, ефект знімається сам.
- Рекомендація: переходьте на `EffectService.apply(enemy, "stun", trap.owner, { duration = ... })`.

## Що бачить клієнт (анімації, підсвітка)

- На хітбоксі ворога атрибут `Effect_<id>` = серверний час кінця ефекту (`workspace:GetServerTimeNow()`),
  `-1` = діє до смерті, `0` = ефекту немає.
- Оглушення також ставить `HeldUntil` (на нього вже зав'язана анімація капкана в `EnemyVisuals`).
- Горіння вішає на хітбокс `Fire` з іменем `TD_Effect_burn`.

**Анімації ворогів під ефекти (горить, заморожений, отруєний тощо) робимо ми (Вася / Агент Смит).**
Якщо пастці потрібна реакція ворога, замовляйте в Slack `#must-die`: який ворог, який ефект, як має виглядати.

## Що змінилось у коді (23.10.2026)

| Модуль | Зміна |
|---|---|
| `TowerDefenseServer.EffectService` | **новий**: накладення, тики, вибух при смерті, атрибути для клієнта |
| `TowerDefenseServer.EnemyService` | прибрано `EnemyService.burn` і горіння в кроці; `hold` → ефект `stun`; рух × `speedMult` (уповільнення) |
| `TowerDefenseServer.CombatService` | вуду й запальні кулі Томмі кличуть `EffectService.apply`; слухач смерті для прокляття прибрано |
| `TowerDefenseServer.ConfigLoader` | читає `rooms/shared/status_effects.json` у `Config.effects` |
| `TowerDefenseServer.Bootstrap` | `EffectService.start()` одразу після `EnemyService.start()` |
| `TowerDefense.Shared.Config` | запасна таблиця `effects` |

Ключі прокачок зброї (`burn`, `incendiary`, `ash`) і поля зброї (`burn_dps`, `burn_time`, `ash_radius`, `ignore_armor`; тепер `on_hit` і `armor_pierce`)
лишились: це числа, які зброя передає в ефект. Механіка ефекту живе лише в `EffectService`.

## Статус

- **Опубліковано 23.10.2026:** TowerDefense v17, TowerDefenseServer v15. Оновлено й опубліковано в Room 1, Room 2, Room Template.
- `status_effects.json` у `main`. У `release` переносимо лише разом із публікацією пекеджа і з «ок» людини.
- Перевірено в Studio (Room 1): горіння вбиває і зараховує вбивство гравцю; повторний ефект не накладається, поки діє попередній (горіння й оглушення); капкан через `hold`;
  уповільнення; вибух прокляття б'є сусіда й зараховує гравцю; вуду й запальні кулі Томмі накладають ефекти.
