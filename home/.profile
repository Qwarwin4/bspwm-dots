case ":$PATH:" in
    *":$HOME/.local/bin:"*) ;;
    *) PATH="$HOME/.local/bin:$HOME/.cargo/bin:$HOME/go/bin:$PATH" ;;
esac
export PATH

export EDITOR=nvim
export VISUAL=nvim
export PAGER=less
export MANPAGER="sh -c 'col -bx | bat -l man -p'"
export MANROFFOPT="-c"
export BROWSER=firefox
export TERMINAL=alacritty

export XDG_CONFIG_HOME="$HOME/.config"
export XDG_CACHE_HOME="$HOME/.cache"
export XDG_DATA_HOME="$HOME/.local/share"
export XDG_STATE_HOME="$HOME/.local/state"

export LESSHISTFILE=-
export CM_LAUNCHER=rofi

[ -f "$HOME/.profile.local" ] && . "$HOME/.profile.local"
