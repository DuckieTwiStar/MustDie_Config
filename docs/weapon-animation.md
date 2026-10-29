# Анімація зброї в руках (29.10.2026)

Власних анімацій-асетів немає: зброя рухається відносно руки, клієнт щокадру змінює `RightGrip.C1` (ліва рука: `LeftWeld.C0`) і зварки деталей `J_*`.

## Де що
- `TowerDefense.Client.WeaponAnimator` (новий): шари руху (віддача-пружина, хитання при ходьбі, поза бігу, дихання, айдл, нахил перезарядки, удари кулаків), деталі рогатки, лука, револьвера. Конфіг по зброї `CFGS` (omega, kickZ, kickPitch, kickY, sprintPitch, bobMul, rest/restRot).
- `TowerDefense.Client.ReloadAnim`: лишилось тільки `state(actor)` (нахил/тремтіння перезарядки), решта в WeaponAnimator.
- `TowerDefense.Client.PlayerController`: `WeaponAnimator.init()`, `predictLocal` після `fireRemote:FireServer` і `punchRemote:FireServer`, обробка fx `"fire"`; `tracerFx` для свого гравця в першій особі починається від дула (70% до лінії прицілу).
- `TowerDefenseServer.WeaponVisuals`: деталі на `J_<Name>` зварках (атрибут `Joint=true`, `weldAll` їх пропускає); рогатка (BandL/BandR/Pouch/Pebble), лук (LimbUp/LimbDown/StringU/StringD/Arrow), револьвер (Drum, Hammer), кулаки = боксерські рукавички (кулька + манжета), друга рука як модель `TD_LeftHand` (чекаємо `tool.Parent == character`).
- `TowerDefenseServer.CombatService`: розсилає `TD_Fx("fire", character, id, hand)`; для кулаків чергує руку (`punchLeft`), для подвійного револьвера ліва рука на парних `DualShot`.

## Правила
- Свій постріл малюється одразу (predict), подія сервера для нього гаситься чергою `pending`.
- Усе локально на клієнті, сервер зсувів не бачить; на слабких пристроях (`Quality.isLow`) хитання вимкнено для чужих персонажів.
- Нова зброя: додати запис у `CFGS` (без нього модуль зброю не рухає).

## Віддача (kickZ / kickPitch)
дробовик 1.3 / 0.55, револьвер 0.36 / 0.28, Tommy 0.34 / 0.17, арбалет 0.3 / 0.12, енергоган 0.06 / 0.03; рогатка й лук трохи «пускають» уперед.

## Публікація
Пакети: TowerDefense v93 (клієнт) і TowerDefenseServer (потрібна нова версія після v85) + публікація кожного place.
