#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=== waybar-rss installieren ==="

mkdir -p ~/.local/bin
cp "$SCRIPT_DIR/waybar-rss.py" ~/.local/bin/waybar-rss.py
chmod +x ~/.local/bin/waybar-rss.py

mkdir -p ~/.config/waybar-rss
[ -f "$SCRIPT_DIR/feeds.txt" ] && cp "$SCRIPT_DIR/feeds.txt" ~/.config/waybar-rss/feeds.txt
[ -f "$SCRIPT_DIR/config.json" ] && cp "$SCRIPT_DIR/config.json" ~/.config/waybar-rss/config.json

if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
    echo "⚠  ~/.local/bin ist nicht im PATH."
    echo "   Füge zu ~/.bashrc / ~/.zshrc hinzu:"
    echo "   export PATH=\"\$HOME/.local/bin:\$PATH\""
fi

# systemd-Timer für stündliche HTML-Generierung
mkdir -p ~/.config/systemd/user
cat > ~/.config/systemd/user/waybar-rss.service << 'SERVICE'
[Unit]
Description=Generate RSS HTML page

[Service]
Type=oneshot
ExecStart=%h/.local/bin/waybar-rss.py generate
SERVICE

cat > ~/.config/systemd/user/waybar-rss.timer << 'TIMER'
[Unit]
Description=Generate RSS HTML page hourly

[Timer]
OnCalendar=hourly
Persistent=true

[Install]
WantedBy=timers.target
TIMER

systemctl --user daemon-reload
systemctl --user enable --now waybar-rss.timer

echo ""
echo "=== Fertig ==="
echo ""
echo "Waybar-Integration:"
echo "1. 'custom/rss' zu modules-center in ~/.config/waybar/config.jsonc hinzufügen"
echo "2. Modul-Block aus waybar-config.jsonc einfügen"
echo "3. CSS-Regeln aus waybar-style.css in style.css einfügen"
echo "4. omarchy restart waybar"
echo ""
echo "Systemd-Timer aktiv: stündliche HTML-Generierung"
echo "HTML liegt unter: $(grep html_path ~/.config/waybar-rss/config.json 2>/dev/null | cut -d'"' -f4 || echo '~/.local/share/waybar-rss/index.html')"
