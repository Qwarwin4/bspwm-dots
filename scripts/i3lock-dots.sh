#!/usr/bin/env bash
# i3lock-dots: i3lock-color с точками в поле пароля и живым индикатором Caps Lock.
# Собирается из pkgs/i3lock-dots/src без сети за пару секунд, если не вышло —
# ставится готовый бинарник. Ставится в /usr/local/bin и не трогает обычный i3lock.

set -uo pipefail

DIR=$(cd "$(dirname "$(readlink -f "$0")")/.." && pwd)
# shellcheck source=scripts/common.sh
. "$DIR/scripts/common.sh"

user=""
while [ $# -gt 0 ]; do
    case "$1" in
        -u|--user) user=${2:-}; shift ;;
        -h|--help) echo "${BUNDLE_NAME:-$0} [-u USER]"; exit 0 ;;
        *) die "Неизвестная опция: $1" ;;
    esac
    shift
done

need_root

SRC="$DIR/pkgs/i3lock-dots/src"
PREBUILT="$DIR/pkgs/i3lock-dots/i3lock-dots.x86_64"
DEST=/usr/local/bin/i3lock-dots
LOG=/var/log/i3lock-dots-build.log
MODS="xcb xcb-xkb xcb-xinerama xcb-randr xcb-composite xcb-image xcb-event xcb-util xcb-atom xcb-xrm xkbcommon xkbcommon-x11 cairo libjpeg fontconfig"

say "i3lock-dots: точки в поле пароля и индикатор Caps Lock"

if ! pac_need cairo fontconfig libev libjpeg-turbo libxcb libxkbcommon-x11 pam xcb-util xcb-util-image xcb-util-xrm >>"$LOG" 2>&1; then
    warn "Не все библиотеки доставились (pacman -Syu поможет), пробую с тем, что есть"
fi

usable() {
    [ -x "$1" ] || return 1
    if ldd "$1" 2>/dev/null | grep -q "not found"; then
        ldd "$1" | grep "not found" | sed 's/^/     нет библиотеки: /' >&2
        return 1
    fi
    "$1" --version 2>&1 | grep -q 'Cassandra Fox' && grep -aq I3LOCK_DOTS "$1"
}

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
bin=""

: >"$LOG"
if command -v gcc >/dev/null && command -v pkg-config >/dev/null; then
    cp -r "$SRC/." "$tmp/"
    # shellcheck disable=SC2086,SC2046
    if (cd "$tmp" && gcc -std=gnu11 -O2 -pipe -funroll-loops -pthread -I. $(pkg-config --cflags $MODS) \
        -o i3lock-dots ./*.c $(pkg-config --libs $MODS) -lev -lpam -lm) >>"$LOG" 2>&1 && usable "$tmp/i3lock-dots"; then
        bin="$tmp/i3lock-dots"
        ok "Собран из исходников"
    else
        warn "Сборка не вышла, ставлю готовый бинарник (лог: $LOG)"
        grep -E "error|not found|No package" "$LOG" | head -n 5 | sed 's/^/     /'
    fi
else
    warn "Нет gcc или pkg-config, ставлю готовый бинарник"
fi

if [ -z "$bin" ]; then
    if usable "$PREBUILT"; then
        bin=$PREBUILT
        ok "Готовый бинарник подходит"
    else
        die "Готовый бинарник не запускается. Обнови систему (pacman -Syu) и запусти ещё раз"
    fi
fi

install -Dm755 "$bin" "$DEST" || die "Не удалось записать $DEST"
if [ ! -f /etc/pam.d/i3lock-dots ]; then
    printf 'auth include system-local-login\n' >/etc/pam.d/i3lock-dots
    chmod 644 /etc/pam.d/i3lock-dots
fi
usable "$DEST" || die "$DEST не запускается"
ok "Установлен $DEST"
