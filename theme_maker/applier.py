"""Theme applier - installs and activates the generated theme system-wide."""

import json
import shutil
import subprocess
import zipfile
import tempfile
from collections.abc import Callable
from pathlib import Path

from theme_maker.palette import get_gnome_accent_name


def _run(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess:
    """Run a command, suppressing stdout/stderr unless it fails."""
    return subprocess.run(cmd, capture_output=True, text=True, check=check)


def _gsettings_set(schema: str, key: str, value: str) -> bool:
    """Set a gsettings key. Returns True on success."""
    try:
        _run(["gsettings", "set", schema, key, value])
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
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


def apply_gnome_settings(name: str, accent_hex: str, wallpaper: str) -> list[str]:
    """Apply GNOME desktop settings via gsettings."""
    log: list[str] = []
    accent_name = get_gnome_accent_name(accent_hex)

    settings = [
        ("org.gnome.desktop.interface", "gtk-theme", name),
        ("org.gnome.desktop.interface", "color-scheme", "prefer-dark"),
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


def apply_terminal(output_dir: Path, name: str) -> list[str]:
    """Install Ptyxis palette, Starship config, Pywal files, Xresources."""
    log: list[str] = []
    home = Path.home()
    slug = name.lower().replace(" ", "")

    # Ptyxis palette
    ptyxis_src = output_dir / "terminal" / "ptyxis" / f"{slug}.palette"
    if ptyxis_src.exists():
        ptyxis_dst = home / ".local" / "share" / "org.gnome.Ptyxis" / "palettes"
        ptyxis_dst.mkdir(parents=True, exist_ok=True)
        _copy_file(ptyxis_src, ptyxis_dst / f"{slug}.palette")
        log.append(f"  Installed Ptyxis palette: {slug}.palette")

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
            _run(["xrdb", "-merge", str(home / ".Xresources")], check=False)
        except FileNotFoundError:
            pass
        log.append("  Installed ~/.Xresources")

    return log


def apply_browsers(output_dir: Path, name: str) -> list[str]:
    """Copy browser theme files to Firefox, Zen, and Chrome profile dirs."""
    log: list[str] = []
    home = Path.home()

    # Firefox - find profile
    ff_profiles = home / ".mozilla" / "firefox"
    if ff_profiles.exists():
        for profile_dir in ff_profiles.iterdir():
            if profile_dir.is_dir() and ".default-release" in profile_dir.name:
                chrome_dir = profile_dir / "chrome"
                chrome_dir.mkdir(parents=True, exist_ok=True)
                ff_src = output_dir / "browsers" / "firefox"
                if ff_src.exists():
                    for f in ["userChrome.css", "userContent.css"]:
                        src = ff_src / f
                        if src.exists():
                            _copy_file(src, chrome_dir / f)
                    userjs = ff_src / "user.js"
                    if userjs.exists():
                        _copy_file(userjs, profile_dir / "user.js")
                    log.append(f"  Installed Firefox theme to {profile_dir.name}")
                break

    # Zen Browser (Flatpak)
    zen_root = home / ".var" / "app" / "app.zen_browser.zen" / ".zen"
    if zen_root.exists():
        for profile_dir in zen_root.iterdir():
            if profile_dir.is_dir() and "Default" in profile_dir.name:
                chrome_dir = profile_dir / "chrome"
                chrome_dir.mkdir(parents=True, exist_ok=True)
                zen_src = output_dir / "browsers" / "zen"
                if zen_src.exists():
                    for f in ["userChrome.css", "userContent.css"]:
                        src = zen_src / f
                        if src.exists():
                            _copy_file(src, chrome_dir / f)
                    userjs = zen_src / "user.js"
                    if userjs.exists():
                        _copy_file(userjs, profile_dir / "user.js")
                    log.append(f"  Installed Zen Browser theme to {profile_dir.name}")
                break

    # Chrome
    chrome_src = output_dir / "browsers" / "chrome"
    if chrome_src.exists():
        chrome_dst = home / ".config" / "google-chrome" / name
        chrome_dst.mkdir(parents=True, exist_ok=True)
        for f in chrome_src.iterdir():
            if f.is_file():
                _copy_file(f, chrome_dst / f.name)
            elif f.is_dir():
                _copy_tree(f, chrome_dst / f.name)
        log.append(f"  Installed Chrome theme to ~/.config/google-chrome/{name}/")
        log.append("  Load via chrome://extensions > Developer mode > Load unpacked")

    return log


def apply_vscode(output_dir: Path, name: str) -> list[str]:
    """Install VS Code theme extension to Flatpak data directory."""
    log: list[str] = []
    slug = name.lower().replace(" ", "-")
    home = Path.home()

    vsc_src = output_dir / "editors" / "vscode"
    if not vsc_src.exists():
        return log

    # Flatpak VS Code
    vsc_ext_root = (
        home
        / ".var"
        / "app"
        / "com.visualstudio.code"
        / "data"
        / "vscode"
        / "extensions"
    )
    if vsc_ext_root.parent.exists():
        ext_dir = vsc_ext_root / f"{slug}-theme"
        ext_dir.mkdir(parents=True, exist_ok=True)
        (ext_dir / "themes").mkdir(exist_ok=True)

        pkg = vsc_src / "package.json"
        if pkg.exists():
            _copy_file(pkg, ext_dir / "package.json")

        themes_src = vsc_src / "themes"
        if themes_src.exists():
            for f in themes_src.iterdir():
                _copy_file(f, ext_dir / "themes" / f.name)

        log.append(f"  Installed VS Code Flatpak extension: {slug}-theme")

    # Also copy settings.json recommendation
    settings_src = vsc_src / "settings.json"
    vsc_settings_dir = (
        home / ".var" / "app" / "com.visualstudio.code" / "config" / "Code" / "User"
    )
    if settings_src.exists() and vsc_settings_dir.exists():
        # Merge colorTheme into existing settings rather than overwriting
        existing = {}
        target = vsc_settings_dir / "settings.json"
        if target.exists():
            try:
                existing = json.loads(target.read_text())
            except (json.JSONDecodeError, OSError):
                pass
        new_settings = json.loads(settings_src.read_text())
        existing.update(new_settings)
        target.write_text(json.dumps(existing, indent=4))
        log.append(f"  Updated VS Code settings with theme: {name}")

    return log


def apply_antigravity(output_dir: Path, name: str) -> list[str]:
    """Build VSIX and install Antigravity theme extension."""
    log: list[str] = []
    slug = name.lower().replace(" ", "-")

    ag_src = output_dir / "editors" / "antigravity"
    if not ag_src.exists():
        return log

    # Check if antigravity binary exists
    ag_bin = shutil.which("antigravity")
    if not ag_bin:
        log.append("  [SKIP] antigravity not found in PATH")
        return log

    # Build VSIX in a temp directory
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        ext_dir = tmp / "extension"
        ext_themes = ext_dir / "themes"
        ext_themes.mkdir(parents=True)

        # Copy package.json and theme
        pkg = ag_src / "package.json"
        if pkg.exists():
            _copy_file(pkg, ext_dir / "package.json")

        themes_dir = ag_src / "themes"
        if themes_dir.exists():
            for f in themes_dir.iterdir():
                _copy_file(f, ext_themes / f.name)

        # Write [Content_Types].xml
        (tmp / "[Content_Types].xml").write_text(
            '<?xml version="1.0" encoding="utf-8"?>\n'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">\n'
            '  <Default Extension=".json" ContentType="application/json" />\n'
            '  <Default Extension=".vsixmanifest" ContentType="text/xml" />\n'
            "</Types>\n"
        )

        # Write extension.vsixmanifest
        (tmp / "extension.vsixmanifest").write_text(
            '<?xml version="1.0" encoding="utf-8"?>\n'
            '<PackageManifest Version="2.0.0" '
            'xmlns="http://schemas.microsoft.com/developer/vsx-schema/2011">\n'
            "  <Metadata>\n"
            f'    <Identity Language="en-US" Id="{slug}-theme" '
            f'Version="1.0.0" Publisher="theme-maker" />\n'
            f"    <DisplayName>{name}</DisplayName>\n"
            "    <Description>Auto-generated dark theme</Description>\n"
            "    <Categories>Themes</Categories>\n"
            "  </Metadata>\n"
            "  <Installation>"
            '<InstallationTarget Id="Microsoft.VisualStudio.Code" />'
            "</Installation>\n"
            "  <Dependencies />\n"
            "  <Assets>"
            '<Asset Type="Microsoft.VisualStudio.Code.Manifest" '
            'Path="extension/package.json" Addressable="true" />'
            "</Assets>\n"
            "</PackageManifest>\n"
        )

        # Create VSIX (zip)
        vsix_path = tmp / f"{slug}-theme.vsix"
        with zipfile.ZipFile(vsix_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for file in tmp.rglob("*"):
                if file.is_file() and file != vsix_path:
                    zf.write(file, file.relative_to(tmp))

        # Install
        try:
            _run([ag_bin, "--install-extension", str(vsix_path)])
            log.append(f"  Installed Antigravity extension via VSIX")
        except subprocess.CalledProcessError as e:
            log.append(f"  [WARN] Antigravity install failed: {e.stderr[:100]}")

    return log


def apply_opencode(output_dir: Path, name: str) -> list[str]:
    """Install OpenCode theme."""
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

    # Update opencode.json config to select theme
    oc_config = home / ".config" / "opencode" / "opencode.json"
    config_data: dict = {}
    if oc_config.exists():
        try:
            config_data = json.loads(oc_config.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    config_data["theme"] = slug
    oc_config.write_text(json.dumps(config_data, indent=2))
    log.append(f"  Set OpenCode theme to: {slug}")

    return log


def apply_kilo(output_dir: Path, name: str) -> list[str]:
    """Install Kilo Code theme."""
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

    # Update kv.json
    kv_path = home / ".local" / "state" / "kilo" / "kv.json"
    kv_path.parent.mkdir(parents=True, exist_ok=True)
    kv_data: dict = {}
    if kv_path.exists():
        try:
            kv_data = json.loads(kv_path.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    kv_data["theme"] = slug
    kv_path.write_text(json.dumps(kv_data, indent=2))
    log.append(f"  Set Kilo theme to: {slug}")

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
            lambda: apply_gnome_settings(name, palette["accent"], wallpaper),
        ),
        ("Dash to Dock", lambda: apply_dash_to_dock(palette)),
        ("Terminal", lambda: apply_terminal(output_dir, name)),
        ("Browsers", lambda: apply_browsers(output_dir, name)),
        ("VS Code", lambda: apply_vscode(output_dir, name)),
        ("Antigravity", lambda: apply_antigravity(output_dir, name)),
        ("OpenCode", lambda: apply_opencode(output_dir, name)),
        ("Kilo Code", lambda: apply_kilo(output_dir, name)),
        ("Fastfetch", lambda: apply_fastfetch(output_dir)),
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
