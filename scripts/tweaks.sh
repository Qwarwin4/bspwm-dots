#!/usr/bin/env bash

set -uo pipefail

DIR=$(cd "$(dirname "$(readlink -f "$0")")/.." && pwd)
# shellcheck source=scripts/common.sh
. "$DIR/scripts/common.sh"

REPO=https://github.com/Zproger/bspwm-dotfiles.git
GTK_THEME=Dracula-pink-accent
ICONS=dracula-icons-main

user=""
do_ff=1
do_thunar=1
do_dracula=1

while [ $# -gt 0 ]; do
    case "$1" in
        -u|--user) user=${2:-}; shift ;;
        --no-firefox) do_ff=0 ;;
        --no-thunar) do_thunar=0 ;;
        --no-dracula) do_dracula=0 ;;
        -h|--help) echo "${BUNDLE_NAME:-$0} [-u USER] [--no-firefox] [--no-thunar] [--no-dracula]"; exit 0 ;;
        *) die "Неизвестная опция: $1" ;;
    esac
    shift
done

need_root
pick_user

ff_profiles() {
    local base ini
    for base in "$home/.mozilla/firefox" "$home/.config/mozilla/firefox"; do
        ini="$base/profiles.ini"
        [ -f "$ini" ] || continue
        awk -F= -v base="$base" '/^Path=/ {
            p = substr($0, 6)
            if (substr(p, 1, 1) != "/") p = base "/" p
            print p
        }' "$ini"
    done | sort -u | while read -r p; do
        [ -d "$p" ] && printf '%s\n' "$p"
    done
}

firefox_tweaks() {
    say "Firefox"
    if ! command -v firefox >/dev/null; then
        warn "Firefox не установлен — пропускаю"
        return
    fi

    local profiles
    profiles=$(ff_profiles)
    if [ -z "$profiles" ]; then
        say "Профиля ещё нет, создаю (первый запуск в фоне)"
        as_user timeout 25 firefox --headless about:blank >/dev/null 2>&1
        profiles=$(ff_profiles)
    fi
    if [ -z "$profiles" ]; then
        warn "Профиль Firefox не найден. Запусти Firefox один раз и повтори скрипт"
        return
    fi

    local p f
    while IFS= read -r p; do
        put_user_file "$DIR/firefox/user.js" "$p/user.js"
        for f in "$DIR"/firefox/chrome/*; do
            put_user_file "$f" "$p/chrome/$(basename "$f")"
        done
        ok "Профиль: ${p#"$home"/}"
    done <<<"$profiles"

    if pgrep -u "$user" -x firefox >/dev/null || pgrep -u "$user" -x firefox-bin >/dev/null; then
        warn "Firefox запущен — изменения появятся после его перезапуска"
    fi
}

dracula() {
    say "Тема и иконки Dracula из ZProger bspwm-dotfiles"
    local tmp
    tmp=$(as_user mktemp -d)
    if ! as_user git clone -q --depth 1 --filter=blob:none --sparse "$REPO" "$tmp/z" ||
        ! as_user git -C "$tmp/z" sparse-checkout set "themes/$GTK_THEME" "local/share/icons/$ICONS" >/dev/null 2>&1; then
        warn "Не удалось скачать тему из $REPO — Thunar останется в текущей теме"
        rm -rf "$tmp"
        return 1
    fi

    as_user mkdir -p "$home/.themes" "$home/.local/share/icons"
    as_user rm -rf "$home/.themes/$GTK_THEME" "$home/.local/share/icons/$ICONS"
    as_user cp -r "$tmp/z/themes/$GTK_THEME" "$home/.themes/"
    as_user cp -r "$tmp/z/local/share/icons/$ICONS" "$home/.local/share/icons/"
    rm -rf "$tmp"

    as_user sed -i 's/^Inherits=.*/Inherits=Papirus-Dark,breeze-dark,Adwaita,hicolor/' \
        "$home/.local/share/icons/$ICONS/index.theme"
    as_user gtk-update-icon-cache -q -f -t "$home/.local/share/icons/$ICONS" 2>/dev/null

    local ini
    for ini in "$home/.config/gtk-3.0/settings.ini" "$home/.config/gtk-4.0/settings.ini"; do
        as_user mkdir -p "$(dirname "$ini")"
        [ -f "$ini" ] || printf '[Settings]\n' | as_user tee "$ini" >/dev/null
        if grep -q '^gtk-icon-theme-name=' "$ini"; then
            as_user sed -i "s/^gtk-icon-theme-name=.*/gtk-icon-theme-name=$ICONS/" "$ini"
        else
            as_user sed -i "/^\[Settings\]/a gtk-icon-theme-name=$ICONS" "$ini"
        fi
    done
    ini="$home/.config/gtk-3.0/settings.ini"
    if grep -q '^gtk-theme-name=' "$ini"; then
        as_user sed -i "s/^gtk-theme-name=.*/gtk-theme-name=$GTK_THEME/" "$ini"
    else
        as_user sed -i "/^\[Settings\]/a gtk-theme-name=$GTK_THEME" "$ini"
    fi

    if [ -f "$home/.gtkrc-2.0" ]; then
        as_user sed -i -e "s/^gtk-theme-name=.*/gtk-theme-name=\"$GTK_THEME\"/" \
            -e "s/^gtk-icon-theme-name=.*/gtk-icon-theme-name=\"$ICONS\"/" "$home/.gtkrc-2.0"
    fi

    local g4="$home/.themes/$GTK_THEME/gtk-4.0" f
    if [ -d "$g4" ]; then
        for f in gtk.css gtk-dark.css assets; do
            [ -e "$g4/$f" ] && as_user ln -sfn "$g4/$f" "$home/.config/gtk-4.0/$f"
        done
    fi

    if command -v gsettings >/dev/null && command -v dbus-run-session >/dev/null; then
        as_user dbus-run-session sh -c '
            gsettings set org.gnome.desktop.interface gtk-theme "$1"
            gsettings set org.gnome.desktop.interface icon-theme "$2"
            gsettings set org.gnome.desktop.interface color-scheme prefer-dark
        ' _ "$GTK_THEME" "$ICONS" >/dev/null 2>&1
    fi
    ok "GTK: $GTK_THEME, иконки: $ICONS (откат — lxappearance или --no-dracula при установке)"
}

thunar_tweaks() {
    say "Thunar"
    pac_need thunar thunar-archive-plugin thunar-volman tumbler ffmpegthumbnailer \
        file-roller gvfs gvfs-mtp xclip fd fzf || warn "Часть пакетов для Thunar не установилась"

    put_user_file "$DIR/thunar/uca.xml" "$home/.config/Thunar/uca.xml"
    put_user_file "$DIR/thunar/thunar.xml" "$home/.config/xfce4/xfconf/xfce-perchannel-xml/thunar.xml"
    put_user_file "$DIR/home/.config/xfce4/helpers.rc" "$home/.config/xfce4/helpers.rc"
    ok "Действия в меню: терминал здесь, Neovim, сделать обоями, путь в буфер, от root, поиск fzf"

    local bm="$home/.config/gtk-3.0/bookmarks" d name
    as_user mkdir -p "$home/.config/gtk-3.0"
    as_user touch "$bm"
    for name in DOWNLOAD DOCUMENTS PICTURES MUSIC VIDEOS; do
        d=$(as_user xdg-user-dir "$name" 2>/dev/null)
        [ -n "$d" ] && [ "$d" != "$home" ] && [ -d "$d" ] || continue
        grep -qF "file://$d" "$bm" || printf 'file://%s\n' "$d" | as_user tee -a "$bm" >/dev/null
    done
    for d in "$home/.config" "$home/.local/bin"; do
        grep -qF "file://$d " "$bm" || printf 'file://%s %s\n' "$d" "${d##*/}" | as_user tee -a "$bm" >/dev/null
    done
    ok "Закладки в боковой панели"

    [ "$do_dracula" = 1 ] && dracula

    if pgrep -u "$user" -x thunar >/dev/null || pgrep -u "$user" -x Thunar >/dev/null; then
        warn "Thunar запущен — закрой его (thunar -q), чтобы он подхватил настройки"
    fi
}

[ "$do_ff" = 1 ] && firefox_tweaks
[ "$do_thunar" = 1 ] && thunar_tweaks
ok "Твики применены"
