#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_ROOT="/usr/local/share/theme-maker"
BIN_PATH="/usr/local/bin/theme-maker"

if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
  echo "Run this installer with sudo: sudo $0" >&2
  exit 1
fi

install -d "$INSTALL_ROOT"
cp -a "$SCRIPT_DIR" "$INSTALL_ROOT/"

cat > "$BIN_PATH" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

export THEME_MAKER_HOME="/usr/local/share/theme-maker"
exec /usr/local/share/theme-maker/theme-maker/theme-maker "$@"
EOF

chmod 755 "$BIN_PATH"
chmod 755 "$INSTALL_ROOT/theme-maker/theme-maker"

echo "Installed theme-maker to $INSTALL_ROOT"
echo "Launcher available at $BIN_PATH"
