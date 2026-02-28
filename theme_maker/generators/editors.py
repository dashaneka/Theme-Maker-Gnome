"""Editor theme generators - VS Code, OpenCode, Kilo."""

import json
from pathlib import Path
from theme_maker.palette import darken


def generate_vscode_theme(p: dict, name: str) -> str:
    data = {
        "name": name,
        "type": "dark",
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
            "activityBarBadge.foreground": "#ffffff",
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
            "statusBar.debuggingForeground": "#ffffff",
            "statusBar.noFolderBackground": p["bg_elevated"],
            "statusBarItem.activeBackground": p["accent"] + "40",
            "statusBarItem.hoverBackground": p["accent"] + "25",
            "statusBarItem.prominentBackground": p["accent"],
            "statusBarItem.prominentForeground": "#ffffff",
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
            "button.foreground": "#ffffff",
            "button.hoverBackground": p["accent_hover"],
            "button.secondaryBackground": p["bg_elevated"],
            "button.secondaryForeground": p["text"],
            "button.secondaryHoverBackground": p["border"],
            "badge.background": p["accent"],
            "badge.foreground": "#ffffff",
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


def generate_vscode_package_json(name: str) -> str:
    slug = name.lower().replace(" ", "-")
    data = {
        "name": f"{slug}-theme",
        "displayName": name,
        "description": f"Dark theme with accent colors - auto-generated by Theme Maker",
        "version": "1.0.0",
        "publisher": "theme-maker",
        "engines": {"vscode": "^1.60.0"},
        "categories": ["Themes"],
        "contributes": {
            "themes": [
                {
                    "label": name,
                    "uiTheme": "vs-dark",
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
            "text-muted": p["text_dim"],
            "text-dim": darken(p["text_dim"], 10),
            "scarlet-rose": p["accent_rose"],
            "deep-maroon": p["deep_maroon"],
            "green": p["green"],
            "red": p["accent_light"],
            "yellow": p["ansi_yellow"],
            "blue": p["blue"],
            "magenta": p["magenta"],
            "cyan": p["cyan"],
        },
        "theme": {
            "primary": {"dark": "accent", "light": "accent"},
            "secondary": {"dark": "accent-soft", "light": "accent-soft"},
            "accent": {"dark": "scarlet-rose", "light": "scarlet-rose"},
            "error": {"dark": "red", "light": "red"},
            "warning": {"dark": "yellow", "light": "yellow"},
            "success": {"dark": "green", "light": "green"},
            "info": {"dark": "accent-soft", "light": "accent-soft"},
            "text": {"dark": "text", "light": "bg-deepest"},
            "textMuted": {"dark": "text-muted", "light": "text-muted"},
            "background": {"dark": "bg-deepest", "light": "#f5f0f2"},
            "backgroundPanel": {"dark": "bg-main", "light": "#ece4e8"},
            "backgroundElement": {"dark": "bg-surface", "light": "#e0d8dc"},
            "border": {"dark": "border-main", "light": "border-main"},
            "borderActive": {"dark": "accent", "light": "accent"},
            "borderSubtle": {"dark": "border-dim", "light": "border-dim"},
            "diffAdded": {"dark": "green", "light": "green"},
            "diffRemoved": {"dark": "red", "light": "red"},
            "diffContext": {"dark": "text-muted", "light": "text-muted"},
            "diffHunkHeader": {"dark": "text-dim", "light": "text-dim"},
            "diffHighlightAdded": {"dark": "green", "light": "green"},
            "diffHighlightRemoved": {"dark": "red", "light": "red"},
            "diffAddedBg": {"dark": "#0d1a0d", "light": "#e8f5e8"},
            "diffRemovedBg": {"dark": "#1a0d10", "light": "#f5e8ea"},
            "diffContextBg": {"dark": "bg-main", "light": "#ece4e8"},
            "diffLineNumber": {"dark": "text-dim", "light": "text-dim"},
            "diffAddedLineNumberBg": {"dark": "#0d1a0d", "light": "#e8f5e8"},
            "diffRemovedLineNumberBg": {"dark": "#1a0d10", "light": "#f5e8ea"},
            "markdownText": {"dark": "text", "light": "bg-deepest"},
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
            "markdownCodeBlock": {"dark": "text", "light": "bg-deepest"},
            "syntaxComment": {"dark": "text-muted", "light": "text-muted"},
            "syntaxKeyword": {"dark": "accent", "light": "accent"},
            "syntaxFunction": {"dark": "scarlet-rose", "light": "scarlet-rose"},
            "syntaxVariable": {"dark": "cyan", "light": "cyan"},
            "syntaxString": {"dark": "green", "light": "green"},
            "syntaxNumber": {"dark": "magenta", "light": "magenta"},
            "syntaxType": {"dark": "accent-soft", "light": "accent-soft"},
            "syntaxOperator": {"dark": "accent-light", "light": "accent"},
            "syntaxPunctuation": {"dark": "text", "light": "bg-deepest"},
        },
    }
    return json.dumps(data, indent=2)


def write_editor_files(output_dir: Path, p: dict, name: str):
    """Write all editor theme files."""
    slug = name.lower().replace(" ", "-")

    # VS Code
    vsc_dir = output_dir / "editors" / "vscode"
    vsc_themes = vsc_dir / "themes"
    vsc_themes.mkdir(parents=True, exist_ok=True)
    (vsc_dir / "package.json").write_text(generate_vscode_package_json(name))
    (vsc_themes / f"{slug}-color-theme.json").write_text(generate_vscode_theme(p, name))
    (vsc_dir / "settings.json").write_text(generate_vscode_settings(name, p))

    # Antigravity (same VS Code format)
    ag_dir = output_dir / "editors" / "antigravity"
    ag_themes = ag_dir / "themes"
    ag_themes.mkdir(parents=True, exist_ok=True)
    (ag_dir / "package.json").write_text(generate_vscode_package_json(name))
    (ag_themes / f"{slug}-color-theme.json").write_text(generate_vscode_theme(p, name))
    (ag_dir / "settings.json").write_text(generate_vscode_settings(name, p))

    # OpenCode
    oc_dir = output_dir / "editors" / "opencode"
    oc_dir.mkdir(parents=True, exist_ok=True)
    theme_slug = slug.replace("-", "")
    (oc_dir / f"{theme_slug}.json").write_text(generate_opencode_theme(p, name))
    oc_config = {"theme": theme_slug}
    (oc_dir / "opencode.json").write_text(json.dumps(oc_config, indent=2))

    # Kilo (same as OpenCode)
    kilo_dir = output_dir / "editors" / "kilo"
    kilo_dir.mkdir(parents=True, exist_ok=True)
    (kilo_dir / f"{theme_slug}.json").write_text(generate_opencode_theme(p, name))
    kilo_kv = {"theme": theme_slug}
    (kilo_dir / "kv.json").write_text(json.dumps(kilo_kv, indent=2))
