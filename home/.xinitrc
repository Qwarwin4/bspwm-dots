#!/bin/sh

if [ -d /etc/X11/xinit/xinitrc.d ]; then
    for f in /etc/X11/xinit/xinitrc.d/?*.sh; do
        [ -x "$f" ] && . "$f"
    done
    unset f
fi

[ -f "$HOME/.Xresources" ] && xrdb -nocpp -merge "$HOME/.Xresources"

exec bspwm
