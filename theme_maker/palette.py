"""Color extraction from wallpapers and palette generation."""

import colorsys

from PIL import Image
import numpy as np


def hex_to_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def rgb_to_hex(r: float, g: float, b: float) -> str:
    return f"#{max(0, min(255, int(r))):02x}{max(0, min(255, int(g))):02x}{max(0, min(255, int(b))):02x}"


def rgb_to_hsl(r: int, g: int, b: int) -> tuple[float, float, float]:
    h, l, s = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
    return (h * 360, s * 100, l * 100)


def hsl_to_rgb(h: float, s: float, l: float) -> tuple[int, int, int]:
    r, g, b = colorsys.hls_to_rgb(h / 360, l / 100, s / 100)
    return (int(r * 255), int(g * 255), int(b * 255))


def hsl_to_hex(h: float, s: float, l: float) -> str:
    return rgb_to_hex(*hsl_to_rgb(h, s, l))


def hex_to_hsl(hexc: str) -> tuple[float, float, float]:
    return rgb_to_hsl(*hex_to_rgb(hexc))


def lighten(hexc: str, amount: float) -> str:
    h, s, l = hex_to_hsl(hexc)
    return hsl_to_hex(h, s, min(100, l + amount))


def darken(hexc: str, amount: float) -> str:
    h, s, l = hex_to_hsl(hexc)
    return hsl_to_hex(h, s, max(0, l - amount))


def saturate(hexc: str, amount: float) -> str:
    h, s, l = hex_to_hsl(hexc)
    return hsl_to_hex(h, min(100, s + amount), l)


def desaturate(hexc: str, amount: float) -> str:
    h, s, l = hex_to_hsl(hexc)
    return hsl_to_hex(h, max(0, s - amount), l)


def blend(hex1: str, hex2: str, factor: float) -> str:
    r1, g1, b1 = hex_to_rgb(hex1)
    r2, g2, b2 = hex_to_rgb(hex2)
    r = r1 + (r2 - r1) * factor
    g = g1 + (g2 - g1) * factor
    b = b1 + (b2 - b1) * factor
    return rgb_to_hex(r, g, b)


def color_distance(c1: np.ndarray, c2: np.ndarray) -> float:
    return float(np.sqrt(np.sum((c1.astype(float) - c2.astype(float)) ** 2)))


def kmeans_colors(
    pixels: np.ndarray, k: int = 8, max_iter: int = 20
) -> list[np.ndarray]:
    """Simple k-means clustering for dominant color extraction."""
    n = len(pixels)
    if n == 0:
        return []

    # Initialize centroids by sampling evenly spaced pixels
    indices = np.linspace(0, n - 1, k, dtype=int)
    centroids = pixels[indices].astype(float)

    for _ in range(max_iter):
        # Assign each pixel to nearest centroid
        dists = np.array(
            [np.sum((pixels.astype(float) - c) ** 2, axis=1) for c in centroids]
        )
        labels = np.argmin(dists, axis=0)

        # Recompute centroids
        new_centroids = np.zeros_like(centroids)
        for j in range(k):
            mask = labels == j
            if np.any(mask):
                new_centroids[j] = pixels[mask].astype(float).mean(axis=0)
            else:
                new_centroids[j] = centroids[j]

        if np.allclose(centroids, new_centroids, atol=1):
            break
        centroids = new_centroids

    # Count cluster sizes for sorting
    dists = np.array(
        [np.sum((pixels.astype(float) - c) ** 2, axis=1) for c in centroids]
    )
    labels = np.argmin(dists, axis=0)
    counts = [(np.sum(labels == j), j) for j in range(k)]
    counts.sort(reverse=True)

    return [centroids[j].astype(int) for _, j in counts]


def extract_colors(image_path: str, num_colors: int = 8) -> list[str]:
    """Extract dominant colors from an image using k-means."""
    img = Image.open(image_path).convert("RGB")

    # Resize for performance
    img = img.resize((200, 200), Image.Resampling.LANCZOS)

    pixels = np.array(img).reshape(-1, 3)

    # Remove very dark and very bright pixels for better accent detection
    brightness = pixels.sum(axis=1)
    mask = (brightness > 60) & (brightness < 700)
    filtered = pixels[mask] if mask.sum() > 1000 else pixels

    # Shuffle for better k-means initialization
    np.random.seed(42)
    np.random.shuffle(filtered)

    centroids = kmeans_colors(filtered, k=num_colors)
    return [rgb_to_hex(int(c[0]), int(c[1]), int(c[2])) for c in centroids]


def score_accent(hexc: str) -> float:
    """Score a color for accent suitability (higher = better accent)."""
    h, s, l = hex_to_hsl(hexc)

    # We want high saturation, moderate lightness
    sat_score = s / 100.0
    # Lightness sweet spot around 35-55
    if l < 15 or l > 85:
        light_score = 0.1
    elif 25 <= l <= 60:
        light_score = 1.0
    else:
        light_score = 0.5

    # Bonus for non-grey colors
    grey_penalty = 1.0 if s > 20 else 0.1

    return sat_score * light_score * grey_penalty


def pick_accent(colors: list[str]) -> str:
    """Pick the best accent color from extracted colors."""
    if not colors:
        return "#c41e3a"

    scored = [(score_accent(c), c) for c in colors]
    scored.sort(reverse=True)
    return scored[0][1]


def generate_palette(accent_hex: str, wallpaper_path: str = "") -> dict[str, str]:
    """Generate a complete theme palette from an accent color."""
    ah, a_s, al = hex_to_hsl(accent_hex)

    # Ensure the accent is reasonably saturated and visible
    if a_s < 40:
        a_s = 60
    if al < 25:
        al = 40
    if al > 65:
        al = 50
    accent = hsl_to_hex(ah, a_s, al)

    # ── Background tiers (dark, tinted with accent hue) ──
    bg_deepest = hsl_to_hex(ah, max(3, a_s * 0.05), 3)
    bg_main = hsl_to_hex(ah, max(5, a_s * 0.08), 5.5)
    bg_surface = hsl_to_hex(ah, max(8, a_s * 0.12), 8.5)
    bg_elevated = hsl_to_hex(ah, max(12, a_s * 0.15), 12)
    border = hsl_to_hex(ah, max(15, a_s * 0.2), 17)
    border_bright = hsl_to_hex(ah, max(15, a_s * 0.2), 22)

    # ── Accent variants ──
    accent_hover = hsl_to_hex(ah, min(100, a_s + 5), min(65, al + 8))
    accent_light = hsl_to_hex(ah, min(100, a_s + 10), min(70, al + 12))
    accent_soft = hsl_to_hex((ah + 15) % 360, max(30, a_s * 0.6), al)
    accent_rose = hsl_to_hex(ah, max(40, a_s * 0.7), min(75, al + 20))

    # ── Text colors (slightly warm-tinted) ──
    text = hsl_to_hex(ah, max(3, a_s * 0.06), 90)
    text_muted = hsl_to_hex(ah, max(4, a_s * 0.08), 63)
    text_dim = hsl_to_hex(ah, max(5, a_s * 0.1), 38)

    # ── Semantic colors ──
    green = hsl_to_hex(130, 50, 46)
    blue = hsl_to_hex(228, 40, 55)
    # Magenta: fixed pink-purple range, slightly tinted toward accent
    mag_hue = 320 if (ah < 60 or ah >= 300) else (ah + 180) % 360
    magenta = hsl_to_hex(mag_hue, min(60, max(40, a_s * 0.8)), 50)
    cyan = hsl_to_hex(175, 40, 48)

    # ── Insensitive / disabled ──
    insensitive_bg = hsl_to_hex(ah, max(5, a_s * 0.06), 7)
    insensitive_fg = text_dim

    # ── Warning uses actual yellow-amber only for semantics ──
    warning = hsl_to_hex(35, 70, 58)

    # ── ANSI terminal colors ──
    ansi = {}
    ansi["black"] = hsl_to_hex(ah, max(3, a_s * 0.05), 5)
    ansi["red"] = accent
    ansi["green"] = green
    # Yellow slot uses a shifted accent variant (avoid clashing orange)
    ansi["yellow"] = hsl_to_hex((ah + 8) % 360, min(80, a_s), min(55, al + 5))
    ansi["blue"] = blue
    ansi["magenta"] = magenta
    ansi["cyan"] = cyan
    ansi["white"] = text_muted

    ansi["bright_black"] = border
    ansi["bright_red"] = accent_light
    ansi["bright_green"] = lighten(green, 8)
    ansi["bright_yellow"] = accent_rose
    ansi["bright_blue"] = lighten(blue, 10)
    ansi["bright_magenta"] = lighten(magenta, 12)
    ansi["bright_cyan"] = lighten(cyan, 10)
    ansi["bright_white"] = lighten(text, 3)

    # ── Deep maroon (for subtle uses) ──
    deep_maroon = hsl_to_hex(ah, max(30, a_s * 0.5), 20)

    return {
        "wallpaper": wallpaper_path,
        "bg_deepest": bg_deepest,
        "bg_main": bg_main,
        "bg_surface": bg_surface,
        "bg_elevated": bg_elevated,
        "border": border,
        "border_bright": border_bright,
        "accent": accent,
        "accent_hover": accent_hover,
        "accent_light": accent_light,
        "accent_soft": accent_soft,
        "accent_rose": accent_rose,
        "text": text,
        "text_muted": text_muted,
        "text_dim": text_dim,
        "green": green,
        "blue": blue,
        "magenta": magenta,
        "cyan": cyan,
        "warning": warning,
        "insensitive_bg": insensitive_bg,
        "insensitive_fg": insensitive_fg,
        "deep_maroon": deep_maroon,
        "ansi_black": ansi["black"],
        "ansi_red": ansi["red"],
        "ansi_green": ansi["green"],
        "ansi_yellow": ansi["yellow"],
        "ansi_blue": ansi["blue"],
        "ansi_magenta": ansi["magenta"],
        "ansi_cyan": ansi["cyan"],
        "ansi_white": ansi["white"],
        "ansi_bright_black": ansi["bright_black"],
        "ansi_bright_red": ansi["bright_red"],
        "ansi_bright_green": ansi["bright_green"],
        "ansi_bright_yellow": ansi["bright_yellow"],
        "ansi_bright_blue": ansi["bright_blue"],
        "ansi_bright_magenta": ansi["bright_magenta"],
        "ansi_bright_cyan": ansi["bright_cyan"],
        "ansi_bright_white": ansi["bright_white"],
    }


def get_gnome_accent_name(accent_hex: str) -> str:
    """Map an accent color to the nearest GNOME accent-color name."""
    h, s, l = hex_to_hsl(accent_hex)
    # GNOME accent-color options: blue, teal, green, yellow, orange, red, pink, purple, slate
    if s < 15:
        return "slate"
    if h < 15 or h >= 345:
        return "red"
    if 15 <= h < 40:
        return "orange"
    if 40 <= h < 70:
        return "yellow"
    if 70 <= h < 160:
        return "green"
    if 160 <= h < 195:
        return "teal"
    if 195 <= h < 260:
        return "blue"
    if 260 <= h < 300:
        return "purple"
    return "pink"  # 300-345
