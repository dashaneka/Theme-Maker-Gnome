"""Icon theme generator - recolors Papirus folders for any accent color."""

import re
import shutil
import subprocess
from pathlib import Path

from theme_maker.palette import hex_to_rgb


def _recolor_svg(svg_content: str, target_color: str) -> str:
    """Recolor SVG content by replacing folder colors with target accent color."""
    accent = target_color
    h, s, l = _hex_to_hsl(accent)
    accent_dark = _hsl_to_hex(h, max(s - 15, 0), max(l - 12, 0))
    accent_light = _hsl_to_hex(h, min(s + 10, 100), min(l + 15, 100))
    accent_bg = _hsl_to_hex(h, max(s - 30, 0), max(l - 25, 0))

    replacements = [
        ("#e25252", accent),
        ("#f5542b", accent),
        ("#c44322", accent_dark),
        ("#d35f5f", accent),
        ("#e85d5d", accent),
        ("#f06292", accent),
        ("#ef5350", accent),
        ("#e53935", accent),
        ("#d32f2f", accent_dark),
        ("#c62828", accent_dark),
        ("#b71c1c", accent_bg),
        ("#ff5252", accent),
        ("#ff1744", accent),
        ("#f44336", accent),
        ("#e57373", accent_light),
        ("#ef9a9a", accent_light),
        ("#ffcdd2", accent_light),
        ("#ff8a80", accent_light),
        ("#ff867c", accent),
        ("#d50000", accent_dark),
        ("#e24f51", accent),
        ("#a30002", accent_bg),
        ("#5294e2", accent),
        ("#93c0ea", accent_light),
        ("#57b8ec", accent),
        ("#1d344f", accent_bg),
        ("#81a1c1", accent_light),
        ("#3b5df4", accent),
        ("#1d99f3", accent),
        ("#3a539b", accent_dark),
        ("#87b158", accent),
        ("#60924b", accent_dark),
        ("#7fcc74", accent),
        ("#75e73c", accent),
        ("#4fef42", accent),
        ("#96e24f", accent_light),
        ("#ee923a", accent),
        ("#eb6637", accent_dark),
        ("#ff9800", accent),
        ("#f27935", accent),
        ("#f9bd30", accent_light),
        ("#eeca8f", accent_light),
        ("#fdbc4b", accent_light),
        ("#fdd285", accent_light),
        ("#7e57c2", accent),
        ("#ca71df", accent_light),
        ("#e040fb", accent),
        ("#d500f9", accent),
        ("#aa00ff", accent_dark),
        ("#e1bee7", accent_light),
        ("#ce93d8", accent_light),
        ("#ba68c8", accent),
        ("#ab47bc", accent),
        ("#9c27b0", accent_dark),
        ("#8e24aa", accent_dark),
        ("#7b1fa2", accent_bg),
        ("#6a1b9a", accent_bg),
        ("#4a148c", accent_bg),
        ("#ea80fc", accent_light),
        ("#c51162", accent_dark),
        ("#f50057", accent),
        ("#ff4081", accent),
        ("#ff80ab", accent_light),
        ("#45abb7", accent),
        ("#16a085", accent_dark),
        ("#00bcd4", accent),
        ("#04896a", accent_dark),
        ("#e4e4e4", accent_light),
        ("#d1bfae", accent_light),
        ("#ae8e6c", accent_dark),
        ("#8e8e8e", accent_dark),
        ("#676767", accent_bg),
        ("#4f4f4f", accent_bg),
        ("#3f3f3f", accent_bg),
        ("#a9a9a9", accent_dark),
        ("#5c6bc0", accent),
        ("#607d8b", accent_dark),
    ]

    result = svg_content
    for old_color, new_color in replacements:
        result = result.replace(old_color, new_color)
    return result


def _hex_to_hsl(hex_color: str) -> tuple[float, float, float]:
    r, g, b = hex_to_rgb(hex_color)
    r, g, b = r / 255.0, g / 255.0, b / 255.0
    cmax, cmin = max(r, g, b), min(r, g, b)
    delta = cmax - cmin
    l = (cmax + cmin) / 2.0
    if delta == 0:
        return (0.0, 0.0, l * 100)
    s = delta / (1 - abs(2 * l - 1))
    if cmax == r:
        h = ((g - b) / delta) % 6
    elif cmax == g:
        h = (b - r) / delta + 2
    else:
        h = (r - g) / delta + 4
    h *= 60
    if h < 0:
        h += 360
    return (h, s * 100, l * 100)


def _hsl_to_hex(h: float, s: float, l: float) -> str:
    s /= 100.0
    l /= 100.0
    a = s * min(l, 1 - l)

    def f(n: int) -> float:
        k = (n + h / 30) % 12
        return l - a * max(min(k - 3, 9 - k, 1), -1)

    return f"#{int(round(f(0) * 255)):02x}{int(round(f(8) * 255)):02x}{int(round(f(4) * 255)):02x}"


def generate_icon_theme(output_dir: Path, palette: dict, name: str) -> None:
    """Generate a custom icon theme that inherits Papirus-Dark with recolored folders."""
    slug = name.lower().replace(" ", "-")
    accent = palette["accent"]

    papirus_src = None
    for candidate in [
        Path("/usr/share/icons/Papirus-Dark"),
        Path.home() / ".local/share/icons/Papirus-Dark",
        Path.home() / ".icons/Papirus-Dark",
    ]:
        if candidate.exists() and (candidate / "16x16").exists():
            papirus_src = candidate
            break

    icon_dir = output_dir / "icons" / slug
    if icon_dir.exists():
        shutil.rmtree(icon_dir)
    icon_dir.mkdir(parents=True, exist_ok=True)

    if papirus_src is None:
        (icon_dir / "index.theme").write_text(
            f"[Icon Theme]\nName={name}\n"
            f"Comment=Custom icon theme with {accent} accent folders (inherits Papirus-Dark)\n"
            f"Inherits=Papirus-Dark,hicolor\n"
        )
        return

    # Build directory listing of Papirus-Dark
    # We only need the places directories for folder icons
    sizes = []
    for item in sorted(papirus_src.iterdir()):
        if item.is_dir() and (item / "places").exists():
            sizes.append(item.name)

    # Create index.theme
    dirs_line = ",".join(f"{s}/places" for s in sizes)
    sections = []
    for s in sizes:
        size_num = (
            s.replace("x16@2x", "16")
            .replace("x22@2x", "22")
            .replace("x24@2x", "24")
            .replace("x32@2x", "32")
            .replace("x48@2x", "48")
            .replace("x64@2x", "64")
        )
        try:
            size_val = int(size_num.split("x")[0])
        except (ValueError, IndexError):
            size_val = 48
        if "@" in s:
            sections.append(
                f"\n[{s}/places]\nContext=Places\nSize={size_val}\nScale=2\nType=Fixed"
            )
        elif s == "scalable":
            sections.append(
                f"\n[{s}/places]\nSize=48\nType=Scalable\nMinSize=8\nMaxSize=512"
            )
        else:
            sections.append(
                f"\n[{s}/places]\nContext=Places\nSize={size_val}\nType=Fixed"
            )

    index_theme = f"""[Icon Theme]
Name={name}
Comment=Custom Papirus icon theme with {accent} accent
Inherits=Papirus-Dark,hicolor

Example=folder

FollowsColorScheme=true

Directories={dirs_line}
{"".join(sections)}
"""
    (icon_dir / "index.theme").write_text(index_theme)

    # Only copy and recolor folder SVGs from Papirus-Dark
    modified_count = 0

    for size in sizes:
        src_places = papirus_src / size / "places"
        if not src_places.exists():
            continue

        dst_places = icon_dir / size / "places"
        dst_places.mkdir(parents=True, exist_ok=True)

        # Copy only folder and user SVGs
        for svg_path in src_places.glob("folder*.svg"):
            _copy_and_recolor_folder(svg_path, dst_places / svg_path.name, accent)
            modified_count += 1
        for svg_path in src_places.glob("user*.svg"):
            _copy_and_recolor_folder(svg_path, dst_places / svg_path.name, accent)
            modified_count += 1

    try:
        subprocess.run(
            ["gtk-update-icon-cache", "-f", str(icon_dir)],
            capture_output=True,
            check=False,
            timeout=10,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass


def _copy_and_recolor_folder(src: Path, dst: Path, accent: str) -> None:
    """Copy a folder SVG and recolor it."""
    # If it's a symlink, follow it
    if src.is_symlink():
        real_src = src.resolve()
        if real_src.exists():
            try:
                content = real_src.read_text(errors="ignore")
            except (OSError, UnicodeDecodeError):
                return
        else:
            return
    else:
        try:
            content = src.read_text(errors="ignore")
        except (OSError, UnicodeDecodeError):
            return

    recolored = _recolor_svg(content, accent)

    # For default folder SVGs using ColorScheme-Text for fill, replace grey with accent
    if dst.name == "folder.svg" or dst.name.startswith("user-"):
        recolored = re.sub(
            r"\.ColorScheme-Text\s*\{\s*color:#[0-9a-fA-F]+\s*\}",
            f".ColorScheme-Text {{ color:{accent} }}",
            recolored,
        )
        recolored = recolored.replace("#dfdfdf", accent)
        recolored = recolored.replace("#DFDFDF", accent)

    dst.write_text(recolored)


def apply_icon_theme(output_dir: Path, name: str) -> list[str]:
    """Install the generated icon theme."""
    log: list[str] = []
    home = Path.home()
    slug = name.lower().replace(" ", "-")

    src = output_dir / "icons" / slug
    if not src.exists():
        return log

    dst = home / ".local/share/icons" / slug
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        shutil.rmtree(dst)

    # Use rsync for fast install
    rsync = shutil.which("rsync")
    if rsync:
        # Ensure destination parent exists and remove old copy
        if dst.exists():
            shutil.rmtree(dst)
        dst.parent.mkdir(parents=True, exist_ok=True)
        result = subprocess.run(
            [
                rsync,
                "-a",
                "--no-perms",
                "--no-owner",
                "--no-group",
                str(src) + "/",
                str(dst) + "/",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode not in (0, 23, 24):
            # Fallback to shutil if rsync fails (23=partial, 24=vanished files)
            shutil.copytree(src, dst, symlinks=False)
    else:
        shutil.copytree(src, dst, symlinks=False)
    log.append(f"  Installed icon theme: {slug}")

    try:
        subprocess.run(
            ["gtk-update-icon-cache", "-f", str(dst)],
            capture_output=True,
            check=False,
            timeout=10,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    try:
        subprocess.run(
            ["gsettings", "set", "org.gnome.desktop.interface", "icon-theme", slug],
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        )
        log.append(f"  Set icon theme to: {slug}")
    except (
        subprocess.CalledProcessError,
        FileNotFoundError,
        subprocess.TimeoutExpired,
    ):
        log.append(f"  [WARN] Could not set icon theme via gsettings")

    return log
