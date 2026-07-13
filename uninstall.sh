#!/usr/bin/env bash
set -euo pipefail

echo "=== waybar-rss deinstallieren ==="

echo "→ systemd-Timer stoppen und entfernen"
systemctl --user stop waybar-rss.timer 2>/dev/null || true
systemctl --user disable waybar-rss.timer 2>/dev/null || true
systemctl --user daemon-reload

rm -f ~/.config/systemd/user/waybar-rss.service
rm -f ~/.config/systemd/user/waybar-rss.timer

echo "→ Script entfernen"
rm -f ~/.local/bin/waybar-rss.py

echo "→ Konfiguration entfernen"
rm -rf ~/.config/waybar-rss

echo "→ Cache und generierte HTML-Dateien entfernen"
rm -rf ~/.cache/waybar-rss
rm -rf ~/.local/share/waybar-rss

echo ""
echo "=== Fertig ==="
echo ""
echo "Noch manuell zu entfernen:"
echo "1. 'custom/rss' aus modules-center in ~/.config/waybar/config.jsonc"
echo "2. Den custom/rss-Modul-Block aus der config.jsonc"
echo "3. #custom-rss CSS-Regeln aus ~/.config/waybar/style.css"
echo "4. omarchy restart waybar"
