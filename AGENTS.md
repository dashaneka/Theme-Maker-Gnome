# AGENTS.md — Theme-Maker-Gnome

## Quickstart

```bash
cd ~/Codes/Theme-Maker-Gnome
pip install -e .
theme-maker wallpaper.jpg -n "MyTheme" -a "#cf3fcf" --apply --no-interactive
```

## Architecture

Entry: `theme_maker/cli.py:main()` → `_generate_all()` → `apply_theme()`

```
cli.py          → interactive CLI, color swatches, wallpaper detection
palette.py      → k-means color extraction, accent scoring, 30+ color palette
applier.py      → system-wide installer (gsettings, symlinks, file copies)
generators/
  gtk.py        → GTK3, GTK4/libadwaita, GNOME Shell CSS
  browsers.py   → Firefox, Zen (Flatpak-aware), Chrome
  terminal.py   → Ptyxis, Starship, Pywal, Xresources
  editors.py    → VS Code, Antigravity, OpenCode, Kilo
  extras.py     → Fastfetch, INSTALL.md
  icons.py      → Papirus-Dark folder recoloring (inherits rest)
  cursors.py    → Bibata cursor build via ctgen (compiles Xcursor binaries)
```

## Critical Subprocess Timeouts

Every `subprocess.run` in this repo **must** have a `timeout=` argument. Without it, the CLI hangs indefinitely at "Applying theme system-wide...". Known hang points:

| Call | Timeout | Why |
|------|---------|-----|
| `antigravity --install-extension` | None — **don't use it** | Hangs forever; install by copying to `~/.antigravity/extensions/` instead |
| `xrdb -merge` | 5s | Hangs if X not running |
| `gsettings set` | 5s | Can block on dbus |
| `gtk-update-icon-cache` | 10s | Can be slow on large themes |
| `rsync` | 30s | Large file copies |
| `magick convert` | 30s | SVG→PNG conversion |
| `ctgen` | 180s | Cursor binary compilation |
| `git clone` (Bibata) | 120s | Cloning cursor source |

Catch `subprocess.TimeoutExpired` alongside `CalledProcessError` and `FileNotFoundError`.

## Icon Theme (`generators/icons.py`)

- **Does NOT copy all of Papirus-Dark** — only copies folder/user SVGs from each size directory, inherits the rest via `Inherits=Papirus-Dark,hicolor` in index.theme
- Recolors 60+ hardcoded folder color variants (red, blue, green, orange, purple, pink, cyan, grey) to the accent
- Default `folder.svg` uses `ColorScheme-Text` for fill — replace `#dfdfdf` with accent so folders show the accent color, not grey
- Follow symlinks when copying (Papirus-Dark symlinks point to base Papirus theme files)
- Uses rsync for fast install; fallback to `shutil.copytree` if rsync fails

## Cursor Theme (`generators/cursors.py`)

- **Clones** `https://github.com/ful1e5/Bibata_Cursor.git` to `/tmp/Bibata_Cursor` if not found locally
- Converts 164 Bibata SVGs → 64px PNGs via ImageMagick (`magick convert`), recoloring `#00FF00`→accent, `#0000FF`→white, `#FF0000`→accent_dark
- Compiles Xcursor binaries via `ctgen` (from clickgen package)
- **TOML must not have duplicate cursor names** — aliases go in `x11_symlinks`, not separate `[cursors.xxx]` sections
- **Fallback hotspots must be scaled** — Bibata SVGs are 256px, PNGs are 64px, so scale by `64/256 = 0.25` (128→16)
- ctgen nests output as `themes/<name>/<name>/` — check both levels when finding built theme
- Cursor theme slug is `<name>-cursors` to avoid collision with icon theme slug `<name>`
- Requires: `ctgen` (pip: clickgen), `magick` (ImageMagick 7), `git`

## Antigravity (`applier.py:apply_antigravity`)

- **Do NOT use `antigravity --install-extension`** — it hangs forever
- Install by copying directly to `~/.antigravity/extensions/<slug>-theme/`
- Set `workbench.colorTheme` in `~/.config/Antigravity/User/settings.json`
- Antigravity's `dataFolderName` is `.antigravity` (from product.json)

## Testing

No test suite exists. Verify by running:

```bash
theme-maker -n "TestTheme" -a "#cf3fcf" -o /tmp/TestTheme --no-interactive --apply
```

Then check:
- `gsettings get org.gnome.desktop.interface icon-theme` → `testtheme`
- `gsettings get org.gnome.desktop.interface cursor-theme` → `testtheme-cursors`
- `~/.local/share/icons/testtheme-cursors/cursors/left_ptr` exists as Xcursor binary
- `~/.local/share/icons/testtheme/48x48/places/folder.svg` contains accent color
- `~/.config/Antigravity/User/settings.json` has `"workbench.colorTheme": "TestTheme"`

## Dependencies

- Python 3.11+
- Pillow, numpy (pip)
- `ctgen` / clickgen (pip, for cursor building)
- ImageMagick 7 (`magick` command, for SVG→PNG)
- rsync (fast file copy, optional but recommended)
- GNOME desktop with gsettings/dconf
