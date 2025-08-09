#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generate a 16,384 x 8,192 16-bit grayscale solar-system map with:
- Jupiter shifted +1500 px, Mercury +250 px (others unchanged)
- Rocky planets (Mercury, Venus, Earth, Mars, Pluto) and ALL moons tripled in radius
- Asteroid belt unchanged in sizes, but bounds shifted: left +300 px, right +800 px
- Grayscale heightmaps applied to Mars, Mercury, Venus, Pluto, and Earth's Moon
Requires the following assets at the given paths:
  /mnt/data/mars_1k_topo.jpg
  /mnt/data/moonmap4k.jpg
  /mnt/data/mercurybump.jpg
  /mnt/data/venusbump.jpg
  /mnt/data/plutomap2k.jpg
Outputs:
  /mnt/data/solar_system_16384x8192_tripled_rockies_moons_shifted_belt.png
"""
import numpy as np
from PIL import Image
import math, random

# ===================== PARAMETERS =====================
WIDTH, HEIGHT = 16384, 8192
GRAY_PLANET      = 45000
GRAY_ORBIT_RING  = 30000
GRAY_SAT_RING    = 60000
GRAY_ASTEROID    = 35000

LEFT_MARGIN, RIGHT_MARGIN = 100, 100
EARTH_PX = 150
MIN_GAP_MARS_JUP = 1100

LOW_OFF, LOW_THICK = 24, 6
HIGH_GAP, HIGH_THICK = 30, 6
MOON_RING_OFF, MOON_RING_THICK = 6, 4

# Requested adjustments
SHIFT_MERCURY = 250   # px right
SHIFT_JUPITER = 1500  # px right
BELT_LEFT_SHIFT  = 300   # px right
BELT_RIGHT_SHIFT = 800   # px right

random.seed(9090)  # keep belt randomness consistent baseline

# ===================== PLANET DATA =====================
PLANET_KM = {
    "Mercury": 2440, "Venus": 6052, "Earth": 6371, "Mars": 3390,
    "Jupiter": 69911, "Saturn": 58232, "Uranus": 25362, "Neptune": 24622,
    "Pluto": 1188
}
GAS = {"Jupiter","Saturn","Uranus","Neptune"}
SATURN = "Saturn"
ROCKY = {"Mercury","Venus","Earth","Mars","Pluto"}

# ===================== BASE SCALE (for original layout) =====================
scale  = EARTH_PX / PLANET_KM["Earth"]
raw_px = {p: PLANET_KM[p] * scale for p in PLANET_KM}
shrink = min(1.0, (3*EARTH_PX) / raw_px["Jupiter"])
radius_base = {p: int(round(raw_px[p] * (shrink if p in GAS else 1))) for p in PLANET_KM}
radius_base["Earth"] = EARTH_PX

def low_outer_from_r(r): return r + LOW_OFF + LOW_THICK

# Ring extents using base radii (for belt baseline & previous layout maths)
ring_low_outer_base  = {p: (int(round(radius_base[p]*1.5)) if p==SATURN else low_outer_from_r(radius_base[p]))
                        for p in PLANET_KM}
ring_high_inner_base = {p: (ring_low_outer_base[p] + HIGH_GAP) if p != SATURN else None for p in PLANET_KM}
ring_high_outer_base = {p: (ring_high_inner_base[p] + HIGH_THICK) if p != SATURN else None for p in PLANET_KM}

# ===================== POSITIONS (original layout) =====================
centre_x_base = {}
INNER = ["Mercury","Venus","Earth","Mars"]
centre_x_base["Mercury"] = LEFT_MARGIN + radius_base["Mercury"]
inner_right = int(WIDTH * 0.30)
inner_spacing = (inner_right - centre_x_base["Mercury"] - radius_base["Mars"]) / (len(INNER)-1)
for i,p in enumerate(INNER[1:],1):
    centre_x_base[p] = int(round(centre_x_base["Mercury"] + i*inner_spacing))

centre_x_base["Jupiter"] = (centre_x_base["Mars"] + ring_high_outer_base["Mars"] +
                            MIN_GAP_MARS_JUP + ring_low_outer_base["Jupiter"]) + 600
centre_x_base["Pluto"]   = WIDTH - RIGHT_MARGIN - radius_base["Pluto"]
dist_jp_pl = centre_x_base["Pluto"] - centre_x_base["Jupiter"]
centre_x_base["Neptune"] = int(round(centre_x_base["Jupiter"] + 0.88*dist_jp_pl))
centre_x_base["Saturn"]  = (centre_x_base["Jupiter"] + centre_x_base["Neptune"])//2 - 100
centre_x_base["Uranus"]  = (centre_x_base["Saturn"] + centre_x_base["Neptune"])//2
centre_y = {p: HEIGHT//2 for p in PLANET_KM}

# ===================== APPLY MOVES (Mercury + Jupiter only) =====================
centre_x = dict(centre_x_base)
centre_x["Mercury"] += SHIFT_MERCURY
centre_x["Jupiter"] += SHIFT_JUPITER

# ===================== UPDATED RADII (tripling rocky & all moons later) =====================
radius_px = dict(radius_base)
for p in ROCKY:
    radius_px[p] = radius_base[p]*3  # triple rocky planet sizes

# Now compute rings based on updated planet radii
ring_low_outer  = {p: (int(round(radius_px[p]*1.5)) if p==SATURN else low_outer_from_r(radius_px[p]))
                   for p in PLANET_KM}
ring_high_inner = {p: (ring_low_outer[p] + HIGH_GAP) if p != SATURN else None for p in PLANET_KM}
ring_high_outer = {p: (ring_high_inner[p] + HIGH_THICK) if p != SATURN else None for p in PLANET_KM}

# ===================== CANVAS =====================
canvas = np.zeros((HEIGHT, WIDTH), dtype=np.uint16)

def draw_circle(cx, cy, r, val):
    x0, x1 = max(0, cx - r), min(WIDTH - 1, cx + r)
    y0, y1 = max(0, cy - r), min(HEIGHT - 1, cy + r)
    y = np.arange(y0, y1 + 1)[:, None]
    x = np.arange(x0, x1 + 1)[None, :]
    mask = (x - cx) ** 2 + (y - cy) ** 2 <= r ** 2
    canvas[y0:y1+1, x0:x1+1][mask] = val

def draw_annulus(cx, cy, r_in, r_out, val):
    x0, x1 = max(0, cx - r_out), min(WIDTH - 1, cx + r_out)
    y0, y1 = max(0, cy - r_out), min(HEIGHT - 1, cy + r_out)
    y = np.arange(y0, y1 + 1)[:, None]
    x = np.arange(x0, x1 + 1)[None, :]
    d2 = (x - cx)**2 + (y - cy)**2
    mask = (d2 <= r_out**2) & (d2 >= r_in**2)
    canvas[y0:y1+1, x0:x1+1][mask] = val

# ===================== Draw planetary rings & bodies =====================
for p in PLANET_KM:
    if p != SATURN:
        low_in = radius_px[p] + LOW_OFF
        draw_annulus(centre_x[p], centre_y[p], low_in, low_in + LOW_THICK, GRAY_ORBIT_RING)
        hi_in  = ring_high_inner[p]
        draw_annulus(centre_x[p], centre_y[p], hi_in, hi_in + HIGH_THICK, GRAY_ORBIT_RING)
sat_in  = radius_px["Saturn"] + 10
sat_out = int(round(radius_px["Saturn"] * 1.5))
draw_annulus(centre_x["Saturn"], centre_y["Saturn"], sat_in, sat_out, GRAY_SAT_RING)

for p in PLANET_KM:
    draw_circle(centre_x[p], centre_y[p], radius_px[p], GRAY_PLANET)

# ===================== Texture mapping helpers =====================
def map_texture_to_disc(tex_img_path, disc_radius_px):
    img = Image.open(tex_img_path).convert("L")
    tex = np.array(img, dtype=np.float32) / 255.0
    th, tw = tex.shape
    diam = disc_radius_px * 2 + 1
    disc = np.zeros((diam, diam), dtype=np.uint16)
    for dy in range(-disc_radius_px, disc_radius_px + 1):
        yy = dy / disc_radius_px
        yrow = dy + disc_radius_px
        for dx in range(-disc_radius_px, disc_radius_px + 1):
            if dx*dx + dy*dy > disc_radius_px**2:
                continue
            xx = dx / disc_radius_px
            z = math.sqrt(max(0.0, 1.0 - xx*xx - yy*yy))
            lat = math.asin(yy)
            lon = math.atan2(xx, z)
            u = (lon + math.pi) / (2 * math.pi) * (tw - 1)
            v = (math.pi/2 - lat) / math.pi * (th - 1)
            ui, vi = int(u), int(v)
            disc[yrow, dx + disc_radius_px] = int(tex[vi, ui] * 65535)
    return disc

def paste_disc(cx, cy, disc):
    r = (disc.shape[0] - 1) // 2
    y0, y1 = cy - r, cy + r + 1
    x0, x1 = cx - r, cx + r + 1
    sy0 = max(0, -y0); sx0 = max(0, -x0)
    sy1 = disc.shape[0] - max(0, y1 - HEIGHT); sx1 = disc.shape[1] - max(0, x1 - WIDTH)
    y0 = max(y0, 0); x0 = max(x0, 0)
    y1 = min(y1, HEIGHT); x1 = min(x1, WIDTH)
    sub_disc = disc[sy0:sy1, sx0:sx1]
    mask = sub_disc > 0
    canvas[y0:y1, x0:x1][mask] = sub_disc[mask]

# ===================== Apply / reapply heightmaps =====================
# Mars (re-texture at same center, same map, but rocky planets tripled => larger disc)
mars_disc = map_texture_to_disc("/mnt/data/mars_1k_topo.jpg", radius_px["Mars"])
paste_disc(centre_x["Mars"], centre_y["Mars"], mars_disc)

# Moon (triple radius)
moon_radius_px = max(int(round(1737 * scale)), 2) * 3
# place Moon relative to (tripled) Earth's rings
base_outer_earth = ring_high_outer["Earth"]
moon_offset = base_outer_earth + 60 + base_outer_earth
moon_cx = centre_x["Earth"]
moon_cy = centre_y["Earth"] - int(round(moon_offset))
moon_disc = map_texture_to_disc("/mnt/data/moonmap4k.jpg", moon_radius_px)
paste_disc(moon_cx, moon_cy, moon_disc)

# Mercury/Venus/Pluto new textures (tripled radii)
mercury_disc = map_texture_to_disc("/mnt/data/mercurybump.jpg", radius_px["Mercury"])
paste_disc(centre_x["Mercury"], centre_y["Mercury"], mercury_disc)

venus_disc = map_texture_to_disc("/mnt/data/venusbump.jpg", radius_px["Venus"])
paste_disc(centre_x["Venus"], centre_y["Venus"], venus_disc)

pluto_disc = map_texture_to_disc("/mnt/data/plutomap2k.jpg", radius_px["Pluto"])
paste_disc(centre_x["Pluto"], centre_y["Pluto"], pluto_disc)

# ===================== Moons & low-orbit rings (moons triple size) =====================
MOON_DATA = {
    "Earth":[("Moon",1737,384400)],
    "Mars":[("Phobos",11.27,9377),("Deimos",6.2,23460)],
    "Jupiter":[("Io",1821,421700),("Europa",1560,671034),
               ("Ganymede",2634,1070412),("Callisto",2410,1882709)],
    "Saturn":[("Titan",2575,1221870),("Rhea",764,527108),
              ("Iapetus",735,3560820),("Dione",561,377415)],
    "Uranus":[("Miranda",235,129900),("Ariel",578,191020),
              ("Umbriel",584,266000),("Titania",788,435910),("Oberon",761,583520)],
    "Neptune":[("Triton",1353,354759),("Proteus",210,117647)],
    "Pluto":[("Charon",606,19591)]
}
for planet, moons in MOON_DATA.items():
    cxp, cyp = centre_x[planet], centre_y[planet]
    base_outer = sat_out if planet=="Saturn" else ring_high_outer[planet]
    max_a = max(m[2] for m in moons)
    for idx, (m_name, r_km, a_km) in enumerate(sorted(moons, key=lambda x: x[2])):
        mr = max(int(round(r_km * scale)), 2) * 3  # triple moon size
        offset = base_outer + 60 + (a_km / max_a) * base_outer
        my = cyp + (-1 if idx % 2 == 0 else 1) * int(round(offset))
        mx = cxp
        if not (planet == "Earth" and m_name == "Moon"):
            draw_circle(mx, my, mr, GRAY_PLANET)
        r_in = mr + MOON_RING_OFF
        draw_annulus(mx, my, r_in, r_in + MOON_RING_THICK, GRAY_ORBIT_RING)

# ===================== Asteroid belt =====================
# Start from baseline belt bounds (from original 16k layout using base radii)
belt_left_base  = centre_x_base["Mars"] + ring_high_outer_base["Mars"] + 250
belt_right_base = centre_x_base["Jupiter"] - ring_low_outer_base["Jupiter"] - 250

# Apply requested shifts
belt_left  = belt_left_base  + BELT_LEFT_SHIFT
belt_right = belt_right_base + BELT_RIGHT_SHIFT
belt_left  = max(0, belt_left)
belt_right = min(WIDTH-1, belt_right)

# Recreate asteroids (same sizes as before)
asteroids = []

# Dwarf bodies with same sizes as before (NOT tripled)
dwarf_defs = [("Ceres",473),("Vesta",262),("Pallas",272),("Hygiea",215)]
dwarf_ring_extents = []
for name, r_km in dwarf_defs:
    core_r = max(int(round(r_km * scale)), 30)  # unchanged size
    placed = False
    tries = 0
    while not placed and tries < 8000:
        ax = random.randint(belt_left, belt_right)
        ay = random.randint(0, HEIGHT-1)
        ok = True
        for (ex, ey, eR) in dwarf_ring_extents:
            if (ax - ex)**2 + (ay - ey)**2 < (core_r + MOON_RING_OFF + MOON_RING_THICK + eR + 2)**2:
                ok = False; break
        if ok:
            draw_circle(ax, ay, core_r, GRAY_ASTEROID)
            r_in = core_r + MOON_RING_OFF
            draw_annulus(ax, ay, r_in, r_in + MOON_RING_THICK, GRAY_ORBIT_RING)
            dwarf_ring_extents.append((ax, ay, r_in + MOON_RING_THICK))
            asteroids.append((ax, ay, core_r))
            placed = True
        tries += 1

# Fill to 200 total asteroids, same size range as before
while len(asteroids) < 200:
    r = random.randint(8, 15)  # unchanged sizes
    ax = random.randint(belt_left, belt_right)
    ay = random.randint(0, HEIGHT-1)
    ok = True
    for ax2, ay2, ar2 in asteroids:
        if (ax - ax2)**2 + (ay - ay2)**2 < (r + ar2 + 2)**2:
            ok = False; break
    if ok:
        for dx, dy, dr in dwarf_ring_extents:
            if (ax - dx)**2 + (y - dy)**2 < (r + dr + 2)**2:
                ok = False; break
    if ok:
        asteroids.append((ax, ay, r))
        draw_circle(ax, ay, r, GRAY_ASTEROID)

# ===================== SAVE =====================
out_path = "/mnt/data/solar_system_16384x8192_tripled_rockies_moons_shifted_belt.png"
Image.fromarray(canvas, mode="I;16").save(out_path)
print("Saved:", out_path)
