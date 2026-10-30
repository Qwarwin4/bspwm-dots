#!/bin/sh

polybar-msg cmd quit >/dev/null 2>&1
killall -q polybar
while pgrep -u "$(id -u)" -x polybar >/dev/null; do sleep 0.2; done

hw="$HOME/.config/bspwm/hardware"
if [ -f "$hw" ]; then
    set -a
    # shellcheck disable=SC1090
    . "$hw"
    set +a
fi

for dir in /sys/class/hwmon/hwmon*; do
    case "$(cat "$dir/name" 2>/dev/null)" in
        coretemp|k10temp|zenpower|cpu_thermal|acpitz)
            if [ -f "$dir/temp1_input" ]; then
                export HWMON_PATH="$dir/temp1_input"
                break
            fi
            ;;
    esac
done

for ps in /sys/class/power_supply/*; do
    [ -e "$ps/type" ] || continue
    case "$(cat "$ps/type")" in
        Battery) [ -z "$BATTERY" ] && [ "$(cat "$ps/scope" 2>/dev/null)" != "Device" ] && export BATTERY="${ps##*/}" ;;
        Mains) [ -z "$ADAPTER" ] && export ADAPTER="${ps##*/}" ;;
    esac
done

if [ -z "$BACKLIGHT_CARD" ]; then
    bl=$(ls /sys/class/backlight 2>/dev/null | head -n1)
    [ -n "$bl" ] && export BACKLIGHT_CARD="$bl"
fi

net=""
ls /sys/class/net/*/wireless >/dev/null 2>&1 && net="wlan"
[ -z "$net" ] && net="eth"

right=""
[ -n "$BATTERY" ] && [ "$BATTERY" != none ] && right="$right battery"
[ -n "$BACKLIGHT_CARD" ] && [ "$BACKLIGHT_CARD" != none ] && right="$right backlight"
right="$right pulseaudio xkeyboard cap-l date cap-r sp $net powermenu"

prim=$(xrandr --query | awk '/ connected primary/{print $1; exit}')
mons=$(polybar --list-monitors 2>/dev/null | cut -d: -f1)
[ -z "$prim" ] && prim=$(echo "$mons" | head -n1)

for m in $mons; do
    if [ "$m" = "$prim" ]; then
        BAR_RIGHT="$right tray"
    else
        BAR_RIGHT="$right"
    fi
    MONITOR=$m BAR_RIGHT=$BAR_RIGHT polybar main >"/tmp/polybar-$(id -u)-$m.log" 2>&1 &
done

[ -z "$mons" ] && polybar main >"/tmp/polybar-$(id -u).log" 2>&1 &
