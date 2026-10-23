#!/usr/bin/env python3
"""Генератор іконок (плоский вектор, темний контур). SVG-джерела лежать у assets/icons_src/, PNG 512x512 у assets/icons/.
Запуск: python3 assets/icons_src/make_icons.py   (потрібен playwright з chromium)."""
import os, sys
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "icons")
OL = "#202337"
STEEL, STEEL_D, STEEL_L = "#8a96b0", "#5a6480", "#b6c0d6"
BROWN, WOOD = "#a8602a", "#c98542"
ORANGE, RED, YELLOW = "#ffa63a", "#e8453c", "#ffd23f"
CYAN, BLUE, PURPLE, GREEN = "#5ee0ff", "#4aa3ff", "#a35bff", "#5ed36a"

def S(fill, sw=14, extra=""):
    return f'fill="{fill}" stroke="{OL}" stroke-width="{sw}" stroke-linejoin="round" stroke-linecap="round" {extra}'

def hl(d, w=8):  # світлий відблиск
    return f'<path d="{d}" fill="none" stroke="#ffffff" stroke-opacity="0.65" stroke-width="{w}" stroke-linecap="round"/>'

FLAME = "M256 50 C292 130 392 160 392 288 C392 378 330 450 256 450 C182 450 120 378 120 288 C120 226 160 196 184 150 C196 190 218 202 238 190 C252 150 240 100 256 50 Z"
FLAME_IN = "M256 200 C280 250 330 270 330 330 C330 382 298 420 256 420 C214 420 182 382 182 330 C182 296 206 280 220 254 C232 276 244 276 252 266 C258 244 250 224 256 200 Z"

def flame(tx=0, ty=0, sc=1.0):
    return (f'<g transform="translate({tx} {ty}) scale({sc})">'
            f'<path d="{FLAME}" {S(RED)}/><path d="{FLAME_IN}" fill="{ORANGE}" stroke="{OL}" stroke-width="10" stroke-linejoin="round"/>'
            f'<path d="M256 300 C274 330 296 340 296 372 C296 398 278 414 256 414 C234 414 216 398 216 372 C216 352 232 344 238 326 C246 336 252 334 256 300 Z" fill="{YELLOW}"/></g>')

def pistol(fill=STEEL):
    return (f'<rect x="60" y="150" width="300" height="70" rx="16" {S(fill)}/>'
            f'<path d="M80 200 L170 200 L150 330 Q146 350 126 350 L96 350 Q80 350 82 332 Z" {S(BROWN)}/>'
            f'<path d="M190 220 Q190 270 230 270" fill="none" stroke="{OL}" stroke-width="14" stroke-linecap="round"/>')

ICONS = {}

# ---------------- зброя ----------------
ICONS["MD_Icon_Weapon_Revolver"] = f'''<g transform="translate(256 256) scale(1.04) translate(-256 -256)"><g transform="rotate(-18 256 256)">
<rect x="250" y="176" width="190" height="44" rx="10" {S(STEEL)}/>
<rect x="262" y="160" width="150" height="20" rx="6" {S(STEEL_D,10)}/>
<rect x="420" y="150" width="22" height="26" rx="4" {S(STEEL_D,10)}/>
<path d="M130 176 L132 140 L168 156 L168 180 Z" {S(STEEL_D)}/>
<rect x="150" y="170" width="140" height="106" rx="22" {S(STEEL)}/>
<rect x="196" y="158" width="84" height="130" rx="24" {S(STEEL_L)}/>
<path d="M222 172 V274 M254 172 V274" stroke="{OL}" stroke-width="9" stroke-linecap="round"/>
<path d="M150 262 L206 262 L196 388 Q192 410 168 408 L122 402 Q104 398 108 380 Z" {S(BROWN)}/>
<path d="M126 340 L180 346" stroke="{WOOD}" stroke-width="10" stroke-linecap="round"/>
<path d="M214 290 Q214 336 254 336 Q290 336 290 296" fill="none" stroke="{OL}" stroke-width="14" stroke-linecap="round"/>
<path d="M236 286 L246 318" stroke="{OL}" stroke-width="12" stroke-linecap="round"/>
{hl("M270 190 H420",7)}</g></g>'''

ICONS["MD_Icon_Weapon_Tommy"] = f'''<g transform="translate(256 256) scale(1.0) translate(-256 -256)"><g transform="rotate(-12 256 256)">
<path d="M40 214 L120 196 L150 196 L150 290 L100 300 Q56 304 44 270 Z" {S(BROWN)}/>
<rect x="140" y="184" width="170" height="88" rx="14" {S(STEEL_D)}/>
<rect x="300" y="196" width="150" height="40" rx="8" {S(STEEL)}/>
<path d="M332 190 v52 M358 190 v52 M384 190 v52 M410 190 v52" stroke="{OL}" stroke-width="10" stroke-linecap="round"/>
<rect x="446" y="202" width="26" height="28" rx="5" {S(STEEL_D,10)}/>
<circle cx="236" cy="320" r="62" {S(STEEL)}/><circle cx="236" cy="320" r="36" {S(STEEL_D,10)}/><circle cx="236" cy="320" r="10" fill="{OL}"/>
<rect x="196" y="262" width="80" height="20" rx="4" {S(STEEL_D,10)}/>
<path d="M326 272 L350 272 L360 360 Q362 378 344 378 L332 378 Q318 378 318 362 Z" {S(WOOD)}/>
<path d="M166 270 Q166 316 130 316" fill="none" stroke="{OL}" stroke-width="12" stroke-linecap="round"/>
<path d="M134 270 L106 360 Q102 380 120 380 L146 380 Q160 380 164 366 L176 270 Z" {S(BROWN)}/>
{hl("M156 200 H300",7)}</g></g>'''

ICONS["MD_Icon_Weapon_Crossbow"] = f'''<g transform="translate(256 256) scale(0.88) translate(-256 -256)"><g transform="rotate(-20 256 256)">
<path d="M80 250 L330 250 L330 296 L110 296 Q80 296 80 270 Z" {S(BROWN)}/>
<rect x="150" y="238" width="190" height="24" rx="6" {S(STEEL_D,12)}/>
<path d="M360 60 Q470 150 360 250 Q470 350 360 450" fill="none" stroke="{OL}" stroke-width="44" stroke-linecap="round"/>
<path d="M360 60 Q470 150 360 250 Q470 350 360 450" fill="none" stroke="{RED}" stroke-width="26" stroke-linecap="round"/>
<path d="M360 60 Q330 250 360 450" fill="none" stroke="#f1e6c8" stroke-width="7" stroke-linecap="round"/>
<path d="M176 218 L360 218 L360 238 L176 238 Z" {S("#f1e6c8",10)}/>
<path d="M360 204 L430 228 L360 252 Z" {S(STEEL_L,12)}/>
<path d="M176 212 L146 196 M176 244 L146 262" stroke="{RED}" stroke-width="12" stroke-linecap="round"/>
<path d="M226 296 L226 350 Q226 370 246 370 L262 370 L262 296" {S(BROWN)}/>
<circle cx="300" cy="250" r="14" {S(YELLOW,10)}/></g></g>'''

ICONS["MD_Icon_Weapon_EnergyGun"] = f'''<g transform="translate(256 256) scale(0.9) translate(-256 -256)"><g transform="rotate(-18 256 256)">
<path d="M80 190 Q70 190 70 210 L70 262 Q70 280 90 280 L250 280 L250 190 Z" {S(PURPLE)}/>
<rect x="240" y="196" width="150" height="62" rx="14" {S(STEEL)}/>
<rect x="262" y="184" width="14" height="86" rx="4" {S(CYAN,10)}/><rect x="298" y="184" width="14" height="86" rx="4" {S(CYAN,10)}/><rect x="334" y="184" width="14" height="86" rx="4" {S(CYAN,10)}/>
<path d="M388 190 L440 190 Q470 190 470 227 Q470 264 440 264 L388 264 Z" {S(STEEL_D)}/>
<circle cx="464" cy="227" r="30" fill="{CYAN}" stroke="{OL}" stroke-width="10"/><circle cx="464" cy="227" r="14" fill="#ffffff"/>
<path d="M120 280 L170 280 L160 396 Q156 416 134 414 L104 410 Q88 406 92 390 Z" {S(STEEL_D)}/>
<circle cx="140" cy="228" r="26" {S(CYAN,10)}/><circle cx="140" cy="228" r="10" fill="#ffffff"/>
<path d="M196 290 Q196 330 232 330 Q262 330 262 296" fill="none" stroke="{OL}" stroke-width="13" stroke-linecap="round"/>
{hl("M96 204 H220",7)}</g></g>'''

ICONS["MD_Icon_Weapon_Voodoo"] = f'''
<path d="M176 330 L120 440 Q112 462 140 462 L184 462 Q204 462 208 440 L236 360 Z" {S("#d9b27a")}/>
<path d="M336 330 L392 440 Q400 462 372 462 L328 462 Q308 462 304 440 L276 360 Z" {S("#d9b27a")}/>
<path d="M160 270 Q110 230 90 150 Q84 126 108 124 Q130 124 138 150 Q150 200 200 236 Z" {S("#d9b27a")}/>
<path d="M352 270 Q402 230 422 150 Q428 126 404 124 Q382 124 374 150 Q362 200 312 236 Z" {S("#d9b27a")}/>
<rect x="160" y="226" width="192" height="160" rx="44" {S("#d9b27a")}/>
<circle cx="256" cy="146" r="82" {S("#d9b27a")}/>
<path d="M172 140 Q172 100 210 90" fill="none" stroke="{OL}" stroke-width="10" stroke-linecap="round"/>
<circle cx="226" cy="140" r="17" {S("#2a2f46",8)}/><circle cx="286" cy="140" r="17" {S("#2a2f46",8)}/>
<path d="M214 186 Q256 206 298 186" fill="none" stroke="{OL}" stroke-width="10" stroke-linecap="round"/>
<path d="M228 184 v18 M246 192 v18 M266 192 v18 M284 184 v18" stroke="{OL}" stroke-width="7" stroke-linecap="round"/>
<path d="M196 300 L316 300 M196 330 L316 330" stroke="{OL}" stroke-width="7" stroke-linecap="round" stroke-dasharray="14 14"/>
<path d="M306 262 L430 388" stroke="{OL}" stroke-width="30" stroke-linecap="round"/><path d="M306 262 L430 388" stroke="{STEEL_L}" stroke-width="14" stroke-linecap="round"/>
<circle cx="440" cy="398" r="22" {S(RED,10)}/>
{flame(0,0,0)}
<g transform="translate(212 -14) scale(0.22)">{flame()[flame().index('<path'):flame().rindex('</g>')]}</g>'''

# ---------------- прокачки ----------------
ICONS["MD_Icon_Upgrade_Choke"] = f'''
<circle cx="110" cy="96" r="30" {S(ORANGE)}/><circle cx="256" cy="80" r="30" {S(ORANGE)}/><circle cx="402" cy="96" r="30" {S(ORANGE)}/>
<path d="M60 170 L452 170 L330 330 L330 400 L182 400 L182 330 Z" {S(STEEL)}/>
<path d="M96 190 L200 322" stroke="#ffffff" stroke-opacity="0.6" stroke-width="9" stroke-linecap="round"/>
<circle cx="256" cy="452" r="30" {S(ORANGE)}/>'''

ICONS["MD_Icon_Upgrade_Dual"] = f'''
<g transform="translate(-30 -70) scale(0.95)">{pistol(STEEL_D)}</g>
<g transform="translate(120 110) scale(0.95)">{pistol(STEEL)}</g>'''

ICONS["MD_Icon_Upgrade_Stability"] = f'''
<circle cx="256" cy="256" r="150" fill="none" stroke="{OL}" stroke-width="46"/><circle cx="256" cy="256" r="150" fill="none" stroke="{GREEN}" stroke-width="26"/>
<path d="M256 40 V150 M256 362 V472 M40 256 H150 M362 256 H472" stroke="{OL}" stroke-width="44" stroke-linecap="round"/>
<path d="M256 40 V150 M256 362 V472 M40 256 H150 M362 256 H472" stroke="{STEEL_L}" stroke-width="24" stroke-linecap="round"/>
<circle cx="256" cy="256" r="30" {S(RED)}/>'''

ICONS["MD_Icon_Upgrade_Incendiary"] = f'''
{flame(86,-10,0.62)}
<g transform="rotate(-35 256 330)"><path d="M190 230 Q256 150 322 230 L322 430 L190 430 Z" {S("#d9a441")}/>
<rect x="184" y="410" width="144" height="40" rx="8" {S(STEEL_D)}/>
<path d="M214 250 V400" stroke="#ffffff" stroke-opacity="0.55" stroke-width="9" stroke-linecap="round"/></g>'''

ICONS["MD_Icon_Upgrade_BeamTime"] = f'''
<rect x="220" y="30" width="72" height="50" rx="10" {S(STEEL_D)}/>
<circle cx="256" cy="278" r="190" {S("#eaf6ff",16)}/><circle cx="256" cy="278" r="150" fill="none" stroke="{CYAN}" stroke-width="22"/>
<path d="M256 278 V160" stroke="{OL}" stroke-width="30" stroke-linecap="round"/><path d="M256 278 V160" stroke="{BLUE}" stroke-width="14" stroke-linecap="round"/>
<path d="M256 278 L336 330" stroke="{OL}" stroke-width="30" stroke-linecap="round"/><path d="M256 278 L336 330" stroke="{BLUE}" stroke-width="14" stroke-linecap="round"/>
<circle cx="256" cy="278" r="18" {S(RED,8)}/>
<path d="M392 80 L440 40" stroke="{OL}" stroke-width="30" stroke-linecap="round"/><path d="M392 80 L440 40" stroke="{STEEL}" stroke-width="14" stroke-linecap="round"/>'''

def snow():
    arms = ""
    for a in range(0, 180, 60):
        arms += f'<g transform="rotate({a} 256 256)"><path d="M256 40 V472 M256 100 L214 60 M256 100 L298 60 M256 412 L214 452 M256 412 L298 452" /></g>'
    return (f'<g stroke="{OL}" stroke-width="44" stroke-linecap="round" fill="none">{arms}</g>'
            f'<g stroke="{CYAN}" stroke-width="24" stroke-linecap="round" fill="none">{arms}</g><circle cx="256" cy="256" r="24" {S("#ffffff",10)}/>')
ICONS["MD_Icon_Upgrade_Cooldown"] = snow()

ICONS["MD_Icon_Upgrade_Plasma"] = f'''
<circle cx="256" cy="256" r="190" {S(PURPLE,16)}/><circle cx="256" cy="256" r="130" fill="#d6a8ff" stroke="{OL}" stroke-width="10"/><circle cx="256" cy="256" r="66" fill="#ffffff"/>
<ellipse cx="256" cy="256" rx="236" ry="64" fill="none" stroke="{OL}" stroke-width="30" transform="rotate(-30 256 256)"/>
<ellipse cx="256" cy="256" rx="236" ry="64" fill="none" stroke="{CYAN}" stroke-width="14" transform="rotate(-30 256 256)"/>
<path d="M150 170 Q190 120 250 112" fill="none" stroke="#ffffff" stroke-opacity="0.7" stroke-width="12" stroke-linecap="round"/>'''

ICONS["MD_Icon_Upgrade_Pierce"] = f'''
<rect x="120" y="70" width="76" height="372" rx="20" {S(STEEL)}/><rect x="316" y="70" width="76" height="372" rx="20" {S(STEEL)}/>
<path d="M142 100 V200 M338 100 V200" stroke="#ffffff" stroke-opacity="0.55" stroke-width="9" stroke-linecap="round"/>
<path d="M40 256 H400" stroke="{OL}" stroke-width="44" stroke-linecap="round"/><path d="M40 256 H400" stroke="#f1e6c8" stroke-width="22" stroke-linecap="round"/>
<path d="M392 196 L488 256 L392 316 Z" {S(RED,12)}/>
<path d="M56 256 L18 218 M56 256 L18 294" stroke="{RED}" stroke-width="16" stroke-linecap="round"/>'''

ICONS["MD_Icon_Upgrade_Burn"] = flame()

ICONS["MD_Icon_Upgrade_Radius"] = f'''
<circle cx="256" cy="256" r="206" fill="#ffe0a8" stroke="{ORANGE}" stroke-width="16" stroke-dasharray="34 24" stroke-linecap="round"/>
<circle cx="256" cy="256" r="130" {S('#ffc46b',14)}/>
<circle cx="256" cy="256" r="52" {S(RED)}/>
<path d="M256 120 V60 M256 392 V452 M120 256 H60 M392 256 H452" stroke="{OL}" stroke-width="30" stroke-linecap="round"/>
<path d="M256 120 V60 M256 392 V452 M120 256 H60 M392 256 H452" stroke="{YELLOW}" stroke-width="14" stroke-linecap="round"/>'''

def bull(cx, cy, r):
    return (f'<circle cx="{cx}" cy="{cy}" r="{r}" {S("#f4f0e6",12)}/><circle cx="{cx}" cy="{cy}" r="{r*0.68:.0f}" fill="{RED}" stroke="{OL}" stroke-width="8"/>'
            f'<circle cx="{cx}" cy="{cy}" r="{r*0.38:.0f}" fill="#f4f0e6" stroke="{OL}" stroke-width="8"/><circle cx="{cx}" cy="{cy}" r="{r*0.14:.0f}" fill="{RED}"/>')
ICONS["MD_Icon_Upgrade_Targets"] = bull(256, 150, 100) + bull(130, 360, 100) + bull(382, 360, 100)

ICONS["MD_Icon_Upgrade_Ash"] = f'''
<path d="M96 300 Q56 170 156 112 Q256 60 356 112 Q456 170 416 300 L384 330 L384 400 Q384 424 360 424 L152 424 Q128 424 128 400 L128 330 Z" {S("#c9c3d9")}/>
<path d="M160 424 V380 M212 424 V380 M264 424 V380 M316 424 V380" stroke="{OL}" stroke-width="12" stroke-linecap="round"/>
<path d="M180 250 Q180 210 218 210 Q250 210 250 252 Q250 290 214 290 Q180 290 180 250 Z" fill="{OL}"/>
<path d="M332 250 Q332 210 294 210 Q262 210 262 252 Q262 290 298 290 Q332 290 332 250 Z" fill="{OL}"/>
<circle cx="214" cy="256" r="16" fill="{ORANGE}"/><circle cx="298" cy="256" r="16" fill="{ORANGE}"/>
<path d="M256 300 L236 336 H276 Z" fill="{OL}"/>
<path d="M150 140 Q190 100 240 96" fill="none" stroke="#ffffff" stroke-opacity="0.65" stroke-width="10" stroke-linecap="round"/>
<circle cx="86" cy="96" r="14" {S(ORANGE,8)}/><circle cx="430" cy="70" r="12" {S(YELLOW,8)}/><circle cx="470" cy="150" r="10" {S(ORANGE,6)}/><circle cx="48" cy="190" r="9" {S(RED,6)}/>'''

# ---------------- бустери (для кошика магазину) ----------------
ICONS["MD_Icon_Booster_Speed"] = f'''
<circle cx="276" cy="256" r="190" {S(BLUE,16)}/>
<path d="M300 70 L170 290 H258 L226 442 L376 210 H286 Z" {S(YELLOW)}/>
<path d="M30 150 H130 M6 256 H90 M30 362 H130" stroke="{OL}" stroke-width="28" stroke-linecap="round"/><path d="M30 150 H130 M6 256 H90 M30 362 H130" stroke="#ffffff" stroke-width="12" stroke-linecap="round"/>
{hl("M150 150 Q170 100 230 82",9)}'''

ICONS["MD_Icon_Booster_LuckyCharm"] = f'''
<path d="M256 96 C256 40 160 40 160 120 C160 150 190 170 256 200 C322 170 352 150 352 120 C352 40 256 96 256 96 Z" {S(GREEN)}/>
<g {S(GREEN)}><circle cx="170" cy="200" r="70"/><circle cx="342" cy="200" r="70"/><circle cx="170" cy="340" r="70"/><circle cx="342" cy="340" r="70"/></g>
<g fill="{GREEN}"><circle cx="170" cy="200" r="58"/><circle cx="342" cy="200" r="58"/><circle cx="170" cy="340" r="58"/><circle cx="342" cy="340" r="58"/><rect x="200" y="200" width="112" height="140"/></g>
<path d="M256 270 Q270 400 220 470" fill="none" stroke="{OL}" stroke-width="34" stroke-linecap="round"/><path d="M256 270 Q270 400 220 470" fill="none" stroke="#3d9a4b" stroke-width="16" stroke-linecap="round"/>
<path d="M130 160 Q150 130 190 140" fill="none" stroke="#ffffff" stroke-opacity="0.6" stroke-width="10" stroke-linecap="round"/>'''

ICONS["MD_Icon_Booster_MegaPack"] = f'''
<rect x="70" y="190" width="372" height="262" rx="28" {S(ORANGE)}/>
<rect x="50" y="130" width="412" height="86" rx="22" {S(RED)}/>
<rect x="226" y="130" width="60" height="322" fill="{YELLOW}" stroke="{OL}" stroke-width="12" stroke-linejoin="round"/>
<path d="M256 130 C200 40 120 70 150 120 C170 150 256 130 256 130 C256 130 342 150 362 120 C392 70 312 40 256 130 Z" {S(YELLOW)}/>
{hl("M96 232 V400",9)}'''

ICONS["MD_Icon_Item_GoldenHat"] = f'''
<ellipse cx="256" cy="386" rx="220" ry="62" {S("#e6a817")}/>
<path d="M120 386 L136 160 Q140 100 256 100 Q372 100 376 160 L392 386 Z" {S(YELLOW)}/>
<path d="M128 330 Q256 372 384 330 L388 384 Q256 430 124 384 Z" {S(RED)}/>
{hl("M170 170 Q176 130 240 124",10)}<circle cx="256" cy="352" r="22" {S(YELLOW,8)}/>'''

ICONS["MD_Icon_Booster_Shield"] = f'''
<path d="M256 40 L440 100 V250 Q440 380 256 472 Q72 380 72 250 V100 Z" {S(BLUE)}/>
<path d="M256 90 L394 134 V248 Q394 346 256 420 V90 Z" fill="#2f6fd0" stroke="{OL}" stroke-width="0"/>
<path d="M256 150 L276 208 L338 208 L288 244 L306 304 L256 268 L206 304 L224 244 L174 208 L236 208 Z" {S(YELLOW,10)}/>
{hl("M120 130 V240",9)}'''

ICONS["MD_Icon_Item_Magnet"] = f'''
<path d="M90 80 H190 V280 Q190 340 256 340 Q322 340 322 280 V80 H422 V290 Q422 450 256 450 Q90 450 90 290 Z" {S(RED)}/>
<rect x="90" y="60" width="100" height="90" rx="10" {S("#e8ecf6")}/><rect x="322" y="60" width="100" height="90" rx="10" {S("#e8ecf6")}/>
{hl("M118 190 V290",9)}
<path d="M240 20 L224 54 M256 12 V50 M272 20 L288 54" stroke="{YELLOW}" stroke-width="12" stroke-linecap="round"/>'''

def render(only=None):
    os.makedirs(OUT, exist_ok=True)
    svgdir = HERE
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 512, "height": 512})
        for name, body in ICONS.items():
            if only and name not in only:
                continue
            svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" width="512" height="512">{body}</svg>'
            open(os.path.join(svgdir, name + ".svg"), "w", encoding="utf-8").write(svg)
            pg.set_content(f'<html><body style="margin:0;background:transparent">{svg}</body></html>')
            pg.screenshot(path=os.path.join(OUT, name + ".png"), omit_background=True, clip={"x": 0, "y": 0, "width": 512, "height": 512})
        b.close()

if __name__ == "__main__":
    render(sys.argv[1:] or None)
    print(f"ok: {len(ICONS)} icons")
