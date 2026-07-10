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
from theme_maker.applier import (
    _browser_profiles,
    _chromium_browser_roots,
    apply_theme,
    create_undo_backup,
    restore_theme,
)


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
    if args.mode == "light":
        build_args.append("--light")
    if args.components:
        build_args.extend(["--components", ",".join(args.components)])
    if args.terminal_opacity is not None:
        build_args.extend(["--terminal-opacity", str(args.terminal_opacity)])
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


def _opacity(value: str | float) -> float:
    """Parse a terminal opacity between 0.10 and 1.00."""
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise argparse.ArgumentTypeError("expected a number between 0.10 and 1.00") from exc
    if not 0.10 <= parsed <= 1.00:
        raise argparse.ArgumentTypeError("expected a number between 0.10 and 1.00")
    return parsed


_COMPONENT_LABELS = {
    "gtk": "GTK Theme",
    "gnome": "GNOME Settings",
    "dock": "Dash to Dock",
    "terminal": "Terminal",
    "browsers": "Browsers",
    "vscode": "VS Code",
    "vim": "Vim",
    "antigravity": "Antigravity",
    "opencode": "OpenCode",
    "kilo": "Kilo Code",
    "codex": "Codex",
    "fastfetch": "Fastfetch",
    "icons": "Icon Theme",
    "cursors": "Cursor Theme",
}


def _components(value: str | list[str] | tuple[str, ...]) -> list[str]:
    """Normalize and validate a component selection."""
    raw = value if isinstance(value, (list, tuple)) else value.split(",")
    selected = [str(item).strip().lower() for item in raw if str(item).strip()]
    if not selected:
        raise argparse.ArgumentTypeError("select at least one component")
    invalid = sorted(set(selected) - set(_COMPONENT_LABELS))
    if invalid:
        raise argparse.ArgumentTypeError(
            f"unknown component(s): {', '.join(invalid)}; choose from "
            + ", ".join(_COMPONENT_LABELS)
        )
    return list(dict.fromkeys(selected))


def _component_skips(selected: list[str] | None) -> list[str]:
    """Translate selected component keys to apply_theme skip labels."""
    if not selected:
        return []
    return [label for key, label in _COMPONENT_LABELS.items() if key not in selected]


def _load_preset(path: Path) -> dict:
    """Load and validate a Theme Maker TOML preset."""
    try:
        import tomllib

        data = tomllib.loads(path.read_text())
    except (OSError, ValueError) as exc:
        raise ValueError(f"could not load preset {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("preset must contain a TOML table")

    allowed = {
        "name",
        "wallpaper",
        "accent",
        "mode",
        "output",
        "apply",
        "components",
        "terminal_opacity",
        "no_interactive",
    }
    unknown = sorted(set(data) - allowed)
    if unknown:
        raise ValueError(f"unknown preset key(s): {', '.join(unknown)}")
    for key in ("name", "wallpaper", "accent", "mode", "output"):
        if key in data and not isinstance(data[key], str):
            raise ValueError(f"preset {key} must be a string")
    for key in ("apply", "no_interactive"):
        if key in data and not isinstance(data[key], bool):
            raise ValueError(f"preset {key} must be true or false")
    if "mode" in data and data["mode"] not in {"dark", "light"}:
        raise ValueError("preset mode must be 'dark' or 'light'")
    if "components" in data:
        data["components"] = _components(data["components"])
    if "terminal_opacity" in data:
        data["terminal_opacity"] = _opacity(data["terminal_opacity"])
    if "accent" in data:
        data["accent"] = _normalize_hex_color(str(data["accent"]))

    # Relative paths in a shared preset are resolved beside the preset file.
    for key in ("wallpaper", "output"):
        if data.get(key):
            candidate = Path(str(data[key])).expanduser()
            if not candidate.is_absolute():
                candidate = path.parent / candidate
            data[key] = str(candidate.resolve())
    return data


def _toml_string(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _save_preset(
    path: Path,
    args: argparse.Namespace,
    wallpaper: str,
    mode: str,
    name: str,
    accent: str,
    output: Path,
) -> None:
    """Save the resolved invocation as a reusable TOML preset."""
    components = args.components or list(_COMPONENT_LABELS)
    lines = [
        f"name = {_toml_string(name)}",
        f"wallpaper = {_toml_string(wallpaper)}",
        f"accent = {_toml_string(accent)}",
        f"mode = {_toml_string(mode)}",
        f"output = {_toml_string(str(output))}",
        f"apply = {'true' if args.apply else 'false'}",
        "components = [" + ", ".join(_toml_string(item) for item in components) + "]",
        f"terminal_opacity = {(args.terminal_opacity or 0.88):.2f}",
        f"no_interactive = {'true' if args.no_interactive else 'false'}",
    ]
    path = path.expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n")


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


def _build_parser(defaults: dict | None = None) -> argparse.ArgumentParser:
    """Create the CLI parser with grouped help and examples."""
    defaults = defaults or {}
    epilog = """Examples:
  theme-maker
  theme-maker --wallpaper ~/Pictures/wallpaper.jpg --name MyTheme --apply
  theme-maker ~/Pictures/wallpaper.jpg -a #2060c0 -y
  theme-maker ~/Pictures/wallpaper.jpg --apply --dry-run --no-interactive
  theme-maker --apply-existing ~/Themes/MyTheme
  theme-maker --config my-theme.toml
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
        default=defaults.get("name"),
        help="Theme name (prompted if omitted)",
    )
    input_group.add_argument(
        "-a",
        "--accent",
        default=defaults.get("accent"),
        help="Override accent color as hex (for example #c41e3a)",
    )
    mode_group = input_group.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--light",
        dest="mode",
        action="store_const",
        const="light",
        help="Generate a light theme instead of a dark theme",
    )
    mode_group.add_argument(
        "--dark",
        dest="mode",
        action="store_const",
        const="dark",
        help="Generate a dark theme (overrides a light preset)",
    )
    parser.set_defaults(mode=defaults.get("mode"))

    output_group = parser.add_argument_group("Output")
    output_group.add_argument(
        "-o",
        "--output",
        default=defaults.get("output"),
        help="Output directory (default: ~/Themes/<ThemeName>)",
    )

    actions = parser.add_argument_group("Actions")
    actions.add_argument(
        "--apply",
        action=argparse.BooleanOptionalAction,
        default=bool(defaults.get("apply", False)),
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
    special.add_argument(
        "--apply-existing",
        metavar="THEME_DIR",
        help="Apply a theme directory previously generated by Theme Maker",
    )

    actions.add_argument(
        "--dry-run",
        action="store_true",
        help="Report detected targets and planned changes without writing anything",
    )
    actions.add_argument(
        "--config",
        metavar="PRESET.toml",
        help="Load options from a reusable TOML preset",
    )
    actions.add_argument(
        "--save-config",
        metavar="PRESET.toml",
        help="Save the resolved options as a reusable TOML preset",
    )
    actions.add_argument(
        "--components",
        type=_components,
        default=defaults.get("components"),
        metavar="LIST",
        help="Comma-separated components to apply (for example gtk,browsers,icons)",
    )
    actions.add_argument(
        "--terminal-opacity",
        type=_opacity,
        default=defaults.get("terminal_opacity"),
        metavar="VALUE",
        help="Ptyxis opacity from 0.10 to 1.00",
    )

    actions.add_argument(
        "--watch-interval",
        type=_positive_int,
        default=5,
        metavar="SECONDS",
        help="Wallpaper watcher poll interval in seconds",
    )
    interaction = actions.add_mutually_exclusive_group()
    interaction.add_argument(
        "-y",
        "--yes",
        "--no-interactive",
        dest="no_interactive",
        action="store_true",
        help="Skip prompts and use defaults",
    )
    interaction.add_argument(
        "--interactive",
        dest="no_interactive",
        action="store_false",
        help="Enable prompts, overriding a non-interactive preset",
    )
    parser.set_defaults(no_interactive=bool(defaults.get("no_interactive", False)))
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


def _write_theme_manifest(
    output_dir: Path,
    palette: dict,
    name: str,
    wallpaper: str,
    components: list[str] | None,
) -> None:
    """Write application metadata used by --apply-existing."""
    manifest = {
        "format_version": 1,
        "generator": "theme-maker-gnome",
        "generator_version": __version__,
        "name": name,
        "wallpaper": wallpaper,
        "mode": palette.get("mode", "dark"),
        "components": components or list(_COMPONENT_LABELS),
        "palette": palette,
    }
    (output_dir / "theme-maker.json").write_text(json.dumps(manifest, indent=2))


def _legacy_theme_metadata(output_dir: Path) -> dict:
    """Reconstruct essential metadata from themes generated before manifests."""
    name = output_dir.name
    index_theme = output_dir / "gtk-theme" / "index.theme"
    if index_theme.exists():
        try:
            import configparser

            parser = configparser.ConfigParser()
            parser.read(index_theme)
            name = parser.get("Desktop Entry", "Name", fallback=name)
        except (configparser.Error, OSError):
            pass

    colors = {}
    color_files = list((output_dir / "terminal" / "pywal").glob("colors.json"))
    if color_files:
        try:
            colors = json.loads(color_files[0].read_text())
        except (json.JSONDecodeError, OSError):
            pass
    special = colors.get("special", {}) if isinstance(colors, dict) else {}
    ansi = colors.get("colors", {}) if isinstance(colors, dict) else {}
    wallpaper = colors.get("wallpaper", "") if isinstance(colors, dict) else ""

    mode = "dark"
    gtk_settings = output_dir / "gtk-config" / "gtk3-settings.ini"
    if gtk_settings.exists():
        try:
            if "gtk-application-prefer-dark-theme=false" in gtk_settings.read_text():
                mode = "light"
        except OSError:
            pass
    accent = special.get("cursor") or ansi.get("color1") or "#c41e3a"
    palette = {
        "mode": mode,
        "wallpaper": wallpaper,
        "accent": accent,
        "accent_light": ansi.get("color9", accent),
        "bg_deepest": special.get("background", "#050505"),
    }
    return {
        "format_version": 0,
        "name": name,
        "wallpaper": wallpaper,
        "mode": mode,
        "components": list(_COMPONENT_LABELS),
        "palette": palette,
    }


def _load_existing_theme(output_dir: Path) -> dict:
    """Load a generated theme manifest, with legacy folder compatibility."""
    output_dir = output_dir.expanduser().resolve()
    if not output_dir.is_dir():
        raise ValueError(f"theme directory not found: {output_dir}")
    manifest_path = output_dir / "theme-maker.json"
    if manifest_path.exists():
        try:
            metadata = json.loads(manifest_path.read_text())
        except (json.JSONDecodeError, OSError) as exc:
            raise ValueError(f"invalid theme manifest: {exc}") from exc
        if not isinstance(metadata, dict) or not isinstance(metadata.get("palette"), dict):
            raise ValueError("theme-maker.json is missing palette metadata")
    else:
        markers = ["gtk-theme", "browsers", "editors", "terminal", "INSTALL.md"]
        if not any((output_dir / marker).exists() for marker in markers):
            raise ValueError("directory does not look like a Theme Maker theme")
        metadata = _legacy_theme_metadata(output_dir)
    metadata["output_dir"] = output_dir
    return metadata


def _dry_run_lines(
    output_dir: Path,
    name: str,
    wallpaper: str,
    components: list[str] | None,
    generating: bool,
    applying: bool,
) -> list[str]:
    """Build a read-only report of targets and planned changes."""
    home = Path.home()
    selected = components or list(_COMPONENT_LABELS)
    lines = [
        f"  Theme: {name}",
        f"  Source: {wallpaper or '(stored theme data)'}",
        f"  Theme directory: {output_dir}",
        f"  Components: {', '.join(selected)}",
        "",
    ]
    if generating:
        lines.append("  Generation dependencies:")
        for command in ("git", "magick", "ctgen", "rsync"):
            state = shutil.which(command) or "MISSING"
            lines.append(f"    {command}: {state}")
        lines.append("")

    lines.append("  Planned changes:")
    if generating:
        lines.append(f"    Generate theme files under {output_dir}")
    if not applying:
        lines.extend(
            [
                "    System apply was not requested; no home-directory or GNOME changes planned",
                "",
                "  Add --apply to preview application targets as well.",
                "  Dry run only: no files or settings were changed.",
            ]
        )
        return lines
    if "gtk" in selected:
        lines.append(f"    GTK: install ~/.themes/{name} and update GTK3/GTK4 config")
    if "gnome" in selected:
        lines.append("    GNOME: set gtk-theme, color-scheme, accent, and wallpaper")
    if "dock" in selected:
        lines.append("    Dash to Dock: update background and running-indicator colors")
    if "terminal" in selected:
        lines.append("    Terminal: install Ptyxis, Starship, Pywal, and Xresources files")
    if "browsers" in selected:
        roots = [
            ("Firefox", home / ".mozilla" / "firefox"),
            (
                "Firefox Flatpak",
                home / ".var/app/org.mozilla.firefox/.mozilla/firefox",
            ),
            ("Firefox Snap", home / "snap/firefox/common/.mozilla/firefox"),
            ("Zen", home / ".zen"),
            ("Zen Flatpak", home / ".var/app/app.zen_browser.zen/.zen"),
        ]
        detected = False
        for label, root in roots:
            profiles = _browser_profiles(root)
            for profile in profiles:
                detected = True
                lines.append(f"    {label}: update profile {profile}")
        for label, root in _chromium_browser_roots(home):
            if root.exists():
                detected = True
                profile_count = sum(
                    1 for preferences in root.glob("*/Preferences") if preferences.is_file()
                )
                lines.append(
                    f"    {label}: refresh active Theme Maker theme locations "
                    f"across {profile_count} profile(s)"
                )
        if not detected:
            lines.append("    Browsers: no supported profiles detected")
    app_targets = {
        "vscode": ("VS Code/VSCodium", [home / ".vscode", home / ".config/Code"]),
        "antigravity": ("Antigravity", [home / ".antigravity", home / ".config/Antigravity"]),
        "opencode": ("OpenCode", [home / ".config/opencode"]),
        "kilo": ("Kilo", [home / ".config/kilo"]),
        "codex": ("Codex", [home / ".codex"]),
        "fastfetch": ("Fastfetch", [home / ".config/fastfetch"]),
    }
    for component, (label, paths) in app_targets.items():
        if component in selected:
            state = "detected" if any(path.exists() for path in paths) else "not detected"
            lines.append(f"    {label}: {state}; generated config will be installed if applicable")
    if "vim" in selected:
        lines.append("    Vim/Neovim: install colorscheme and update init configuration")
    if "icons" in selected:
        lines.append("    Icons: install and activate the generated Papirus-derived theme")
    if "cursors" in selected:
        lines.append("    Cursors: install and activate the generated Xcursor theme")
    restart_targets = []
    if "browsers" in selected:
        restart_targets.append("browsers")
    if {"vscode", "antigravity"} & set(selected):
        restart_targets.append("VS Code-compatible editors")
    if restart_targets:
        lines.extend(["", f"  Restart required: {', '.join(restart_targets)}"])
    lines.extend(["", "  Dry run only: no files or settings were changed."])
    return lines


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
    raw_argv = list(argv) if argv is not None else sys.argv[1:]
    config_probe = argparse.ArgumentParser(add_help=False)
    config_probe.add_argument("--config")
    config_args, _ = config_probe.parse_known_args(raw_argv)
    preset: dict = {}
    if config_args.config:
        try:
            preset = _load_preset(Path(config_args.config).expanduser().resolve())
        except ValueError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 2

    parser = _build_parser(preset)
    args = parser.parse_args(raw_argv)
    if args.dry_run and (args.backup or args.restore is not None or args.doctor or args.watch):
        parser.error("--dry-run is supported for generation/apply and --apply-existing")
    if args.apply_existing and args.save_config:
        parser.error("--save-config is only available while generating a theme")
    if not args.wallpaper and not args.wallpaper_path and preset.get("wallpaper"):
        args.wallpaper_path = preset["wallpaper"]
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

    if args.apply_existing:
        try:
            existing = _load_existing_theme(Path(args.apply_existing))
        except ValueError as exc:
            print(f"  {RED}Error:{RESET} {exc}")
            return 1
        output_dir = existing["output_dir"]
        name = str(existing.get("name") or output_dir.name)
        wallpaper = str(existing.get("wallpaper") or "")
        palette = existing["palette"]
        if args.terminal_opacity is not None:
            palette["terminal_opacity"] = args.terminal_opacity
        selected = args.components or existing.get("components") or list(_COMPONENT_LABELS)
        try:
            selected = _components(selected)
        except argparse.ArgumentTypeError as exc:
            print(f"  {RED}Error:{RESET} invalid stored component list: {exc}")
            return 1

        if args.dry_run:
            print(f"  {BOLD}Existing theme apply preview{RESET}")
            print()
            for line in _dry_run_lines(
                output_dir,
                name,
                wallpaper,
                selected,
                generating=False,
                applying=True,
            ):
                print(line)
            print()
            return 0

        print(f"  {BOLD}Applying existing theme: {name}{RESET}")
        print(f"  {DIM}From {output_dir}{RESET}")
        print()
        backup_dir, backup_logs = create_undo_backup(name)
        print(f"  {DIM}Saved restore point: {backup_dir}{RESET}")
        for line in backup_logs:
            print(f"  {line}")
        logs = apply_theme(
            output_dir,
            name,
            palette,
            wallpaper,
            skip=_component_skips(selected),
        )
        for line in logs:
            print(f"  {line}")
        print()
        if any(line.startswith("[FAIL]") for line in logs):
            print(f"  {RED}{BOLD}Existing theme apply completed with errors.{RESET}")
            return 1
        print(f"  {GREEN}{BOLD}Existing theme applied!{RESET}")
        print(f"  {DIM}Restart open browsers and editors to reload it.{RESET}")
        print()
        return 0

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
    if args.mode in {"dark", "light"}:
        mode = args.mode
    elif interactive:
        mode_input = _prompt_input("Theme mode (dark/light)", "dark").strip().lower()
        mode = "light" if mode_input == "light" else "dark"
    else:
        mode = "dark"

    print(f"  {BOLD}Generating palette from accent {accent} ({mode} mode)...{RESET}")
    palette = generate_palette(accent, wallpaper, mode=mode)
    palette["terminal_opacity"] = args.terminal_opacity or 0.88

    _print_palette_table(palette)
    _print_ansi_strip(palette)

    if interactive:
        if not _prompt_yn("Proceed with this palette?"):
            print(f"  {YELLOW}Aborted.{RESET}")
            return 0

    # ── Step 6: Generate theme files ──────────────────────────────────────
    output = args.output or str(Path.home() / "Themes" / name)
    output_dir = Path(output).expanduser().resolve()

    if args.dry_run:
        print(f"  {BOLD}Theme generation and apply preview{RESET}")
        print()
        for line in _dry_run_lines(
            output_dir,
            name,
            wallpaper,
            args.components,
            generating=True,
            applying=args.apply,
        ):
            print(line)
        if args.save_config:
            print(f"  {DIM}Preset was not saved because dry-run never writes files.{RESET}")
        print()
        return 0

    if args.save_config:
        _save_preset(
            Path(args.save_config),
            args,
            wallpaper,
            mode,
            name,
            accent,
            output_dir,
        )
        print(f"  {GREEN}Saved preset:{RESET} {Path(args.save_config).expanduser()}")
        print()

    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"  {BOLD}Generating theme files...{RESET}")
    _generate_all(output_dir, palette, name, wallpaper)
    _write_theme_manifest(output_dir, palette, name, wallpaper, args.components)

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
        logs = apply_theme(
            output_dir,
            name,
            palette,
            wallpaper,
            skip=_component_skips(args.components),
        )
        for line in logs:
            print(f"  {line}")
        print()
        if any(line.startswith("[FAIL]") for line in logs):
            print(f"  {RED}{BOLD}Theme apply completed with errors.{RESET}")
            return 1
        print(f"  {GREEN}{BOLD}Theme applied!{RESET}")
        print(f"  {DIM}Some changes may require logging out and back in.{RESET}")
        print(
            f"  {DIM}Restart open browsers and editors so they reload generated themes.{RESET}"
        )
    else:
        print(f"  {DIM}Theme files saved to {output_dir}{RESET}")
        print(f"  {DIM}See INSTALL.md for manual installation instructions.{RESET}")
        print(f"  {DIM}Or re-run with --apply to apply system-wide.{RESET}")

    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
