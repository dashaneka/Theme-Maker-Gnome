"""Theme applier - installs and activates the generated theme system-wide."""

import json
import re
import shutil
import subprocess
import zipfile
import tempfile
import configparser
import time
from datetime import datetime
from collections.abc import Callable
from pathlib import Path

from theme_maker.palette import get_gnome_accent_name
from theme_maker.generators.icons import apply_icon_theme
from theme_maker.generators.cursors import apply_cursor_theme


_STATIC_BACKUP_PATHS = [
    Path(".codex/config.toml"),
    Path(".config/gtk-3.0"),
    Path(".config/gtk-4.0"),
    Path(".local/share/org.gnome.Ptyxis/palettes"),
    Path(".config/starship.toml"),
    Path(".cache/wal"),
    Path(".Xresources"),
    Path(".vscode/extensions/extensions.json"),
    Path(".vscodium/extensions/extensions.json"),
    Path(".config/Code/User/settings.json"),
    Path(".config/VSCodium/User/settings.json"),
    Path(".var/app/com.visualstudio.code/config/Code/User/settings.json"),
    Path(".var/app/com.visualstudio.code/data/vscode/extensions/extensions.json"),
    Path(".var/app/com.vscodium.codium/config/VSCodium/User/settings.json"),
    Path(".var/app/com.vscodium.codium/data/vscodium/extensions/extensions.json"),
    Path(".config/Antigravity/User"),
    Path(".antigravity/extensions/extensions.json"),
    Path(".config/opencode/tui.json"),
    Path(".config/opencode/themes"),
    Path(".config/kilo/kilo.jsonc"),
    Path(".config/kilo/themes"),
    Path(".vim"),
    Path(".vimrc"),
    Path(".config/nvim"),
    Path(".config/fastfetch"),
]


def _backup_home_dir() -> Path:
    """Return the root directory used for automatic restore points."""
    return Path.home() / ".local" / "state" / "theme-maker" / "backups"


def _backup_pointer_file() -> Path:
    """Return the file that stores the path to the latest restore point."""
    return Path.home() / ".local" / "state" / "theme-maker" / "last-backup.json"


def parse_jsonc(text: str) -> dict:
    """Parse JSON text that may contain comments and trailing commas."""
    # Remove single line comments
    text = re.sub(r'//.*$', '', text, flags=re.MULTILINE)
    # Remove multi-line comments
    text = re.sub(r'/\*.*?\*/', '', text, flags=re.DOTALL)
    # Remove trailing commas before closing braces/brackets
    text = re.sub(r',\s*([\]}])', r'\1', text)
    return json.loads(text)


def _iter_existing_rel_paths(paths: list[Path]) -> list[Path]:
    """Return unique home-relative paths that currently exist."""
    home = Path.home()
    unique: list[Path] = []
    seen: set[Path] = set()
    for rel_path in paths:
        if rel_path in seen:
            continue
        candidate = home / rel_path
        if candidate.exists() or candidate.is_symlink():
            unique.append(rel_path)
            seen.add(rel_path)
    return unique


def _browser_profiles(root: Path) -> list[Path]:
    """Return browser profiles declared by profiles.ini, with a safe fallback."""
    if not root.exists():
        return []

    profiles: list[Path] = []
    ini_path = root / "profiles.ini"
    if ini_path.exists():
        parser = configparser.ConfigParser()
        try:
            parser.read(ini_path)
            for section in parser.sections():
                if not section.startswith("Profile") or not parser.has_option(section, "Path"):
                    continue
                raw_path = Path(parser.get(section, "Path"))
                profile = root / raw_path if parser.getboolean(
                    section, "IsRelative", fallback=True
                ) else raw_path.expanduser()
                if profile.is_dir() and profile not in profiles:
                    profiles.append(profile)
        except (configparser.Error, OSError, ValueError):
            pass

    if profiles:
        return profiles

    try:
        return [
            child
            for child in root.iterdir()
            if child.is_dir()
            and any((child / marker).exists() for marker in ("prefs.js", "times.json"))
        ]
    except OSError:
        return []


def _detect_profile_paths(root: Path) -> list[Path]:
    """Collect browser profile paths that this tool mutates."""
    home = Path.home()
    rel_paths: list[Path] = []
    for profile_dir in _browser_profiles(root):
        for child in [profile_dir / "chrome", profile_dir / "user.js"]:
            if child.exists() or child.is_symlink():
                try:
                    rel_paths.append(child.relative_to(home))
                except ValueError:
                    pass
    return rel_paths


def _current_theme_backup_paths(settings_data: dict[str, str]) -> list[Path]:
    """Return only the active theme directories that may be overwritten."""
    rel_paths: list[Path] = []
    for key in [
        "org.gnome.desktop.interface.gtk-theme",
        "org.gnome.shell.extensions.user-theme.name",
    ]:
        theme_name = settings_data.get(key, "").strip()
        if theme_name:
            rel_paths.extend(
                [
                    Path(".themes") / theme_name,
                    Path(".local/share/themes") / theme_name,
                ]
            )

    for key in [
        "org.gnome.desktop.interface.icon-theme",
        "org.gnome.desktop.interface.cursor-theme",
    ]:
        theme_name = settings_data.get(key, "").strip()
        if theme_name:
            rel_paths.extend(
                [
                    Path(".icons") / theme_name,
                    Path(".local/share/icons") / theme_name,
                ]
            )

    for root in _gecko_browser_roots():
        rel_paths.extend(_detect_profile_paths(root))
    document_origins = _flatpak_document_origins()
    home = Path.home()
    for _, root in _chromium_browser_roots(home):
        for theme_dir in _active_chromium_theme_dirs(root, document_origins):
            try:
                rel_paths.append(theme_dir.relative_to(home))
            except ValueError:
                pass
    return _iter_existing_rel_paths(rel_paths)


def _gecko_browser_roots() -> list[Path]:
    """Return supported Firefox and Zen profile roots."""
    home = Path.home()
    return [
        home / ".mozilla" / "firefox",
        home / ".var" / "app" / "org.mozilla.firefox" / ".mozilla" / "firefox",
        home / "snap" / "firefox" / "common" / ".mozilla" / "firefox",
        home / ".zen",
        home / ".var" / "app" / "app.zen_browser.zen" / ".zen",
    ]


def _backup_paths_for_restore(
    settings_data: dict[str, str], theme_name: str = ""
) -> list[Path]:
    """Return the minimal set of paths needed for a restore point."""
    paths = (
        _STATIC_BACKUP_PATHS
        + _current_theme_backup_paths(settings_data)
        + _current_codex_theme_backup_paths()
    )
    if theme_name:
        slug = theme_name.lower().replace(" ", "-")
        extension_dir = f"theme-maker.{slug}-theme-1.0.0"
        paths.extend(
            [
                Path(".antigravity/extensions") / extension_dir,
                Path(".vscode/extensions") / extension_dir,
                Path(".vscodium/extensions") / extension_dir,
                Path(".var/app/com.visualstudio.code/data/vscode/extensions")
                / extension_dir,
                Path(".var/app/com.vscodium.codium/data/vscodium/extensions")
                / extension_dir,
            ]
        )
    return _iter_existing_rel_paths(paths)


def _read_codex_theme_name() -> str | None:
    """Return the current Codex TUI theme name from ~/.codex/config.toml."""
    config_path = Path.home() / ".codex" / "config.toml"
    if not config_path.exists():
        return None
    try:
        import tomllib

        data = tomllib.loads(config_path.read_text())
    except (ModuleNotFoundError, OSError, ValueError):
        return None
    tui = data.get("tui")
    if not isinstance(tui, dict):
        return None
    theme = tui.get("theme")
    return theme if isinstance(theme, str) and theme.strip() else None


def _current_codex_theme_backup_paths() -> list[Path]:
    """Back up the active custom Codex theme file if one is selected."""
    theme_name = _read_codex_theme_name()
    if not theme_name:
        return []
    return _iter_existing_rel_paths([Path(".codex/themes") / f"{theme_name}.tmTheme"])


def _fast_copy(src: Path, dst: Path) -> None:
    """Copy directory tree using rsync for speed, falling back to shutil."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        shutil.rmtree(dst)
    rsync = shutil.which("rsync")
    if rsync:
        try:
            subprocess.run(
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
                check=True,
                text=True,
                timeout=30,
            )
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            shutil.copytree(src, dst, symlinks=False)
    else:
        shutil.copytree(src, dst, symlinks=False)


def _run(
    cmd: list[str], check: bool = True, timeout: int = 10
) -> subprocess.CompletedProcess:
    """Run a command, suppressing stdout/stderr unless it fails."""
    return subprocess.run(
        cmd, capture_output=True, text=True, check=check, timeout=timeout
    )


_GSETTINGS_NUMBER = re.compile(r"^-?\d+(\.\d+)?$")


def _to_gsettings_value(value: str) -> str:
    """Convert a plain Python string into a gsettings CLI value literal."""
    if value in {"true", "false"}:
        return value
    if _GSETTINGS_NUMBER.fullmatch(value):
        return value
    if value.startswith("'") and value.endswith("'"):
        return value
    escaped = value.replace("\\", "\\\\").replace("'", "\\'")
    return f"'{escaped}'"


def _gsettings_set(schema: str, key: str, value: str) -> bool:
    """Set a gsettings key. Returns True on success."""
    try:
        _run(["gsettings", "set", schema, key, _to_gsettings_value(value)])
        return True
    except (
        subprocess.CalledProcessError,
        FileNotFoundError,
        subprocess.TimeoutExpired,
    ):
        return False


def _symlink(target: Path, link: Path) -> None:
    """Create a symlink, removing any existing file/link at the destination."""
    link.parent.mkdir(parents=True, exist_ok=True)
    if link.exists() or link.is_symlink():
        link.unlink()
    link.symlink_to(target)


def _copy_file(src: Path, dst: Path) -> None:
    """Copy a single file, creating parent dirs as needed."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def _copy_tree(src: Path, dst: Path) -> None:
    """Copy a directory tree, overwriting destination."""
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)


def _copy_home_path(src: Path, backup_home: Path) -> None:
    """Back up a path from the user's home directory preserving relative layout."""
    home = Path.home()
    if not src.exists() and not src.is_symlink():
        return
    rel = src.relative_to(home)
    dst = backup_home / rel
    if src.is_dir() and not src.is_symlink():
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(src, dst, symlinks=True)
    else:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst, follow_symlinks=False)


def _load_json(path: Path) -> dict:
    """Load JSON from disk, returning an empty dict if missing or invalid."""
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text())
        if isinstance(data, dict):
            return data
    except (json.JSONDecodeError, OSError):
        pass
    return {}


def _write_json(path: Path, data: dict, indent: int = 2) -> None:
    """Write JSON to disk with parent directories created first."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=indent))


def _quote_toml_string(value: str) -> str:
    """Serialize a TOML basic string value."""
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _upsert_toml_table_key(path: Path, table: str, key: str, value: str) -> bool:
    """Set a key inside a TOML table while preserving unrelated content."""
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        content = path.read_text() if path.exists() else ""
    except OSError:
        return False

    header = f"[{table}]"
    rendered = f"{key} = {_quote_toml_string(value)}"
    lines = content.splitlines()

    start = None
    end = len(lines)
    for idx, line in enumerate(lines):
        if line.strip() == header:
            start = idx
            break

    if start is None:
        if lines and lines[-1].strip():
            lines.append("")
        lines.extend([header, rendered])
    else:
        for idx in range(start + 1, len(lines)):
            stripped = lines[idx].strip()
            if stripped.startswith("[") and stripped.endswith("]"):
                end = idx
                break
        replaced = False
        for idx in range(start + 1, end):
            if lines[idx].strip().startswith(f"{key} ="):
                lines[idx] = rendered
                replaced = True
                break
        if not replaced:
            insert_at = end
            while insert_at > start + 1 and not lines[insert_at - 1].strip():
                insert_at -= 1
            lines.insert(insert_at, rendered)

    try:
        path.write_text("\n".join(lines).rstrip() + "\n")
        return True
    except OSError:
        return False


def create_undo_backup(theme_name: str = "") -> tuple[Path, list[str]]:
    """Create a restore point for the current user theme state."""
    log: list[str] = []
    home = Path.home()
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    safe_name = re.sub(r"[^A-Za-z0-9._-]+", "-", theme_name.strip()) or "state"
    backup_dir = _backup_home_dir() / f"{timestamp}-{safe_name}"
    backup_home = backup_dir / "home"
    backup_home.mkdir(parents=True, exist_ok=True)

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

    settings_data: dict[str, str] = {}
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

    backup_paths = _backup_paths_for_restore(settings_data, theme_name)
    for rel_path in backup_paths:
        src = home / rel_path
        if src.exists() or src.is_symlink():
            try:
                _copy_home_path(src, backup_home)
                log.append(f"  Backed up: {src}")
            except (OSError, shutil.Error) as exc:
                log.append(f"  [WARN] Failed to backup {src}: {exc}")

    manifest = {
        "name": theme_name or "Theme Backup",
        "created_at": timestamp,
        "settings": settings_data,
        "paths": [str(path) for path in backup_paths],
    }
    _write_json(backup_dir / "manifest.json", manifest, indent=2)
    _write_json(backup_dir / "settings.json", settings_data, indent=2)
    _write_json(_backup_pointer_file(), {"backup_dir": str(backup_dir)}, indent=2)
    log.append(f"  Saved restore point: {backup_dir}")
    return backup_dir, log


def _resolve_backup_dir(backup_dir: Path | None) -> Path | None:
    """Resolve explicit or last-used backup directories."""
    if backup_dir is not None:
        return backup_dir
    pointer = _backup_pointer_file()
    if pointer.exists():
        try:
            data = json.loads(pointer.read_text())
            candidate = data.get("backup_dir")
            if candidate:
                return Path(candidate)
        except (json.JSONDecodeError, OSError):
            pass
    return None


def _backup_paths_from_manifest(backup_dir: Path) -> list[Path]:
    """Load the relative paths stored for a restore point."""
    manifest = _load_json(backup_dir / "manifest.json")
    raw_paths = manifest.get("paths")
    if not isinstance(raw_paths, list):
        return list(_STATIC_BACKUP_PATHS)
    paths: list[Path] = []
    for raw_path in raw_paths:
        if isinstance(raw_path, str) and raw_path:
            paths.append(Path(raw_path))
    return paths or list(_STATIC_BACKUP_PATHS)


def restore_theme(backup_dir: Path | None = None) -> list[str]:
    """Restore a saved theme state."""
    log: list[str] = []
    resolved = _resolve_backup_dir(backup_dir)
    if resolved is None or not resolved.exists():
        return ["  [FAIL] No restore point found"]

    home = Path.home()
    backup_home = resolved / "home"

    settings_file = resolved / "settings.json"
    settings_data = _load_json(settings_file)
    for full_key, value in settings_data.items():
        if "." not in full_key:
            continue
        schema, key = full_key.rsplit(".", 1)
        if _gsettings_set(schema, key, value):
            log.append(f"  Restored {schema} {key} = {value}")
        else:
            log.append(f"  [WARN] Could not restore {schema} {key}")

    if backup_home.exists():
        for rel_path in _backup_paths_from_manifest(resolved):
            src = backup_home / rel_path
            dst = home / rel_path
            if not src.exists() and not src.is_symlink():
                continue
            try:
                if src.is_dir() and not src.is_symlink():
                    if dst.exists() or dst.is_symlink():
                        shutil.rmtree(dst)
                    shutil.copytree(src, dst, symlinks=True)
                else:
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    if dst.exists() or dst.is_symlink():
                        dst.unlink()
                    shutil.copy2(src, dst, follow_symlinks=False)
                log.append(f"  Restored {dst}")
            except OSError as exc:
                log.append(f"  [WARN] Failed to restore {dst}: {exc}")
        log.append(f"  Restored files from {backup_home}")
    else:
        # Legacy backup format support.
        legacy_map = {
            "gtk3-settings.ini": home / ".config" / "gtk-3.0" / "settings.ini",
            "gtk4-settings.ini": home / ".config" / "gtk-4.0" / "settings.ini",
            "gtk3.css": home / ".config" / "gtk-3.0" / "gtk.css",
            "gtk4.css": home / ".config" / "gtk-4.0" / "gtk.css",
        }
        for name, dst in legacy_map.items():
            src = resolved / name
            if src.exists():
                _copy_file(src, dst)
                log.append(f"  Restored {dst}")

        for legacy_dir, dst in [("themes", home / ".themes"), ("icons", home / ".icons")]:
            src = resolved / legacy_dir
            if src.exists():
                _fast_copy(src, dst)
                log.append(f"  Restored {dst}")

    return log


def _inject_vim_colorscheme(block_path: Path, theme_name: str, slug: str) -> bool:
    """Ensure a Vimscript config loads the generated colorscheme."""
    lines: list[str] = []
    if block_path.exists():
        try:
            lines = block_path.read_text().splitlines()
        except OSError:
            return False

    start = f'" Theme Maker for GNOME: start {theme_name}'
    end = f'" Theme Maker for GNOME: end {theme_name}'
    block = [
        start,
        f"if filereadable(expand('~/.vim/colors/{slug}.vim'))",
        f"  colorscheme {slug}",
        "endif",
        f"command! ThemeMakerReload if filereadable(expand('~/.vim/colors/{slug}.vim')) | colorscheme {slug} | endif",
        end,
    ]

    if any(line == start for line in lines) and any(line == end for line in lines):
        # Replace the existing managed block in place.
        new_lines: list[str] = []
        inside = False
        for line in lines:
            if line == start:
                inside = True
                new_lines.extend(block)
                continue
            if inside and line == end:
                inside = False
                continue
            if not inside:
                new_lines.append(line)
        lines = new_lines
    else:
        if lines and lines[-1].strip():
            lines.append("")
        lines.extend(block)

    try:
        block_path.write_text("\n".join(lines) + "\n")
        return True
    except OSError:
        return False


def _inject_lua_colorscheme(block_path: Path, theme_name: str, slug: str) -> bool:
    """Ensure a Neovim Lua config loads the generated colorscheme."""
    lines: list[str] = []
    if block_path.exists():
        try:
            lines = block_path.read_text().splitlines()
        except OSError:
            return False

    start = f"-- Theme Maker for GNOME: start {theme_name}"
    end = f"-- Theme Maker for GNOME: end {theme_name}"
    block = [
        start,
        f"vim.api.nvim_create_user_command('ThemeMakerReload', function()",
        f"  pcall(vim.cmd.colorscheme, '{slug}')",
        "end, {})",
        f"pcall(vim.cmd.colorscheme, '{slug}')",
        end,
    ]

    if any(line == start for line in lines) and any(line == end for line in lines):
        new_lines: list[str] = []
        inside = False
        for line in lines:
            if line == start:
                inside = True
                new_lines.extend(block)
                continue
            if inside and line == end:
                inside = False
                continue
            if not inside:
                new_lines.append(line)
        lines = new_lines
    else:
        if lines and lines[-1].strip():
            lines.append("")
        lines.extend(block)

    try:
        block_path.write_text("\n".join(lines) + "\n")
        return True
    except OSError:
        return False


def apply_gtk_theme(output_dir: Path, name: str) -> list[str]:
    """Install GTK3/GTK4/GNOME Shell theme to ~/.themes and create symlinks."""
    log: list[str] = []
    home = Path.home()
    theme_root = home / ".themes" / name

    # Create theme directory structure
    for subdir in ["gtk-3.0", "gtk-4.0", "gnome-shell"]:
        (theme_root / subdir).mkdir(parents=True, exist_ok=True)

    # Copy GTK3 CSS
    gtk3_src = output_dir / "gtk-theme" / "gtk3.css"
    if gtk3_src.exists():
        _copy_file(gtk3_src, theme_root / "gtk-3.0" / "gtk.css")
        log.append(f"  Installed GTK3 theme to {theme_root / 'gtk-3.0'}")

    # Copy GTK4 CSS
    gtk4_src = output_dir / "gtk-theme" / "gtk4.css"
    if gtk4_src.exists():
        _copy_file(gtk4_src, theme_root / "gtk-4.0" / "gtk.css")
        log.append(f"  Installed GTK4 theme to {theme_root / 'gtk-4.0'}")

    # Copy index.theme
    idx_src = output_dir / "gtk-theme" / "index.theme"
    if idx_src.exists():
        _copy_file(idx_src, theme_root / "index.theme")

    # Copy GNOME Shell CSS
    shell_src = output_dir / "gnome-shell" / "gnome-shell.css"
    if shell_src.exists():
        _copy_file(shell_src, theme_root / "gnome-shell" / "gnome-shell.css")
        log.append(f"  Installed GNOME Shell theme")

    # Create symlinks for GTK3/GTK4 config
    gtk3_config = home / ".config" / "gtk-3.0"
    gtk4_config = home / ".config" / "gtk-4.0"
    gtk3_config.mkdir(parents=True, exist_ok=True)
    gtk4_config.mkdir(parents=True, exist_ok=True)

    _symlink(theme_root / "gtk-3.0" / "gtk.css", gtk3_config / "gtk.css")
    _symlink(theme_root / "gtk-4.0" / "gtk.css", gtk4_config / "gtk.css")
    log.append(f"  Symlinked ~/.config/gtk-3.0/gtk.css")
    log.append(f"  Symlinked ~/.config/gtk-4.0/gtk.css")

    # Copy GTK settings.ini files
    gtk3_settings = output_dir / "gtk-config" / "gtk3-settings.ini"
    if gtk3_settings.exists():
        _copy_file(gtk3_settings, gtk3_config / "settings.ini")

    gtk4_settings = output_dir / "gtk-config" / "gtk4-settings.ini"
    if gtk4_settings.exists():
        _copy_file(gtk4_settings, gtk4_config / "settings.ini")

    return log


def apply_gnome_settings(name: str, accent_hex: str, wallpaper: str, mode: str = "dark") -> list[str]:
    """Apply GNOME desktop settings via gsettings."""
    log: list[str] = []
    accent_name = get_gnome_accent_name(accent_hex)
    color_scheme = "prefer-dark" if mode == "dark" else "prefer-light"

    settings = [
        ("org.gnome.desktop.interface", "gtk-theme", name),
        ("org.gnome.desktop.interface", "color-scheme", color_scheme),
        ("org.gnome.desktop.interface", "accent-color", accent_name),
        ("org.gnome.shell.extensions.user-theme", "name", name),
    ]

    # Set wallpaper if provided
    if wallpaper:
        wp_uri = wallpaper if wallpaper.startswith("file://") else f"file://{wallpaper}"
        settings.append(("org.gnome.desktop.background", "picture-uri-dark", wp_uri))
        settings.append(("org.gnome.desktop.background", "picture-uri", wp_uri))

    for schema, key, value in settings:
        if _gsettings_set(schema, key, value):
            log.append(f"  Set {schema} {key} = {value}")
        else:
            log.append(f"  [SKIP] Could not set {schema} {key}")

    return log


def apply_dash_to_dock(p: dict) -> list[str]:
    """Configure Dash to Dock extension colors."""
    log: list[str] = []
    schema = "org.gnome.shell.extensions.dash-to-dock"

    settings = [
        ("custom-background-color", "true"),
        ("background-color", p["bg_deepest"]),
        ("background-opacity", "0.6"),
        ("transparency-mode", "FIXED"),
        ("custom-theme-shrink", "true"),
        ("custom-theme-customize-running-dots", "true"),
        ("custom-theme-running-dots-color", p["accent"]),
        ("custom-theme-running-dots-border-color", p["accent_light"]),
        ("custom-theme-running-dots-border-width", "0"),
        ("running-indicator-style", "DOTS"),
    ]

    for key, value in settings:
        _gsettings_set(schema, key, value)

    log.append("  Configured Dash to Dock colors")
    return log


def apply_terminal(
    output_dir: Path, name: str, opacity: float = 0.88
) -> list[str]:
    """Install Ptyxis palette, Starship config, Pywal files, Xresources."""
    log: list[str] = []
    home = Path.home()
    slug = name.lower().replace(" ", "-")

    # Ptyxis palette
    ptyxis_src = output_dir / "terminal" / "ptyxis" / f"{slug}.palette"
    if ptyxis_src.exists():
        # Native path
        ptyxis_dst = home / ".local" / "share" / "org.gnome.Ptyxis" / "palettes"
        ptyxis_dst.mkdir(parents=True, exist_ok=True)
        _copy_file(ptyxis_src, ptyxis_dst / f"{slug}.palette")
        
        # Flatpak path
        ptyxis_flatpak_dst = home / ".var" / "app" / "app.devsuite.Ptyxis" / "data" / "ptyxis" / "palettes"
        if ptyxis_flatpak_dst.parent.exists():
            ptyxis_flatpak_dst.mkdir(parents=True, exist_ok=True)
            _copy_file(ptyxis_src, ptyxis_flatpak_dst / f"{slug}.palette")

        log.append(f"  Installed Ptyxis palette: {slug}.palette")

        # Programmatically apply the palette to the default profile and configure opacity/scrollbars
        try:
            res = subprocess.run(
                ["gsettings", "get", "org.gnome.Ptyxis", "default-profile-uuid"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if res.returncode == 0:
                uuid = res.stdout.strip().strip("'")
                if uuid:
                    path = f"org.gnome.Ptyxis.Profile:/org/gnome/Ptyxis/Profiles/{uuid}/"
                    _gsettings_set(path, "palette", name)
                    _gsettings_set(path, "opacity", f"{opacity:.2f}")
                    _gsettings_set("org.gnome.Ptyxis", "scrollbar-policy", "never")
                    log.append(
                        f"  Applied Ptyxis palette '{name}', set opacity to "
                        f"{opacity:.2f}, and hid scrollbar"
                    )
        except Exception as e:
            log.append(f"  [WARN] Failed to configure Ptyxis profile via gsettings: {e}")

    # Starship
    star_src = output_dir / "terminal" / "starship" / "starship.toml"
    if star_src.exists():
        _copy_file(star_src, home / ".config" / "starship.toml")
        log.append("  Installed starship.toml")

    # Pywal
    pywal_src = output_dir / "terminal" / "pywal"
    if pywal_src.exists():
        wal_dst = home / ".cache" / "wal"
        wal_dst.mkdir(parents=True, exist_ok=True)
        for f in pywal_src.iterdir():
            if f.is_file():
                _copy_file(f, wal_dst / f.name)
        log.append("  Installed pywal color files to ~/.cache/wal/")

    # Xresources
    xres_src = output_dir / "terminal" / "Xresources"
    if xres_src.exists():
        _copy_file(xres_src, home / ".Xresources")
        # Try to merge
        try:
            _run(["xrdb", "-merge", str(home / ".Xresources")], check=False, timeout=5)
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        log.append("  Installed ~/.Xresources")

    return log


_THEME_MAKER_USER_PREF = (
    'user_pref("toolkit.legacyUserProfileCustomizations.stylesheets", true);'
)


def _enable_gecko_user_chrome(user_js: Path) -> None:
    """Enable userChrome.css without overwriting unrelated user.js preferences."""
    content = user_js.read_text() if user_js.exists() else ""
    pattern = re.compile(
        r'^\s*user_pref\("toolkit\.legacyUserProfileCustomizations\.stylesheets"'
        r"\s*,\s*(?:true|false)\s*\);\s*$",
        re.MULTILINE,
    )
    if pattern.search(content):
        content = pattern.sub(_THEME_MAKER_USER_PREF, content)
    else:
        content = content.rstrip() + ("\n" if content.strip() else "") + _THEME_MAKER_USER_PREF
    user_js.write_text(content.rstrip() + "\n")


def _install_gecko_theme(src: Path, root: Path, label: str) -> list[str]:
    """Install generated CSS into every declared profile under a Gecko root."""
    log: list[str] = []
    if not src.exists():
        return log
    for profile_dir in _browser_profiles(root):
        try:
            chrome_dir = profile_dir / "chrome"
            chrome_dir.mkdir(parents=True, exist_ok=True)
            for filename in ("userChrome.css", "userContent.css"):
                generated = src / filename
                if generated.exists():
                    _copy_file(generated, chrome_dir / filename)
            _enable_gecko_user_chrome(profile_dir / "user.js")
            log.append(f"  Installed {label} theme to {profile_dir.name}")
        except OSError as exc:
            log.append(f"  [WARN] Could not theme {label} profile {profile_dir}: {exc}")
    return log


def _is_theme_maker_chromium_theme(theme_dir: Path) -> bool:
    manifest = _load_json(theme_dir / "manifest.json")
    description = manifest.get("description", "")
    return isinstance(description, str) and "Theme Maker" in description


def _chromium_browser_roots(home: Path | None = None) -> list[tuple[str, Path]]:
    """Return supported Chromium-family native and sandbox profile roots."""
    home = home or Path.home()
    return [
        ("Chrome", home / ".config" / "google-chrome"),
        ("Chromium", home / ".config" / "chromium"),
        ("Brave", home / ".config" / "BraveSoftware" / "Brave-Browser"),
        (
            "Brave Flatpak",
            home
            / ".var"
            / "app"
            / "com.brave.Browser"
            / "config"
            / "BraveSoftware"
            / "Brave-Browser",
        ),
        ("Helium", home / ".config" / "net.imput.helium"),
        (
            "Helium Flatpak",
            home / ".var" / "app" / "net.imput.helium" / "config" / "net.imput.helium",
        ),
        ("Edge", home / ".config" / "microsoft-edge"),
    ]


def _flatpak_document_origins() -> dict[str, Path]:
    """Map Flatpak document portal IDs to their writable host paths."""
    try:
        result = _run(
            ["flatpak", "documents", "--columns=id,origin"], timeout=5
        )
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        return {}
    origins: dict[str, Path] = {}
    for line in result.stdout.splitlines():
        doc_id, separator, origin = line.partition("\t")
        if separator and doc_id and origin:
            origins[doc_id] = Path(origin).expanduser()
    return origins


def _resolve_flatpak_theme_path(
    theme_dir: Path, document_origins: dict[str, Path]
) -> Path:
    """Translate a sandbox /run/*/doc/<id> path to its host origin."""
    parts = theme_dir.parts
    try:
        doc_index = parts.index("doc")
        doc_id = parts[doc_index + 1]
    except (ValueError, IndexError):
        return theme_dir
    return document_origins.get(doc_id, theme_dir)


def _active_chromium_theme_dirs(
    browser_root: Path, document_origins: dict[str, Path] | None = None
) -> list[Path]:
    """Return active Theme Maker directories used by profiles in a browser root."""
    found: list[Path] = []
    if not browser_root.exists():
        return found
    origins = document_origins if document_origins is not None else _flatpak_document_origins()
    try:
        profile_dirs = [p for p in browser_root.iterdir() if p.is_dir()]
    except OSError:
        return found
    for profile in profile_dirs:
        preferences = _load_json(profile / "Preferences")
        theme = preferences.get("extensions", {}).get("theme", {})
        pack = theme.get("pack") if isinstance(theme, dict) else None
        if not isinstance(pack, str):
            continue
        theme_dir = _resolve_flatpak_theme_path(Path(pack).expanduser(), origins)
        if theme_dir not in found and _is_theme_maker_chromium_theme(theme_dir):
            found.append(theme_dir)
    return found


def _update_active_chromium_themes(
    src: Path,
    browser_root: Path,
    document_origins: dict[str, Path] | None = None,
    updated: set[Path] | None = None,
) -> int:
    """Refresh active Theme Maker unpacked themes without modifying Preferences."""
    updated = updated if updated is not None else set()
    initial_count = len(updated)
    if not browser_root.exists():
        return 0
    for theme_dir in _active_chromium_theme_dirs(browser_root, document_origins):
        if theme_dir in updated:
            continue
        try:
            if theme_dir.resolve() == src.resolve():
                updated.add(theme_dir)
                continue
        except OSError:
            pass
        _copy_tree(src, theme_dir)
        updated.add(theme_dir)
    return len(updated) - initial_count


def apply_browsers(output_dir: Path, name: str) -> list[str]:
    """Install browser themes across native, Flatpak, and Snap profiles."""
    log: list[str] = []
    home = Path.home()
    firefox_src = output_dir / "browsers" / "firefox"
    zen_src = output_dir / "browsers" / "zen"

    gecko_roots = [
        (home / ".mozilla" / "firefox", firefox_src, "Firefox"),
        (
            home / ".var" / "app" / "org.mozilla.firefox" / ".mozilla" / "firefox",
            firefox_src,
            "Firefox Flatpak",
        ),
        (
            home / "snap" / "firefox" / "common" / ".mozilla" / "firefox",
            firefox_src,
            "Firefox Snap",
        ),
        (home / ".zen", zen_src, "Zen Browser"),
        (
            home / ".var" / "app" / "app.zen_browser.zen" / ".zen",
            zen_src,
            "Zen Browser Flatpak",
        ),
    ]
    for root, src, label in gecko_roots:
        log.extend(_install_gecko_theme(src, root, label))

    chromium_src = output_dir / "browsers" / "chrome"
    if chromium_src.exists():
        # Keep one stable location. Once loaded unpacked a single time, every
        # future generated theme updates automatically on browser restart.
        stable_dir = home / ".local" / "share" / "theme-maker" / "browser-theme"
        _copy_tree(chromium_src, stable_dir)
        updated = 0
        updated_dirs: set[Path] = set()
        document_origins = _flatpak_document_origins()
        for _, browser_root in _chromium_browser_roots(home):
            updated += _update_active_chromium_themes(
                chromium_src, browser_root, document_origins, updated_dirs
            )
        brave_flatpak_stable = (
            home
            / ".var"
            / "app"
            / "com.brave.Browser"
            / "config"
            / "theme-maker"
            / "browser-theme"
        )
        if brave_flatpak_stable.parents[2].exists():
            _copy_tree(chromium_src, brave_flatpak_stable)
            log.append(
                f"  Installed Brave Flatpak theme copy to {brave_flatpak_stable}"
            )
        log.append(f"  Installed Chromium-family theme to {stable_dir}")
        if updated:
            log.append(
                f"  Updated {updated} active Chromium-family theme location(s); restart the browser"
            )
        else:
            log.append(
                "  One-time setup: load that folder unpacked in chrome://extensions; future applies update it"
            )

    return log


def _register_vscode_extension(
    ext_root: Path, ext_dir: Path, extension_id: str, version: str = "1.0.0"
) -> None:
    """Add a directly copied extension to a VS Code-compatible registry."""
    registry_file = ext_root / "extensions.json"
    registry: list[dict] = []
    if registry_file.exists():
        try:
            loaded = json.loads(registry_file.read_text())
            if isinstance(loaded, list):
                registry = [entry for entry in loaded if isinstance(entry, dict)]
        except (json.JSONDecodeError, OSError):
            pass
    registry = [
        entry
        for entry in registry
        if entry.get("identifier", {}).get("id") != extension_id
    ]
    registry.append(
        {
            "identifier": {"id": extension_id},
            "version": version,
            "location": {"$mid": 1, "path": str(ext_dir), "scheme": "file"},
            "relativeLocation": ext_dir.name,
            "metadata": {
                "installedTimestamp": int(time.time() * 1000),
                "pinned": True,
                "source": "vsix",
            },
        }
    )
    _write_json(registry_file, registry)


def apply_vscode(output_dir: Path, name: str) -> list[str]:
    """Install VS Code/VSCodium theme extensions and configure settings."""
    log: list[str] = []
    slug = name.lower().replace(" ", "-")
    home = Path.home()

    vsc_src = output_dir / "editors" / "vscode"
    if not vsc_src.exists():
        return log

    # Define all paths for native/Flatpak versions of VS Code & VSCodium
    configs = [
        (
            "VS Code (Native)",
            home / ".vscode" / "extensions",
            home / ".config" / "Code" / "User"
        ),
        (
            "VS Code (Flatpak)",
            home / ".var" / "app" / "com.visualstudio.code" / "data" / "vscode" / "extensions",
            home / ".var" / "app" / "com.visualstudio.code" / "config" / "Code" / "User"
        ),
        (
            "VSCodium (Native)",
            home / ".vscodium" / "extensions",
            home / ".config" / "VSCodium" / "User"
        ),
        (
            "VSCodium (Flatpak)",
            home / ".var" / "app" / "com.vscodium.codium" / "data" / "vscodium" / "extensions",
            home / ".var" / "app" / "com.vscodium.codium" / "config" / "VSCodium" / "User"
        ),
    ]

    for label, ext_root, settings_dir in configs:
        if settings_dir.parent.exists() or ext_root.parent.exists():
            try:
                # 1. Install Extension
                ext_dir = ext_root / f"theme-maker.{slug}-theme-1.0.0"
                if ext_dir.exists():
                    shutil.rmtree(ext_dir)
                ext_dir.mkdir(parents=True, exist_ok=True)
                (ext_dir / "themes").mkdir(exist_ok=True)

                pkg = vsc_src / "package.json"
                if pkg.exists():
                    _copy_file(pkg, ext_dir / "package.json")

                themes_src = vsc_src / "themes"
                if themes_src.exists():
                    for f in themes_src.iterdir():
                        _copy_file(f, ext_dir / "themes" / f.name)

                _register_vscode_extension(
                    ext_root, ext_dir, f"theme-maker.{slug}-theme"
                )

                log.append(f"  Installed {label} extension: theme-maker.{slug}-theme-1.0.0")

                # 2. Update Settings
                settings_src = vsc_src / "settings.json"
                if settings_src.exists():
                    settings_dir.mkdir(parents=True, exist_ok=True)
                    target = settings_dir / "settings.json"
                    existing = {}
                    if target.exists():
                        try:
                            existing = parse_jsonc(target.read_text())
                        except Exception:
                            pass
                    try:
                        new_settings = parse_jsonc(settings_src.read_text())
                        existing.update(new_settings)
                        target.write_text(json.dumps(existing, indent=4))
                        log.append(f"  Updated {label} settings with theme: {name}")
                    except Exception as e:
                        log.append(f"  [WARN] Failed to write settings to {target}: {e}")
            except Exception as e:
                log.append(f"  [WARN] Failed to apply to {label}: {e}")

    return log


def apply_antigravity(output_dir: Path, name: str) -> list[str]:
    """Install Antigravity theme extension by copying directly to extensions dir."""
    log: list[str] = []
    slug = name.lower().replace(" ", "-")

    ag_src = output_dir / "editors" / "antigravity"
    if not ag_src.exists():
        return log

    # Antigravity stores extensions at ~/.antigravity/extensions/
    home = Path.home()
    ext_root = home / ".antigravity" / "extensions"
    ext_root.mkdir(parents=True, exist_ok=True)

    ext_dir = ext_root / f"theme-maker.{slug}-theme-1.0.0"
    if ext_dir.exists():
        shutil.rmtree(ext_dir)
    ext_dir.mkdir(parents=True)

    # Copy package.json
    pkg = ag_src / "package.json"
    if pkg.exists():
        _copy_file(pkg, ext_dir / "package.json")

    # Copy theme files
    themes_src = ag_src / "themes"
    if themes_src.exists():
        themes_dst = ext_dir / "themes"
        themes_dst.mkdir(parents=True, exist_ok=True)
        for f in themes_src.iterdir():
            if f.is_file():
                _copy_file(f, themes_dst / f.name)

    # Register the copied extension. Antigravity/VS Code normally writes this
    # registry during VSIX installation; a directory copy alone is not reliably
    # discovered, which is why older generated themes appeared in settings but
    # did not actually load.
    extension_id = f"theme-maker.{slug}-theme"
    _register_vscode_extension(ext_root, ext_dir, extension_id)

    # Set the theme in Antigravity settings
    settings_file = home / ".config" / "Antigravity" / "User" / "settings.json"
    settings_data = {}
    if settings_file.exists():
        try:
            settings_data = parse_jsonc(settings_file.read_text())
        except Exception:
            pass

    # Get display name from package.json
    display_name = name
    if pkg.exists():
        try:
            pkg_data = parse_jsonc(pkg.read_text())
            themes = pkg_data.get("contributes", {}).get("themes", [])
            if themes and isinstance(themes[0], dict):
                display_name = themes[0].get("label", name)
            else:
                display_name = pkg_data.get("displayName", name)
        except Exception:
            pass

    settings_data["workbench.colorTheme"] = display_name
    settings_file.parent.mkdir(parents=True, exist_ok=True)
    settings_file.write_text(json.dumps(settings_data, indent=4))

    log.append(f"  Installed Antigravity theme: theme-maker.{slug}-theme-1.0.0")
    log.append("  Registered Antigravity extension in extensions.json")
    log.append(f"  Set Antigravity color theme to: {display_name}")
    log.append("  Restart Antigravity to load the new extension")

    return log


def apply_opencode(output_dir: Path, name: str) -> list[str]:
    """Install OpenCode theme and activate it via tui.json."""
    log: list[str] = []
    slug = name.lower().replace(" ", "").replace("-", "")
    home = Path.home()

    oc_src = output_dir / "editors" / "opencode"
    if not oc_src.exists():
        return log

    oc_themes = home / ".config" / "opencode" / "themes"
    oc_themes.mkdir(parents=True, exist_ok=True)

    theme_file = oc_src / f"{slug}.json"
    if theme_file.exists():
        _copy_file(theme_file, oc_themes / f"{slug}.json")
        log.append(f"  Installed OpenCode theme: {slug}")

    # OpenCode reads the active theme from tui.json, not opencode.json
    tui_config = home / ".config" / "opencode" / "tui.json"
    tui_data = _load_json(tui_config)   # keep existing keys
    tui_data["theme"] = slug            # overwrite only the theme key
    _write_json(tui_config, tui_data)
    log.append(f"  Set OpenCode theme to: {slug} (in tui.json)")

    return log


def apply_kilo(output_dir: Path, name: str) -> list[str]:
    """Install Kilo Code theme and activate it via kilo.jsonc."""
    log: list[str] = []
    slug = name.lower().replace(" ", "").replace("-", "")
    home = Path.home()

    kilo_src = output_dir / "editors" / "kilo"
    if not kilo_src.exists():
        return log

    kilo_themes = home / ".config" / "kilo" / "themes"
    kilo_themes.mkdir(parents=True, exist_ok=True)

    theme_file = kilo_src / f"{slug}.json"
    if theme_file.exists():
        _copy_file(theme_file, kilo_themes / f"{slug}.json")
        log.append(f"  Installed Kilo theme: {slug}")

    # Kilo Code reads its active theme from kilo.jsonc (global config)
    kilo_config = home / ".config" / "kilo" / "kilo.jsonc"
    config_data = _load_json(kilo_config)   # keep existing keys
    config_data["theme"] = slug             # overwrite only the theme key
    _write_json(kilo_config, config_data)
    log.append(f"  Set Kilo theme to: {slug} (in kilo.jsonc)")

    return log


def apply_codex(output_dir: Path, name: str) -> list[str]:
    """Install a custom Codex syntax theme and select it in config.toml."""
    log: list[str] = []
    home = Path.home()
    slug = name.lower().replace(" ", "-")

    codex_src = output_dir / "editors" / "codex"
    if not codex_src.exists():
        return log

    theme_src = codex_src / f"{slug}.tmTheme"
    if theme_src.exists():
        theme_dst = home / ".codex" / "themes" / f"{slug}.tmTheme"
        theme_dst.parent.mkdir(parents=True, exist_ok=True)
        _copy_file(theme_src, theme_dst)
        log.append(f"  Installed Codex theme: {slug}")

    config_path = home / ".codex" / "config.toml"
    if _upsert_toml_table_key(config_path, "tui", "theme", slug):
        log.append(f"  Set Codex TUI theme to: {slug}")
    else:
        log.append("  [WARN] Could not update ~/.codex/config.toml")

    return log


def apply_vim(output_dir: Path, name: str) -> list[str]:
    """Install Vim color scheme to ~/.vim/colors/."""
    log: list[str] = []
    home = Path.home()
    slug = name.lower().replace(" ", "_")

    vim_src = output_dir / "editors" / "vim" / "colors" / f"{slug}.vim"
    if not vim_src.exists():
        return log

    # Standard Vim
    vim_colors = home / ".vim" / "colors"
    vim_colors.mkdir(parents=True, exist_ok=True)
    _copy_file(vim_src, vim_colors / f"{slug}.vim")
    log.append(f"  Installed Vim colorscheme: {slug}")
    if _inject_vim_colorscheme(home / ".vimrc", name, slug):
        log.append("  Enabled Vim colorscheme in ~/.vimrc")

    # Neovim
    nvim_colors = home / ".config" / "nvim" / "colors"
    nvim_colors.mkdir(parents=True, exist_ok=True)
    _copy_file(vim_src, nvim_colors / f"{slug}.vim")
    log.append(f"  Installed Neovim colorscheme: {slug}")
    nvim_init_vim = home / ".config" / "nvim" / "init.vim"
    nvim_init_lua = home / ".config" / "nvim" / "init.lua"
    if nvim_init_lua.exists():
        if _inject_lua_colorscheme(nvim_init_lua, name, slug):
            log.append("  Enabled Neovim colorscheme in init.lua")
    else:
        if _inject_vim_colorscheme(nvim_init_vim, name, slug):
            log.append("  Enabled Neovim colorscheme in init.vim")

    return log


def apply_fastfetch(output_dir: Path) -> list[str]:
    """Install fastfetch config."""
    log: list[str] = []
    home = Path.home()

    src = output_dir / "fastfetch" / "config.jsonc"
    if src.exists():
        dst = home / ".config" / "fastfetch" / "config.jsonc"
        dst.parent.mkdir(parents=True, exist_ok=True)
        _copy_file(src, dst)
        
        # Clear fastfetch image cache so chafa logo updates
        cache_dir = home / ".cache" / "fastfetch"
        if cache_dir.exists():
            try:
                shutil.rmtree(cache_dir)
                log.append("  Cleared fastfetch logo cache")
            except OSError:
                pass

        log.append("  Installed fastfetch config")

    return log


def apply_theme(
    output_dir: Path,
    name: str,
    palette: dict,
    wallpaper: str,
    skip: list[str] | None = None,
) -> list[str]:
    """
    Apply the complete theme system-wide.

    Args:
        output_dir: Path to the generated theme folder (e.g. ~/MyTheme)
        name: Theme name
        palette: The generated palette dict
        wallpaper: Absolute path to the wallpaper image
        skip: Optional list of component names to skip

    Returns:
        List of log messages describing what was done.
    """
    skip = skip or []
    all_log: list[str] = []

    steps: list[tuple[str, Callable[[], list[str]]]] = [
        ("GTK Theme", lambda: apply_gtk_theme(output_dir, name)),
        (
            "GNOME Settings",
            lambda: apply_gnome_settings(name, palette["accent"], wallpaper, palette.get("mode", "dark")),
        ),
        ("Dash to Dock", lambda: apply_dash_to_dock(palette)),
        (
            "Terminal",
            lambda: apply_terminal(
                output_dir, name, float(palette.get("terminal_opacity", 0.88))
            ),
        ),
        ("Browsers", lambda: apply_browsers(output_dir, name)),
        ("VS Code", lambda: apply_vscode(output_dir, name)),
        ("Vim", lambda: apply_vim(output_dir, name)),
        ("Antigravity", lambda: apply_antigravity(output_dir, name)),
        ("OpenCode", lambda: apply_opencode(output_dir, name)),
        ("Kilo Code", lambda: apply_kilo(output_dir, name)),
        ("Codex", lambda: apply_codex(output_dir, name)),
        ("Fastfetch", lambda: apply_fastfetch(output_dir)),
        ("Icon Theme", lambda: apply_icon_theme(output_dir, name)),
        ("Cursor Theme", lambda: apply_cursor_theme(output_dir, name)),
    ]

    for label, fn in steps:
        if label.lower().replace(" ", "") in [s.lower().replace(" ", "") for s in skip]:
            all_log.append(f"[SKIP] {label}")
            continue
        try:
            result = fn()
            all_log.append(f"[OK] {label}")
            all_log.extend(result)
        except Exception as e:
            all_log.append(f"[FAIL] {label}: {e}")

    return all_log
