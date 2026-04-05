"""Generator package for theme files."""

from theme_maker.generators.gtk import write_gtk_files
from theme_maker.generators.browsers import write_browser_files
from theme_maker.generators.terminal import write_terminal_files
from theme_maker.generators.editors import write_editor_files
from theme_maker.generators.extras import write_extra_files
from theme_maker.generators.icons import generate_icon_theme, apply_icon_theme
from theme_maker.generators.cursors import generate_cursor_theme, apply_cursor_theme
