# bspwm-dots

**English** | [Русский](README.ru.md)

[![License: GPL-3.0](https://img.shields.io/badge/license-GPL--3.0-blue)](LICENSE)
[![Email](https://img.shields.io/badge/email-qwarwin%40gmail.com-D14836?logo=gmail&logoColor=white)](mailto:qwarwin@gmail.com)
[![Telegram](https://img.shields.io/badge/Telegram-Channel-26A5E4?logo=telegram&logoColor=white)](https://t.me/qwarwin4git)

A bspwm setup for Arch Linux in the style of [ZProger/bspwm-dotfiles](https://github.com/Zproger/bspwm-dotfiles), rebuilt from scratch for current Arch: PipeWire, picom 12+, polybar 3.7, rofi 2, your choice of zsh, fish or bash, an interactive Python installer and `debug.py` for common problems.

![desktop](assets/desktop.jpg)

| | |
|---|---|
| WM | bspwm + sxhkd |
| Bar | polybar |
| Compositor | picom: blur, rounded corners, animations |
| Menus | rofi: apps, calculator, emoji, clipboard, power, Wi‑Fi |
| Notifications | dunst |
| Terminal | alacritty |
| Shell | zsh, fish or bash + starship, fzf, zoxide, eza, bat |
| Editor | neovim: lazy.nvim, mason, treesitter, blink.cmp |
| Login | SDDM with a custom theme |
| Lock screen | i3lock-dots (i3lock-color with password dots and Caps Lock) + xss-lock |
| Files | Thunar, yazi |
| Browser | Firefox with userChrome.css |

<p>
<img src="assets/login.jpg" width="49%">
<img src="assets/lock.jpg" width="49%">
</p>

## Installation

You need an installed Arch system with a network connection; a minimal `archinstall` setup is enough.

```sh
su -c 'pacman -S --needed git python'
git clone https://github.com/Qwarwin4/bspwm-dots
cd bspwm-dots
su -c 'python install.py'
reboot
```

The installer runs as root, so it never stops to ask for a password. AUR packages are built as your user through a temporary sudoers rule that is removed right after the build.

What it asks about:

- user name: configs are written for this user and SDDM preselects it on the login screen; if the user doesn't exist, the installer can create it
- shell: zsh, fish or bash
- app groups (Firefox, Thunar, mpv, Zathura, screenshots, Telegram) and development packages (Neovim, C/C++, Python, Node, Rust, Go, Docker), picked by number
- Firefox and Thunar tweaks, Dracula theme, AUR, ZProger wallpaper pack
- keyboard layouts (defaults from your locale, switched with Alt+Shift)
- battery and power adapter: found in `/sys/class/power_supply`, you are asked only if there are several
- backlight and brightness keys: press the keys and the installer detects what they send (`XF86MonBrightness`, `F3`/`F4`, etc.)
- NVIDIA driver if an NVIDIA card is present; SDDM autologin

SDDM with the theme is always installed, any other display manager (ly etc.) is disabled. Microcode, GPU drivers, VM guest tools, bluetooth, monitors and redshift coordinates (from your time zone) are detected automatically.

```
python install.py -h
  -u, --user NAME        user, without asking
  -y, --yes              no questions, all defaults
      --shell zsh|fish|bash
      --no-aur
      --lock             lock screen only
      --flameshot        screenshots (flameshot) only
```

Existing configs are backed up to `~/.dots-backup/<date>/`, the log goes to `/var/log/bspwm-dots-install.log`. Running it again is safe. Detected hardware is written to `~/.config/bspwm/hardware`, which you can edit by hand.

## Troubleshooting

```sh
python debug.py              # check everything and offer fixes
python debug.py lock         # one section: session lock brightness panel sddm system
python debug.py --fix        # fix everything without asking
python debug.py --keys       # re-detect brightness keys by pressing them
python debug.py --report     # write a report to ~/bspwm-debug.txt
```

Run it as your user from a terminal inside the bspwm session. Anything that needs root (building i3lock-dots, packages, SDDM) asks for your password via sudo.

## Standalone scripts

For an already configured system there are self-contained scripts. Build them with `tools/bundle.sh` (they end up in `dist/`):

| Script | What it does |
|---|---|
| `switch-to-sddm.sh` | installs SDDM with the theme, disables ly or another DM, updates `wallpaper` and `lock` |
| `firefox-thunar-tweaks.sh` | Firefox and Thunar tweaks, Dracula theme and icons |
| `lock-fix.sh` | lock screen: password dots and Caps Lock |
| `flameshot-fix.sh` | screenshots: makes flameshot 14 capture through X11 directly |

```sh
chmod +x lock-fix.sh
./lock-fix.sh
```

These run as a regular user and ask for root themselves, via sudo or the root password.

Inside the repository the same jobs are done by `scripts/sddm.sh`, `scripts/tweaks.sh` and `install.py --lock`; those run only as root (`su -c ...`) and all have `-h`.

## Login screen

The SDDM theme lives in `sddm/bspwm-dots`: your current wallpaper, clock, date, session picker, keyboard layout and power buttons. The background follows the desktop: `wallpaper` copies the image to `/var/lib/bspwm-dots/user/background.jpg`, since SDDM can't read your home directory. Colors, font and dimming are set in `/usr/share/sddm/themes/bspwm-dots/theme.conf`.

Preview the theme without logging out:

```sh
sddm-greeter-qt6 --test-mode --theme /usr/share/sddm/themes/bspwm-dots
```

### ly

If you prefer ly over SDDM: `su -c ./scripts/ly.sh` sets the console palette to your `~/.Xresources` colors (`/etc/vtrgb`, `vtrgb.service`) and configures a 16-color ly theme with the wallpaper drawn in half-blocks or an animation (`LY_ANIMATION=doom|matrix|colormix|gameoflife|none`). Installing and enabling ly itself is up to you.

## Lock screen

`Super + Shift + L`, plus automatically after 15 minutes of inactivity and before suspend. Blurred current wallpaper, clock, date and a password field styled like the SDDM login: a "Password" hint, dots while typing, "Checking..." and "Wrong password". The current layout and a live Caps Lock indicator sit in the bottom left. The layout switches to Latin before locking.

picom is stopped while the screen is locked and started again afterwards. With picom running, the lock screen can freeze: the clock stops, and after the screen blanks a stale frame of the desktop may show while input is already grabbed.

Dots and Caps Lock come from a small patch to i3lock-color (`pkgs/i3lock-dots`: patched sources plus a prebuilt fallback binary). `scripts/i3lock-dots.sh` compiles it in a couple of seconds without network access or makepkg, and installs the prebuilt binary if the build fails. The result is `/usr/local/bin/i3lock-dots` next to the regular i3lock; `lock` picks it up automatically.

Lock screen only, on an already configured system: `su -c 'python install.py --lock'` or `./lock-fix.sh` (the same installer in `--lock` mode). `~/.cache/lock/last-run` shows what was actually started on the last lock, errors go to `~/.cache/lock/error.log`.

## Screenshots

`Print` captures a region, `Shift + Print` copies the whole screen to the clipboard. Flameshot 14 captures through xdg-desktop-portal by default, but portal-gtk has no screenshot support, so on bspwm it silently fails. The installer sets `useX11LegacyScreenshot=true` in `~/.config/flameshot/flameshot.ini` to capture through X11 directly, only for version 14 and newer: older versions don't know the key and refuse to start with an error dialog. Separately: `su -c 'python install.py --flameshot'` or `./flameshot-fix.sh`.

## Brightness

Brightness keys go through systemd-logind, so you don't need to be in the `video` group. The installer asks which keys and which backlight to use; change it later with `python debug.py --keys` or by hand in `~/.config/bspwm/hardware` and the `# brightness-keys` block in `sxhkdrc`.

## Firefox and Thunar

Firefox: `user.js` (dark theme, blank new tab without ads, calculator in the address bar) and the original `userChrome.css`, rewritten for current Firefox variables and the dotfiles palette. Applied to every profile found in `~/.mozilla/firefox` and `~/.config/mozilla/firefox`.

Thunar:
- custom actions: open terminal here, open in Neovim, set as wallpaper, copy path, open as root, fzf search
- thumbnails, list view, folders first, bookmarks for XDG folders
- archive and removable media plugins
- Dracula-pink-accent GTK theme and dracula icons from the original repository, downloaded during install; disable with `--no-dracula`

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
| `Super + Ctrl + 1…9` | preselect split ratio |
| `Super + G` | swap with the biggest window |
| `Alt + Tab` | next window |
| `Super + P` | hide / show bar |
| `Super + W` | random wallpaper |
| `Super + Shift + W` | Wi‑Fi |
| `Super + Shift + F` / `I` | Firefox / private window |
| `Super + Shift + N` | Thunar |
| `Super + Shift + P` | pavucontrol |
| `Super + Shift + T` | Telegram |
| `Super + Shift + C` | calculator |
| `Super + Shift + E` | emoji |
| `Super + Shift + X` | color picker (copies to clipboard) |
| `Super + Shift + L` | lock screen |
| `Super + Shift + S` | btop |
| `Super + Shift + B` | bluetooth |
| `Super + Shift + M` | redetect monitors and restart bar |
| `Print` / `Shift + Print` | screenshot region / full screen |
| `Super + Esc` | reload sxhkd |
| `Ctrl + Shift + R` / `Q` | restart bspwm / quit |
| `Alt + Shift` | switch layout |

Media keys (volume, mic, brightness, player) work and show a slider notification.

## Customizing

- autostart: `~/.config/bspwm/autostart.local`
- your own monitor layout: `~/.config/bspwm/screens`, otherwise `autorandr`, otherwise everything to the right of the primary
- aliases and variables: `~/.zshrc.local`, `~/.bashrc.local`, `~/.config/fish/local.fish`, `~/.profile.local`
- bar colors: `~/.config/polybar/colors.ini`
- battery, adapter, backlight: `~/.config/bspwm/hardware`
- wallpapers: `~/Pictures/wallpapers`, `Super + W` picks a random one

## Layout

```
install.py              installer
debug.py                diagnostics and fixes
pkgs/*.txt              package lists, [groups] are offered as choices
pkgs/i3lock-dots/       patched i3lock-color: sources and prebuilt binary
home/                   everything copied into $HOME
scripts/sddm.sh         SDDM and its theme
scripts/tweaks.sh       Firefox and Thunar
scripts/i3lock-dots.sh  i3lock-dots build
scripts/ly.sh           console palette and ly
sddm/bspwm-dots/        SDDM theme
firefox/                user.js and chrome/
thunar/                 Thunar actions and settings
system/                 ly wallpaper helpers
wallpapers/             default wallpapers
tools/bundle.sh         builds standalone scripts into dist/
```

## Credits

- [ZProger/bspwm-dotfiles](https://github.com/Zproger/bspwm-dotfiles): the original look, wallpaper pack, Dracula theme and icons
- [Dracula](https://draculatheme.com) GTK theme and icons
- [Catppuccin](https://github.com/catppuccin) terminal and neovim palette
- [i3lock-color](https://github.com/Raymo111/i3lock-color), the base of i3lock-dots

## License

[GPL-3.0](LICENSE). The patched i3lock-color in `pkgs/i3lock-dots` keeps its own MIT license (`pkgs/i3lock-dots/src/LICENSE`).
