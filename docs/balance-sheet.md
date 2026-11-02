# Зведена таблиця балансу `[MD]Balance_vXXXX`

Google Sheets у папці Balance на Диску. Імена: `[MD]Balance_vXXXX`, де XXXX = найбільша BAL-версія серед файлів у листі `meta` (зараз v0018). Старі таблиці лежать у `Balance/Old`.

## Що всередині
34 листи: README, links, 14 спільних (rules, debug, run_rewards, bots, enemies, weapons_defaults, weapons, weapon_upgrade_types, weapon_upgrades, traps, trap_upgrade_types, trap_upgrades, effect_stats, status_effects), 16 листів кімнат (room1..4 × room, zones, players, waves), waves_summary, meta.
Не входять: template, lobby, items, sounds, leaderboards.

## Правила перетворення (`tools/balance_sheet.py`)
- колекція файлу = лист; масив об'єктів = таблиця (рядок = запис, перший рядок = імена полів), об'єкт = лист `key,value`;
- вкладені об'єкти розгортаються в колонки через крапку (`on_hit.stun.chance`), масиви й порожні об'єкти лежать у клітинці як компактний JSON;
- порожня клітинка = ключа в записі немає;
- колонки `*_calc` і листи waves_summary, README, links не експортуються; meta кожного файлу лежить на листі `meta`;
- `exported_at` у meta пишеться з апострофом (`'2026-10-23`), інакше Sheets зробить з нього дату.

## Команди (з кореня репо)
```
python3 tools/balance_sheet.py export OUT.json     # git -> листи
python3 tools/balance_sheet.py import IN.json DIR  # листи -> JSON-файли
python3 tools/balance_sheet.py check               # git -> листи -> git, має бути 0 помилок
python3 tools/validate.py                          # після імпорту
```
Перевірено 02.11.2026: експорт живої таблиці (xlsx) і імпорт дають байт-у-байт ті самі JSON, що в git: імпорт зберігає 1.0 як 1.0 і стиль файлу (масиви в рядок або в стовпчик). `check` порівнює і зміст, і текст.

## Процес
git -> таблиця: експорт, запис у листи. Таблиця -> git: експорт xlsx, імпорт, validate, комміт у main. У release лише вручну.
