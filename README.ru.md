# bspwm-dots

[English](README.md) | **Русский**

[![License: GPL-3.0](https://img.shields.io/badge/license-GPL--3.0-blue)](LICENSE)
[![Email](https://img.shields.io/badge/email-qwarwin%40gmail.com-D14836?logo=gmail&logoColor=white)](mailto:qwarwin@gmail.com)
[![Telegram](https://img.shields.io/badge/Telegram-Channel-26A5E4?logo=telegram&logoColor=white)](https://t.me/qwarwin4git)

Мои доты для bspwm на Arch. Это форк [ZProger/bspwm-dotfiles](https://github.com/Zproger/bspwm-dotfiles): внешний вид и обои оттуда, но всё остальное переписано заново под текущий Arch. Старые конфиги picom, polybar и rofi на свежих версиях уже не работают, а установщик хотелось сделать без привязки к конкретным именам и путям.

![desktop](assets/desktop.jpg)

<p>
<img src="assets/login.jpg" width="49%">
<img src="assets/lock.jpg" width="49%">
</p>

## Что внутри

- bspwm + sxhkd, polybar, picom 12+ (blur, скругления, анимации)
- rofi: приложения, калькулятор, эмодзи, буфер обмена, питание, Wi-Fi
- dunst, alacritty, starship
- zsh, fish или bash на выбор
- neovim на lazy.nvim с LSP через mason
- SDDM со своей темой, обои на экране входа те же, что на рабочем столе
- экран блокировки на i3lock-color в стиле SDDM: точки в поле пароля, раскладка и Caps Lock
- Thunar и Firefox с твиками из оригинального репозитория

Отличия от оригинала:

- установщик на Python и с вопросами: какой пользователь, какая оболочка, какие программы ставить
- ничего не захардкожено: батарея, подсветка, мониторы и видеокарта определяются сами
- звук на PipeWire, конфиги под текущие версии пакетов
- `debug.py`, который проверяет систему и чинит частые проблемы

## Установка

Нужен установленный Arch с интернетом, хватит минимальной установки через `archinstall`.

```sh
su -c 'pacman -S --needed git python'
git clone https://github.com/Qwarwin4/bspwm-dots
cd bspwm-dots
su -c 'python install.py'
reboot
```

Установщик запускается от root, чтобы не спрашивать пароль по ходу. Старые конфиги он сохраняет в `~/.dots-backup/`, лог пишет в `/var/log/bspwm-dots-install.log`. Запускать повторно можно.

```
python install.py -h
  -u, --user NAME          пользователь, без вопроса
  -y, --yes                без вопросов, всё по умолчанию
      --shell zsh|fish|bash
      --no-aur
```

## Если что-то не работает

Из терминала внутри сессии bspwm:

```sh
python debug.py          # проверить и предложить исправления
python debug.py --fix    # исправить без вопросов
```

## Горячие клавиши

| Клавиши | Действие |
|---|---|
| `Super + Enter` | терминал |
| `Super + Shift + Enter` | плавающий терминал |
| `Super + D` | меню приложений |
| `Super + X` | меню питания |
| `Super + V` | история буфера обмена |
| `Super + C` | закрыть окно (`Super + Alt + C` — убить) |
| `Super + Space` | плавающее / тайлинг |
| `Super + F` | полноэкранный режим |
| `Super + T` / `Super + Ctrl + T` | tiled / pseudo-tiled |
| `Super + M` | monocle |
| `Super + H/J/K/L`, стрелки | фокус |
| `Super + Alt + H/J/K/L` | поменять окна местами |
| `Super + Ctrl + H/J/K/L` | размер окна |
| `Super + Shift + стрелки` | двигать плавающее окно |
| `Super + 1…0` / `Super + Shift + 1…0` | рабочий стол / перенести окно |
| `Super + G` | поменять с самым большим окном |
| `Alt + Tab` | следующее окно |
| `Super + P` | скрыть / показать бар |
| `Super + W` | случайные обои |
| `Super + Shift + W` | Wi-Fi |
| `Super + Shift + F` / `I` | Firefox / приватное окно |
| `Super + Shift + N` | Thunar |
| `Super + Shift + T` | Telegram |
| `Super + Shift + C` | калькулятор |
| `Super + Shift + E` | эмодзи |
| `Super + Shift + X` | пипетка |
| `Super + Shift + L` | заблокировать экран |
| `Super + Shift + S` | btop |
| `Print` / `Shift + Print` | скриншот области / всего экрана |
| `Super + Esc` | перечитать sxhkd |
| `Ctrl + Shift + R` / `Q` | перезапустить bspwm / выйти |
| `Alt + Shift` | раскладка |

## Под себя

- автозапуск: `~/.config/bspwm/autostart.local`
- схема мониторов: `~/.config/bspwm/screens`
- алиасы и переменные: `~/.zshrc.local`, `~/.bashrc.local`, `~/.config/fish/local.fish`
- цвета бара: `~/.config/polybar/colors.ini`
- обои: `~/Pictures/wallpapers`

Проверял только на Arch под X11. Wayland не поддерживается, это bspwm.

## Благодарности

- [ZProger/bspwm-dotfiles](https://github.com/Zproger/bspwm-dotfiles), откуда всё началось
- [i3lock-color](https://github.com/Raymo111/i3lock-color)
- [Dracula](https://draculatheme.com), [Catppuccin](https://github.com/catppuccin)

## Лицензия

[GPL-3.0](LICENSE). i3lock-color в `pkgs/i3lock-dots` под своей лицензией MIT.
