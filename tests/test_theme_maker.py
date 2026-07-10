import json
import argparse
import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from theme_maker.applier import (
    _chromium_browser_roots,
    _browser_profiles,
    _enable_gecko_user_chrome,
    _resolve_flatpak_theme_path,
    apply_antigravity,
    apply_browsers,
)
from theme_maker.generators.editors import (
    generate_opencode_theme,
    generate_vscode_package_json,
)
from theme_maker.palette import contrast_ratio, generate_palette
from theme_maker.cli import (
    _load_existing_theme,
    _load_preset,
    _save_preset,
    _write_theme_manifest,
    main,
)


class PaletteTests(unittest.TestCase):
    def test_light_palette_text_colors_are_readable(self):
        for accent in ("#cf3fcf", "#ffff00", "#eeeeee", "#111111", "#4080ff"):
            palette = generate_palette(accent, mode="light")
            for key in (
                "text",
                "text_muted",
                "accent",
                "accent_hover",
                "accent_light",
                "accent_soft",
                "accent_rose",
                "green",
                "blue",
                "magenta",
                "cyan",
                "warning",
            ):
                self.assertGreaterEqual(
                    contrast_ratio(palette[key], palette["bg_main"]), 4.5, key
                )

    def test_light_editor_extension_declares_light_ui(self):
        package = json.loads(
            generate_vscode_package_json("Test Theme", {"mode": "light"})
        )
        self.assertEqual(package["contributes"]["themes"][0]["uiTheme"], "vs")

    def test_opencode_light_roles_use_generated_light_palette(self):
        palette = generate_palette("#cf3fcf", mode="light")
        theme = json.loads(generate_opencode_theme(palette, "Test"))
        self.assertEqual(theme["theme"]["text"]["light"], "text")
        self.assertEqual(theme["theme"]["background"]["light"], "bg-deepest")
        self.assertEqual(theme["defs"]["text"], palette["text"])


class BrowserTests(unittest.TestCase):
    def test_chromium_roots_include_helium_and_brave_flatpak(self):
        home = Path("/tmp/example-home")
        roots = dict(_chromium_browser_roots(home))
        self.assertEqual(roots["Helium"], home / ".config/net.imput.helium")
        self.assertEqual(
            roots["Brave Flatpak"],
            home / ".var/app/com.brave.Browser/config/BraveSoftware/Brave-Browser",
        )

    def test_flatpak_document_theme_path_resolves_to_writable_origin(self):
        portal_path = Path("/run/flatpak/doc/abc123/chrome")
        origin = Path("/home/user/Themes/Ocean/browsers/chrome")
        self.assertEqual(
            _resolve_flatpak_theme_path(portal_path, {"abc123": origin}), origin
        )

    def test_profiles_ini_paths_are_used_instead_of_name_guessing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            profile = root / "unexpected-profile-name"
            profile.mkdir()
            (root / "profiles.ini").write_text(
                "[Profile0]\nName=Default\nIsRelative=1\n"
                "Path=unexpected-profile-name\nDefault=1\n"
            )
            self.assertEqual(_browser_profiles(root), [profile])

    def test_user_js_is_merged_and_existing_preferences_survive(self):
        with tempfile.TemporaryDirectory() as tmp:
            user_js = Path(tmp) / "user.js"
            user_js.write_text(
                'user_pref("browser.startup.page", 3);\n'
                'user_pref("toolkit.legacyUserProfileCustomizations.stylesheets", false);\n'
            )
            _enable_gecko_user_chrome(user_js)
            content = user_js.read_text()
            self.assertIn('user_pref("browser.startup.page", 3);', content)
            self.assertEqual(content.count("legacyUserProfileCustomizations"), 1)
            self.assertIn("stylesheets\", true", content)

    def test_apply_updates_gecko_and_active_chromium_theme(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / "home"
            output = base / "output"
            firefox = home / ".mozilla" / "firefox"
            profile = firefox / "random.default"
            profile.mkdir(parents=True)
            (firefox / "profiles.ini").write_text(
                "[Profile0]\nName=Default\nIsRelative=1\n"
                "Path=random.default\nDefault=1\n"
            )
            (profile / "user.js").write_text('user_pref("browser.startup.page", 3);\n')
            gecko_src = output / "browsers" / "firefox"
            gecko_src.mkdir(parents=True)
            (gecko_src / "userChrome.css").write_text("/* new chrome */")
            (gecko_src / "userContent.css").write_text("/* new content */")

            chromium_src = output / "browsers" / "chrome"
            chromium_src.mkdir(parents=True)
            new_manifest = {
                "name": "New",
                "description": "Light theme - auto-generated by Theme Maker",
                "manifest_version": 2,
                "version": "1.0",
                "theme": {},
            }
            (chromium_src / "manifest.json").write_text(json.dumps(new_manifest))
            active_theme = base / "old-theme"
            active_theme.mkdir()
            (active_theme / "manifest.json").write_text(
                json.dumps(
                    {
                        "name": "Old",
                        "description": "Dark theme - auto-generated by Theme Maker",
                    }
                )
            )
            chrome_profile = home / ".config" / "google-chrome" / "Default"
            chrome_profile.mkdir(parents=True)
            (chrome_profile / "Preferences").write_text(
                json.dumps({"extensions": {"theme": {"pack": str(active_theme)}}})
            )

            with patch("pathlib.Path.home", return_value=home):
                logs = apply_browsers(output, "New")

            self.assertEqual(
                (profile / "chrome" / "userChrome.css").read_text(), "/* new chrome */"
            )
            self.assertIn("browser.startup.page", (profile / "user.js").read_text())
            self.assertEqual(
                json.loads((active_theme / "manifest.json").read_text())["name"], "New"
            )
            self.assertTrue(
                (home / ".local/share/theme-maker/browser-theme/manifest.json").exists()
            )
            self.assertTrue(any("Updated 1 active" in line for line in logs))

    def test_apply_updates_helium_and_brave_flatpak_portal_theme(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / "home"
            output = base / "output"
            chromium_src = output / "browsers" / "chrome"
            chromium_src.mkdir(parents=True)
            new_manifest = {
                "name": "New Browser Theme",
                "description": "Dark theme - auto-generated by Theme Maker",
            }
            (chromium_src / "manifest.json").write_text(json.dumps(new_manifest))

            helium_theme = base / "helium-theme"
            brave_theme = base / "brave-theme"
            for theme_dir, name in (
                (helium_theme, "Old Helium"),
                (brave_theme, "Old Brave"),
            ):
                theme_dir.mkdir()
                (theme_dir / "manifest.json").write_text(
                    json.dumps(
                        {
                            "name": name,
                            "description": "Dark theme - auto-generated by Theme Maker",
                        }
                    )
                )

            helium_profile = home / ".config/net.imput.helium/Default"
            helium_profile.mkdir(parents=True)
            (helium_profile / "Preferences").write_text(
                json.dumps({"extensions": {"theme": {"pack": str(helium_theme)}}})
            )
            brave_profile = (
                home
                / ".var/app/com.brave.Browser/config/BraveSoftware/Brave-Browser/Default"
            )
            brave_profile.mkdir(parents=True)
            (brave_profile / "Preferences").write_text(
                json.dumps(
                    {
                        "extensions": {
                            "theme": {"pack": "/run/flatpak/doc/doc123/chrome"}
                        }
                    }
                )
            )

            with (
                patch("pathlib.Path.home", return_value=home),
                patch(
                    "theme_maker.applier._flatpak_document_origins",
                    return_value={"doc123": brave_theme},
                ),
            ):
                logs = apply_browsers(output, "New Browser Theme")

            self.assertEqual(
                json.loads((helium_theme / "manifest.json").read_text())["name"],
                "New Browser Theme",
            )
            self.assertEqual(
                json.loads((brave_theme / "manifest.json").read_text())["name"],
                "New Browser Theme",
            )
            brave_stable = home / ".var/app/com.brave.Browser/config/theme-maker/browser-theme"
            self.assertTrue((brave_stable / "manifest.json").exists())
            self.assertTrue(any("Updated 2 active" in line for line in logs))


class AntigravityTests(unittest.TestCase):
    def test_copy_install_also_registers_extension(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / "home"
            output = base / "output"
            source = output / "editors" / "antigravity"
            (source / "themes").mkdir(parents=True)
            package = {
                "name": "sample-theme",
                "displayName": "Sample",
                "version": "1.0.0",
                "publisher": "theme-maker",
                "contributes": {
                    "themes": [
                        {
                            "label": "Sample",
                            "uiTheme": "vs-dark",
                            "path": "./themes/sample-color-theme.json",
                        }
                    ]
                },
            }
            (source / "package.json").write_text(json.dumps(package))
            (source / "themes" / "sample-color-theme.json").write_text("{}")

            with patch("pathlib.Path.home", return_value=home):
                apply_antigravity(output, "Sample")

            registry = json.loads(
                (home / ".antigravity" / "extensions" / "extensions.json").read_text()
            )
            self.assertEqual(
                registry[-1]["identifier"]["id"], "theme-maker.sample-theme"
            )
            settings = json.loads(
                (home / ".config" / "Antigravity" / "User" / "settings.json").read_text()
            )
            self.assertEqual(settings["workbench.colorTheme"], "Sample")


class CliWorkflowTests(unittest.TestCase):
    def test_dry_run_does_not_create_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            wallpaper = root / "wallpaper.png"
            Image.new("RGB", (4, 4), "#4080ff").save(wallpaper)
            output = root / "must-not-exist"
            with redirect_stdout(io.StringIO()):
                result = main(
                    [
                        str(wallpaper),
                        "--name",
                        "Dry Test",
                        "--accent",
                        "#4080ff",
                        "--output",
                        str(output),
                        "--components",
                        "gtk,browsers",
                        "--dry-run",
                        "--no-interactive",
                    ]
                )
            self.assertEqual(result, 0)
            self.assertFalse(output.exists())

    def test_manifest_round_trip_for_apply_existing(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "theme"
            output.mkdir()
            palette = generate_palette("#cf3fcf", "/wallpaper.png", "light")
            _write_theme_manifest(
                output, palette, "Saved Theme", "/wallpaper.png", ["gtk", "icons"]
            )
            loaded = _load_existing_theme(output)
            self.assertEqual(loaded["name"], "Saved Theme")
            self.assertEqual(loaded["palette"]["mode"], "light")
            self.assertEqual(loaded["components"], ["gtk", "icons"])

    def test_generation_writes_manifest_and_shareable_preset(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            wallpaper = root / "wallpaper.png"
            Image.new("RGB", (4, 4), "#cf3fcf").save(wallpaper)
            output = root / "generated"
            preset = root / "theme.toml"
            with (
                patch("theme_maker.cli._generate_all"),
                redirect_stdout(io.StringIO()),
            ):
                result = main(
                    [
                        str(wallpaper),
                        "--name",
                        "Generated Theme",
                        "--accent",
                        "#cf3fcf",
                        "--light",
                        "--output",
                        str(output),
                        "--components",
                        "gtk,antigravity",
                        "--terminal-opacity",
                        "0.91",
                        "--save-config",
                        str(preset),
                        "--no-interactive",
                    ]
                )
            self.assertEqual(result, 0)
            manifest = json.loads((output / "theme-maker.json").read_text())
            self.assertEqual(manifest["name"], "Generated Theme")
            self.assertEqual(manifest["components"], ["gtk", "antigravity"])
            self.assertEqual(manifest["palette"]["terminal_opacity"], 0.91)
            loaded_preset = _load_preset(preset)
            self.assertEqual(loaded_preset["mode"], "light")
            self.assertEqual(loaded_preset["accent"], "#cf3fcf")

    def test_apply_existing_uses_selected_components(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "theme"
            output.mkdir()
            palette = generate_palette("#cf3fcf", "", "dark")
            _write_theme_manifest(output, palette, "Saved Theme", "", None)
            with (
                patch("theme_maker.cli.create_undo_backup", return_value=(Path(tmp), [])),
                patch("theme_maker.cli.apply_theme", return_value=[]) as apply_mock,
                redirect_stdout(io.StringIO()),
            ):
                result = main(
                    [
                        "--apply-existing",
                        str(output),
                        "--components",
                        "gtk,browsers",
                    ]
                )
            self.assertEqual(result, 0)
            skip = apply_mock.call_args.kwargs["skip"]
            self.assertNotIn("GTK Theme", skip)
            self.assertNotIn("Browsers", skip)
            self.assertIn("Terminal", skip)

    def test_legacy_generated_theme_without_manifest_is_supported(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "legacy"
            (output / "gtk-theme").mkdir(parents=True)
            (output / "gtk-config").mkdir()
            (output / "terminal" / "pywal").mkdir(parents=True)
            (output / "gtk-theme" / "index.theme").write_text(
                "[Desktop Entry]\nName=Legacy Theme\n"
            )
            (output / "gtk-config" / "gtk3-settings.ini").write_text(
                "gtk-application-prefer-dark-theme=false\n"
            )
            (output / "terminal" / "pywal" / "colors.json").write_text(
                json.dumps(
                    {
                        "wallpaper": "/old-wallpaper.png",
                        "special": {
                            "background": "#fafafa",
                            "foreground": "#202020",
                            "cursor": "#8040c0",
                        },
                        "colors": {"color1": "#8040c0", "color9": "#602090"},
                    }
                )
            )
            loaded = _load_existing_theme(output)
            self.assertEqual(loaded["name"], "Legacy Theme")
            self.assertEqual(loaded["palette"]["mode"], "light")
            self.assertEqual(loaded["palette"]["accent"], "#8040c0")

    def test_preset_save_load_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            preset_path = root / "shared.toml"
            args = argparse.Namespace(
                components=["gtk", "antigravity"],
                apply=True,
                terminal_opacity=0.91,
                no_interactive=True,
            )
            _save_preset(
                preset_path,
                args,
                "/wallpaper.png",
                "light",
                "Shared Theme",
                "#cf3fcf",
                root / "output",
            )
            loaded = _load_preset(preset_path)
            self.assertEqual(loaded["name"], "Shared Theme")
            self.assertEqual(loaded["mode"], "light")
            self.assertEqual(loaded["components"], ["gtk", "antigravity"])
            self.assertEqual(loaded["terminal_opacity"], 0.91)


if __name__ == "__main__":
    unittest.main()
