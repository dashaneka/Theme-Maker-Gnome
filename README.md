# Theme Maker for GNOME

Generate complete system-wide GNOME themes from any wallpaper image. Extracts dominant colors, builds a full palette from your chosen accent, and produces ready-to-use theme files for every part of your desktop.

## Highlights in 1.1.0

- Contrast-checked light and dark palettes across GTK, browsers, terminals, and editors
- Reliable Firefox, Zen, Chrome, Chromium, Brave, Helium, and Edge profile updates
- Direct, registered VS Code and Antigravity extension installation
- Read-only `--dry-run` reports and reusable TOML presets
- `--apply-existing` support for both new and legacy generated theme folders
- Automatic restore points plus regression tests for critical apply workflows

## What it generates

One command produces a complete theme across these targets:

| Target | Files |
|--------|-------|
| GTK3 | Full CSS theme with 500+ style rules |
| GTK4 / libadwaita | Named colors + component overrides |
| GNOME Shell | Panel, overview, quick settings, OSD, lock screen |
| Firefox | userChrome.css, userContent.css, user.js |
| Zen Browser | Same as Firefox (Flatpak-aware) |
| Chrome / Chromium / Brave / Helium / Edge | Refreshable unpacked theme |
| Ptyxis Terminal | 16-color palette file |
| Starship Prompt | Accent-colored prompt config |
| Pywal | colors.sh, colors.json, colors.css, sequences, plain |
| Xresources | 16-color terminal config |
| VS Code (Flatpak) | Full extension with 200+ UI colors, 39 token rules |
| Antigravity | Direct-copy extension with registry activation |
| OpenCode | Theme JSON |
| Kilo Code | Theme JSON |
| Codex CLI | TextMate `.tmTheme` + `tui.theme` config |
| **Vim/Neovim** | **Complete color scheme with 100+ highlight groups** |
| Fastfetch | Accent-colored config with wallpaper logo |
| INSTALL.md | Step-by-step manual installation guide |

## Requirements

- Python 3.11+
- Pillow (`pip install Pillow`)
- NumPy (`pip install numpy`)
- GNOME desktop (Fedora, Ubuntu, Arch, etc.)
- `ctgen` / clickgen and ImageMagick 7 for cursor generation
- Papirus-Dark for inherited application icons
- `git`; `rsync` is optional but recommended

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

### Generate a light theme

```bash
theme-maker ~/Pictures/wallpaper.jpg -n "MyLightTheme" --light --apply
```

### Preview changes without writing

```bash
theme-maker ~/Pictures/wallpaper.jpg -n "Ocean" --apply --dry-run --no-interactive
```

The report shows detected applications and browser profiles, dependencies,
selected components, settings, paths, and restart requirements. A dry run does
not generate files, create a backup, or change desktop settings.

### Apply a previously generated theme

Every newly generated theme includes `theme-maker.json`, which stores its name,
wallpaper, palette, mode, opacity, and component selection. Reapply it without
rebuilding icons or cursors:

```bash
theme-maker --apply-existing ~/Themes/Ocean
```

Older Theme Maker output folders without the manifest are also supported by
reading their GTK and Pywal files.

### Reusable TOML presets

Save the resolved options while generating:

```bash
theme-maker wallpaper.jpg -n "Ocean" -a "#4080ff" --light \
  --components gtk,gnome,browsers,antigravity,icons \
  --terminal-opacity 0.91 --save-config ocean.toml --no-interactive
```

Then reuse or share the preset:

```bash
theme-maker --config ocean.toml
```

Preset format:

```toml
name = "Ocean"
wallpaper = "/home/user/Pictures/ocean.jpg"
accent = "#4080ff"
mode = "light"
output = "/home/user/Themes/Ocean"
apply = true
components = ["gtk", "gnome", "browsers", "antigravity", "icons"]
terminal_opacity = 0.91
no_interactive = true
```

Available component keys are `gtk`, `gnome`, `dock`, `terminal`, `browsers`,
`vscode`, `vim`, `antigravity`, `opencode`, `kilo`, `codex`, `fastfetch`,
`icons`, and `cursors`. Explicit command-line values override preset values.

### All options

```
usage: theme-maker [-h] [-w WALLPAPER_PATH] [-n NAME] [-a ACCENT]
                   [--light | --dark]
                   [-o OUTPUT] [--apply | --no-apply]
                   [--backup] [--restore [RESTORE]] [--doctor]
                   [--watch] [--apply-existing THEME_DIR] [--dry-run]
                   [--config PRESET.toml] [--save-config PRESET.toml]
                   [--components LIST] [--terminal-opacity VALUE]
                   [--watch-interval WATCH_INTERVAL]
                   [--no-interactive | --interactive] [-V]
                   [wallpaper]

positional arguments:
  wallpaper            Path to wallpaper image (auto-detects if omitted)

options:
  -w, --wallpaper      Named form of the wallpaper path
  -n, --name NAME      Theme name (prompted if omitted)
  -a, --accent ACCENT  Override accent color as hex (e.g. #c41e3a)
  --light              Generate a light theme
  --dark               Generate a dark theme, overriding a light preset
  -o, --output OUTPUT  Output directory (default: ~/<ThemeName>)
  --apply              Apply theme system-wide after generating
  --no-apply           Override a preset that enables automatic apply
  --backup              Backup current theme as a reusable template
  --restore [RESTORE]   Restore the last saved theme state or a backup dir
  --doctor              Check dependencies and desktop readiness
  --watch               Watch wallpaper changes and auto-regenerate
  --apply-existing DIR  Apply a previously generated Theme Maker directory
  --dry-run             Preview detected targets and changes without writes
  --config FILE         Load a reusable TOML preset
  --save-config FILE    Save resolved options as a TOML preset
  --components LIST     Comma-separated components to apply
  --terminal-opacity N  Ptyxis opacity between 0.10 and 1.00
  --watch-interval N    Wallpaper poll interval in seconds
  --no-interactive     Skip all prompts, use defaults
  --interactive        Override a preset and enable prompts
  -V, --version        Show version
```

### Restore and watch

Before every apply, the app now saves an automatic restore point in
`~/.local/state/theme-maker/backups/`. You can undo the last apply with:

```bash
theme-maker --restore
```

You can also restore a specific backup directory:

```bash
theme-maker --restore ~/.local/state/theme-maker/backups/<timestamp>-<name>
```

To keep the theme updated when your wallpaper changes, run:

```bash
theme-maker --watch --apply
```

`--watch` regenerates and reapplies the theme whenever the wallpaper path or
file timestamp changes.

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

5. **System apply** -- Saves a restore point, sets GNOME settings, installs desktop assets, discovers browser profiles, refreshes Chrome-family themes, registers VS Code-compatible extensions, and updates application configs. Antigravity is installed by direct copy because its CLI installer can hang.

## Output structure

```
~/MyTheme/
  theme-maker.json
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
    opencode/   (<name>.json, tui.json)
    kilo/       (<name>.json, kilo.jsonc)
    codex/      (<name>.tmTheme)
    vim/        (colors/<name>.vim)  ← Full Vim/Neovim color scheme
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
    editors.py         VS Code, Antigravity, OpenCode, Kilo, Codex, Vim/Neovim
    icons.py           Papirus-Dark folder icon recoloring
    cursors.py         Bibata cursor theme building
    extras.py          Fastfetch, INSTALL.md
```

## Vim/Neovim Theme

The generated Vim color scheme includes:

- **100+ highlight groups** covering UI, syntax, and plugins
- **Dual mode support**: GUI colors (`guifg/guibg`) for modern Vim + 256-color terminal (`ctermfg/ctermbg`)
- **Neovim terminal colors**: All 16 ANSI colors exported as `g:terminal_color_*`
- **Treesitter support**: Full highlight groups for modern Neovim syntax parsing
- **LSP diagnostics**: Error, warning, info, hint highlights with undercurls
- **Git gutter integration**: Added, changed, deleted indicators
- **Plugin support**: NERDTree, Netrw, markdown, HTML highlighting

The theme is installed to:
- `~/.vim/colors/<name>.vim` (Vim)
- `~/.config/nvim/colors/<name>.vim` (Neovim)

To use, add to your `.vimrc` or `init.vim`:
```vim
colorscheme <theme_name>
```

## Design choices

- **No orange in terminal** -- The ANSI yellow slot uses a hue-shifted accent variant instead of actual yellow/orange, keeping the palette coherent.
- **Subtle panels** -- Backgrounds are never pure black; they carry a faint tint of the accent hue for warmth.
- **No colored window borders** -- Active window decorations use subtle shadows, not accent-colored outlines.
- **Translucent quick toggles** -- GNOME Shell quick settings use `alpha(accent, 0.18)` when checked, not garish solid backgrounds.
- **Light and dark modes** -- Both modes use contrast-checked foreground and semantic colors, with matching GTK and editor metadata.
- **Browser-profile aware** -- Reads Firefox and Zen `profiles.ini`, supports native/Flatpak/Snap locations, preserves existing `user.js`, and updates active Theme Maker Chrome, Chromium, Brave, Helium, and Edge theme folders. Flatpak document-portal paths are resolved back to their writable host origins.
- **Flatpak-aware** -- Knows where VS Code Flatpak, Zen Browser Flatpak, and other sandboxed apps store their data.

## License

MIT
