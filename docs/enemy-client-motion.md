# Рух ворогів на клієнті (A1 з `optimization-lowend.md`)

Статус: сервер готовий (Агент J, 28.10.2026), клієнтська частина за Васею (`EnemyVisuals`).
Нічого не змінюється для гравців, поки `rules.enemies.client_motion = false` (типово).

## Навіщо

Сервер зараз пише `part.CFrame` кожного ворога кожен кадр (≈1100 реплікацій/с у Room 3, хвиля 2). Клієнт може сам порахувати позицію з маршруту й кількох атрибутів. Це перший крок; коли `EnemyVisuals` рахує позицію сам, сервер можна перестати писати CFrame (окремий крок, робить Женя, коли Вася скаже, що клієнт готовий).

## Що вже є

1. `ReplicatedStorage.TowerDefense.Shared.Route`: чисті функції маршруту (та сама математика, що на сервері).
   - `Route.build(pts, turnRadius) -> Route` (`pts`: вузли PathNode за зростанням `Order`, точка = центр верхньої грані мінус половина висоти, тобто на підлозі; сервер робить так само);
   - `Route.pointAt(route, s) -> (точка осі, нормаль)`;
   - `Route.lanePos(route, s, offset, limit, seed, driftAmplitude, driftScale) -> Vector3` (позиція на підлозі, без підйому на пів висоти).
2. Атрибути руху на хітбоксі ворога (`workspace.TD_Enemies.<Enemy_*>`), якщо `client_motion = true`.
3. Влучання зброї тепер рахуються математикою по `enemy.cf`/`size` (`EnemyService.rayHit`), а не рейкастом по деталі. Тому хітбокс можна буде не рухати/не реплікувати. Перевірено в Play: револьвер, томмі, дробовик, лук, арбалет (пробиття), рогатка, енергогармата, вуду.

## Атрибути

Часи в **серверному часі** (`workspace:GetServerTimeNow()`), Vector3 у світових координатах.

Сталі (ставляться при створенні):

| атрибут | тип | що |
|---|---|---|
| `MRoute` | string | id гілки маршруту (`s1`, `s2`...) |
| `MSpeed` | number | базова швидкість ворога, studs/с (вже з розкидом) |
| `MLimit` | number | межа зсуву від осі, studs |
| `MSeed` | number | зерно шуму дрейфу |
| `MJoin` | Vector3 | куди йде ворог у режимі `approach` |

Динамічні (оновлюються при зміні й що 0.5 с):

| атрибут | тип | що |
|---|---|---|
| `MMode` | string | `approach` / `lane` / `orbit` / `glide` |
| `MT` | number | серверний час цього синку |
| `MS` | number | пройдений шлях `s` на момент `MT` |
| `MPos` | Vector3 | позиція (на підлозі) на момент `MT` |
| `MMult` | number | множник швидкості (уповільнення ефектами) |
| `MHold` | number | до якого часу ворог стоїть (двері, оглушення, замороження); `0` = не стоїть |
| `MOffset` | number | зсув смуги від осі |

Лише в режимі `orbit` (воронка): `MOCenter`, `MORadius`, `MOAngle0`, `MOOmega`, `MOStart`, `MODur`, `MOY`.
Лише в режимі `glide`: `MGFrom`, `MGStart`.

## Як рахувати позицію зараз `now = workspace:GetServerTimeNow()`

- `lane`: `run = now - MT`; якщо `MHold > MT` то `run = max(0, now - MHold)`. `s = MS + MSpeed * MMult * run`. Позиція `Route.lanePos(route, s, MOffset, MLimit, MSeed, rules.driftAmplitude, rules.driftScale)`. Якщо `s >= route.total` ворог дійшов до бази (сервер сам його прибере).
- `approach`: той самий `run`; `pos = MPos + (MJoin - MPos).Unit * MSpeed * MMult * run`, але не далі за `MJoin`.
- `orbit`: `t = now - MOStart`; кут `MOAngle0 + MOOmega * t`; `pos = (MOCenter.X + cos * MORadius, MOY, MOCenter.Z + sin * MORadius)`, підйом `1.2 * sin(pi * t / MODur)` (див. `ORBIT_LIFT` у `EnemyService`). Через `MODur` с режим зміниться на `glide`.
- `glide`: `a = (now - MGStart) / 0.4`, `smooth = a*a*(3-2a)`, `pos = MGFrom:Lerp(lanePos(s = MS, нова MOffset), smooth)`. `s` у цей час не росте.
- Вертикаль: `pos` на підлозі; центр моделі вище на `size.Y / 2` (як хітбокс), `lift` тільки в орбіті.
- Орієнтація: напрям руху (різниця позицій між кадрами), як на сервері.

Маршрут клієнт будує сам один раз із тегнутих `PathNode` (як `EnemyService.buildPaths`): для кожного `Route`-id вузли з цим id і вузли без id, відсортовані за `Order`, точка = `Position - (0, Size.Y/2, 0)`; `Route.build(pts, rules.enemies.turnRadius)`. Якщо жодного `Route` на вузлах немає, id один: `s1`.

## Згладжування

Прогноз клієнта розходиться з сервером на мережеву затримку (виміряно в Studio ≈0.3–0.5 studs на швидкості 13). Рекомендація: рахувати позицію як прогноз, а різницю з реальним `part.Position` (поки сервер ще пише CFrame) або з новим синком гасити експонентно (~0.1–0.2 с), а не стрибком. Стрибок у режимі зміни (`MMode`) допустимий.

## Перевірка

У Play з `client_motion = true` (додати `"client_motion": true` у `rules.json` кімнати або `rooms/shared`): порівняти позицію за формулою з `part.Position`. Мій тест: 18 ворогів у `lane`, найгірша похибка 0.48 studs, середня 0.33; `approach` до 0.45. `orbit`, `glide`, `hold` у Play ще не гонялись (потрібна воронка/двері): перевірте на морозному вентиляторі.

## Що далі (за Васею)

1. `EnemyVisuals`: будувати маршрути, рахувати позицію за атрибутами, згладжувати.
2. Сказати Жені, коли готово: ми вимкнемо запис `part.CFrame` на сервері (хітбокс залишиться нерухомою деталлю або зникне; влучання вже не залежать від нього).
3. Далі за планом A2–A5.
