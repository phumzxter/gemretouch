"""Core image tools for Gem Retoucher.

Pipeline for one photo:
  find the gemstone (not the tweezers) -> 1:1 crop -> dust removal (gem only)
  -> healing brush strokes -> color / HSL
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import os
import re
from pathlib import Path
import cv2
import numpy as np

IMG_EXT = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".webp"}

# Hue centers in degrees for the HSL editor
BANDS = {
    "Red": 0, "Orange": 30, "Yellow": 60, "Green": 120,
    "Aqua": 180, "Blue": 240, "Purple": 275, "Magenta": 320,
}

DEFAULTS = dict(
    crop=True, padding=0.15, dx=0.0, dy=0.0, out_size=2000,
    dust=True, dust_thr=18, dust_area=250, dust_mode="Both",
    gem_only=True, gem_margin=0.03, heal_method="smart",
    saturation=1.0, hsl={},
)


# ---------------------------------------------------------------- file helpers
def list_images(folder):
    folder = Path(folder)
    return sorted(p for p in folder.iterdir()
                  if p.suffix.lower() in IMG_EXT and not p.name.startswith("."))


def load_image(path):
    data = np.fromfile(str(path), dtype=np.uint8)
    img = cv2.imdecode(data, cv2.IMREAD_COLOR)  # applies EXIF rotation
    if img is None:
        raise ValueError(f"Could not read {path}")
    return img


def save_image(path, img, quality=95):
    ext = Path(path).suffix.lower()
    params = []
    if ext in (".jpg", ".jpeg"):
        params = [cv2.IMWRITE_JPEG_QUALITY, int(quality)]
    ok, buf = cv2.imencode(ext, img, params)
    if not ok:
        raise ValueError(f"Could not encode {path}")
    buf.tofile(str(path))


def fit(img, max_side=1000):
    h, w = img.shape[:2]
    s = max_side / max(h, w)
    if s >= 1:
        return img
    return cv2.resize(img, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)


def load_thumb(path, size=220):
    """Fast small square thumbnail for the photo strip."""
    data = np.fromfile(str(path), dtype=np.uint8)
    img = cv2.imdecode(data, cv2.IMREAD_REDUCED_COLOR_4)
    if img is None:
        raise ValueError(f"Could not read {path}")
    h, w = img.shape[:2]
    s = min(h, w)
    y0, x0 = (h - s) // 2, (w - s) // 2
    return cv2.resize(img[y0:y0 + s, x0:x0 + s], (size, size), interpolation=cv2.INTER_AREA)


# ------------------------------------------------------------------ gem finder
def _ellipse(radius):
    r = max(1, int(radius))
    return cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))


def _gem_body(filled):
    """Keep the compact stone, drop thin attachments such as tweezers arms.

    The widest point of the shape (largest inscribed circle, radius R) belongs to the gem.
    Anything narrower than ~0.8R across is thin metal and gets removed by a morphological
    opening; a small regrow then restores the stone's corners.
    """
    dist = cv2.distanceTransform(filled, cv2.DIST_L2, 5)
    R = float(dist.max())
    if R < 4:
        return filled
    opened = cv2.morphologyEx(filled, cv2.MORPH_OPEN, _ellipse(R * 0.4))
    n, lab, stats, _ = cv2.connectedComponentsWithStats(opened, connectivity=8)
    if n <= 1:
        return filled
    best = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    body = np.where(lab == best, 255, 0).astype(np.uint8)
    regrow = cv2.dilate(body, _ellipse(R * 0.15))
    return cv2.bitwise_and(regrow, filled)


def analyze_gem(img):
    """Locate the gemstone against a plain background.

    Returns dict(bbox=(x, y, w, h) in photo pixels, mask=small uint8 mask of the stone,
    sx/sy=mask size / photo size, found=bool). Tweezers are not part of the mask.
    """
    h, w = img.shape[:2]
    scale = 600 / max(h, w) if max(h, w) > 600 else 1.0
    small = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA) if scale < 1 else img
    sh, sw = small.shape[:2]
    b = max(2, int(min(sh, sw) * 0.03))
    border = np.concatenate([
        small[:b].reshape(-1, 3), small[-b:].reshape(-1, 3),
        small[:, :b].reshape(-1, 3), small[:, -b:].reshape(-1, 3),
    ])
    bg = np.median(border, axis=0)
    diff = np.linalg.norm(small.astype(np.float32) - bg, axis=2)
    diff = cv2.GaussianBlur(diff, (5, 5), 0)
    d8 = np.clip(diff * 255 / max(float(diff.max()), 1.0), 0, 255).astype(np.uint8)
    t, _ = cv2.threshold(d8, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    mask = np.where(d8 > t, 255, 0).astype(np.uint8)
    k = max(3, int(min(sh, sw) * 0.02)) | 1
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((k, k), np.uint8))
    cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    gem, found = None, False
    if cnts:
        c = max(cnts, key=cv2.contourArea)
        if cv2.contourArea(c) > 0.01 * sh * sw:
            filled = np.zeros((sh, sw), np.uint8)
            cv2.drawContours(filled, [c], -1, 255, -1)  # fills holes (dark facets)
            gem = _gem_body(filled)
            found = cv2.countNonZero(gem) > 0.01 * sh * sw
    sx, sy = sw / w, sh / h
    if found:
        x, y, bw, bh = cv2.boundingRect(gem)
        bbox = (int(x / sx), int(y / sy), int(bw / sx), int(bh / sy))
    else:  # could not find it: use the centre of the photo
        gem = np.zeros((sh, sw), np.uint8)
        cv2.ellipse(gem, (sw // 2, sh // 2), (int(sw * 0.35), int(sh * 0.35)), 0, 0, 360, 255, -1)
        side = min(h, w)
        bbox = ((w - side) // 2, (h - side) // 2, side, side)
    return dict(bbox=bbox, mask=gem, sx=sx, sy=sy, found=found)


def find_gem_bbox(img):
    return analyze_gem(img)["bbox"]


def crop_rect(shape, bbox, padding=0.15, dx=0.0, dy=0.0):
    """Square crop window (x0, y0, side) in photo pixels."""
    h, w = shape[:2]
    x, y, bw, bh = bbox
    short = min(h, w)
    cx = x + bw / 2 + dx * short
    cy = y + bh / 2 + dy * short
    side = int(round(min(max(bw, bh) * (1 + 2 * padding), short)))
    x0 = int(round(cx - side / 2))
    y0 = int(round(cy - side / 2))
    x0 = min(max(x0, 0), w - side)
    y0 = min(max(y0, 0), h - side)
    return x0, y0, side


def square_crop(img, bbox, padding=0.15, dx=0.0, dy=0.0, out_size=2000):
    x0, y0, side = crop_rect(img.shape, bbox, padding, dx, dy)
    crop = img[y0:y0 + side, x0:x0 + side]
    if out_size and side != out_size:
        interp = cv2.INTER_AREA if side > out_size else cv2.INTER_CUBIC
        crop = cv2.resize(crop, (int(out_size), int(out_size)), interpolation=interp)
    return crop


# ----------------------------------------------------------------- dust removal
def remove_dust(img, threshold=18, max_area=250, mode="Both", region=None):
    """Find small specks (compared with their surroundings) and fill them in.

    Large or long shapes (facet edges, real features) are left alone.
    If `region` (uint8 mask) is given, only specks completely inside it are touched.
    """
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    k = 2 * max(3, int(round(np.sqrt(max_area)))) + 1
    med = cv2.medianBlur(gray, k)
    signed = gray.astype(np.int16) - med.astype(np.int16)
    if mode == "Dark specks":
        m = signed < -threshold
    elif mode == "Bright specks":
        m = signed > threshold
    else:
        m = np.abs(signed) > threshold
    m = m.astype(np.uint8)
    n, labels, stats, _ = cv2.connectedComponentsWithStats(m, connectivity=8)
    if n <= 1:
        return img, np.zeros_like(m)
    area = stats[:, cv2.CC_STAT_AREA]
    cw = stats[:, cv2.CC_STAT_WIDTH]
    ch = stats[:, cv2.CC_STAT_HEIGHT]
    longest = np.maximum(cw, ch)
    shortest = np.maximum(np.minimum(cw, ch), 1)
    good = (area >= 2) & (area <= max_area) & (longest <= 3 * np.sqrt(max_area)) & (longest / shortest <= 3)
    good[0] = False
    if region is not None:
        outside = np.bincount(labels[region == 0], minlength=n)
        good &= outside == 0
    keep = good[labels].astype(np.uint8) * 255
    if not keep.any():
        return img, keep
    keep = cv2.dilate(keep, np.ones((3, 3), np.uint8), iterations=2)
    return cv2.inpaint(img, keep, 3, cv2.INPAINT_TELEA), keep


# --------------------------------------------------------------- healing brush
def stroke_to_original(stroke, rect, max_points=3000):
    """Convert a brush stroke from the viewer (0..1 across the shown picture, radius as a
    fraction of its width) into photo pixels, using the crop window `rect`."""
    x0, y0, rw, rh = rect
    pts = []
    for p in list(stroke.get("pts", []))[:max_points]:
        u, v = float(p[0]), float(p[1])
        if not (-0.05 <= u <= 1.05 and -0.05 <= v <= 1.05):
            continue
        pts.append([x0 + u * rw, y0 + v * rh])
    r = float(stroke.get("r", 0)) * rw
    if not pts or not (0 < r < rw):
        return None
    return {"sid": str(stroke["sid"]), "r": r, "pts": pts}


def _grain_sigma(gray, known):
    """Noise level (std of fine detail) of the pixels in `known`."""
    hp = (gray.astype(np.float32) - cv2.GaussianBlur(gray, (0, 0), 1.5))[known]
    return float(np.std(hp)) if hp.size > 10 else 0.0


def _smooth_fill(out, labels, i, box, allmask, seed):
    """Fallback: smooth inpainting plus noise matched to the surroundings, so it does not look blurry."""
    H, W = labels.shape
    x, y, w, h = box
    s = max(w, h)
    pad = int(min(max(12, s * 0.5), 60))
    X0, Y0, X1, Y1 = max(0, x - pad), max(0, y - pad), min(W, x + w + pad), min(H, y + h + pad)
    hole = (labels[Y0:Y1, X0:X1] == i).astype(np.uint8)
    win = out[Y0:Y1, X0:X1]
    unknown = np.where(allmask[Y0:Y1, X0:X1] > 0, 255, 0).astype(np.uint8)   # this piece + still-damaged neighbours
    filled = cv2.inpaint(win, unknown, int(min(max(3, s * 0.35), 15)), cv2.INPAINT_TELEA)
    gray = cv2.cvtColor(win, cv2.COLOR_BGR2GRAY)
    ring = (cv2.dilate(hole, _ellipse(6)) > 0) & (allmask[Y0:Y1, X0:X1] == 0)
    sig = _grain_sigma(gray, ring)
    if sig > 0.5:
        noise = np.random.default_rng(seed).normal(0, sig, hole.shape).astype(np.float32)
        filled = np.clip(filled.astype(np.float32) + noise[:, :, None], 0, 255).astype(np.uint8)
    sel = hole > 0
    win[sel] = filled[sel]


def _smart_fill(out, labels, i, box, allmask):
    """Texture-matching heal (like Photoshop's healing brush).

    Looks around the painted spot for the clean patch whose surroundings best match the spot's
    surroundings, copies it in and blends it with Poisson blending, so facets, gradients and
    grain continue naturally. Returns False if no good patch exists (caller falls back).
    """
    H, W = labels.shape
    x, y, w, h = box
    s = max(w, h)
    if s > 600:
        return False
    r = int(np.clip(s * 0.6, 6, 40))
    pad = r + 2
    X0, Y0, X1, Y1 = max(0, x - pad), max(0, y - pad), min(W, x + w + pad), min(H, y + h + pad)
    tw, th = X1 - X0, Y1 - Y0
    hole = (labels[Y0:Y1, X0:X1] == i).astype(np.uint8)
    known = allmask[Y0:Y1, X0:X1] == 0
    ring = ((cv2.dilate(hole, _ellipse(r)) > 0) & known).astype(np.uint8)
    if int(ring.sum()) < 30:
        return False

    R = int(min(max(2 * s, 60), 500))
    SX0, SY0, SX1, SY1 = max(0, X0 - R), max(0, Y0 - R), min(W, X1 + R), min(H, Y1 + R)
    if (SX1 - SX0) < tw + 4 or (SY1 - SY0) < th + 4:
        return False
    search = out[SY0:SY1, SX0:SX1]
    templ = out[Y0:Y1, X0:X1]
    am = (allmask[SY0:SY1, SX0:SX1] > 0).astype(np.float32)

    f = max(1, int(np.ceil(s / 100)))            # big spots: find the position on a smaller copy
    if f > 1:
        def dn(a):
            return cv2.resize(a, (max(1, a.shape[1] // f), max(1, a.shape[0] // f)), interpolation=cv2.INTER_AREA)
        s_in, t_in, r_in, a_in = dn(search), dn(templ), (dn(ring.astype(np.float32)) > 0.5), dn(am)
    else:
        s_in, t_in, r_in, a_in = search, templ, ring > 0, am
    sf, tf = s_in.astype(np.float32), t_in.astype(np.float32)
    th2, tw2 = tf.shape[:2]
    if sf.shape[0] <= th2 or sf.shape[1] <= tw2 or not r_in.any():
        return False
    mk = np.repeat(r_in[:, :, None].astype(np.float32), 3, axis=2)
    res = cv2.matchTemplate(sf, tf, cv2.TM_SQDIFF, mask=mk) / max(1.0, float(r_in.sum()) * 3)
    over = cv2.matchTemplate(a_in.astype(np.float32), np.ones((th2, tw2), np.float32), cv2.TM_CCORR)
    res[over > 1e-3] = 1e9                        # never copy from painted areas (or from the spot itself)
    if res.min() >= 1e9:
        return False

    flat = res.ravel()
    cand = np.argpartition(flat, min(6, flat.size) - 1)[:6]
    best = None
    for idx in cand:
        v = float(flat[idx])
        if v >= 1e9:
            continue
        cy, cx = divmod(int(idx), res.shape[1])
        sy = min(cy * f, search.shape[0] - th)
        sx = min(cx * f, search.shape[1] - tw)
        g = cv2.cvtColor(search[sy:sy + th, sx:sx + tw], cv2.COLOR_BGR2GRAY)
        specks = np.abs(g.astype(np.int16) - cv2.medianBlur(g, 5).astype(np.int16)) > 28
        frac = float(specks[hole > 0].mean())     # do not copy another speck
        score = v * (1 + 8 * frac)
        if best is None or score < best[0]:
            best = (score, v, sy, sx)
    if best is None or best[1] > 2000:            # no similar enough clean area
        return False

    _, _, sy, sx = best
    p = 8
    patch = search[sy:sy + th, sx:sx + tw]
    # Damaged pixels (this spot and not-yet-healed neighbours) must never act as blend boundary:
    # give the blend a smooth, plausible estimate there instead.
    unk = np.where(allmask[Y0:Y1, X0:X1] > 0, 255, 0).astype(np.uint8)
    dstw = cv2.inpaint(templ, unk, 3, cv2.INPAINT_TELEA)
    src = cv2.copyMakeBorder(patch, p, p, p, p, cv2.BORDER_REPLICATE)
    dst = cv2.copyMakeBorder(dstw, p, p, p, p, cv2.BORDER_REPLICATE)
    m255 = cv2.copyMakeBorder(cv2.dilate(hole, np.ones((3, 3), np.uint8), iterations=2) * 255, p, p, p, p,
                              cv2.BORDER_CONSTANT, value=0)
    bx, by, bw, bh = cv2.boundingRect(m255)
    try:
        blended = cv2.seamlessClone(src, dst, m255, (bx + bw // 2, by + bh // 2), cv2.NORMAL_CLONE)
    except cv2.error:
        return False
    region = out[Y0:Y1, X0:X1]
    region[hole > 0] = blended[p:p + th, p:p + tw][hole > 0]
    return True


def heal_mask(img, mask, method="smart"):
    """Heal every painted area of `mask` (non-zero = repair). Returns a new image."""
    out = img.copy()
    m = (mask > 0).astype(np.uint8)
    if not m.any():
        return out
    n, labels, stats, _ = cv2.connectedComponentsWithStats(m, connectivity=8)
    order = sorted(range(1, n), key=lambda i: stats[i, cv2.CC_STAT_AREA])   # small spots first
    next_id = n
    for i in order:
        box = tuple(int(v) for v in stats[i, :4])
        jobs, next_id = _split_thin(labels, i, box, int(stats[i, cv2.CC_STAT_AREA]), next_id)
        for jid, (x, y, w, h) in jobs:
            if not (method == "smart" and _smart_fill(out, labels, jid, (x, y, w, h), m)):
                _smooth_fill(out, labels, jid, (x, y, w, h), m, seed=jid)
            # a healed piece counts as clean context for the next one, so scratches heal continuously
            m[y:y + h, x:x + w][labels[y:y + h, x:x + w] == jid] = 0
    return out


def _split_thin(labels, i, box, area, next_id):
    """Cut a long thin stroke (scratch, striation) into short pieces, healed one after another."""
    x, y, w, h = box
    L = max(w, h)
    if L <= 48 or area > 0.3 * L * L:
        return [(i, box)], next_id
    width = area / float(np.hypot(w, h))
    c = int(np.clip(width * 3, 24, 80))
    roi = labels[y:y + h, x:x + w]
    ys, xs = np.nonzero(roi == i)
    tile = (ys // c) * 100000 + (xs // c)
    jobs = []
    for t in np.unique(tile):
        sel = tile == t
        nid = next_id
        next_id += 1
        roi[ys[sel], xs[sel]] = nid
        bx0, bx1, by0, by1 = xs[sel].min(), xs[sel].max(), ys[sel].min(), ys[sel].max()
        jobs.append((nid, (x + int(bx0), y + int(by0), int(bx1 - bx0 + 1), int(by1 - by0 + 1))))
    jobs.sort(key=lambda j: j[1][0] if w >= h else j[1][1])      # walk along the stroke
    return jobs, next_id


def apply_heals(img, strokes, x0, y0, rw, rh, method="smart"):
    """Fill every painted area. Strokes are in photo pixels."""
    if not strokes:
        return img
    oh, ow = img.shape[:2]
    kx, ky = ow / rw, oh / rh
    m = np.zeros((oh, ow), np.uint8)
    for s in strokes:
        r = max(1, int(round(s["r"] * kx)))
        pts = [(int(round((px - x0) * kx)), int(round((py - y0) * ky))) for px, py in s["pts"]]
        for a, b in zip(pts[:-1], pts[1:]):
            cv2.line(m, a, b, 255, 2 * r)
        for pt in pts:
            cv2.circle(m, pt, r, 255, -1)
    if not m.any():
        return img
    return heal_mask(img, cv2.dilate(m, np.ones((3, 3), np.uint8)), method)


# ------------------------------------------------------------------ color tools
def adjust_color(img, saturation=1.0, hsl=None):
    hsl = hsl or {}
    active = {n: p for n, p in hsl.items() if n in BANDS and any(p.get(k, 0) for k in ("h", "s", "l"))}
    if saturation == 1.0 and not active:
        return img
    f = img.astype(np.float32) / 255.0
    H, L, S = cv2.split(cv2.cvtColor(f, cv2.COLOR_BGR2HLS))
    S0 = S.copy()
    dh = np.zeros_like(H)
    ds = np.zeros_like(H)
    dl = np.zeros_like(H)
    for name, p in active.items():
        d = np.abs(((H - BANDS[name] + 180) % 360) - 180)
        w = np.clip(1 - d / 45.0, 0, None) * np.clip(S0 * 3, 0, 1)  # spare neutral grays
        dh += w * p.get("h", 0)
        ds += w * p.get("s", 0) / 100.0
        dl += w * p.get("l", 0) / 100.0
    H = (H + dh) % 360
    S = np.clip(S * saturation * (1 + ds), 0, 1)
    L = np.clip(L * (1 + dl), 0, 1)
    out = cv2.cvtColor(cv2.merge([H, L, S]), cv2.COLOR_HLS2BGR)
    return np.clip(out * 255, 0, 255).astype(np.uint8)


# --------------------------------------------------------------------- pipeline
def process_full(img, p, heals=None):
    """Run the full edit. Returns dict(result, dust_mask, gem_mask, rect).

    rect = (x0, y0, w, h): the part of the original photo shown in `result`.
    gem_mask = the area where dust removal is allowed (stone minus an edge margin).
    """
    p = {**DEFAULTS, **p}
    a = analyze_gem(img)
    H, W = img.shape[:2]
    if p["crop"]:
        x0, y0, side = crop_rect(img.shape, a["bbox"], p["padding"], p["dx"], p["dy"])
        out = img[y0:y0 + side, x0:x0 + side]
        size = int(p["out_size"]) if p["out_size"] else side
        if size and side != size:
            interp = cv2.INTER_AREA if side > size else cv2.INTER_CUBIC
            out = cv2.resize(out, (size, size), interpolation=interp)
        rw = rh = float(side)
    else:
        x0 = y0 = 0
        out = img
        rw, rh = float(W), float(H)
    oh, ow = out.shape[:2]

    # stone mask in the coordinates of the cropped picture
    M = np.float32([[ow / (rw * a["sx"]), 0, -x0 * ow / rw],
                    [0, oh / (rh * a["sy"]), -y0 * oh / rh]])
    gem = cv2.warpAffine(a["mask"], M, (ow, oh), flags=cv2.INTER_LINEAR)
    gem = np.where(gem > 127, 255, 0).astype(np.uint8)
    region = gem
    if p["gem_margin"] > 0 and gem.any():
        kr = max(1, int(round(p["gem_margin"] * ow)))
        region = np.where(cv2.distanceTransform(gem, cv2.DIST_L2, 5) > kr, 255, 0).astype(np.uint8)

    dust_mask = None
    if p["dust"]:
        out, dust_mask = remove_dust(out, p["dust_thr"], p["dust_area"], p["dust_mode"],
                                     region=region if p["gem_only"] else None)
    if heals:
        out = apply_heals(out, heals, x0, y0, rw, rh, p["heal_method"])
    out = adjust_color(out, p["saturation"], p["hsl"])
    return dict(result=out, dust_mask=dust_mask, gem_mask=region, rect=(x0, y0, rw, rh))


def process(img, p, heals=None):
    r = process_full(img, p, heals)
    return r["result"], r["dust_mask"]


# ------------------------------------------------------- stones: grouping and naming
def capture_time(path):
    """When the photo was taken (EXIF). Falls back to the file's modified time."""
    try:
        from PIL import Image
        with Image.open(path) as im:
            ex = im.getexif()
            sub = ex.get_ifd(0x8769)
            t = sub.get(36867) or sub.get(36868) or ex.get(306)
            if t:
                return datetime.strptime(str(t)[:19], "%Y:%m:%d %H:%M:%S").timestamp()
    except Exception:
        pass
    return Path(path).stat().st_mtime


def group_photos(files, times, mode="count", per_stone=5, gap=45.0, force_new=(), force_join=()):
    """Split an ordered list of photos into stones.

    mode "count": a new stone after every `per_stone` photos.
    mode "pause": a new stone whenever more than `gap` seconds passed since the previous photo.
    force_new / force_join: sets of file paths the user corrected by hand. After a manual
    correction the automatic grouping carries on from there.
    times: dict path -> seconds.
    """
    groups, cur, prev = [], [], None
    for f in files:
        key = str(f)
        if not cur:
            cur = [f]
        else:
            if key in force_new:
                new = True
            elif key in force_join:
                new = False
            elif mode == "count":
                new = len(cur) >= max(1, int(per_stone))
            else:
                new = (times.get(key, 0) - times.get(str(prev), 0)) > gap
            if new:
                groups.append(cur)
                cur = [f]
            else:
                cur.append(f)
        prev = f
    if cur:
        groups.append(cur)
    return groups


def _clean(name):
    return re.sub(r'[\\/:*?"<>|]+', "-", str(name)).strip() or "stone"


def stone_names(groups, prefix="stone_", start=1, digits=3, custom=None):
    """One name per stone. `custom` maps the first photo's path of a stone to a typed-in name."""
    custom = custom or {}
    names = []
    for i, g in enumerate(groups):
        typed = str(custom.get(str(g[0]), "")).strip()
        names.append(_clean(typed) if typed else f"{prefix}{start + i:0{digits}d}")
    return names


def output_names(groups, names, sep="_", labels="", subfolders=False):
    """Map every photo path to its new name (without extension)."""
    lab = [x.strip() for x in str(labels).split(",") if x.strip()]
    out = {}
    for g, stone in zip(groups, names):
        for k, f in enumerate(g):
            suffix = _clean(lab[k]) if k < len(lab) else str(k + 1)
            base = f"{stone}{sep}{suffix}"
            out[str(f)] = f"{stone}/{base}" if subfolders else base
    return out


def find_duplicates(outs):
    seen, dup = set(), set()
    for v in outs.values():
        (dup if v in seen else seen).add(v)
    return sorted(dup)


# --------------------------------------------------------------------------- export
def export_batch(items, outdir, params, fmt=".jpg", quality=95, progress=None, heals=None,
                 overwrite=True, workers=None):
    """Process and save photos, several at once.

    items: list of (source path, new name without extension; may contain a sub folder).
    Returns dict(done, skipped, errors=[(file, message)]).
    """
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    heals = heals or {}
    workers = workers or max(1, min(4, (os.cpu_count() or 2)))
    result = dict(done=0, skipped=0, errors=[])

    def one(src, rel):
        dest = outdir / f"{rel}{fmt}"
        if dest.exists() and not overwrite:
            return "skipped"
        dest.parent.mkdir(parents=True, exist_ok=True)
        out, _ = process(load_image(src), params, heals.get(str(src)))
        save_image(dest, out, quality)
        return "done"

    finished = 0
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(one, src, rel): src for src, rel in items}
        for fut in as_completed(futs):
            try:
                result[fut.result()] += 1
            except Exception as e:
                result["errors"].append((Path(futs[fut]).name, str(e)))
            finished += 1
            if progress:
                progress(finished, len(items))
    return result
