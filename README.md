# waybar-rss

RSS reader as a Waybar custom module + HTML view — for Hyprland / Wayland compositors.

## How it works

- **Waybar module:** Shows RSS icon with article count for a configurable time window.
- **Left click:** Opens `index.html` with all articles from the last N hours, grouped by feed.
- **Right click:** Forces immediate refresh + HTML regeneration.
- **systemd timer:** Regenerates the HTML page every hour automatically.

## Features

| Feature | Description |
|---|---|
| Time window | Configurable in hours (default: 24h) |
| HTML view | Dark theme, articles with title + link + date + summary |
| Tooltip | Current headlines directly in Waybar |
| Auto-update | Hourly background regeneration via systemd timer |
| No external deps | Python 3 only (stdlib + urllib) |
| Idle blogs | If a feed has no articles in the time window, its latest article is shown anyway |

## Installation

```bash
git clone https://github.com/saigkill/waybar-rss.git
cd waybar-rss
./install.sh
```

This copies the script, installs the systemd timer, and creates the config directory.

## Uninstall

```bash
./uninstall.sh
```

Removes the script, config, cache, generated HTMLs, and systemd timer. You'll still need to manually clean up the Waybar config.

## Waybar Integration

In `~/.config/waybar/config.jsonc`:

```jsonc
// Add "custom/rss" to modules-center or modules-right:
"custom/rss": {
    "format": "{}",
    "exec": "waybar-rss.py read",
    "on-click": "waybar-rss.py open",
    "on-click-right": "waybar-rss.py generate",
    "return-type": "json",
    "interval": 300,
    "tooltip": true
}
```

In `~/.config/waybar/style.css`:

```css
#custom-rss.has-articles { color: #a6e3a1; }
#custom-rss.no-articles { color: #6c7086; }
```

Restart Waybar:

```bash
omarchy restart waybar   # on Omarchy
# or:
pkill waybar && waybar &
```

## Configuration

**`~/.config/waybar-rss/config.json`:**
```json
{
  "hours": 24,
  "html_path": "/home/sascha/.local/share/waybar-rss/index.html"
}
```

**`~/.config/waybar-rss/feeds.txt`:**
```
https://news.ycombinator.com/rss
https://www.heise.de/rss/heise.rdf
# ...
```

## Commands

```bash
waybar-rss.py generate   # Regenerate HTML page
waybar-rss.py read       # Output JSON for Waybar
waybar-rss.py open       # Open HTML in browser
```

## Project Files

| File | Purpose |
|---|---|
| `waybar-rss.py` | Main script — fetches feeds, outputs JSON, generates HTML |
| `waybar-config.jsonc` | Waybar module block snippet |
| `waybar-style.css` | Waybar CSS snippet |
| `feeds.txt` | RSS feed URL list |
| `config.json` | Configuration (hours, html_path) |
| `install.sh` | Installation script |
| `uninstall.sh` | Uninstall script |

## License

MIT
