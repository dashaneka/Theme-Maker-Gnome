"""CLI entry point for Theme Maker for GNOME."""

import argparse
import json
import shutil
import subprocess
import sys
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
from theme_maker.applier import apply_theme


# ── ANSI helpers ──────────────────────────────────────────────────────────────

BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
CYAN = "\033[36m"
WHITE = "\033[97m"


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
    """Try to detect the current GNOME wallpaper from gsettings."""
    for key in ["picture-uri-dark", "picture-uri"]:
        try:
            result = subprocess.run(
                ["gsettings", "get", "org.gnome.desktop.background", key],
                capture_output=True,
                text=True,
                check=True,
            )
            uri = result.stdout.strip().strip("'\"")
            if uri.startswith("file://"):
                uri = uri[7:]
            if uri and Path(uri).exists():
                return uri
        except (subprocess.CalledProcessError, FileNotFoundError):
            continue
    return None


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
            )
            value = result.stdout.strip().strip("'\"")
            if value and value != "''":
                settings_data[f"{schema}.{key}"] = value
                log.append(f"  Backed up: {schema}.{key} = {value}")
        except (subprocess.CalledProcessError, FileNotFoundError):
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
    parser = argparse.ArgumentParser(
        prog="theme-maker",
        description="Theme Maker for GNOME - Generate system-wide themes from wallpapers.",
    )
    parser.add_argument(
        "wallpaper",
        nargs="?",
        help="Path to wallpaper image (auto-detects if omitted)",
    )
    parser.add_argument(
        "-n",
        "--name",
        help="Theme name (prompted if omitted)",
    )
    parser.add_argument(
        "-a",
        "--accent",
        help="Override accent color as hex (e.g. #c41e3a)",
    )
    parser.add_argument(
        "-o",
        "--output",
        help="Output directory (default: ~/<ThemeName>)",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply theme system-wide after generating",
    )
    parser.add_argument(
        "--backup",
        action="store_true",
        help="Backup current theme as a reusable template",
    )
    parser.add_argument(
        "--no-interactive",
        action="store_true",
        help="Skip all prompts, use defaults",
    )
    parser.add_argument(
        "-V",
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    args = parser.parse_args(argv)
    interactive = not args.no_interactive

    _print_header()

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
    wallpaper = args.wallpaper

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
    if args.accent:
        accent = args.accent.strip()
        if not accent.startswith("#"):
            accent = "#" + accent
        print(f"  {CYAN}Using provided accent:{RESET} {_color_swatch(accent)} {accent}")
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
                    accent = custom.strip()
                    if not accent.startswith("#"):
                        accent = "#" + accent
                    print(
                        f"  {CYAN}Using custom accent:{RESET} {_color_swatch(accent)} {accent}"
                    )

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
