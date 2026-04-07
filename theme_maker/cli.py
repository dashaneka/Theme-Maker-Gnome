"""CLI entry point for Theme Maker for GNOME."""

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

from theme_maker import __version__
from theme_maker.palette import (
    extract_colors,
    pick_accent,
    generate_palette,
    hex_to_hsl,
    get_gnome_accent_name,
)
from theme_maker.generators.gtk import write_gtk_files
from theme_maker.generators.browsers import write_browser_files
from theme_maker.generators.terminal import write_terminal_files
from theme_maker.generators.editors import write_editor_files
from theme_maker.generators.extras import write_extra_files
from theme_maker.generators.icons import generate_icon_theme
from theme_maker.generators.cursors import generate_cursor_theme
from theme_maker.applier import apply_theme, create_undo_backup, restore_theme


# ── ANSI helpers ──────────────────────────────────────────────────────────────

BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
CYAN = "\033[36m"
WHITE = "\033[97m"


class _HelpFormatter(argparse.ArgumentDefaultsHelpFormatter, argparse.RawDescriptionHelpFormatter):
    """Help formatter that preserves examples and shows defaults."""

    def _get_help_string(self, action: argparse.Action) -> str:
        help_text = action.help or ""
        if "%(default)" in help_text:
            return help_text
        if action.default in (None, False, argparse.SUPPRESS):
            return help_text
        return f"{help_text} (default: %(default)s)"


def _normalize_hex_color(value: str) -> str:
    """Normalize a user-provided hex color and reject invalid values."""
    color = value.strip()
    if not color.startswith("#"):
        color = "#" + color
    if len(color) != 7:
        raise ValueError("expected a 6-digit hex color like #c41e3a")
    try:
        int(color[1:], 16)
    except ValueError as exc:
        raise ValueError("expected a 6-digit hex color like #c41e3a") from exc
    return color.lower()


def _color_swatch(hexc: str) -> str:
    """Return an ANSI true-color swatch block for a hex color."""
    h = hexc.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"\033[48;2;{r};{g};{b}m  \033[0m"


def _print_header() -> None:
    print()
    print(f"{BOLD}{RED}  Theme Maker for GNOME{RESET}  {DIM}v{__version__}{RESET}")
    print(f"{DIM}  Generate system-wide themes from any wallpaper.{RESET}")
    print()


def _print_palette_table(palette: dict) -> None:
    """Print a compact palette preview."""
    rows = [
        ("Deepest BG", "bg_deepest"),
        ("Main BG", "bg_main"),
        ("Surface", "bg_surface"),
        ("Elevated", "bg_elevated"),
        ("Border", "border"),
        ("Accent", "accent"),
        ("Accent Hover", "accent_hover"),
        ("Accent Light", "accent_light"),
        ("Accent Soft", "accent_soft"),
        ("Rose", "accent_rose"),
        ("Text", "text"),
        ("Text Muted", "text_muted"),
        ("Green", "green"),
        ("Blue", "blue"),
        ("Magenta", "magenta"),
        ("Cyan", "cyan"),
    ]
    print(f"  {BOLD}Generated Palette:{RESET}")
    print()
    for label, key in rows:
        hexc = palette.get(key, "#000000")
        swatch = _color_swatch(hexc)
        marker = f" {BOLD}<-- accent{RESET}" if key == "accent" else ""
        print(f"    {swatch} {hexc}  {DIM}{label}{RESET}{marker}")
    print()


def _print_ansi_strip(palette: dict) -> None:
    """Print ANSI color strip (16 colors)."""
    ansi_keys = [
        "ansi_black",
        "ansi_red",
        "ansi_green",
        "ansi_yellow",
        "ansi_blue",
        "ansi_magenta",
        "ansi_cyan",
        "ansi_white",
        "ansi_bright_black",
        "ansi_bright_red",
        "ansi_bright_green",
        "ansi_bright_yellow",
        "ansi_bright_blue",
        "ansi_bright_magenta",
        "ansi_bright_cyan",
        "ansi_bright_white",
    ]
    print(f"  {BOLD}Terminal Colors:{RESET}")
    normal = "    "
    bright = "    "
    for i, key in enumerate(ansi_keys):
        hexc = palette.get(key, "#000000")
        swatch = _color_swatch(hexc)
        if i < 8:
            normal += swatch
        else:
            bright += swatch
    print(normal + f"  {DIM}normal{RESET}")
    print(bright + f"  {DIM}bright{RESET}")
    print()


def _prompt_yn(question: str, default: bool = True) -> bool:
    """Ask a yes/no question. Returns True for yes."""
    hint = "[Y/n]" if default else "[y/N]"
    try:
        answer = input(f"  {question} {DIM}{hint}{RESET} ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print()
        return default
    if not answer:
        return default
    return answer.startswith("y")


def _prompt_input(question: str, default: str = "") -> str:
    """Ask for text input with optional default."""
    hint = f" {DIM}[{default}]{RESET}" if default else ""
    try:
        answer = input(f"  {question}{hint}: ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return default
    return answer or default


def _detect_wallpaper() -> str | None:
    """
    Auto-detect current wallpaper from multiple sources.

    Supports:
    - GNOME (gsettings picture-uri-dark / picture-uri)
    - KDE Plasma (kreadconfig5)
    - XFCE (xfconf-query)
    - MATE (gsettings)
    - Cinnamon (gsettings)
    - feh/nitrogen (common wallpaper setters)
    - Fallback: recent files in common wallpaper directories
    """
    import urllib.parse

    home = Path.home()

    # ── Method 1: GNOME / GNOME-based (Fedora Workstation default) ────────────────
    for schema, key in [
        ("org.gnome.desktop.background", "picture-uri-dark"),
        ("org.gnome.desktop.background", "picture-uri"),
    ]:
        try:
            result = subprocess.run(
                ["gsettings", "get", schema, key],
                capture_output=True,
                text=True,
                check=True,
                timeout=5,
            )
            uri = result.stdout.strip().strip("'\"")
            if uri.startswith("file://"):
                uri = urllib.parse.unquote(uri[7:])  # Decode URL encoding (%20, etc.)
            else:
                uri = urllib.parse.unquote(uri)

            if uri and Path(uri).exists():
                return str(Path(uri).resolve())
        except (
            subprocess.CalledProcessError,
            FileNotFoundError,
            subprocess.TimeoutExpired,
        ):
            continue

    # ── Method 2: KDE Plasma ─────────────────────────────────────────────────────
    try:
        result = subprocess.run(
            [
                "kreadconfig5",
                "--file",
                "kwinrc",
                "--group",
                "Wallpaper",
                "--key",
                "Image",
                "--default",
                "",
            ],
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        )
        wallpaper = result.stdout.strip()
        if wallpaper:
            # KDE stores as file:// or just path
            if wallpaper.startswith("file://"):
                wallpaper = urllib.parse.unquote(wallpaper[7:])
            if Path(wallpaper).exists():
                return str(Path(wallpaper).resolve())
    except (
        subprocess.CalledProcessError,
        FileNotFoundError,
        subprocess.TimeoutExpired,
    ):
        pass

    # ── Method 3: XFCE ────────────────────────────────────────────────────────────
    try:
        result = subprocess.run(
            [
                "xfconf-query",
                "-c",
                "xfce4-desktop",
                "-p",
                "/backdrop/screen0/monitor0/workspace0/last-image",
            ],
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        )
        wallpaper = result.stdout.strip()
        if wallpaper and Path(wallpaper).exists():
            return str(Path(wallpaper).resolve())
    except (
        subprocess.CalledProcessError,
        FileNotFoundError,
        subprocess.TimeoutExpired,
    ):
        pass

    # ── Method 4: MATE ─────────────────────────────────────────────────────────────
    try:
        result = subprocess.run(
            ["gsettings", "get", "org.mate.desktop.background", "picture-uri"],
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        )
        uri = result.stdout.strip().strip("'\"")
        if uri.startswith("file://"):
            uri = urllib.parse.unquote(uri[7:])
        if uri and Path(uri).exists():
            return str(Path(uri).resolve())
    except (
        subprocess.CalledProcessError,
        FileNotFoundError,
        subprocess.TimeoutExpired,
    ):
        pass

    # ── Method 5: Cinnamon ─────────────────────────────────────────────────────────
    try:
        result = subprocess.run(
            ["gsettings", "get", "org.cinnamon.desktop.background", "picture-uri"],
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        )
        uri = result.stdout.strip().strip("'\"")
        if uri.startswith("file://"):
            uri = urllib.parse.unquote(uri[7:])
        if uri and Path(uri).exists():
            return str(Path(uri).resolve())
    except (
        subprocess.CalledProcessError,
        FileNotFoundError,
        subprocess.TimeoutExpired,
    ):
        pass

    # ── Method 6: feh (common lightweight wallpaper setter) ───────────────────────
    fehbg = home / ".fehbg"
    if fehbg.exists():
        try:
            content = fehbg.read_text()
            # Parse: feh --no-fehbg --bg-fill '/path/to/wallpaper.jpg'
            if "'" in content:
                path = content.split("'")[1]
                if Path(path).exists():
                    return str(Path(path).resolve())
        except (IndexError, OSError):
            pass

    # ── Method 7: nitrogen (another wallpaper setter) ───────────────────────────────
    nitrogen_cfg = home / ".config" / "nitrogen" / "bg-saved.cfg"
    if nitrogen_cfg.exists():
        try:
            content = nitrogen_cfg.read_text()
            for line in content.split("\n"):
                if line.startswith("file="):
                    path = line[5:]
                    if Path(path).exists():
                        return str(Path(path).resolve())
        except (IndexError, OSError):
            pass

    # ── Method 8: Fallback - find most recent wallpaper in common dirs ─────────────
    common_dirs = [
        home / ".local" / "share" / "backgrounds",  # GNOME default (Fedora)
        home / "Pictures" / "Wallpapers",
        home / "Pictures" / "Wallpaper",
        home / "Wallpapers",
        home / "Pictures",
        Path("/usr/share/backgrounds"),  # System wallpapers
        Path("/usr/share/backgrounds/gnome"),
        Path("/usr/share/backgrounds/fedora"),
    ]

    image_extensions = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif"}
    candidates: list[tuple[Path, float]] = []

    for directory in common_dirs:
        if directory.exists():
            try:
                for f in directory.iterdir():
                    if f.is_file() and f.suffix.lower() in image_extensions:
                        # Get modification time for recency sorting
                        try:
                            mtime = f.stat().st_mtime
                            candidates.append((f, mtime))
                        except OSError:
                            continue
            except PermissionError:
                continue

    # Return the most recently modified wallpaper
    if candidates:
        candidates.sort(key=lambda x: x[1], reverse=True)
        return str(candidates[0][0].resolve())

    return None


def _wallpaper_state(explicit_wallpaper: str | None) -> tuple[str | None, int | None]:
    """Return the current wallpaper path plus a content-change signal."""
    wallpaper = explicit_wallpaper or _detect_wallpaper()
    if not wallpaper:
        return (None, None)
    path = Path(wallpaper).expanduser().resolve()
    if not path.exists():
        return (str(path), None)
    try:
        return (str(path), path.stat().st_mtime_ns)
    except OSError:
        return (str(path), None)


def _build_cli_args(args: argparse.Namespace, wallpaper: str) -> list[str]:
    """Reconstruct a one-shot CLI invocation from the parsed args."""
    build_args = [wallpaper, "--no-interactive", "--apply"]
    if args.name:
        build_args.extend(["--name", args.name])
    if args.accent:
        build_args.extend(["--accent", args.accent])
    if args.output:
        build_args.extend(["--output", args.output])
    return build_args


def _positive_int(value: str) -> int:
    """Parse a positive integer for CLI options."""
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("expected a positive integer") from exc
    if parsed < 1:
        raise argparse.ArgumentTypeError("expected a positive integer")
    return parsed


def _resolve_wallpaper_argument(args: argparse.Namespace) -> str | None:
    """Resolve the wallpaper from positional and named forms."""
    positional = getattr(args, "wallpaper", None)
    named = getattr(args, "wallpaper_path", None)

    if positional and named:
        pos_path = str(Path(positional).expanduser().resolve())
        named_path = str(Path(named).expanduser().resolve())
        if pos_path != named_path:
            raise ValueError(
                "provide the wallpaper either positionally or with --wallpaper, not both"
            )

    return named or positional


def _build_parser() -> argparse.ArgumentParser:
    """Create the CLI parser with grouped help and examples."""
    epilog = """Examples:
  theme-maker
  theme-maker --wallpaper ~/Pictures/wallpaper.jpg --name MyTheme --apply
  theme-maker ~/Pictures/wallpaper.jpg -a #2060c0 -y
  theme-maker --restore
  theme-maker --watch --apply
"""
    parser = argparse.ArgumentParser(
        prog="theme-maker",
        description="Theme Maker for GNOME - generate system-wide themes from wallpapers.",
        formatter_class=_HelpFormatter,
        epilog=epilog,
    )

    input_group = parser.add_argument_group("Input")
    input_group.add_argument(
        "wallpaper",
        nargs="?",
        help="Wallpaper image path (auto-detects if omitted)",
    )
    input_group.add_argument(
        "-w",
        "--wallpaper",
        dest="wallpaper_path",
        help="Wallpaper image path (named form; overrides the positional argument)",
    )
    input_group.add_argument(
        "-n",
        "--name",
        "--theme-name",
        dest="name",
        help="Theme name (prompted if omitted)",
    )
    input_group.add_argument(
        "-a",
        "--accent",
        help="Override accent color as hex (for example #c41e3a)",
    )

    output_group = parser.add_argument_group("Output")
    output_group.add_argument(
        "-o",
        "--output",
        help="Output directory (default: ~/<ThemeName>)",
    )

    actions = parser.add_argument_group("Actions")
    actions.add_argument(
        "--apply",
        action="store_true",
        help="Apply the generated theme system-wide after writing files",
    )
    special = parser.add_mutually_exclusive_group()
    special.add_argument(
        "--backup",
        action="store_true",
        help="Back up the current theme state into a reusable template",
    )
    special.add_argument(
        "--restore",
        nargs="?",
        const="__LAST__",
        help="Restore the last saved theme state or a specific backup directory",
    )
    special.add_argument(
        "--doctor",
        action="store_true",
        help="Check system readiness and theme tool dependencies",
    )
    special.add_argument(
        "--watch",
        action="store_true",
        help="Watch wallpaper changes and regenerate/apply automatically",
    )

    actions.add_argument(
        "--watch-interval",
        type=_positive_int,
        default=5,
        metavar="SECONDS",
        help="Wallpaper watcher poll interval in seconds",
    )
    actions.add_argument(
        "-y",
        "--yes",
        "--no-interactive",
        dest="no_interactive",
        action="store_true",
        help="Skip prompts and use defaults",
    )
    actions.add_argument(
        "-V",
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    return parser


def _doctor_report() -> tuple[list[str], int]:
    """Check runtime prerequisites and desktop state."""
    log: list[str] = []
    failures = 0

    def ok(msg: str) -> None:
        log.append(f"  [OK] {msg}")

    def warn(msg: str) -> None:
        log.append(f"  [WARN] {msg}")

    def fail(msg: str) -> None:
        nonlocal failures
        failures += 1
        log.append(f"  [FAIL] {msg}")

    for mod in ["PIL", "numpy"]:
        try:
            __import__(mod)
            ok(f"Python module available: {mod}")
        except ImportError:
            fail(f"Missing Python module: {mod}")

    required_commands = [
        "gsettings",
        "gtk-update-icon-cache",
        "git",
        "magick",
        "ctgen",
    ]
    optional_commands = ["rsync"]
    for cmd in required_commands:
        if shutil.which(cmd):
            ok(f"Command available: {cmd}")
        else:
            fail(f"Missing required command: {cmd}")
    for cmd in optional_commands:
        if shutil.which(cmd):
            ok(f"Optional command available: {cmd}")
        else:
            warn(f"Optional command missing: {cmd}")

    xdg_desktop = (os.environ.get("XDG_CURRENT_DESKTOP") or "").lower()
    if "gnome" in xdg_desktop:
        ok(f"GNOME desktop detected: {xdg_desktop}")
    else:
        warn(f"XDG_CURRENT_DESKTOP is {xdg_desktop or 'unset'}")

    wallpaper = _detect_wallpaper()
    if wallpaper:
        ok(f"Wallpaper detected: {wallpaper}")
    else:
        warn("Wallpaper auto-detection failed")

    for schema, key in [
        ("org.gnome.desktop.interface", "gtk-theme"),
        ("org.gnome.desktop.interface", "icon-theme"),
        ("org.gnome.desktop.interface", "cursor-theme"),
    ]:
        try:
            subprocess.run(
                ["gsettings", "get", schema, key],
                capture_output=True,
                text=True,
                check=True,
                timeout=5,
            )
            ok(f"gsettings schema readable: {schema}.{key}")
        except (
            subprocess.CalledProcessError,
            FileNotFoundError,
            subprocess.TimeoutExpired,
        ):
            warn(f"Could not read gsettings key: {schema}.{key}")

    for target in [
        Path.home() / ".themes",
        Path.home() / ".icons",
        Path.home() / ".config",
    ]:
        try:
            target.mkdir(parents=True, exist_ok=True)
            ok(f"Writable path: {target}")
        except OSError:
            fail(f"Cannot write to {target}")

    return log, failures


def _watch_wallpaper(args: argparse.Namespace) -> int:
    """Regenerate and apply the theme when the wallpaper changes."""
    interval = max(2, getattr(args, "watch_interval", 5))
    try:
        explicit_wallpaper = _resolve_wallpaper_argument(args)
    except ValueError as exc:
        print(f"  {RED}Error:{RESET} {exc}")
        return 1

    last_state: tuple[str | None, int | None] | None = None
    print(f"  Watching wallpaper changes every {interval}s...")
    print()

    while True:
        current_path, current_sig = _wallpaper_state(explicit_wallpaper)
        current_state = (current_path, current_sig)

        if current_path and current_state != last_state:
            print(f"  Wallpaper changed: {current_path}")
            build_args = _build_cli_args(args, current_path)
            result = main(build_args)
            if result == 0:
                last_state = current_state
            print()

        if current_path is None:
            print("  Waiting for wallpaper...")

        time.sleep(interval)


def _generate_all(output_dir: Path, palette: dict, name: str, wallpaper: str) -> None:
    """Run all generators and write files to output_dir."""
    write_gtk_files(output_dir, palette, name)
    write_browser_files(output_dir, palette, name)
    write_terminal_files(output_dir, palette, name, wallpaper)
    write_editor_files(output_dir, palette, name)
    write_extra_files(output_dir, palette, name, wallpaper)
    generate_icon_theme(output_dir, palette, name)
    generate_cursor_theme(output_dir, palette, name)


def _backup_current_theme(output_dir: Path) -> list[str]:
    """Backup current theme settings as a reusable template."""
    log: list[str] = []
    home = Path.home()

    # Create backup directory
    backup_dir = output_dir / "backup"
    backup_dir.mkdir(parents=True, exist_ok=True)

    # Backup gsettings
    settings_to_backup = [
        ("org.gnome.desktop.interface", "gtk-theme"),
        ("org.gnome.desktop.interface", "color-scheme"),
        ("org.gnome.desktop.interface", "accent-color"),
        ("org.gnome.desktop.interface", "icon-theme"),
        ("org.gnome.desktop.interface", "cursor-theme"),
        ("org.gnome.shell.extensions.user-theme", "name"),
        ("org.gnome.desktop.background", "picture-uri"),
        ("org.gnome.desktop.background", "picture-uri-dark"),
    ]

    settings_data = {}
    for schema, key in settings_to_backup:
        try:
            result = subprocess.run(
                ["gsettings", "get", schema, key],
                capture_output=True,
                text=True,
                check=True,
                timeout=5,
            )
            value = result.stdout.strip().strip("'\"")
            if value and value != "''":
                settings_data[f"{schema}.{key}"] = value
                log.append(f"  Backed up: {schema}.{key} = {value}")
        except (
            subprocess.CalledProcessError,
            FileNotFoundError,
            subprocess.TimeoutExpired,
        ):
            pass

    # Save settings to JSON
    settings_file = backup_dir / "settings.json"
    settings_file.write_text(json.dumps(settings_data, indent=2))
    log.append(f"  Saved settings to {settings_file}")

    # Backup GTK config files
    gtk_configs = [
        (home / ".config" / "gtk-3.0" / "settings.ini", "gtk3-settings.ini"),
        (home / ".config" / "gtk-4.0" / "settings.ini", "gtk4-settings.ini"),
        (home / ".config" / "gtk-3.0" / "gtk.css", "gtk3.css"),
        (home / ".config" / "gtk-4.0" / "gtk.css", "gtk4.css"),
    ]

    for src, dst_name in gtk_configs:
        if src.exists():
            dst = backup_dir / dst_name
            shutil.copy2(src, dst)
            log.append(f"  Backed up: {src} -> {dst}")

    # Backup theme directories
    # NOTE: These can be large (hundreds of MB), so we warn the user.
    theme_dirs = [
        (home / ".themes", "themes"),
        (home / ".icons", "icons"),
    ]

    for src_dir, dst_name in theme_dirs:
        if src_dir.exists():
            dst = backup_dir / dst_name
            if dst.exists():
                shutil.rmtree(dst)
            try:
                shutil.copytree(src_dir, dst)
                log.append(f"  Backed up: {src_dir} -> {dst}")
            except (OSError, shutil.Error) as e:
                log.append(f"  [WARN] Failed to backup {src_dir}: {e}")

    # Create backup manifest
    manifest = {
        "name": "Theme Backup",
        "description": "Backup of current GNOME theme settings",
        "settings": settings_data,
        "files": [
            "settings.json",
            "gtk3-settings.ini",
            "gtk4-settings.ini",
            "gtk3.css",
            "gtk4.css",
            "themes/",
            "icons/",
        ],
    }

    manifest_file = backup_dir / "manifest.json"
    manifest_file.write_text(json.dumps(manifest, indent=2))
    log.append(f"  Created manifest: {manifest_file}")

    return log


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    interactive = not args.no_interactive

    try:
        wallpaper_arg = _resolve_wallpaper_argument(args)
    except ValueError as exc:
        parser.error(str(exc))

    _print_header()

    if args.doctor:
        print(f"  {BOLD}Running doctor checks...{RESET}")
        print()
        logs, failures = _doctor_report()
        for line in logs:
            print(line)
        print()
        if failures:
            print(f"  {RED}{BOLD}Doctor found {failures} issue(s).{RESET}")
            return 1
        print(f"  {GREEN}{BOLD}Doctor checks passed.{RESET}")
        return 0

    if args.restore is not None:
        print(f"  {BOLD}Restoring theme state...{RESET}")
        print()
        restore_path = None if args.restore == "__LAST__" else Path(args.restore)
        logs = restore_theme(restore_path)
        for line in logs:
            print(line)
        print()
        if any(line.startswith("  [FAIL]") for line in logs):
            print(f"  {RED}{BOLD}Restore failed.{RESET}")
            return 1
        print(f"  {GREEN}{BOLD}Restore complete.{RESET}")
        return 0

    if args.watch:
        return _watch_wallpaper(args)

    # ── Handle backup mode ────────────────────────────────────────────────
    if args.backup:
        print(f"  {BOLD}Backing up current theme...{RESET}")
        print()

        output = args.output or str(Path.home() / "ThemeBackup")
        output_dir = Path(output)
        output_dir.mkdir(parents=True, exist_ok=True)

        logs = _backup_current_theme(output_dir)
        for line in logs:
            print(f"  {line}")

        print()
        print(f"  {GREEN}{BOLD}Backup complete!{RESET}")
        print(f"  {DIM}Backup saved to {output_dir}{RESET}")
        print()
        return 0

    # ── Step 1: Wallpaper ─────────────────────────────────────────────────
    wallpaper = wallpaper_arg

    if not wallpaper:
        detected = _detect_wallpaper()
        if detected:
            print(f"  {GREEN}Detected wallpaper:{RESET} {detected}")
            if interactive and not _prompt_yn("Use this wallpaper?"):
                wallpaper = _prompt_input("Wallpaper path")
            else:
                wallpaper = detected
        elif interactive:
            wallpaper = _prompt_input("Wallpaper path")
        else:
            print(f"  {RED}Error:{RESET} No wallpaper provided and auto-detect failed.")
            return 1

    wallpaper = str(Path(wallpaper).expanduser().resolve())

    if not Path(wallpaper).exists():
        print(f"  {RED}Error:{RESET} File not found: {wallpaper}")
        return 1

    print(f"  {CYAN}Wallpaper:{RESET} {wallpaper}")
    print()

    # ── Step 2: Extract colors ────────────────────────────────────────────
    print(f"  {BOLD}Extracting dominant colors...{RESET}")
    extracted = extract_colors(wallpaper)

    print(f"  Found {len(extracted)} dominant colors:")
    line = "    "
    for c in extracted:
        line += _color_swatch(c) + " "
    print(line)
    print(f"    {DIM}{' '.join(extracted)}{RESET}")
    print()

    # ── Step 3: Pick accent ───────────────────────────────────────────────
    try:
        if args.accent:
            accent = _normalize_hex_color(args.accent)
            print(
                f"  {CYAN}Using provided accent:{RESET} {_color_swatch(accent)} {accent}"
            )
        else:
            accent = pick_accent(extracted)
            h, s, l = hex_to_hsl(accent)
            gnome_name = get_gnome_accent_name(accent)
            print(
                f"  {CYAN}Best accent candidate:{RESET} "
                f"{_color_swatch(accent)} {accent}  "
                f"{DIM}(hue={h:.0f} sat={s:.0f} lum={l:.0f}, GNOME: {gnome_name}){RESET}"
            )

            if interactive:
                if not _prompt_yn("Use this accent color?"):
                    custom = _prompt_input("Enter accent hex (e.g. #c41e3a)")
                    if custom:
                        accent = _normalize_hex_color(custom)
                        print(
                            f"  {CYAN}Using custom accent:{RESET} {_color_swatch(accent)} {accent}"
                        )
    except ValueError as exc:
        print(f"  {RED}Error:{RESET} Invalid accent color: {exc}")
        return 1

    print()

    # ── Step 4: Theme name ────────────────────────────────────────────────
    if args.name:
        name = args.name
    elif interactive:
        name = _prompt_input("Theme name", "MyTheme")
    else:
        name = "MyTheme"

    print(f"  {CYAN}Theme name:{RESET} {name}")
    print()

    # ── Step 5: Generate palette ──────────────────────────────────────────
    print(f"  {BOLD}Generating palette from accent {accent}...{RESET}")
    palette = generate_palette(accent, wallpaper)

    _print_palette_table(palette)
    _print_ansi_strip(palette)

    if interactive:
        if not _prompt_yn("Proceed with this palette?"):
            print(f"  {YELLOW}Aborted.{RESET}")
            return 0

    # ── Step 6: Generate theme files ──────────────────────────────────────
    output = args.output or str(Path.home() / name)
    output_dir = Path(output)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"  {BOLD}Generating theme files...{RESET}")
    _generate_all(output_dir, palette, name, wallpaper)

    # Count generated files
    file_count = sum(1 for _ in output_dir.rglob("*") if _.is_file())
    print(f"  {GREEN}Generated {file_count} files{RESET} in {output_dir}")
    print()

    # List top-level structure
    print(f"  {BOLD}Output structure:{RESET}")
    for entry in sorted(output_dir.iterdir()):
        if entry.is_dir():
            sub_count = sum(1 for _ in entry.rglob("*") if _.is_file())
            print(f"    {entry.name}/  {DIM}({sub_count} files){RESET}")
        else:
            print(f"    {entry.name}")
    print()

    # ── Step 7: Apply theme ───────────────────────────────────────────────
    do_apply = args.apply

    if not do_apply and interactive:
        do_apply = _prompt_yn("Apply theme system-wide now?", default=False)

    if do_apply:
        print()
        print(f"  {BOLD}Applying theme system-wide...{RESET}")
        print()
        backup_dir, backup_logs = create_undo_backup(name)
        print(f"  {DIM}Saved restore point: {backup_dir}{RESET}")
        for line in backup_logs:
            print(f"  {line}")
        logs = apply_theme(output_dir, name, palette, wallpaper)
        for line in logs:
            print(f"  {line}")
        print()
        print(f"  {GREEN}{BOLD}Theme applied!{RESET}")
        print(f"  {DIM}Some changes may require logging out and back in.{RESET}")
        print(f"  {DIM}Chrome theme: load manually via chrome://extensions{RESET}")
    else:
        print(f"  {DIM}Theme files saved to {output_dir}{RESET}")
        print(f"  {DIM}See INSTALL.md for manual installation instructions.{RESET}")
        print(f"  {DIM}Or re-run with --apply to apply system-wide.{RESET}")

    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
