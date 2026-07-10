"""Editor theme generators - VS Code, OpenCode, Kilo, Vim."""

import json
from pathlib import Path
from xml.sax.saxutils import escape
from theme_maker.palette import blend, darken, hex_to_rgb


def _hex_to_256(hex_color: str) -> int:
    """Convert hex color to approximate 256-color terminal code."""
    r, g, b = hex_to_rgb(hex_color)
    # Standard 256-color conversion
    if r == g == b:
        # Grayscale
        if r < 8:
            return 16
        if r > 248:
            return 231
        return round(((r - 8) / 247) * 24) + 232
    # Color cube (6x6x6)
    r_idx = round((r / 255) * 5)
    g_idx = round((g / 255) * 5)
    b_idx = round((b / 255) * 5)
    return 16 + (36 * r_idx) + (6 * g_idx) + b_idx


def generate_vscode_theme(p: dict, name: str) -> str:
    data = {
        "name": name,
        "type": p.get("mode", "dark"),
        "semanticHighlighting": True,
        "colors": {
            "editor.background": p["bg_main"],
            "editor.foreground": p["text"],
            "editor.lineHighlightBackground": p["bg_surface"] + "80",
            "editor.selectionBackground": p["accent"] + "40",
            "editor.selectionHighlightBackground": p["accent"] + "25",
            "editor.findMatchBackground": p["accent"] + "50",
            "editor.findMatchHighlightBackground": p["accent"] + "30",
            "editor.wordHighlightBackground": p["accent"] + "25",
            "editor.wordHighlightStrongBackground": p["accent"] + "35",
            "editorCursor.foreground": p["accent"],
            "editorWhitespace.foreground": p["border"] + "50",
            "editorIndentGuide.background1": p["border"] + "40",
            "editorIndentGuide.activeBackground1": p["accent"] + "60",
            "editorLineNumber.foreground": p["text_dim"],
            "editorLineNumber.activeForeground": p["accent"],
            "editorBracketMatch.background": p["accent"] + "30",
            "editorBracketMatch.border": p["accent"],
            "editorGutter.addedBackground": p["green"],
            "editorGutter.modifiedBackground": p["accent"],
            "editorGutter.deletedBackground": darken(p["accent"], 15),
            "diffEditor.insertedTextBackground": p["green"] + "30",
            "diffEditor.removedTextBackground": p["accent"] + "30",
            "activityBar.background": p["bg_main"],
            "activityBar.foreground": p["accent"],
            "activityBar.inactiveForeground": p["text_dim"],
            "activityBar.border": p["border"] + "40",
            "activityBarBadge.background": p["accent"],
            "activityBarBadge.foreground": p["accent_fg"],
            "sideBar.background": p["bg_surface"],
            "sideBar.foreground": p["text"],
            "sideBar.border": p["border"] + "40",
            "sideBarTitle.foreground": p["text"],
            "sideBarSectionHeader.background": p["bg_main"],
            "sideBarSectionHeader.foreground": p["text"],
            "list.activeSelectionBackground": p["accent"] + "35",
            "list.activeSelectionForeground": p["text"],
            "list.inactiveSelectionBackground": p["accent"] + "20",
            "list.hoverBackground": p["accent"] + "15",
            "list.highlightForeground": p["accent"],
            "list.focusBackground": p["accent"] + "30",
            "tree.indentGuidesStroke": p["border"] + "60",
            "statusBar.background": p["bg_main"],
            "statusBar.foreground": p["text_muted"],
            "statusBar.border": p["border"] + "40",
            "statusBar.debuggingBackground": p["accent"],
            "statusBar.debuggingForeground": p["accent_fg"],
            "statusBar.noFolderBackground": p["bg_elevated"],
            "statusBarItem.activeBackground": p["accent"] + "40",
            "statusBarItem.hoverBackground": p["accent"] + "25",
            "statusBarItem.prominentBackground": p["accent"],
            "statusBarItem.prominentForeground": p["accent_fg"],
            "titleBar.activeBackground": p["bg_main"],
            "titleBar.activeForeground": p["text"],
            "titleBar.inactiveBackground": p["bg_main"],
            "titleBar.inactiveForeground": p["text_dim"],
            "titleBar.border": p["border"] + "40",
            "tab.activeBackground": p["bg_surface"],
            "tab.activeForeground": p["text"],
            "tab.inactiveBackground": p["bg_main"],
            "tab.inactiveForeground": p["text_dim"],
            "tab.border": p["bg_main"],
            "tab.activeBorderTop": p["accent"],
            "tab.hoverBackground": p["accent"] + "15",
            "editorGroupHeader.tabsBackground": p["bg_main"],
            "editorGroupHeader.tabsBorder": p["border"] + "40",
            "editorGroup.border": p["border"] + "40",
            "panel.background": p["bg_main"],
            "panel.border": p["border"] + "40",
            "panelTitle.activeBorder": p["accent"],
            "panelTitle.activeForeground": p["text"],
            "panelTitle.inactiveForeground": p["text_dim"],
            "terminal.background": p["bg_deepest"],
            "terminal.foreground": p["text"],
            "terminal.ansiBlack": p["ansi_black"],
            "terminal.ansiRed": p["ansi_red"],
            "terminal.ansiGreen": p["ansi_green"],
            "terminal.ansiYellow": p["ansi_yellow"],
            "terminal.ansiBlue": p["ansi_blue"],
            "terminal.ansiMagenta": p["ansi_magenta"],
            "terminal.ansiCyan": p["ansi_cyan"],
            "terminal.ansiWhite": p["ansi_white"],
            "terminal.ansiBrightBlack": p["ansi_bright_black"],
            "terminal.ansiBrightRed": p["ansi_bright_red"],
            "terminal.ansiBrightGreen": p["ansi_bright_green"],
            "terminal.ansiBrightYellow": p["ansi_bright_yellow"],
            "terminal.ansiBrightBlue": p["ansi_bright_blue"],
            "terminal.ansiBrightMagenta": p["ansi_bright_magenta"],
            "terminal.ansiBrightCyan": p["ansi_bright_cyan"],
            "terminal.ansiBrightWhite": p["ansi_bright_white"],
            "terminalCursor.foreground": p["accent"],
            "input.background": p["bg_elevated"] + "80",
            "input.foreground": p["text"],
            "input.border": p["border"] + "80",
            "input.placeholderForeground": p["text_dim"],
            "inputOption.activeBorder": p["accent"],
            "inputOption.activeBackground": p["accent"] + "30",
            "focusBorder": p["accent"],
            "dropdown.background": p["bg_elevated"],
            "dropdown.foreground": p["text"],
            "dropdown.border": p["border"] + "80",
            "button.background": p["accent"],
            "button.foreground": p["accent_fg"],
            "button.hoverBackground": p["accent_hover"],
            "button.secondaryBackground": p["bg_elevated"],
            "button.secondaryForeground": p["text"],
            "button.secondaryHoverBackground": p["border"],
            "badge.background": p["accent"],
            "badge.foreground": p["accent_fg"],
            "scrollbar.shadow": "#00000050",
            "scrollbarSlider.background": p["text_dim"] + "50",
            "scrollbarSlider.hoverBackground": p["accent"] + "80",
            "scrollbarSlider.activeBackground": p["accent"],
            "progressBar.background": p["accent"],
            "minimap.selectionHighlight": p["accent"] + "60",
            "minimap.findMatchHighlight": p["accent"],
            "minimapGutter.addedBackground": p["green"],
            "minimapGutter.modifiedBackground": p["accent"],
            "minimapGutter.deletedBackground": darken(p["accent"], 15),
            "breadcrumb.foreground": p["text_dim"],
            "breadcrumb.focusForeground": p["text"],
            "breadcrumb.activeSelectionForeground": p["accent"],
            "breadcrumbPicker.background": p["bg_elevated"],
            "menu.background": p["bg_surface"],
            "menu.foreground": p["text"],
            "menu.selectionBackground": p["accent"] + "30",
            "menu.selectionForeground": p["text"],
            "menu.separatorBackground": p["border"] + "40",
            "menubar.selectionBackground": p["accent"] + "30",
            "notificationCenter.border": p["border"] + "80",
            "notificationCenterHeader.background": p["bg_surface"],
            "notifications.background": p["bg_surface"],
            "notifications.border": p["border"] + "80",
            "notificationsInfoIcon.foreground": p["blue"],
            "notificationsWarningIcon.foreground": p["accent_rose"],
            "notificationsErrorIcon.foreground": p["accent"],
            "gitDecoration.addedResourceForeground": p["green"],
            "gitDecoration.modifiedResourceForeground": p["accent_rose"],
            "gitDecoration.deletedResourceForeground": p["accent"],
            "gitDecoration.untrackedResourceForeground": p["cyan"],
            "gitDecoration.conflictingResourceForeground": p["accent_hover"],
            "gitDecoration.ignoredResourceForeground": p["text_dim"] + "80",
            "peekView.border": p["accent"],
            "peekViewEditor.background": p["bg_surface"],
            "peekViewEditor.matchHighlightBackground": p["accent"] + "40",
            "peekViewResult.background": p["bg_main"],
            "peekViewResult.fileForeground": p["text"],
            "peekViewResult.matchHighlightBackground": p["accent"] + "40",
            "peekViewTitle.background": p["bg_elevated"],
            "peekViewTitleLabel.foreground": p["text"],
            "debugToolBar.background": p["bg_elevated"],
            "debugIcon.breakpointForeground": p["accent"],
            "debugIcon.startForeground": p["green"],
            "settings.headerForeground": p["text"],
            "settings.modifiedItemIndicator": p["accent"],
            "settings.focusedRowBackground": p["accent"] + "15",
            "welcomePage.tileBackground": p["bg_surface"],
            "welcomePage.progress.foreground": p["accent"],
            "editorWidget.background": p["bg_surface"],
            "editorWidget.foreground": p["text"],
            "editorWidget.border": p["border"] + "80",
            "editorSuggestWidget.background": p["bg_surface"],
            "editorSuggestWidget.foreground": p["text"],
            "editorSuggestWidget.selectedBackground": p["accent"] + "30",
            "editorSuggestWidget.highlightForeground": p["accent"],
            "editorHoverWidget.background": p["bg_surface"],
            "editorHoverWidget.border": p["border"] + "80",
            "commandCenter.foreground": p["text_muted"],
            "commandCenter.activeBackground": p["accent"] + "30",
            "commandCenter.activeForeground": p["text"],
            "commandCenter.border": p["border"] + "40",
            "keybindingLabel.background": p["bg_elevated"],
            "keybindingLabel.foreground": p["text"],
            "keybindingLabel.border": p["border"],
            "keybindingLabel.bottomBorder": p["border"],
            "textLink.foreground": p["accent"],
            "textLink.activeForeground": p["accent_hover"],
            "selection.background": p["accent"] + "40",
            "icon.foreground": p["text_muted"],
            "sash.hoverBorder": p["accent"],
        },
        "tokenColors": [
            {
                "scope": ["comment", "punctuation.definition.comment"],
                "settings": {"foreground": p["text_dim"], "fontStyle": "italic"},
            },
            {
                "scope": ["string", "string.quoted", "string.template"],
                "settings": {"foreground": p["accent_rose"]},
            },
            {
                "scope": ["constant.numeric", "constant.language.boolean"],
                "settings": {"foreground": p["accent_hover"]},
            },
            {
                "scope": ["constant.language", "constant.character", "constant.other"],
                "settings": {"foreground": p["accent_hover"]},
            },
            {
                "scope": ["variable", "variable.other", "variable.parameter"],
                "settings": {"foreground": p["text"]},
            },
            {
                "scope": ["variable.language.this", "variable.language.self"],
                "settings": {"foreground": p["accent"], "fontStyle": "italic"},
            },
            {
                "scope": ["keyword", "keyword.control", "keyword.operator.expression"],
                "settings": {"foreground": p["accent"]},
            },
            {
                "scope": ["keyword.operator"],
                "settings": {"foreground": p["accent_soft"]},
            },
            {
                "scope": ["storage", "storage.type", "storage.modifier"],
                "settings": {"foreground": p["accent"]},
            },
            {
                "scope": ["entity.name.function", "support.function"],
                "settings": {"foreground": p["cyan"]},
            },
            {
                "scope": ["entity.name.class", "entity.name.type", "support.class"],
                "settings": {"foreground": p["accent_rose"]},
            },
            {
                "scope": ["entity.name.tag"],
                "settings": {"foreground": p["accent"]},
            },
            {
                "scope": ["entity.other.attribute-name"],
                "settings": {"foreground": p["accent_hover"], "fontStyle": "italic"},
            },
            {
                "scope": ["support.type", "support.constant"],
                "settings": {"foreground": p["cyan"]},
            },
            {
                "scope": ["punctuation"],
                "settings": {"foreground": p["text_dim"]},
            },
            {
                "scope": ["punctuation.definition.string"],
                "settings": {"foreground": p["accent_rose"]},
            },
            {
                "scope": ["meta.brace"],
                "settings": {"foreground": p["text_muted"]},
            },
            {
                "scope": ["entity.name.namespace", "entity.name.module"],
                "settings": {"foreground": p["magenta"]},
            },
            {
                "scope": ["markup.heading", "markdown.heading"],
                "settings": {"foreground": p["accent"], "fontStyle": "bold"},
            },
            {
                "scope": ["markup.bold"],
                "settings": {"foreground": p["accent_rose"], "fontStyle": "bold"},
            },
            {
                "scope": ["markup.italic"],
                "settings": {"foreground": p["accent_soft"], "fontStyle": "italic"},
            },
            {
                "scope": ["markup.inline.raw", "markup.fenced_code"],
                "settings": {"foreground": p["cyan"]},
            },
            {
                "scope": ["markup.quote"],
                "settings": {"foreground": p["text_dim"], "fontStyle": "italic"},
            },
            {
                "scope": ["markup.underline.link"],
                "settings": {"foreground": p["accent"]},
            },
            {
                "scope": ["meta.embedded", "source.groovy.embedded"],
                "settings": {"foreground": p["text"]},
            },
            {
                "scope": ["invalid", "invalid.illegal"],
                "settings": {"foreground": p["accent_light"], "fontStyle": "underline"},
            },
            {
                "scope": ["invalid.deprecated"],
                "settings": {
                    "foreground": p["accent_soft"],
                    "fontStyle": "strikethrough",
                },
            },
            {
                "scope": [
                    "support.type.property-name.css",
                    "support.type.property-name.json",
                ],
                "settings": {"foreground": p["cyan"]},
            },
            {
                "scope": ["entity.other.inherited-class"],
                "settings": {"foreground": p["cyan"], "fontStyle": "italic"},
            },
            {
                "scope": ["meta.function-call"],
                "settings": {"foreground": p["cyan"]},
            },
            {
                "scope": ["entity.name.import", "entity.name.package"],
                "settings": {"foreground": p["accent_rose"]},
            },
            {
                "scope": ["meta.jsx.children", "meta.tsx.children"],
                "settings": {"foreground": p["text"]},
            },
            {
                "scope": ["support.type.vendored.property-name"],
                "settings": {"foreground": p["cyan"]},
            },
            {
                "scope": [
                    "entity.name.variable",
                    "variable.other.readwrite",
                    "variable.other.object",
                ],
                "settings": {"foreground": p["text"]},
            },
            {
                "scope": ["variable.other.property"],
                "settings": {"foreground": p["text_muted"]},
            },
            {
                "scope": ["string.regexp"],
                "settings": {"foreground": p["magenta"]},
            },
            {
                "scope": ["keyword.operator.assignment"],
                "settings": {"foreground": p["text_muted"]},
            },
            {
                "scope": ["meta.decorator", "entity.name.function.decorator"],
                "settings": {"foreground": p["accent_hover"], "fontStyle": "italic"},
            },
            {
                "scope": ["support.variable"],
                "settings": {"foreground": p["blue"]},
            },
        ],
        "semanticTokenColors": {
            "function": p["cyan"],
            "function.declaration": p["cyan"],
            "method": p["cyan"],
            "method.declaration": p["cyan"],
            "variable": p["text"],
            "variable.declaration": p["text"],
            "variable.readonly": p["accent_hover"],
            "parameter": p["text_muted"],
            "property": p["text_muted"],
            "property.declaration": p["text_muted"],
            "class": p["accent_rose"],
            "interface": p["accent_rose"],
            "enum": p["accent_rose"],
            "enumMember": p["accent_hover"],
            "type": p["accent_rose"],
            "namespace": p["magenta"],
            "decorator": {"foreground": p["accent_hover"], "italic": True},
            "keyword": p["accent"],
            "comment": {"foreground": p["text_dim"], "italic": True},
            "string": p["accent_rose"],
            "number": p["accent_hover"],
            "regexp": p["magenta"],
            "operator": p["accent_soft"],
        },
    }
    return json.dumps(data, indent=2)


def generate_vscode_package_json(name: str, p: dict) -> str:
    slug = name.lower().replace(" ", "-")
    mode = p.get("mode", "dark")
    data = {
        "name": f"{slug}-theme",
        "displayName": name,
        "description": f"{mode.title()} theme with accent colors - auto-generated by Theme Maker",
        "version": "1.0.0",
        "publisher": "theme-maker",
        "engines": {"vscode": "^1.60.0"},
        "categories": ["Themes"],
        "contributes": {
            "themes": [
                {
                    "label": name,
                    "uiTheme": "vs" if mode == "light" else "vs-dark",
                    "path": f"./themes/{slug}-color-theme.json",
                }
            ]
        },
    }
    return json.dumps(data, indent=2)


def generate_vscode_settings(name: str, p: dict) -> str:
    data = {
        "workbench.colorTheme": name,
        "workbench.colorCustomizations": {
            "terminal.background": p["bg_deepest"],
            "terminal.foreground": p["text"],
            "terminal.ansiBlack": p["ansi_black"],
            "terminal.ansiRed": p["ansi_red"],
            "terminal.ansiGreen": p["ansi_green"],
            "terminal.ansiYellow": p["ansi_yellow"],
            "terminal.ansiBlue": p["ansi_blue"],
            "terminal.ansiMagenta": p["ansi_magenta"],
            "terminal.ansiCyan": p["ansi_cyan"],
            "terminal.ansiWhite": p["ansi_white"],
            "terminal.ansiBrightBlack": p["ansi_bright_black"],
            "terminal.ansiBrightRed": p["ansi_bright_red"],
            "terminal.ansiBrightGreen": p["ansi_bright_green"],
            "terminal.ansiBrightYellow": p["ansi_bright_yellow"],
            "terminal.ansiBrightBlue": p["ansi_bright_blue"],
            "terminal.ansiBrightMagenta": p["ansi_bright_magenta"],
            "terminal.ansiBrightCyan": p["ansi_bright_cyan"],
            "terminal.ansiBrightWhite": p["ansi_bright_white"],
            "terminalCursor.foreground": p["accent"],
        },
    }
    return json.dumps(data, indent=4)


def generate_opencode_theme(p: dict, name: str) -> str:
    diff_added_bg = blend(p["bg_main"], p["green"], 0.14)
    diff_removed_bg = blend(p["bg_main"], p["accent_light"], 0.14)
    data = {
        "$schema": "https://opencode.ai/theme.json",
        "defs": {
            "bg-deepest": p["bg_deepest"],
            "bg-main": p["bg_main"],
            "bg-surface": p["bg_surface"],
            "bg-elevated": p["bg_elevated"],
            "border-dim": p["bg_elevated"],
            "border-main": p["border"],
            "border-bright": p["border_bright"],
            "accent": p["accent"],
            "accent-light": p["accent_light"],
            "accent-soft": p["accent_soft"],
            "text": p["text"],
            "text-muted": p["text_muted"],
            "text-dim": p["text_dim"],
            "scarlet-rose": p["accent_rose"],
            "deep-maroon": p["deep_maroon"],
            "green": p["green"],
            "red": p["accent_light"],
            "yellow": p["ansi_yellow"],
            "blue": p["blue"],
            "magenta": p["magenta"],
            "cyan": p["cyan"],
            "diff-added-bg": diff_added_bg,
            "diff-removed-bg": diff_removed_bg,
        },
        "theme": {
            "primary": {"dark": "accent", "light": "accent"},
            "secondary": {"dark": "accent-soft", "light": "accent-soft"},
            "accent": {"dark": "scarlet-rose", "light": "scarlet-rose"},
            "error": {"dark": "red", "light": "red"},
            "warning": {"dark": "yellow", "light": "yellow"},
            "success": {"dark": "green", "light": "green"},
            "info": {"dark": "accent-soft", "light": "accent-soft"},
            "text": {"dark": "text", "light": "text"},
            "textMuted": {"dark": "text-muted", "light": "text-muted"},
            "background": {"dark": "bg-deepest", "light": "bg-deepest"},
            "backgroundPanel": {"dark": "bg-main", "light": "bg-main"},
            "backgroundElement": {"dark": "bg-surface", "light": "bg-surface"},
            "border": {"dark": "border-main", "light": "border-main"},
            "borderActive": {"dark": "accent", "light": "accent"},
            "borderSubtle": {"dark": "border-dim", "light": "border-dim"},
            "diffAdded": {"dark": "green", "light": "green"},
            "diffRemoved": {"dark": "red", "light": "red"},
            "diffContext": {"dark": "text-muted", "light": "text-muted"},
            "diffHunkHeader": {"dark": "text-dim", "light": "text-dim"},
            "diffHighlightAdded": {"dark": "green", "light": "green"},
            "diffHighlightRemoved": {"dark": "red", "light": "red"},
            "diffAddedBg": {"dark": "diff-added-bg", "light": "diff-added-bg"},
            "diffRemovedBg": {"dark": "diff-removed-bg", "light": "diff-removed-bg"},
            "diffContextBg": {"dark": "bg-main", "light": "bg-main"},
            "diffLineNumber": {"dark": "text-dim", "light": "text-dim"},
            "diffAddedLineNumberBg": {"dark": "diff-added-bg", "light": "diff-added-bg"},
            "diffRemovedLineNumberBg": {"dark": "diff-removed-bg", "light": "diff-removed-bg"},
            "markdownText": {"dark": "text", "light": "text"},
            "markdownHeading": {"dark": "accent", "light": "accent"},
            "markdownLink": {"dark": "scarlet-rose", "light": "scarlet-rose"},
            "markdownLinkText": {"dark": "accent-light", "light": "accent"},
            "markdownCode": {"dark": "magenta", "light": "magenta"},
            "markdownBlockQuote": {"dark": "text-muted", "light": "text-muted"},
            "markdownEmph": {"dark": "accent-soft", "light": "accent-soft"},
            "markdownStrong": {"dark": "accent-light", "light": "accent"},
            "markdownHorizontalRule": {"dark": "border-main", "light": "border-main"},
            "markdownListItem": {"dark": "accent", "light": "accent"},
            "markdownListEnumeration": {"dark": "accent-soft", "light": "accent-soft"},
            "markdownImage": {"dark": "scarlet-rose", "light": "scarlet-rose"},
            "markdownImageText": {"dark": "accent-soft", "light": "accent-soft"},
            "markdownCodeBlock": {"dark": "text", "light": "text"},
            "syntaxComment": {"dark": "text-muted", "light": "text-muted"},
            "syntaxKeyword": {"dark": "accent", "light": "accent"},
            "syntaxFunction": {"dark": "scarlet-rose", "light": "scarlet-rose"},
            "syntaxVariable": {"dark": "cyan", "light": "cyan"},
            "syntaxString": {"dark": "green", "light": "green"},
            "syntaxNumber": {"dark": "magenta", "light": "magenta"},
            "syntaxType": {"dark": "accent-soft", "light": "accent-soft"},
            "syntaxOperator": {"dark": "accent-light", "light": "accent"},
            "syntaxPunctuation": {"dark": "text", "light": "text"},
        },
    }
    return json.dumps(data, indent=2)


def generate_codex_tmtheme(p: dict, name: str) -> str:
    """Generate a TextMate theme for Codex TUI syntax highlighting."""
    theme_name = escape(name)
    settings = [
        (
            "",
            {
                "background": p["bg_deepest"],
                "foreground": p["text"],
                "caret": p["accent"],
                "invisibles": p["border"],
                "lineHighlight": p["bg_main"],
                "selection": p["accent"] + "40",
                "gutterBackground": p["bg_deepest"],
                "gutterForeground": p["text_dim"],
            },
        ),
        (
            "comment, punctuation.definition.comment, comment.line.number-sign, comment.block.documentation",
            {"foreground": p["text_dim"], "fontStyle": "italic"},
        ),
        (
            "string, string.quoted, string.template, string.unquoted.heredoc, string.interpolated",
            {"foreground": p["accent_rose"]},
        ),
        (
            "constant.numeric, constant.language.boolean, constant.numeric.integer, constant.numeric.float",
            {"foreground": p["accent_hover"]},
        ),
        (
            "constant.language, constant.character, constant.other, constant.character.escape",
            {"foreground": p["accent_hover"]},
        ),
        (
            "variable, variable.other, variable.parameter, meta.definition.variable",
            {"foreground": p["text"]},
        ),
        (
            "variable.language.this, variable.language.self, variable.language.special",
            {"foreground": p["accent"], "fontStyle": "italic"},
        ),
        (
            "keyword, keyword.control, storage, storage.type, storage.modifier, keyword.declaration, keyword.other.special-method",
            {"foreground": p["accent"]},
        ),
        (
            "keyword.operator, punctuation.accessor, punctuation.separator.key-value",
            {"foreground": p["accent_soft"]},
        ),
        (
            "entity.name.function, support.function, meta.function-call, entity.name.method, variable.function",
            {"foreground": p["cyan"]},
        ),
        (
            "entity.name.class, entity.name.type, support.class, support.type, entity.name.struct, entity.name.enum",
            {"foreground": p["accent_rose"]},
        ),
        (
            "entity.name.namespace, entity.name.module, support.module",
            {"foreground": p["magenta"]},
        ),
        ("entity.name.tag", {"foreground": p["accent"]}),
        (
            "entity.other.attribute-name, entity.other.attribute-name.class.css, entity.other.attribute-name.id.css",
            {"foreground": p["accent_hover"], "fontStyle": "italic"},
        ),
        (
            "variable.other.property, support.type.property-name.css, support.type.property-name.json, meta.object-literal.key",
            {"foreground": p["text_muted"]},
        ),
        (
            "support.constant, support.variable, support.type.primitive, support.type.builtin",
            {"foreground": p["blue"]},
        ),
        ("punctuation, meta.brace, meta.delimiter", {"foreground": p["text_dim"]}),
        ("punctuation.definition.string", {"foreground": p["accent_rose"]}),
        ("string.regexp, constant.other.character-class.regexp", {"foreground": p["magenta"]}),
        (
            "markup.heading, markdown.heading, entity.name.section.markdown",
            {"foreground": p["accent"], "fontStyle": "bold"},
        ),
        ("markup.bold", {"foreground": p["accent_rose"], "fontStyle": "bold"}),
        (
            "markup.italic, markup.quote, punctuation.definition.quote.begin.markdown",
            {"foreground": p["accent_soft"], "fontStyle": "italic"},
        ),
        (
            "markup.inline.raw, markup.fenced_code, markup.raw.block, markup.raw.inline",
            {"foreground": p["cyan"]},
        ),
        (
            "markup.underline.link, string.other.link, markup.link, markup.link.text",
            {"foreground": p["accent"]},
        ),
        (
            "markup.list, punctuation.definition.list.begin.markdown",
            {"foreground": p["accent_hover"]},
        ),
        (
            "markup.inserted, diff.inserted, meta.diff.header.from-file",
            {"foreground": p["green"]},
        ),
        (
            "markup.deleted, diff.deleted, meta.diff.header.to-file",
            {"foreground": p["accent_light"]},
        ),
        (
            "markup.changed, diff.changed, meta.diff.range",
            {"foreground": p["accent_hover"]},
        ),
        (
            "meta.separator, punctuation.section.embedded, punctuation.separator.continuation",
            {"foreground": p["border_bright"]},
        ),
        (
            "source.shell, meta.prompt, entity.name.tag.prompt, constant.other.prompt",
            {"foreground": p["green"]},
        ),
        (
            "invalid, invalid.illegal, invalid.deprecated",
            {"foreground": p["accent_light"], "fontStyle": "underline"},
        ),
    ]

    entries: list[str] = []
    for scope, values in settings:
        pairs = []
        if scope:
            pairs.append(
                f"        <key>scope</key>\n        <string>{escape(scope)}</string>"
            )
        pairs.append("        <key>settings</key>")
        pairs.append("        <dict>")
        for key, value in values.items():
            pairs.append(f"          <key>{escape(key)}</key>")
            pairs.append(f"          <string>{escape(value)}</string>")
        pairs.append("        </dict>")
        entries.append("      <dict>\n" + "\n".join(pairs) + "\n      </dict>")

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>name</key>
  <string>{theme_name}</string>
  <key>settings</key>
  <array>
{chr(10).join(entries)}
  </array>
</dict>
</plist>
"""


def generate_vim_theme(p: dict, name: str) -> str:
    """Generate a Vim color scheme in .vim format."""
    slug = name.lower().replace(" ", "_")

    # Build cterm colors (256-color approximations)
    cterm = {
        "bg": _hex_to_256(p["bg_deepest"]),
        "fg": _hex_to_256(p["text"]),
        "accent": _hex_to_256(p["accent"]),
        "accent_rose": _hex_to_256(p["accent_rose"]),
        "accent_soft": _hex_to_256(p["accent_soft"]),
        "green": _hex_to_256(p["green"]),
        "red": _hex_to_256(p["accent_light"]),
        "blue": _hex_to_256(p["blue"]),
        "magenta": _hex_to_256(p["magenta"]),
        "cyan": _hex_to_256(p["cyan"]),
        "yellow": _hex_to_256(p["ansi_yellow"]),
        "text_muted": _hex_to_256(p["text_muted"]),
        "text_dim": _hex_to_256(p["text_dim"]),
        "bg_surface": _hex_to_256(p["bg_surface"]),
        "bg_elevated": _hex_to_256(p["bg_elevated"]),
    }

    return f"""" {name} - Auto-generated Vim color scheme
" Maintainer: Theme Maker for GNOME
" Background: {p.get("mode", "dark")}

set background={p.get("mode", "dark")}
hi clear
if exists("syntax_on")
  syntax reset
endif

let g:colors_name = "{slug}"

" ═══════════════════════════════════════════════════════════════════════════════
" UI Elements
" ═══════════════════════════════════════════════════════════════════════════════

" Normal text
hi Normal guifg={p["text"]} guibg={p["bg_deepest"]} ctermfg={cterm["fg"]} ctermbg={cterm["bg"]}

" Cursor
hi Cursor guifg={p["bg_deepest"]} guibg={p["accent"]} ctermfg={cterm["bg"]} ctermbg={cterm["accent"]}
hi CursorLine guibg={p["bg_main"]} ctermbg={cterm["bg"]} gui=none
hi CursorColumn guibg={p["bg_main"]} ctermbg={cterm["bg"]}

" Line numbers
hi LineNr guifg={p["text_dim"]} guibg={p["bg_deepest"]} ctermfg={cterm["text_dim"]} ctermbg={cterm["bg"]}
hi CursorLineNr guifg={p["accent"]} guibg={p["bg_main"]} ctermfg={cterm["accent"]} ctermbg={cterm["bg"]} gui=bold

" Status line
hi StatusLine guifg={p["text"]} guibg={p["bg_surface"]} ctermfg={cterm["fg"]} ctermbg={cterm["bg_surface"]} gui=none
hi StatusLineNC guifg={p["text_muted"]} guibg={p["bg_main"]} ctermfg={cterm["text_muted"]} ctermbg={cterm["bg"]} gui=none

" Vertical split
hi VertSplit guifg={p["border"]} guibg={p["bg_deepest"]} ctermfg={cterm["text_dim"]} ctermbg={cterm["bg"]} gui=none

" Tabs
hi TabLine guifg={p["text_muted"]} guibg={p["bg_main"]} ctermfg={cterm["text_muted"]} ctermbg={cterm["bg"]} gui=none
hi TabLineFill guifg={p["text_dim"]} guibg={p["bg_deepest"]} ctermfg={cterm["text_dim"]} ctermbg={cterm["bg"]} gui=none
hi TabLineSel guifg={p["bg_deepest"]} guibg={p["accent"]} ctermfg={cterm["bg"]} ctermbg={cterm["accent"]} gui=bold

" Search and match
hi Search guifg={p["bg_deepest"]} guibg={p["accent"]} ctermfg={cterm["bg"]} ctermbg={cterm["accent"]} gui=bold
hi IncSearch guifg={p["bg_deepest"]} guibg={p["accent_rose"]} ctermfg={cterm["bg"]} ctermbg={cterm["accent_rose"]} gui=bold
hi MatchParen guifg={p["accent_light"]} guibg=NONE ctermfg={cterm["accent"]} ctermbg=NONE gui=bold,underline

" Selection
hi Visual guibg={p["accent"]} ctermbg={cterm["accent"]} gui=none
hi VisualNOS guibg={p["bg_elevated"]} ctermbg={cterm["bg_elevated"]} gui=none
if has("nvim")
  hi Visual blend=20
endif

" Folded text
hi Folded guifg={p["text_muted"]} guibg={p["bg_surface"]} ctermfg={cterm["text_muted"]} ctermbg={cterm["bg_surface"]}
hi FoldColumn guifg={p["text_dim"]} guibg={p["bg_deepest"]} ctermfg={cterm["text_dim"]} ctermbg={cterm["bg"]}

" Pop-up menu
hi Pmenu guifg={p["text"]} guibg={p["bg_surface"]} ctermfg={cterm["fg"]} ctermbg={cterm["bg_surface"]}
hi PmenuSel guifg={p["bg_deepest"]} guibg={p["accent"]} ctermfg={cterm["bg"]} ctermbg={cterm["accent"]} gui=bold
hi PmenuSbar guibg={p["bg_elevated"]} ctermbg={cterm["bg_elevated"]}
hi PmenuThumb guibg={p["accent"]} ctermbg={cterm["accent"]}

" Wild menu
hi WildMenu guifg={p["bg_deepest"]} guibg={p["accent"]} ctermfg={cterm["bg"]} ctermbg={cterm["accent"]}

" Sign column (for gitgutter, diagnostics)
hi SignColumn guifg={p["text_dim"]} guibg={p["bg_deepest"]} ctermfg={cterm["text_dim"]} ctermbg={cterm["bg"]}
hi ColorColumn guibg={p["bg_main"]} ctermbg={cterm["bg"]}

" Gutter
hi GitGutterAdd guifg={p["green"]} guibg={p["bg_deepest"]} ctermfg={cterm["green"]} ctermbg={cterm["bg"]} gui=bold
hi GitGutterChange guifg={p["accent"]} guibg={p["bg_deepest"]} ctermfg={cterm["accent"]} ctermbg={cterm["bg"]} gui=bold
hi GitGutterDelete guifg={p["accent_light"]} guibg={p["bg_deepest"]} ctermfg={cterm["red"]} ctermbg={cterm["bg"]} gui=bold
hi GitGutterChangeDelete guifg={p["accent_rose"]} guibg={p["bg_deepest"]} ctermfg={cterm["accent_rose"]} ctermbg={cterm["bg"]} gui=bold

" Diagnostics (LSP)
hi DiagnosticError guifg={p["accent_light"]} ctermfg={cterm["red"]} gui=bold
hi DiagnosticWarn guifg={p["ansi_yellow"]} ctermfg={cterm["yellow"]} gui=bold
hi DiagnosticInfo guifg={p["blue"]} ctermfg={cterm["blue"]}
hi DiagnosticHint guifg={p["cyan"]} ctermfg={cterm["cyan"]}
hi DiagnosticOk guifg={p["green"]} ctermfg={cterm["green"]}

" Underlines for diagnostics
hi DiagnosticUnderlineError guifg=NONE guibg=NONE gui=underline guisp={p["accent_light"]}
hi DiagnosticUnderlineWarn guifg=NONE guibg=NONE gui=underline guisp={p["ansi_yellow"]}
hi DiagnosticUnderlineInfo guifg=NONE guibg=NONE gui=underline guisp={p["blue"]}
hi DiagnosticUnderlineHint guifg=NONE guibg=NONE gui=underline guisp={p["cyan"]}

" ═══════════════════════════════════════════════════════════════════════════════
" Syntax Highlighting
" ═══════════════════════════════════════════════════════════════════════════════

" Comments
hi Comment guifg={p["text_dim"]} ctermfg={cterm["text_dim"]} gui=italic

" Constants
hi Constant guifg={p["accent_hover"]} ctermfg={cterm["accent"]}
hi String guifg={p["accent_rose"]} ctermfg={cterm["accent_rose"]}
hi Character guifg={p["accent_rose"]} ctermfg={cterm["accent_rose"]}
hi Number guifg={p["accent_hover"]} ctermfg={cterm["accent"]}
hi Boolean guifg={p["accent_hover"]} ctermfg={cterm["accent"]}
hi Float guifg={p["accent_hover"]} ctermfg={cterm["accent"]}

" Identifiers
hi Identifier guifg={p["text"]} ctermfg={cterm["fg"]}
hi Function guifg={p["cyan"]} ctermfg={cterm["cyan"]}

" Statements
hi Statement guifg={p["accent"]} ctermfg={cterm["accent"]} gui=none
hi Conditional guifg={p["accent"]} ctermfg={cterm["accent"]}
hi Repeat guifg={p["accent"]} ctermfg={cterm["accent"]}
hi Label guifg={p["accent"]} ctermfg={cterm["accent"]}
hi Operator guifg={p["accent_soft"]} ctermfg={cterm["accent_soft"]}
hi Keyword guifg={p["accent"]} ctermfg={cterm["accent"]}
hi Exception guifg={p["accent"]} ctermfg={cterm["accent"]}

" Preprocessor
hi PreProc guifg={p["accent"]} ctermfg={cterm["accent"]}
hi Include guifg={p["accent"]} ctermfg={cterm["accent"]}
hi Define guifg={p["accent"]} ctermfg={cterm["accent"]}
hi Macro guifg={p["accent"]} ctermfg={cterm["accent"]}
hi PreCondit guifg={p["accent"]} ctermfg={cterm["accent"]}

" Types
hi Type guifg={p["accent_rose"]} ctermfg={cterm["accent_rose"]} gui=none
hi StorageClass guifg={p["accent"]} ctermfg={cterm["accent"]}
hi Structure guifg={p["accent_rose"]} ctermfg={cterm["accent_rose"]}
hi Typedef guifg={p["accent_rose"]} ctermfg={cterm["accent_rose"]}

" Special
hi Special guifg={p["magenta"]} ctermfg={cterm["magenta"]}
hi SpecialChar guifg={p["accent_hover"]} ctermfg={cterm["accent"]}
hi Tag guifg={p["accent"]} ctermfg={cterm["accent"]}
hi Delimiter guifg={p["text_muted"]} ctermfg={cterm["text_muted"]}
hi SpecialComment guifg={p["text_dim"]} ctermfg={cterm["text_dim"]} gui=italic
hi Debug guifg={p["accent_light"]} ctermfg={cterm["red"]}

" Underlined
hi Underlined guifg={p["accent"]} ctermfg={cterm["accent"]} gui=underline

" Ignore
hi Ignore guifg={p["text_dim"]} ctermfg={cterm["text_dim"]}

" Errors
hi Error guifg={p["accent_light"]} guibg=NONE ctermfg={cterm["red"]} ctermbg=NONE gui=bold,underline
hi ErrorMsg guifg={p["accent_light"]} guibg=NONE ctermfg={cterm["red"]} ctermbg=NONE
hi WarningMsg guifg={p["ansi_yellow"]} guibg=NONE ctermfg={cterm["yellow"]} ctermbg=NONE

" Todo
hi Todo guifg={p["green"]} guibg=NONE ctermfg={cterm["green"]} ctermbg=NONE gui=bold

" ═══════════════════════════════════════════════════════════════════════════════
" Diff Mode
" ═══════════════════════════════════════════════════════════════════════════════

hi DiffAdd guifg={p["green"]} guibg={p["bg_surface"]} ctermfg={cterm["green"]} ctermbg={cterm["bg"]}
hi DiffChange guifg={p["accent"]} guibg={p["bg_surface"]} ctermfg={cterm["accent"]} ctermbg={cterm["bg"]}
hi DiffDelete guifg={p["accent_light"]} guibg={p["bg_main"]} ctermfg={cterm["red"]} ctermbg={cterm["bg"]}
hi DiffText guifg={p["accent_rose"]} guibg={p["bg_elevated"]} ctermfg={cterm["accent_rose"]} ctermbg={cterm["bg"]} gui=bold

" ═══════════════════════════════════════════════════════════════════════════════
" Spelling
" ═══════════════════════════════════════════════════════════════════════════════

hi SpellBad guifg={p["accent_light"]} gui=undercurl guisp={p["accent_light"]}
hi SpellCap guifg={p["ansi_yellow"]} gui=undercurl guisp={p["ansi_yellow"]}
hi SpellRare guifg={p["magenta"]} gui=undercurl guisp={p["magenta"]}
hi SpellLocal guifg={p["cyan"]} gui=undercurl guisp={p["cyan"]}

" ═══════════════════════════════════════════════════════════════════════════════
" Terminal (Neovim/Vim terminal)
" ═══════════════════════════════════════════════════════════════════════════════

if has("nvim")
  let g:terminal_color_0  = "{p["ansi_black"]}"
  let g:terminal_color_1  = "{p["ansi_red"]}"
  let g:terminal_color_2  = "{p["ansi_green"]}"
  let g:terminal_color_3  = "{p["ansi_yellow"]}"
  let g:terminal_color_4  = "{p["ansi_blue"]}"
  let g:terminal_color_5  = "{p["ansi_magenta"]}"
  let g:terminal_color_6  = "{p["ansi_cyan"]}"
  let g:terminal_color_7  = "{p["ansi_white"]}"
  let g:terminal_color_8  = "{p["ansi_bright_black"]}"
  let g:terminal_color_9  = "{p["ansi_bright_red"]}"
  let g:terminal_color_10 = "{p["ansi_bright_green"]}"
  let g:terminal_color_11 = "{p["ansi_bright_yellow"]}"
  let g:terminal_color_12 = "{p["ansi_bright_blue"]}"
  let g:terminal_color_13 = "{p["ansi_bright_magenta"]}"
  let g:terminal_color_14 = "{p["ansi_bright_cyan"]}"
  let g:terminal_color_15 = "{p["ansi_bright_white"]}"
endif

" ═══════════════════════════════════════════════════════════════════════════════
" Neovim Treesitter / LSP / Modern Plugins
" ═══════════════════════════════════════════════════════════════════════════════

if has("nvim")
  " Treesitter
  hi @text guifg={p["text"]} ctermfg={cterm["fg"]}
  hi @text.strong guifg={p["accent_rose"]} ctermfg={cterm["accent_rose"]} gui=bold
  hi @text.emphasis guifg={p["accent_soft"]} ctermfg={cterm["accent_soft"]} gui=italic
  hi @text.underline guifg={p["text"]} ctermfg={cterm["fg"]} gui=underline
  hi @text.strike guifg={p["text_muted"]} ctermfg={cterm["text_muted"]} gui=strikethrough
  hi @text.literal guifg={p["cyan"]} ctermfg={cterm["cyan"]}
  hi @text.uri guifg={p["accent"]} ctermfg={cterm["accent"]} gui=underline
  hi @text.reference guifg={p["accent_rose"]} ctermfg={cterm["accent_rose"]}
  hi @text.title guifg={p["accent"]} ctermfg={cterm["accent"]} gui=bold
  hi @text.todo guifg={p["green"]} ctermfg={cterm["green"]} gui=bold
  hi @text.note guifg={p["blue"]} ctermfg={cterm["blue"]} gui=bold
  hi @text.warning guifg={p["ansi_yellow"]} ctermfg={cterm["yellow"]} gui=bold
  hi @text.danger guifg={p["accent_light"]} ctermfg={cterm["red"]} gui=bold
  
  " Treesitter - Code
  hi @comment guifg={p["text_dim"]} ctermfg={cterm["text_dim"]} gui=italic
  hi @punctuation guifg={p["text_muted"]} ctermfg={cterm["text_muted"]}
  hi @punctuation.bracket guifg={p["text_muted"]} ctermfg={cterm["text_muted"]}
  hi @punctuation.special guifg={p["accent"]} ctermfg={cterm["accent"]}
  hi @punctuation.delimiter guifg={p["text_muted"]} ctermfg={cterm["text_muted"]}
  
  hi @constant guifg={p["accent_hover"]} ctermfg={cterm["accent"]}
  hi @constant.builtin guifg={p["accent_hover"]} ctermfg={cterm["accent"]} gui=italic
  hi @constant.macro guifg={p["accent"]} ctermfg={cterm["accent"]}
  hi @define guifg={p["accent"]} ctermfg={cterm["accent"]}
  hi @macro guifg={p["accent"]} ctermfg={cterm["accent"]}
  hi @string guifg={p["accent_rose"]} ctermfg={cterm["accent_rose"]}
  hi @string.escape guifg={p["magenta"]} ctermfg={cterm["magenta"]}
  hi @string.special guifg={p["accent_hover"]} ctermfg={cterm["accent"]}
  hi @character guifg={p["accent_rose"]} ctermfg={cterm["accent_rose"]}
  hi @character.special guifg={p["magenta"]} ctermfg={cterm["magenta"]}
  hi @number guifg={p["accent_hover"]} ctermfg={cterm["accent"]}
  hi @float guifg={p["accent_hover"]} ctermfg={cterm["accent"]}
  hi @boolean guifg={p["accent_hover"]} ctermfg={cterm["accent"]}
  
  hi @function guifg={p["cyan"]} ctermfg={cterm["cyan"]}
  hi @function.builtin guifg={p["cyan"]} ctermfg={cterm["cyan"]} gui=italic
  hi @function.call guifg={p["cyan"]} ctermfg={cterm["cyan"]}
  hi @function.macro guifg={p["cyan"]} ctermfg={cterm["cyan"]}
  hi @method guifg={p["cyan"]} ctermfg={cterm["cyan"]}
  hi @method.call guifg={p["cyan"]} ctermfg={cterm["cyan"]}
  hi @constructor guifg={p["accent_rose"]} ctermfg={cterm["accent_rose"]}
  hi @parameter guifg={p["text"]} ctermfg={cterm["fg"]} gui=italic
  
  hi @keyword guifg={p["accent"]} ctermfg={cterm["accent"]}
  hi @keyword.coroutine guifg={p["accent"]} ctermfg={cterm["accent"]}
  hi @keyword.function guifg={p["accent"]} ctermfg={cterm["accent"]}
  hi @keyword.operator guifg={p["accent_soft"]} ctermfg={cterm["accent_soft"]}
  hi @keyword.import guifg={p["accent"]} ctermfg={cterm["accent"]}
  hi @keyword.storage guifg={p["accent"]} ctermfg={cterm["accent"]}
  hi @keyword.repeat guifg={p["accent"]} ctermfg={cterm["accent"]}
  hi @keyword.return guifg={p["accent"]} ctermfg={cterm["accent"]}
  hi @keyword.debug guifg={p["accent_light"]} ctermfg={cterm["red"]}
  hi @keyword.exception guifg={p["accent"]} ctermfg={cterm["accent"]}
  hi @conditional guifg={p["accent"]} ctermfg={cterm["accent"]}
  hi @conditional.ternary guifg={p["accent"]} ctermfg={cterm["accent"]}
  hi @repeat guifg={p["accent"]} ctermfg={cterm["accent"]}
  hi @debug guifg={p["accent_light"]} ctermfg={cterm["red"]}
  hi @label guifg={p["accent"]} ctermfg={cterm["accent"]}
  hi @include guifg={p["accent"]} ctermfg={cterm["accent"]}
  hi @exception guifg={p["accent"]} ctermfg={cterm["accent"]}
  
  hi @type guifg={p["accent_rose"]} ctermfg={cterm["accent_rose"]}
  hi @type.builtin guifg={p["accent_rose"]} ctermfg={cterm["accent_rose"]} gui=italic
  hi @type.definition guifg={p["accent_rose"]} ctermfg={cterm["accent_rose"]}
  hi @type.qualifier guifg={p["accent"]} ctermfg={cterm["accent"]}
  hi @storageclass guifg={p["accent"]} ctermfg={cterm["accent"]}
  hi @attribute guifg={p["accent_hover"]} ctermfg={cterm["accent"]} gui=italic
  hi @field guifg={p["text"]} ctermfg={cterm["fg"]}
  hi @property guifg={p["text_muted"]} ctermfg={cterm["text_muted"]}
  hi @variable guifg={p["text"]} ctermfg={cterm["fg"]}
  hi @variable.builtin guifg={p["accent"]} ctermfg={cterm["accent"]} gui=italic
  hi @variable.parameter guifg={p["text"]} ctermfg={cterm["fg"]} gui=italic
  hi @variable.member guifg={p["text_muted"]} ctermfg={cterm["text_muted"]}
  
  hi @constant guifg={p["accent_hover"]} ctermfg={cterm["accent"]}
  hi @constant.builtin guifg={p["accent_hover"]} ctermfg={cterm["accent"]} gui=italic
  hi @constant.macro guifg={p["accent"]} ctermfg={cterm["accent"]}
  
  hi @namespace guifg={p["magenta"]} ctermfg={cterm["magenta"]}
  hi @symbol guifg={p["accent"]} ctermfg={cterm["accent"]}
  
  " LSP
  hi @lsp.type.class guifg={p["accent_rose"]} ctermfg={cterm["accent_rose"]}
  hi @lsp.type.decorator guifg={p["accent_hover"]} ctermfg={cterm["accent"]} gui=italic
  hi @lsp.type.enum guifg={p["accent_rose"]} ctermfg={cterm["accent_rose"]}
  hi @lsp.type.enumMember guifg={p["accent_hover"]} ctermfg={cterm["accent"]}
  hi @lsp.type.function guifg={p["cyan"]} ctermfg={cterm["cyan"]}
  hi @lsp.type.interface guifg={p["accent_rose"]} ctermfg={cterm["accent_rose"]}
  hi @lsp.type.macro guifg={p["accent"]} ctermfg={cterm["accent"]}
  hi @lsp.type.method guifg={p["cyan"]} ctermfg={cterm["cyan"]}
  hi @lsp.type.namespace guifg={p["magenta"]} ctermfg={cterm["magenta"]}
  hi @lsp.type.parameter guifg={p["text"]} ctermfg={cterm["fg"]} gui=italic
  hi @lsp.type.property guifg={p["text_muted"]} ctermfg={cterm["text_muted"]}
  hi @lsp.type.struct guifg={p["accent_rose"]} ctermfg={cterm["accent_rose"]}
  hi @lsp.type.type guifg={p["accent_rose"]} ctermfg={cterm["accent_rose"]}
  hi @lsp.type.typeParameter guifg={p["accent_rose"]} ctermfg={cterm["accent_rose"]}
  hi @lsp.type.variable guifg={p["text"]} ctermfg={cterm["fg"]}
endif

" ═══════════════════════════════════════════════════════════════════════════════
" HTML / XML / Markdown
" ═══════════════════════════════════════════════════════════════════════════════

hi htmlArg guifg={p["accent_hover"]} ctermfg={cterm["accent"]}
hi htmlBold guifg={p["accent_rose"]} ctermfg={cterm["accent_rose"]} gui=bold
hi htmlEndTag guifg={p["accent"]} ctermfg={cterm["accent"]}
hi htmlH1 guifg={p["accent"]} ctermfg={cterm["accent"]} gui=bold
hi htmlH2 guifg={p["accent"]} ctermfg={cterm["accent"]} gui=bold
hi htmlH3 guifg={p["accent"]} ctermfg={cterm["accent"]} gui=bold
hi htmlH4 guifg={p["accent"]} ctermfg={cterm["accent"]} gui=bold
hi htmlH5 guifg={p["accent"]} ctermfg={cterm["accent"]} gui=bold
hi htmlH6 guifg={p["accent"]} ctermfg={cterm["accent"]} gui=bold
hi htmlItalic guifg={p["accent_soft"]} ctermfg={cterm["accent_soft"]} gui=italic
hi htmlLink guifg={p["accent"]} ctermfg={cterm["accent"]} gui=underline
hi htmlTag guifg={p["accent"]} ctermfg={cterm["accent"]}
hi htmlTagName guifg={p["accent"]} ctermfg={cterm["accent"]}
hi htmlTitle guifg={p["accent"]} ctermfg={cterm["accent"]} gui=bold

hi markdownBold guifg={p["accent_rose"]} ctermfg={cterm["accent_rose"]} gui=bold
hi markdownCode guifg={p["cyan"]} ctermfg={cterm["cyan"]}
hi markdownCodeBlock guifg={p["cyan"]} ctermfg={cterm["cyan"]}
hi markdownH1 guifg={p["accent"]} ctermfg={cterm["accent"]} gui=bold
hi markdownH2 guifg={p["accent"]} ctermfg={cterm["accent"]} gui=bold
hi markdownH3 guifg={p["accent"]} ctermfg={cterm["accent"]} gui=bold
hi markdownH4 guifg={p["accent"]} ctermfg={cterm["accent"]} gui=bold
hi markdownH5 guifg={p["accent"]} ctermfg={cterm["accent"]} gui=bold
hi markdownH6 guifg={p["accent"]} ctermfg={cterm["accent"]} gui=bold
hi markdownItalic guifg={p["accent_soft"]} ctermfg={cterm["accent_soft"]} gui=italic
hi markdownLink guifg={p["accent"]} ctermfg={cterm["accent"]} gui=underline
hi markdownListMarker guifg={p["accent"]} ctermfg={cterm["accent"]}
hi markdownOrderedListMarker guifg={p["accent_soft"]} ctermfg={cterm["accent_soft"]}
hi markdownRule guifg={p["border"]} ctermfg={cterm["text_dim"]}
hi markdownUrl guifg={p["accent"]} ctermfg={cterm["accent"]} gui=underline

" ═══════════════════════════════════════════════════════════════════════════════
" NERDTree / Netrw / File Browsers
" ═══════════════════════════════════════════════════════════════════════════════

hi NERDTreeDir guifg={p["accent"]} ctermfg={cterm["accent"]}
hi NERDTreeDirSlash guifg={p["accent"]} ctermfg={cterm["accent"]}
hi NERDTreeOpenable guifg={p["accent"]} ctermfg={cterm["accent"]}
hi NERDTreeClosable guifg={p["accent"]} ctermfg={cterm["accent"]}
hi NERDTreeFile guifg={p["text"]} ctermfg={cterm["fg"]}
hi NERDTreeExecFile guifg={p["green"]} ctermfg={cterm["green"]}
hi NERDTreeUp guifg={p["text_muted"]} ctermfg={cterm["text_muted"]}
hi NERDTreeCWD guifg={p["accent_rose"]} ctermfg={cterm["accent_rose"]} gui=bold
hi NERDTreeHelp guifg={p["text"]} ctermfg={cterm["fg"]}
hi NERDTreeToggleOn guifg={p["green"]} ctermfg={cterm["green"]}
hi NERDTreeToggleOff guifg={p["accent_light"]} ctermfg={cterm["red"]}

" Netrw
hi netrwDir guifg={p["accent"]} ctermfg={cterm["accent"]}
hi netrwClassify guifg={p["accent"]} ctermfg={cterm["accent"]}
hi netrwLink guifg={p["cyan"]} ctermfg={cterm["cyan"]}
hi netrwSymLink guifg={p["cyan"]} ctermfg={cterm["cyan"]}
hi netrwExe guifg={p["green"]} ctermfg={cterm["green"]}
hi netrwComment guifg={p["text_dim"]} ctermfg={cterm["text_dim"]}
hi netrwList guifg={p["text_muted"]} ctermfg={cterm["text_muted"]}
hi netrwHelpCmd guifg={p["cyan"]} ctermfg={cterm["cyan"]}
hi netrwCmdSep guifg={p["text_muted"]} ctermfg={cterm["text_muted"]}
hi netrwVersion guifg={p["accent_rose"]} ctermfg={cterm["accent_rose"]}

" ═══════════════════════════════════════════════════════════════════════════════
" Quickfix / Location List
" ═══════════════════════════════════════════════════════════════════════════════

hi qfFileName guifg={p["cyan"]} ctermfg={cterm["cyan"]}
hi qfLineNr guifg={p["text_dim"]} ctermfg={cterm["text_dim"]}
hi qfError guifg={p["accent_light"]} ctermfg={cterm["red"]}

" ═══════════════════════════════════════════════════════════════════════════════
" Mode Messages
" ═══════════════════════════════════════════════════════════════════════════════

hi ModeMsg guifg={p["accent"]} ctermfg={cterm["accent"]} gui=bold
hi MoreMsg guifg={p["green"]} ctermfg={cterm["green"]} gui=bold
hi Question guifg={p["accent"]} ctermfg={cterm["accent"]} gui=bold

" ═══════════════════════════════════════════════════════════════════════════════
" End of color scheme
" ═══════════════════════════════════════════════════════════════════════════════
" To use this theme, add to your .vimrc or init.vim:
"
"   colorscheme {slug}
"
" Or for conditional loading:
"
"   if filereadable(expand("~/.vim/colors/{slug}.vim"))
"     colorscheme {slug}
"   endif
" ═══════════════════════════════════════════════════════════════════════════════
"""


def write_editor_files(output_dir: Path, p: dict, name: str):
    """Write all editor theme files."""
    slug = name.lower().replace(" ", "-")

    # VS Code
    vsc_dir = output_dir / "editors" / "vscode"
    vsc_themes = vsc_dir / "themes"
    vsc_themes.mkdir(parents=True, exist_ok=True)
    (vsc_dir / "package.json").write_text(generate_vscode_package_json(name, p))
    (vsc_themes / f"{slug}-color-theme.json").write_text(generate_vscode_theme(p, name))
    (vsc_dir / "settings.json").write_text(generate_vscode_settings(name, p))

    # Antigravity (same VS Code format)
    ag_dir = output_dir / "editors" / "antigravity"
    ag_themes = ag_dir / "themes"
    ag_themes.mkdir(parents=True, exist_ok=True)
    (ag_dir / "package.json").write_text(generate_vscode_package_json(name, p))
    (ag_themes / f"{slug}-color-theme.json").write_text(generate_vscode_theme(p, name))
    (ag_dir / "settings.json").write_text(generate_vscode_settings(name, p))

    # OpenCode
    oc_dir = output_dir / "editors" / "opencode"
    oc_dir.mkdir(parents=True, exist_ok=True)
    theme_slug = slug.replace("-", "")
    (oc_dir / f"{theme_slug}.json").write_text(generate_opencode_theme(p, name))
    # tui.json controls the active theme; opencode.json is for general settings
    oc_tui = {"$schema": "https://opencode.ai/tui.json", "theme": theme_slug}
    (oc_dir / "tui.json").write_text(json.dumps(oc_tui, indent=2))

    # Kilo Code — uses kilo.jsonc for config, themes/*.json for theme files
    kilo_dir = output_dir / "editors" / "kilo"
    kilo_dir.mkdir(parents=True, exist_ok=True)
    (kilo_dir / f"{theme_slug}.json").write_text(generate_opencode_theme(p, name))
    kilo_config = {"theme": theme_slug}
    (kilo_dir / "kilo.jsonc").write_text(json.dumps(kilo_config, indent=2))

    # Codex CLI
    codex_dir = output_dir / "editors" / "codex"
    codex_dir.mkdir(parents=True, exist_ok=True)
    codex_theme_slug = slug
    (codex_dir / f"{codex_theme_slug}.tmTheme").write_text(
        generate_codex_tmtheme(p, name)
    )
    codex_config = {"tui": {"theme": codex_theme_slug}}
    (codex_dir / "config.json").write_text(json.dumps(codex_config, indent=2))

    # Vim / Neovim
    vim_dir = output_dir / "editors" / "vim"
    vim_colors = vim_dir / "colors"
    vim_colors.mkdir(parents=True, exist_ok=True)
    vim_slug = name.lower().replace(" ", "_")
    (vim_colors / f"{vim_slug}.vim").write_text(generate_vim_theme(p, name))
