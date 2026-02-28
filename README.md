# Theme Maker for GNOME

Generate complete system-wide GNOME themes from any wallpaper image. Extracts dominant colors, builds a full palette from your chosen accent, and produces ready-to-use theme files for every part of your desktop.

## What it generates

One command produces **33 files** across 10 targets:

| Target | Files |
|--------|-------|
| GTK3 | Full CSS theme with 500+ style rules |
| GTK4 / libadwaita | Named colors + component overrides |
| GNOME Shell | Panel, overview, quick settings, OSD, lock screen |
| Firefox | userChrome.css, userContent.css, user.js |
| Zen Browser | Same as Firefox (Flatpak-aware) |
| Google Chrome | manifest.json theme |
| Ptyxis Terminal | 16-color palette file |
| Starship Prompt | Accent-colored prompt config |
| Pywal | colors.sh, colors.json, colors.css, sequences, plain |
| Xresources | 16-color terminal config |
| VS Code (Flatpak) | Full extension with 200+ UI colors, 39 token rules |
| Antigravity | VSIX package (auto-installed) |
| OpenCode | Theme JSON |
| Kilo Code | Theme JSON |
| Fastfetch | Accent-colored config with wallpaper logo |
| INSTALL.md | Step-by-step manual installation guide |

## Requirements

- Python 3.11+
- Pillow (`pip install Pillow`)
- NumPy (`pip install numpy`)
- GNOME desktop (Fedora, Ubuntu, Arch, etc.)

## Installation

```bash
git clone https://github.com/dashaneka/Theme-Maker-Gnome.git
cd Theme-Maker-Gnome
pip install -e .
```

This registers the `theme-maker` command in your PATH.

## Usage

### Interactive mode (recommended)

```bash
theme-maker
```

Auto-detects your current GNOME wallpaper, extracts colors, lets you pick or override the accent, choose a name, preview the palette, and optionally apply everything system-wide.

### One-shot with apply

```bash
theme-maker ~/Pictures/wallpaper.jpg -n "MyTheme" --apply
```

### Override accent color

```bash
theme-maker ~/Pictures/wallpaper.jpg -n "OceanBlue" -a "#2060c0" --apply
```

### Generate without applying

```bash
theme-maker ~/Pictures/wallpaper.jpg -n "MyTheme" -o ~/MyTheme
```

Files are saved to `~/MyTheme/` with an `INSTALL.md` for manual setup.

### All options

```
usage: theme-maker [-h] [-n NAME] [-a ACCENT] [-o OUTPUT] [--apply]
                   [--no-interactive] [-V]
                   [wallpaper]

positional arguments:
  wallpaper            Path to wallpaper image (auto-detects if omitted)

options:
  -n, --name NAME      Theme name (prompted if omitted)
  -a, --accent ACCENT  Override accent color as hex (e.g. #c41e3a)
  -o, --output OUTPUT  Output directory (default: ~/<ThemeName>)
  --apply              Apply theme system-wide after generating
  --no-interactive     Skip all prompts, use defaults
  -V, --version        Show version
```

## How it works

1. **Color extraction** -- Resizes the wallpaper to 200x200, runs k-means clustering (k=8) to find dominant colors, filters out near-black and near-white pixels for better accent detection.

2. **Accent scoring** -- Each extracted color is scored by saturation, lightness sweet-spot (25-60%), and grey penalty. The highest-scoring color becomes the accent candidate.

3. **Palette generation** -- From a single accent hex, generates 30+ colors:
   - 4 background tiers (deepest, main, surface, elevated) tinted with the accent hue
   - 2 border levels
   - 4 accent variants (hover, light, soft, rose)
   - 3 text levels (primary, muted, dim)
   - 4 semantic colors (green, blue, magenta, cyan)
   - 16 ANSI terminal colors (all accent-coherent, no clashing orange)
   - Warning, insensitive, and deep maroon utility colors

4. **File generation** -- Each generator takes the palette dict and produces complete, ready-to-use config files using f-string templates.

5. **System apply** -- Sets gsettings, creates symlinks, copies files to correct locations, builds and installs VSIX for Antigravity, updates editor configs.

## Output structure

```
~/MyTheme/
  INSTALL.md
  gtk-theme/
    gtk3.css
    gtk4.css
    index.theme
  gnome-shell/
    gnome-shell.css
  gtk-config/
    gtk3-settings.ini
    gtk4-settings.ini
  browsers/
    firefox/    (userChrome.css, userContent.css, user.js)
    zen/        (same as firefox)
    chrome/     (manifest.json)
  terminal/
    ptyxis/     (<name>.palette)
    starship/   (starship.toml)
    pywal/      (colors.sh, colors.json, colors.css, colors, sequences)
    Xresources
  editors/
    vscode/     (package.json, settings.json, themes/<name>-color-theme.json)
    antigravity/ (same as vscode)
    opencode/   (<name>.json, opencode.json)
    kilo/       (<name>.json, kv.json)
  fastfetch/
    config.jsonc
```

## Project structure

```
theme_maker/
  __init__.py          Package init (version)
  __main__.py          python -m theme_maker entry point
  palette.py           Color extraction and palette generation
  cli.py               Interactive CLI with ANSI color swatches
  applier.py           System-wide theme installer
  generators/
    gtk.py             GTK3, GTK4/libadwaita, GNOME Shell
    browsers.py        Firefox, Zen Browser, Chrome
    terminal.py        Ptyxis, Starship, Pywal, Xresources
    editors.py         VS Code, Antigravity, OpenCode, Kilo
    extras.py          Fastfetch, INSTALL.md
```

## Design choices

- **No orange in terminal** -- The ANSI yellow slot uses a hue-shifted accent variant instead of actual yellow/orange, keeping the palette coherent.
- **Subtle panels** -- Backgrounds are never pure black; they carry a faint tint of the accent hue for warmth.
- **No colored window borders** -- Active window decorations use subtle shadows, not accent-colored outlines.
- **Translucent quick toggles** -- GNOME Shell quick settings use `alpha(accent, 0.18)` when checked, not garish solid backgrounds.
- **Flatpak-aware** -- Knows where VS Code Flatpak, Zen Browser Flatpak, and other sandboxed apps store their data.

## License

MIT
