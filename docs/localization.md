# Локалізація `[MD]Localization`

Google Sheets у папці Balance на Диску, лист **Strings**. Джерело правди для текстів — таблиця; у git лежить `localization/strings.csv`.

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

## Статус (18.11.2026)
264 рядки × 8 мов. Код гри ще читає захардкоджені рядки — підключення таблиці (LocalizationService + Translator, перемикання мови) окремим кроком.
