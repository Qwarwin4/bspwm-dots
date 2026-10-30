#!/usr/bin/env bash

set -uo pipefail

DIR=$(cd "$(dirname "$(readlink -f "$0")")/.." && pwd)
# shellcheck source=scripts/common.sh
. "$DIR/scripts/common.sh"

user=""
enable=1
home_files=1

while [ $# -gt 0 ]; do
    case "$1" in
        -u|--user) user=${2:-}; shift ;;
        --no-enable) enable=0 ;;
        --no-home) home_files=0 ;;
        -h|--help) echo "${BUNDLE_NAME:-$0} [-u USER] [--no-enable] [--no-home]"; exit 0 ;;
        *) die "Неизвестная опция: $1" ;;
    esac
    shift
done

need_root
pick_user

say "SDDM для $user"
pac_need sddm imagemagick || die "Не удалось установить sddm"

theme=/usr/share/sddm/themes/bspwm-dots
install -d "$theme"
install -m 644 "$DIR"/sddm/bspwm-dots/* "$theme/"
ok "Тема: $theme"

cursor=Adwaita
[ -d /usr/share/icons/Bibata-Modern-Classic ] && cursor=Bibata-Modern-Classic
install -d /etc/sddm.conf.d
cat >/etc/sddm.conf.d/10-bspwm-dots.conf <<EOF
[Theme]
Current=bspwm-dots
CursorTheme=$cursor
CursorSize=24

[Users]
RememberLastUser=true
RememberLastSession=true
EOF
ok "Конфиг: /etc/sddm.conf.d/10-bspwm-dots.conf"

pub=/var/lib/bspwm-dots/user
install -d -m 755 /var/lib/bspwm-dots
install -d -m 755 -o "$user" -g "$group" "$pub"

if [ "$home_files" = 1 ]; then
    put_user_file "$DIR/home/.local/bin/wallpaper" "$home/.local/bin/wallpaper" 755
    put_user_file "$DIR/home/.local/bin/lock" "$home/.local/bin/lock" 755
    as_user find "$home/.cache/lock" -name '*.png' -delete 2>/dev/null
    ok "Обновлены ~/.local/bin/wallpaper и lock (старые версии — *.bak)"
fi

cur=$(as_user head -n1 "$home/.cache/wallpaper" 2>/dev/null)
if [ -n "$cur" ] && as_user test -f "$cur"; then
    as_user sh -c 'printf "%s\n" "$1" >"$2/wallpaper"' _ "$cur" "$pub"
    if as_user magick "$cur" -resize '2560x2560>' -quality 90 "$pub/background.jpg"; then
        ok "Фон входа: $cur"
    else
        warn "Не удалось подготовить фон, будет встроенный"
    fi
else
    warn "Текущие обои не найдены — до первого Super + W будет встроенный фон"
fi

if [ "$enable" = 1 ]; then
    for u in ly@tty2.service ly.service; do
        if systemctl is-enabled "$u" >/dev/null 2>&1; then
            systemctl disable "$u" >/dev/null 2>&1 && ok "Отключён $u"
        fi
    done
    if [ -L /etc/systemd/system/display-manager.service ]; then
        cur_dm=$(basename "$(readlink -f /etc/systemd/system/display-manager.service)" .service)
        if [ "$cur_dm" != sddm ]; then
            systemctl disable display-manager.service >/dev/null 2>&1 && ok "Отключён $cur_dm"
        fi
    fi
    systemctl enable sddm.service >/dev/null 2>&1 || die "Не удалось включить sddm.service"
    ok "Включён sddm.service"
    echo
    say "Перезагрузись (reboot). Запускать sddm прямо сейчас не нужно — он займёт экран поверх текущей сессии."
fi
say "Посмотреть тему без выхода: sddm-greeter-qt6 --test-mode --theme $theme"
