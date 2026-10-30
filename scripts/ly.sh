#!/usr/bin/env bash
# палитра консоли и ly из *color0..15 в ~/.Xresources
# LY_ANIMATION=wallpaper|none|doom|matrix|colormix|gameoflife

set -euo pipefail

anim=${LY_ANIMATION:-wallpaper}
src=${1:-}
dir=$(cd "$(dirname "$(readlink -f "$0")")/.." && pwd)

[ "$(id -u)" -eq 0 ] || { echo "Нужен root: su -c $0" >&2; exit 1; }

u=${SUDO_USER:-}
[ "$u" = root ] && u=""
if [ -z "$u" ] && [ -r /proc/self/loginuid ]; then
    uid=$(cat /proc/self/loginuid)
    [ "$uid" != 4294967295 ] && [ "$uid" != 0 ] && u=$(id -nu "$uid" 2>/dev/null || true)
fi
if [ -z "$src" ] && [ -n "$u" ]; then
    src="$(getent passwd "$u" | cut -d: -f6)/.Xresources"
fi
[ -f "$src" ] || src="$dir/home/.Xresources"
[ -f "$src" ] || { echo "Не найден .Xresources с палитрой" >&2; exit 1; }
if [ -z "$u" ]; then
    u=$(stat -c %U "$src")
    [ "$u" = root ] && u=""
fi

declare -a pal
while read -r i hex; do
    pal[i]=$hex
done < <(awk -F'[: \t]+' '/^\*\.?color([0-9]|1[0-5]):/ {
    sub(/^\*\.?color/, "", $1); print $1, $2
}' "$src")

for i in $(seq 0 15); do
    [[ ${pal[i]:-} =~ ^#[0-9a-fA-F]{6}$ ]] || { echo "В $src нет корректного *color$i" >&2; exit 1; }
done

r="" g="" b=""
for i in $(seq 0 15); do
    h=${pal[i]#\#}
    r+="$((16#${h:0:2})),"
    g+="$((16#${h:2:2})),"
    b+="$((16#${h:4:2})),"
done
printf '%s\n%s\n%s\n' "${r%,}" "${g%,}" "${b%,}" >/etc/vtrgb

cat >/etc/systemd/system/vtrgb.service <<'EOF'
[Unit]
Description=Console color palette
DefaultDependencies=no
After=systemd-vconsole-setup.service
Before=getty.target display-manager.service
ConditionPathExists=/etc/vtrgb

[Service]
Type=oneshot
ExecStart=/usr/bin/setvtrgb /etc/vtrgb
RemainAfterExit=yes

[Install]
WantedBy=sysinit.target
EOF
systemctl enable vtrgb.service >/dev/null 2>&1 || true
setvtrgb /etc/vtrgb 2>/dev/null || true
echo "Палитра TTY: $src → /etc/vtrgb"

cfg=""
[ -f /etc/ly/config.lua ] && cfg=/etc/ly/config.lua
[ -z "$cfg" ] && [ -f /etc/ly/config.ini ] && cfg=/etc/ly/config.ini
if [ -z "$cfg" ]; then
    echo "ly не установлен — настроена только консоль"
    exit 0
fi
[ -f "$cfg.orig" ] || cp "$cfg" "$cfg.orig"

set_opt() {
    local k=$1 v=$2 kind=${3:-raw}
    if [[ $cfg == *.lua ]]; then
        [ "$kind" = str ] && v="\"$v\""
        sed -i -E "s|^([[:space:]]*)(--[[:space:]]*)?${k}[[:space:]]*=.*,[[:space:]]*\$|\1$k = $v,|" "$cfg"
    elif grep -Eq "^#?[[:space:]]*${k}[[:space:]]*=" "$cfg"; then
        sed -i -E "s|^#?[[:space:]]*${k}[[:space:]]*=.*|$k = $v|" "$cfg"
    else
        printf '%s = %s\n' "$k" "$v" >>"$cfg"
    fi
}

# 0x0001..0x0008: black red green yellow blue magenta cyan white, 0x01…… — bold
set_opt full_color false
set_opt bg 0x00000000
set_opt fg 0x00000008
set_opt border_fg 0x00000006
set_opt error_fg 0x01000002
set_opt error_bg 0x00000000
set_opt blank_box true
set_opt hide_version_string true
set_opt bigclock en str
set_opt clock "%a, %d %b  %H:%M" str
if [ "$anim" = wallpaper ]; then
    lib=/usr/local/lib/bspwm-dots
    state=/var/lib/bspwm-dots
    install -d -m 755 "$lib" "$state"
    install -m 755 "$dir/system/ly-dur" "$dir/system/ly-wallpaper" "$lib/"
    install -m 644 "$dir/system/ly-empty.dur" "$lib/"

    if [ -n "$u" ]; then
        install -d -m 755 -o "$u" -g "$(id -gn "$u")" "$state/user"
        cur="$(getent passwd "$u" | cut -d: -f6)/.cache/wallpaper"
        if [ -f "$cur" ] && [ ! -s "$state/user/wallpaper" ]; then
            runuser -u "$u" -- sh -c 'head -n1 "$1" >"$2"' _ "$cur" "$state/user/wallpaper" || true
        fi
    fi

    for unit in ly@.service ly.service; do
        mkdir -p "/etc/systemd/system/$unit.d"
        printf '[Service]\nExecStartPre=-%s/ly-wallpaper %%I\n' "$lib" >"/etc/systemd/system/$unit.d/wallpaper.conf"
    done
    systemctl daemon-reload >/dev/null 2>&1 || true
    "$lib/ly-wallpaper" tty2 || true

    set_opt animation dur_file str
    set_opt dur_file_path "$state/ly.dur" str
    set_opt dur_offset_alignment center str
    set_opt dur_x_offset 0
    set_opt dur_y_offset 0
    set_opt animation_timeout_sec 0
else
    rm -f /etc/systemd/system/ly@.service.d/wallpaper.conf /etc/systemd/system/ly.service.d/wallpaper.conf
    systemctl daemon-reload >/dev/null 2>&1 || true
    set_opt animation "$anim" str
fi
set_opt doom_top_color 0x00000002
set_opt doom_middle_color 0x00000004
set_opt doom_bottom_color 0x00000008
set_opt cmatrix_fg 0x00000006
set_opt cmatrix_head_col 0x01000008
set_opt colormix_col1 0x00000002
set_opt colormix_col2 0x00000006
set_opt colormix_col3 0x00000001
set_opt gameoflife_fg 0x00000006

echo "ly: $cfg (оригинал — $cfg.orig), анимация: $anim"
echo "Новый вид — после выхода из сессии или перезагрузки"
