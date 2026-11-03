"""Draws the branded scoreboard on the rendered frames and cuts the demo clips (NVENC).

python overlay.py            all clips + a full preview
"""
import math, os, pathlib, subprocess, sys
from PIL import Image, ImageDraw, ImageFont

HERE = pathlib.Path(__file__).parent
FR = HERE / 'work' / 'frames'
OUT_FR = HERE / 'work' / 'frames_ov'
CLIPS = pathlib.Path(r"output\2026-11-01_rl-environment-pizza-delivery-robot\clips")
LOGO = Image.open(HERE / 'brand' / 'logo120.png').convert('RGBA')
FPS = 30
NAVY = (23, 32, 44); YEL = (255, 216, 77); WHITE = (251, 251, 249); GREY = (201, 209, 217)
RED = (229, 72, 77); GREEN = (63, 185, 80)
F = lambda w, s: ImageFont.truetype({'b': 'C:/Windows/Fonts/segoeuib.ttf', 's': 'C:/Windows/Fonts/seguisb.ttf', 'r': 'C:/Windows/Fonts/segoeui.ttf'}[w], s)
f_head, f_pill, f_lab, f_big, f_val, f_pop, f_ban = F('s', 22), F('b', 24), F('s', 20), F('b', 64), F('b', 34), F('b', 40), F('b', 40)
f_shop = F('b', 38)
logo_s = LOGO.resize((int(LOGO.width * 44 / LOGO.height), 44), Image.LANCZOS)


import json as _json
_K = _json.load(open(HERE / 'work' / 'keys.json'))
_FR = [k[0] for k in _K['R']['Location.X']]
_X = [k[1] for k in _K['R']['Location.X']]
_Y = [k[1] for k in _K['R']['Location.Y']]


def robot_xy(t):
    f = t * FPS
    for i in range(len(_FR) - 1):
        if _FR[i] <= f <= _FR[i + 1]:
            u = (f - _FR[i]) / max(1, _FR[i + 1] - _FR[i])
            if _FR[i + 1] - _FR[i] <= 1:  # a cut: no blending between tries
                return _X[i + 1], _Y[i + 1]
            return _X[i] + (_X[i + 1] - _X[i]) * u, _Y[i] + (_Y[i + 1] - _Y[i]) * u
    return _X[-1], _Y[-1]


def travelled(t0, t):
    """Centimetres the robot moved between t0 and t (sampled path)."""
    d, k = 0.0, t0
    px, py = robot_xy(t0)
    while k < t:
        k = min(t, k + 0.1)
        x, y = robot_xy(k)
        d += ((x - px) ** 2 + (y - py) ** 2) ** 0.5
        px, py = x, y
    return d


PRO_LEN = None


def state(t):
    """What the board shows at time t (seconds into the sequence). Every run starts at 0 and earns points by getting
    closer to the door; each bump costs 30; the delivery adds 20 (owner, 2026-11-01: the score must be earned)."""
    global PRO_LEN
    if t < 9:
        earned = int(min(20, travelled(0, t) / 25))
        bumps = (t >= 3.0) + (t >= 7.4)
        score = earned - 30 * bumps
        pop = 'BUMP  -30' if (3.0 <= t < 4.0 or 7.4 <= t < 8.4) else ''
        return dict(mode='FIRST TRY' if t < 8.2 else 'FAILED', mcol=RED, score=score, scol=RED if score < 0 else WHITE,
                    rows=[('TIME', f'{t:0.1f} s'), ('BUMPS', str(bumps))], pop=pop)
    if t < 17:
        return None
    if t < 29:
        u = (t - 17) / 12
        tries = int(1 + 2399 * u ** 2.2)
        best = int(-40 + 140 * (1 - (1 - u) ** 2.5))
        return dict(mode='PRACTICE, SPED UP', mcol=YEL, score=best, scol=YEL, rows=[('TRIES', f'{tries:,}'), ('SPEED', '30x')], pop='', score_label='BEST SCORE')
    tt = min(t - 29, 20.0)
    done = t >= 48.6
    if PRO_LEN is None:
        PRO_LEN = travelled(29, 49)
    score = int(80 * min(1.0, travelled(29, min(t, 49)) / PRO_LEN)) + (20 if done else 0)
    pop = 'DELIVERED  +20' if 48.6 <= t < 49.8 else ''
    return dict(mode='DELIVERED' if done else 'AFTER PRACTICE', mcol=GREEN, score=score, scol=GREEN,
                rows=[('TIME', f'{tt:0.1f} s'), ('BUMPS', '0')], pop=pop, pop_col=GREEN, banner=t >= 49.2)


def rr(d, box, r, fill, outline=None, width=0):
    d.rounded_rectangle(box, r, fill=fill, outline=outline, width=width)


def draw(im, t):
    st = state(t)
    if not st:
        return im
    ov = Image.new('RGBA', im.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    # Top-down practice shot: the white robot blends into the white sidewalk from above (owner, 2026-11-01), so a
    # yellow ring and a short trail follow it. Screen position from the keyed path (0.387 px per cm, measured).
    if 17 <= t < 29:
        def scr(tt):
            x, y = robot_xy(tt)
            return 954 + x * 0.387, 537 + y * 0.387
        start = 17 if t < 20 else 20 if t < 24.5 else 24.5  # each try starts fresh, no trail across the cut
        k = t - 1.2
        while k < t:
            if k >= start:
                px, py = scr(k)
                a = int(60 + 150 * (1 - (t - k) / 1.2))
                d.ellipse((px - 7, py - 7, px + 7, py + 7), fill=YEL + (a,))
            k += 0.1
        px, py = scr(t)
        d.ellipse((px - 46, py - 46, px + 46, py + 46), outline=NAVY + (255,), width=12)
        d.ellipse((px - 44, py - 44, px + 44, py + 44), outline=YEL + (255,), width=8)
        tw = d.textlength('ROBOT', font=f_pill)
        rr(d, (px - tw / 2 - 14, py - 96, px + tw / 2 + 14, py - 58), 16, YEL)
        d.text((px - tw / 2, py - 94), 'ROBOT', font=f_pill, fill=NAVY)
    x0, y0, w = 1452, 48, 420
    h = 330
    rr(d, (x0, y0, x0 + w, y0 + h), 18, NAVY + (232,))
    d.rectangle((x0, y0 + 14, x0 + 6, y0 + h - 14), fill=YEL)
    ov.alpha_composite(logo_s, (x0 + 22, y0 + 18))
    # Branded like the pizza shop's sign (owner, 2026-11-01): logo, PIZZA in yellow, the card's name under it.
    d.text((x0 + 30 + logo_s.width, y0 + 12), 'PIZZA', font=f_shop, fill=YEL)
    d.text((x0 + 32 + logo_s.width, y0 + 50), 'DELIVERY SCORECARD', font=f_lab, fill=GREY)
    # mode pill
    tw = d.textlength(st['mode'], font=f_pill)
    rr(d, (x0 + 22, y0 + 80, x0 + 22 + tw + 32, y0 + 120), 20, st['mcol'])
    d.text((x0 + 38, y0 + 84), st['mode'], font=f_pill, fill=NAVY if st['mcol'] != RED else WHITE)
    # score
    d.text((x0 + 24, y0 + 136), st.get('score_label', 'SCORE'), font=f_lab, fill=GREY)
    d.text((x0 + 22, y0 + 156), str(st['score']), font=f_big, fill=st['scol'])
    # rows
    for k, (lab, val) in enumerate(st['rows']):
        cx = x0 + 22 + k * 200
        d.text((cx, y0 + 248), lab, font=f_lab, fill=GREY)
        d.text((cx, y0 + 270), val, font=f_val, fill=WHITE)
    if st['pop']:
        pf = f_pop if d.textlength(st['pop'], font=f_pop) < 180 else f_pill
        pw = d.textlength(st['pop'], font=pf) + 28
        rr(d, (x0 + w - 18 - pw, y0 + 160, x0 + w - 18, y0 + 222), 12, st.get('pop_col', RED))
        d.text((x0 + w - 4 - pw, y0 + (166 if pf is f_pop else 176)), st['pop'], font=pf, fill=WHITE if st.get('pop_col', RED) == RED else NAVY)
    if st.get('banner'):
        txt = 'DELIVERED   20.0 s   0 bumps   100 points'
        bw = d.textlength(txt, font=f_ban) + 80
        bx = (1920 - bw) / 2 - 140
        rr(d, (bx, 880, bx + bw, 952), 16, NAVY + (236,))
        d.rectangle((bx, 880, bx + 8, 952), fill=GREEN)
        d.text((bx + 40, 890), txt, font=f_ban, fill=WHITE)
    return Image.alpha_composite(im.convert('RGBA'), ov).convert('RGB')


def main():
    OUT_FR.mkdir(exist_ok=True)
    frames = sorted(FR.glob('f*.jpg'))
    for i, p in enumerate(frames):
        draw(Image.open(p), i / FPS).save(OUT_FR / f'o{i:04d}.jpg', quality=94)
    CLIPS.mkdir(parents=True, exist_ok=True)
    cuts = {'hook': (0, 270), 'world': (270, 510), 'practice': (510, 870), 'pro': (870, 1470), 'delivered': (1470, len(frames))}
    enc = ['-c:v', 'h264_nvenc', '-preset', 'p5', '-cq', '19', '-pix_fmt', 'yuv420p', '-movflags', '+faststart']
    for name, (a, b) in cuts.items():
        subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-framerate', str(FPS), '-start_number', str(a), '-i', str(OUT_FR / 'o%04d.jpg'),
                        '-frames:v', str(b - a)] + enc + [str(CLIPS / f'{name}.mp4')], check=True)
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-framerate', str(FPS), '-i', str(OUT_FR / 'o%04d.jpg')] + enc + [str(CLIPS.parent / 'demo-preview.mp4')], check=True)
    print('clips:', sorted(p.name for p in CLIPS.glob('*.mp4')))


if __name__ == '__main__':
    main()
