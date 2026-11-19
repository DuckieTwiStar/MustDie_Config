# Локалізація `[MD]Localization`

Google Sheets у папці Balance на Диску, лист **Strings**. Джерело правди для текстів — таблиця; у git лежить `localization/strings.csv`.

## Правило (з 19.11.2026)
**Усі тексти гри (UI, повідомлення, написи на мапі, назви й описи предметів) додаються через таблицю `[MD]Localization`.**
1. Новий або змінений текст спершу вносимо в лист Strings: ключ, Context, en і всі 7 мов.
2. Потім `import` -> `strings.csv` -> `check` -> коміт.
3. У коді й на мапі лише ключ / переклад за ключем, без захардкоджених рядків. Тимчасово, до підключення Translator, напис на мапі може містити en-текст зі таблиці (приклад: `room.hud.pen_gate` = PEN GATE над воротами загону в Room 3 і 4).

## Мови
Джерело `en` + `de`, `fr`, `it`, `es`, `pt-pt`, `pt-br`, `uk` (коди Roblox: https://create.roblox.com/docs/production/localization/language-codes).
pt-pt і pt-br — окремі колонки: pt-pt на «tu» з європейською лексикою (equipa, vaga, câmara), pt-br на «você».

## Лист Strings
`Key | Context | en | de | fr | it | es | pt-pt | pt-br | uk`
- Key: `група.підгрупа.назва`, малі літери, цифри, `_`. Групи: `room.*` (HUD кімнати, легенда керування, пастки, вибір зброї, інтро, вихід, підсумки), `msg.*` (повідомлення сервера), `sys.*` (кік), `lobby.*` (портали, магазин, щоденні нагороди, спільнота, таймери), `item.<id>.title/desc` (каталог items.json).
- Context: де показується рядок (для перекладача і для Roblox Context).
- Плейсхолдери `{name}`, `{n}`, `{value}`… підставляє код; у перекладі ті самі, порядок може бути інший.
- RichText `<b>…</b>` і переноси рядка — ті самі, що в en.
- Новий рядок: додати в кінець своєї групи, заповнити всі мови. Порожня клітинка = помилка перевірки.

## Команди (з кореня репо)
```
python3 tools/localization_sheet.py import IN.json   # лист -> localization/strings.csv (з перевіркою)
python3 tools/localization_sheet.py export OUT.json  # strings.csv -> рядки для листа
python3 tools/localization_sheet.py check            # перевірка + export->import без втрат
```
IN.json — значення листа `Strings!A1:J` (get_values) або той самий список зі скачаного xlsx.

## Формат strings.csv
Формат LocalizationTable Roblox: `Key, Source, Context, Example, de, fr, it, es, pt-pt, pt-br, uk` (Source = en). Імпортується в Studio через Localization Tools або `LocalizationTable:SetEntries`.

## Що генерує import
- `localization/strings.csv` — джерело в git (формат LocalizationTable Roblox).
- `lobby/localization.json` і `rooms/shared/localization.json` — runtime-таблиця для гри (усі мови), копії побайтно однакові.
- `localization/LocFallback.lua` — англійські тексти, вшиті в гру. **Після зміни таблиці** вміст файлу вставляємо в
  ModuleScript `ReplicatedStorage.Core.Shared.LocFallback` (place Packages) і публікуємо Core.
- Помилки таблиці (`#ERROR!` тощо) ловить import: текст, що починається з `+ = -`, вводимо з апострофом (`'+{delta} ...`).

## Як це працює в грі
- Сервер `CoreServer.LocalizationServer`: одразу публікує англійську з `LocFallback`, потім таблицю з GitHub
  (атрибути `ReplicatedStorage.LocStrings_<мова>`), і ставить `LocReady = true` (або через 10 с, якщо GitHub недоступний).
- Клієнт `Core.Client.Loc`: перший `require` чекає `LocReady` (до 8 с), далі `Loc.t(key, params)`.
  Порядок пошуку: мова гравця -> en з таблиці -> en з `LocFallback` -> сам ключ (з попередженням `[Loc] немає ключа`).
- Мова: `LocalPlayer.LocaleId`. Тест у Studio: `workspace:SetAttribute("LocTestLanguage", "uk")` **до** Play
  (UI будується один раз, тож мову треба задати до старту).
- Сповіщення сервера (`TD_Notice`, `PortalNotice`, `PortalTeleportStarted`) несуть ключ і параметри, перекладає клієнт.
- Серверні тексти (кік): `LocalizationServer.t(player, key, params)`.

## Ключі в конфігах і на мапі
- Тексти в конфігах лобі (`title`, `description`, `buttonText`, `infoText`, `hardShopText`, `insufficientText`,
  назви нагород) — ключі. Клієнт показує їх через `Loc.maybe(текстАбоКлюч, params)`: ключ перекладається, звичайний текст лишається.
  Параметри: портали — `titleParams` поруч (`{ "n": 1 }`), магазини — `values`, нагороди — `{n}` = `amount`.
  `validate.py` перевіряє, що ключ є в таблиці і плейсхолдери мають значення.
- Назви й описи предметів: `item.<id>.title` / `item.<id>.desc` (ItemCatalog.title / ItemCatalog.description).
- Описи рівнів прокачок у магазині лобі: `lobby.upgrade.<weapon|trap>.<id>.desc` (+ `.name` для типів без item_id);
  `validate.py` вимагає ключ для кожного `upgrade_types`.
- Написи на мапі (TextLabel у workspace): атрибут `LocKey` = ключ, `LocParam_<ім'я>` = параметр (на написі або предку),
  `LocUpper = true` — великими літерами (з кирилицею). Текст у Studio лишається англійським.
- Підказки взаємодії (ProximityPrompt від InteractionService): атрибути моделі `ActionText` / `ObjectText` = ключі
  (`lobby.prompt.*`, `lobby.portal.room` + `LocParam_n`). Перекладає `Core.Client.LocMap`.

## Порядок релізу
1. Код (Packages: Core, CoreServer, Leaderboard, TowerDefense; лобі: Portal, PortalUI, ShopSoft, ShopHard, DailyReward, RateUs) — Publish, Get Latest, Save/Publish place.
2. Лише потім promote-release: старий код показав би ключі з нових конфігів.

## Статус (19.11.2026)
330 рядків × 8 мов. Підключено: усі UI кімнат і лобі, серверні сповіщення, конфіги лобі, написи й підказки на мапі лобі, PEN GATE у Room 3/4.
Не локалізовано свідомо: дебаг-панель, декоративні вивіски Room 4 (WET FLOOR, HOTEL…), імена ворогів/боса (окремий крок).
