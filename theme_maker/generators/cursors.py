"""Cursor theme generator - builds Bibata cursors with custom accent color."""

import os
import shutil
import subprocess
from pathlib import Path

from theme_maker.palette import hex_to_rgb


def _hex_to_hsl(hex_color: str) -> tuple[float, float, float]:
    r, g, b = hex_to_rgb(hex_color)
    r, g, b = r / 255.0, g / 255.0, b / 255.0
    cmax, cmin = max(r, g, b), min(r, g, b)
    delta = cmax - cmin
    l = (cmax + cmin) / 2.0
    if delta == 0:
        h = s = 0.0
    else:
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


def _find_bibata_source() -> Path | None:
    candidates = [
        Path.home() / "Bibata_Cursor",
        Path.home() / "Codes" / "Bibata_Cursor",
        Path("/tmp/Bibata_Cursor"),
    ]
    for c in candidates:
        if (c / "svg").exists() and (c / "build.sh").exists():
            return c
    clone_target = Path("/tmp/Bibata_Cursor")
    if clone_target.exists():
        shutil.rmtree(clone_target)
    try:
        subprocess.run(
            [
                "git",
                "clone",
                "--depth",
                "1",
                "https://github.com/ful1e5/Bibata_Cursor.git",
                str(clone_target),
            ],
            capture_output=True,
            text=True,
            timeout=120,
            check=True,
        )
        if (clone_target / "svg").exists():
            return clone_target
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError):
        pass
    return None


def generate_cursor_theme(output_dir: Path, palette: dict, name: str) -> None:
    """Generate a custom cursor theme by building Bibata with accent color."""
    slug = name.lower().replace(" ", "-") + "-cursors"
    accent = palette["accent"]
    h, s, l = _hex_to_hsl(accent)
    accent_dark = _hsl_to_hex(h, max(s - 10, 0), max(l - 15, 0))

    cursor_dir = output_dir / "cursors" / slug
    if cursor_dir.exists():
        shutil.rmtree(cursor_dir)

    bibata_src = _find_bibata_source()
    if bibata_src is None:
        _write_fallback_theme(cursor_dir, name, accent)
        return

    build_dir = output_dir / "cursors" / "bibata-build"
    build_dir.mkdir(parents=True, exist_ok=True)
    bitmaps_dir = build_dir / "bitmaps"
    bitmaps_dir.mkdir(parents=True, exist_ok=True)

    svg_modern = bibata_src / "svg" / "modern"
    svg_files = list(svg_modern.glob("*.svg"))
    for anim_subdir in ["left_ptr_watch", "wait"]:
        anim_dir = svg_modern / anim_subdir
        if anim_dir.exists():
            svg_files.extend(anim_dir.glob("*.svg"))

    magick = shutil.which("magick")
    if not magick:
        shutil.rmtree(build_dir, ignore_errors=True)
        _write_fallback_theme(cursor_dir, name, accent)
        return

    base_size = 64
    for svg_path in svg_files:
        filename = svg_path.name.replace(".svg", ".png")
        out_path = bitmaps_dir / filename
        try:
            content = svg_path.read_text()
        except (OSError, UnicodeDecodeError):
            continue
        content = content.replace("#00FF00", accent)
        content = content.replace("#0000FF", "#ffffff")
        content = content.replace("#FF0000", accent_dark)
        tmp_svg = bitmaps_dir / filename.replace(".png", "_tmp.svg")
        tmp_svg.write_text(content)
        subprocess.run(
            [
                magick,
                "convert",
                "-background",
                "none",
                "-density",
                "300",
                "-resize",
                f"{base_size}x{base_size}",
                str(tmp_svg),
                str(out_path),
            ],
            capture_output=True,
            timeout=30,
        )
        tmp_svg.unlink(missing_ok=True)

    hotspot_scale = base_size / 256.0

    # Cursor definitions: name -> (png, x_hotspot, y_hotspot, x11_name, [symlinks])
    # None for hotspot means use fallback (128, 128)
    cursors = [
        (
            "bd_double_arrow",
            "bd_double_arrow.png",
            None,
            None,
            "bd_double_arrow",
            ["c7088f0f3e6c8088236ef8e1e3e70000", "nwse-resize", "size_fdiag"],
        ),
        (
            "bottom_left_corner",
            "bottom_left_corner.png",
            26,
            232,
            "bottom_left_corner",
            ["sw-resize"],
        ),
        (
            "bottom_right_corner",
            "bottom_right_corner.png",
            229,
            232,
            "bottom_right_corner",
            ["se-resize"],
        ),
        ("bottom_side", "bottom_side.png", 129, 234, "bottom_side", ["s-resize"]),
        ("bottom_tee", "bottom_tee.png", 128, 230, "bottom_tee", []),
        ("center_ptr", "center_ptr.png", 127, 17, "center_ptr", []),
        ("circle", "circle.png", 55, 17, "circle", ["forbidden"]),
        ("context-menu", "context-menu.png", 57, 17, "context-menu", []),
        (
            "copy",
            "copy.png",
            55,
            17,
            "copy",
            [
                "1081e37283d90000800003c07f3ef6bf",
                "6407b0e94181790501fd1e167b474872",
                "b66166c04f8c3109214a4fbd64a50fc8",
            ],
        ),
        ("cross", "cross.png", None, None, "cross", ["cross_reverse", "diamond_cross"]),
        (
            "crossed_circle",
            "crossed_circle.png",
            None,
            None,
            "crossed_circle",
            ["03b6e0fcb3499374a867c041f52298f0", "not-allowed"],
        ),
        ("crosshair", "crosshair.png", None, None, "crosshair", []),
        ("dnd_no_drop", "dnd_no_drop.png", 100, 65, "dnd_no_drop", ["no-drop"]),
        ("dnd-ask", "dnd-ask.png", 100, 65, "dnd-ask", []),
        ("dnd-copy", "dnd-copy.png", 100, 65, "dnd-copy", []),
        ("dnd-link", "dnd-link.png", 100, 65, "dnd-link", ["alias"]),
        (
            "dotbox",
            "dotbox.png",
            None,
            None,
            "dotbox",
            ["dot_box_mask", "draped_box", "icon", "target"],
        ),
        (
            "fd_double_arrow",
            "fd_double_arrow.png",
            None,
            None,
            "fd_double_arrow",
            ["fcf1c3c7cd4491d801f1e1c78f100000", "nesw-resize", "size_bdiag"],
        ),
        (
            "grabbing",
            "grabbing.png",
            128,
            66,
            "grabbing",
            ["closedhand", "dnd-move", "dnd-none", "fcf21c00b30f7e3f83fe0dfd12e71cff"],
        ),
        ("hand1", "hand1.png", 144, 79, "hand1", ["grab", "openhand"]),
        (
            "hand2",
            "hand2.png",
            114,
            18,
            "hand2",
            [
                "9d800788f1b08800ae810202380a0822",
                "e29285e634086352946a0e7090d73106",
                "pointer",
                "pointing_hand",
            ],
        ),
        (
            "left_ptr",
            "left_ptr.png",
            55,
            17,
            "left_ptr",
            ["arrow", "default", "top_left_arrow"],
        ),
        (
            "left_ptr_watch",
            "left_ptr_watch-*.png",
            55,
            17,
            "left_ptr_watch",
            [
                "00000000000000020006000e7e9ffc3f",
                "08e8e1c95fe2fc01f976f1e063a24ccd",
                "3ecb610c1bf2410f44200f48c40d3599",
                "progress",
            ],
        ),
        ("left_side", "left_side.png", 21, 128, "left_side", ["w-resize"]),
        ("left_tee", "left_tee.png", 230, 128, "left_tee", []),
        (
            "link",
            "link.png",
            55,
            17,
            "link",
            [
                "3085a0e285430894940527032f8b26df",
                "640fb0e74195791501fd1ed57b41487f",
                "a2a266d0498c3104214a4fbd64ab0fc8",
            ],
        ),
        ("ll_angle", "ll_angle.png", 30, 223, "ll_angle", []),
        ("lr_angle", "lr_angle.png", 224, 230, "lr_angle", []),
        (
            "move",
            "move.png",
            None,
            None,
            "move",
            [
                "4498f0e0c1937ffe01fd06f973665830",
                "9081237383d90e509aa00f00170e968f",
                "all-scroll",
                "fleur",
                "size_all",
            ],
        ),
        ("pencil", "pencil.png", 46, 211, "pencil", ["draft"]),
        ("plus", "plus.png", None, None, "plus", ["cell"]),
        ("pointer-move", "pointer-move.png", 55, 17, "pointer-move", []),
        (
            "question_arrow",
            "question_arrow.png",
            42,
            86,
            "question_arrow",
            [
                "5c6cd98b3f3ebcb1f9c7f1c204630408",
                "d9ce0ab605698f320427677b458ad60b",
                "help",
                "left_ptr_help",
                "whats_this",
            ],
        ),
        (
            "right_ptr",
            "right_ptr.png",
            204,
            17,
            "right_ptr",
            ["draft_large", "draft_small"],
        ),
        ("right_side", "right_side.png", 233, 128, "right_side", ["e-resize"]),
        ("right_tee", "right_tee.png", 29, 128, "right_tee", []),
        (
            "sb_down_arrow",
            "sb_down_arrow.png",
            128,
            222,
            "sb_down_arrow",
            ["down-arrow"],
        ),
        (
            "sb_h_double_arrow",
            "sb_h_double_arrow.png",
            None,
            None,
            "sb_h_double_arrow",
            [
                "028006030e0e7ebffc7f7070c0600140",
                "14fef782d02440884392942c1120523",
                "col-resize",
                "ew-resize",
                "h_double_arrow",
                "size-hor",
                "size_hor",
                "split_h",
            ],
        ),
        (
            "sb_left_arrow",
            "sb_left_arrow.png",
            33,
            128,
            "sb_left_arrow",
            ["left-arrow"],
        ),
        (
            "sb_right_arrow",
            "sb_right_arrow.png",
            223,
            128,
            "sb_right_arrow",
            ["right-arrow"],
        ),
        ("sb_up_arrow", "sb_up_arrow.png", 128, 33, "sb_up_arrow", ["up-arrow"]),
        (
            "sb_v_double_arrow",
            "sb_v_double_arrow.png",
            None,
            None,
            "sb_v_double_arrow",
            [
                "00008160000006810000408080010102",
                "2870a09082c103050810ffdffffe0204",
                "double_arrow",
                "ns-resize",
                "row-resize",
                "size-ver",
                "size_ver",
                "split_v",
                "v_double_arrow",
            ],
        ),
        ("tcross", "tcross.png", None, None, "tcross", ["color-picker"]),
        (
            "top_left_corner",
            "top_left_corner.png",
            29,
            24,
            "top_left_corner",
            ["nw-resize"],
        ),
        (
            "top_right_corner",
            "top_right_corner.png",
            229,
            24,
            "top_right_corner",
            ["ne-resize"],
        ),
        ("top_side", "top_side.png", 128, 23, "top_side", ["n-resize"]),
        ("top_tee", "top_tee.png", 128, 27, "top_tee", []),
        ("ul_angle", "ul_angle.png", 33, 33, "ul_angle", []),
        ("ur_angle", "ur_angle.png", 225, 33, "ur_angle", []),
        ("vertical-text", "vertical-text.png", None, None, "vertical-text", []),
        ("wait", "wait-*.png", None, None, "wait", ["watch"]),
        ("wayland-cursor", "wayland-cursor.png", None, None, "wayland-cursor", []),
        ("X_cursor", "X_cursor.png", None, None, "X_cursor", ["pirate", "x-cursor"]),
        ("xterm", "xterm.png", None, None, "xterm", ["ibeam", "text"]),
        ("zoom_in", "zoom-in.png", 116, 116, "zoom-in", []),
        ("zoom_out", "zoom-out.png", 116, 116, "zoom-out", []),
    ]

    toml_lines = [
        "[theme]",
        f"name = '{slug}'",
        f"comment = 'Custom accent Bibata cursors ({accent})'",
        "website = 'https://www.bibata.live'",
        "",
        "[config]",
        "bitmaps_dir = 'bitmaps'",
        f"out_dir = 'themes/{slug}'",
        "platforms = 'x11'",
        "",
        "[cursors]",
        "[cursors.fallback_settings]",
        "x11_sizes = [16, 22, 24, 32, 48, 64]",
        f"x_hotspot = {int(128 * hotspot_scale)}",
        f"y_hotspot = {int(128 * hotspot_scale)}",
        "x11_delay = 40",
        "",
    ]

    for _, png, xh, yh, x11_name, symlinks in cursors:
        toml_lines.append(f"[cursors.{_.replace('-', '_')}]")
        toml_lines.append(f"png = '{png}'")
        if xh is not None:
            toml_lines.append(f"x_hotspot = {int(xh * hotspot_scale)}")
        if yh is not None:
            toml_lines.append(f"y_hotspot = {int(yh * hotspot_scale)}")
        toml_lines.append(f"x11_name = '{x11_name}'")
        if symlinks:
            sl = ", ".join(f'"{s}"' for s in symlinks)
            toml_lines.append(f"x11_symlinks = [{sl}]")
        toml_lines.append("")

    toml_path = build_dir / f"{slug}.toml"
    toml_path.write_text("\n".join(toml_lines) + "\n")

    # Build with ctgen
    built_theme = None
    if shutil.which("ctgen"):
        os.chdir(build_dir)
        try:
            result = subprocess.run(
                ["ctgen", str(toml_path), "-p", "x11"],
                capture_output=True,
                text=True,
                timeout=180,
            )
            if result.returncode == 0:
                themes_dir = build_dir / "themes"
                if themes_dir.exists():
                    for td in themes_dir.iterdir():
                        if td.is_dir():
                            # ctgen nests the theme name inside out_dir
                            for nested in td.iterdir():
                                if nested.is_dir() and (nested / "cursors").exists():
                                    built_theme = nested
                                    break
                            if built_theme:
                                break
                            elif (td / "cursors").exists():
                                built_theme = td
                                break
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            pass

    if built_theme and (built_theme / "cursors").exists():
        cursor_files = list((built_theme / "cursors").iterdir())
        if cursor_files:
            shutil.copytree(built_theme, cursor_dir, dirs_exist_ok=True)
            shutil.rmtree(build_dir, ignore_errors=True)
            return

    # Fallback: inherit from Bibata-Modern-Classic
    shutil.rmtree(build_dir, ignore_errors=True)
    _write_fallback_theme(cursor_dir, name, accent)


def _write_fallback_theme(cursor_dir: Path, name: str, accent: str) -> None:
    cursor_dir.mkdir(parents=True, exist_ok=True)
    (cursor_dir / "cursors").mkdir(exist_ok=True)
    (cursor_dir / "index.theme").write_text(
        f"[Icon Theme]\nName={name}\n"
        f"Comment=Custom cursor theme with {accent} accent (inherits Bibata-Modern-Classic)\n"
        f"Inherits=Bibata-Modern-Classic,hicolor\n"
    )
    (cursor_dir / "cursor.theme").write_text(
        f"[Icon Theme]\nName={name}\n"
        f"Comment=Custom cursor theme with {accent} accent\n"
        f"Inherits=Bibata-Modern-Classic\n"
    )


def apply_cursor_theme(output_dir: Path, name: str) -> list[str]:
    """Install the generated cursor theme."""
    log: list[str] = []
    home = Path.home()
    slug = name.lower().replace(" ", "-") + "-cursors"

    src = output_dir / "cursors" / slug
    if not src.exists():
        return log

    dst = home / ".local/share/icons" / slug
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        shutil.rmtree(dst)

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
            shutil.copytree(src, dst, symlinks=True)
    else:
        shutil.copytree(src, dst, symlinks=True)
    log.append(f"  Installed cursor theme: {slug}")

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
            [
                "gsettings",
                "set",
                "org.gnome.desktop.interface",
                "cursor-theme",
                f"'{slug}'",
            ],
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        )
        log.append(f"  Set cursor theme to: {slug}")
    except (
        subprocess.CalledProcessError,
        FileNotFoundError,
        subprocess.TimeoutExpired,
    ):
        log.append(f"  [WARN] Could not set cursor theme via gsettings")

    try:
        subprocess.run(
            ["gsettings", "set", "org.gnome.desktop.interface", "cursor-size", "24"],
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        )
    except (
        subprocess.CalledProcessError,
        FileNotFoundError,
        subprocess.TimeoutExpired,
    ):
        pass

    return log
