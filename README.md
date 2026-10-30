# bspwm-dots

**English** | [Русский](README.ru.md)

[![License: GPL-3.0](https://img.shields.io/badge/license-GPL--3.0-blue)](LICENSE)
[![Email](https://img.shields.io/badge/email-qwarwin%40gmail.com-D14836?logo=gmail&logoColor=white)](mailto:qwarwin@gmail.com)
[![Telegram](https://img.shields.io/badge/Telegram-Channel-26A5E4?logo=telegram&logoColor=white)](https://t.me/qwarwin4git)

My bspwm dotfiles for Arch. It's a fork of [ZProger/bspwm-dotfiles](https://github.com/Zproger/bspwm-dotfiles): the look and wallpapers come from there, everything else is rewritten for current Arch. The old picom, polybar and rofi configs no longer work with recent versions, and I wanted an installer that isn't tied to specific user names or paths.

![desktop](assets/desktop.jpg)

<p>
<img src="assets/login.jpg" width="49%">
<img src="assets/lock.jpg" width="49%">
</p>

## What's inside

- bspwm + sxhkd, polybar, picom 12+ (blur, rounded corners, animations)
- rofi: apps, calculator, emoji, clipboard, power menu, Wi-Fi
- dunst, alacritty, starship
- zsh, fish or bash, your choice
- neovim with lazy.nvim and LSP through mason
- SDDM with its own theme, the login background follows your wallpaper
- lock screen on i3lock-color styled like SDDM: password dots, layout and Caps Lock
- Thunar and Firefox tweaks from the original repo

Compared to the original:

- Python installer that asks what you want: user, shell, which apps to install
- nothing hardcoded: battery, backlight, monitors and GPU are detected
- PipeWire audio, configs updated for current package versions
- `debug.py` that checks the setup and fixes common problems

## Installation

You need an installed Arch with a network connection; a minimal `archinstall` setup is enough.

```sh
su -c 'pacman -S --needed git python'
git clone https://github.com/Qwarwin4/bspwm-dots
cd bspwm-dots
su -c 'python install.py'
reboot
```

The installer runs as root so it doesn't stop to ask for a password. Old configs go to `~/.dots-backup/`, the log to `/var/log/bspwm-dots-install.log`. Running it again is fine.

```
python install.py -h
  -u, --user NAME          user, without asking
  -y, --yes                no questions, all defaults
      --shell zsh|fish|bash
      --no-aur
```

## If something breaks

From a terminal inside the bspwm session:

```sh
python debug.py          # check and offer fixes
python debug.py --fix    # fix without asking
```

## Keybindings

| Keys | Action |
|---|---|
| `Super + Enter` | terminal |
| `Super + Shift + Enter` | floating terminal |
| `Super + D` | app launcher |
| `Super + X` | power menu |
| `Super + V` | clipboard history |
| `Super + C` | close window (`Super + Alt + C` to kill) |
| `Super + Space` | toggle floating / tiled |
| `Super + F` | fullscreen |
| `Super + T` / `Super + Ctrl + T` | tiled / pseudo-tiled |
| `Super + M` | monocle |
| `Super + H/J/K/L`, arrows | focus |
| `Super + Alt + H/J/K/L` | swap windows |
| `Super + Ctrl + H/J/K/L` | resize window |
| `Super + Shift + arrows` | move floating window |
| `Super + 1…0` / `Super + Shift + 1…0` | switch desktop / move window |
| `Super + G` | swap with the biggest window |
| `Alt + Tab` | next window |
| `Super + P` | hide / show bar |
| `Super + W` | random wallpaper |
| `Super + Shift + W` | Wi-Fi |
| `Super + Shift + F` / `I` | Firefox / private window |
| `Super + Shift + N` | Thunar |
| `Super + Shift + T` | Telegram |
| `Super + Shift + C` | calculator |
| `Super + Shift + E` | emoji |
| `Super + Shift + X` | color picker |
| `Super + Shift + L` | lock screen |
| `Super + Shift + S` | btop |
| `Print` / `Shift + Print` | screenshot region / full screen |
| `Super + Esc` | reload sxhkd |
| `Ctrl + Shift + R` / `Q` | restart bspwm / quit |
| `Alt + Shift` | switch layout |

## Customizing

- autostart: `~/.config/bspwm/autostart.local`
- monitor layout: `~/.config/bspwm/screens`
- aliases and variables: `~/.zshrc.local`, `~/.bashrc.local`, `~/.config/fish/local.fish`
- bar colors: `~/.config/polybar/colors.ini`
- wallpapers: `~/Pictures/wallpapers`

Tested only on Arch with X11. No Wayland, it's bspwm.

## Credits

- [ZProger/bspwm-dotfiles](https://github.com/Zproger/bspwm-dotfiles), where it all started
- [i3lock-color](https://github.com/Raymo111/i3lock-color)
- [Dracula](https://draculatheme.com), [Catppuccin](https://github.com/catppuccin)

## License

[GPL-3.0](LICENSE). i3lock-color in `pkgs/i3lock-dots` keeps its own MIT license.
