[[ $- != *i* ]] && return

HISTFILE="${XDG_STATE_HOME:-$HOME/.local/state}/bash/history"
mkdir -p "${HISTFILE%/*}"
HISTSIZE=50000
HISTFILESIZE=50000
HISTCONTROL=ignoreboth:erasedups
shopt -s histappend autocd cdspell checkwinsize globstar
PROMPT_COMMAND="history -a${PROMPT_COMMAND:+; $PROMPT_COMMAND}"

[ -r /usr/share/bash-completion/bash_completion ] && . /usr/share/bash-completion/bash_completion

bind 'set completion-ignore-case on'
bind 'set show-all-if-ambiguous on'
bind 'set colored-stats on'
bind '"\e[A": history-search-backward'
bind '"\e[B": history-search-forward'

export FZF_DEFAULT_COMMAND='fd --type f --hidden --exclude .git'
export FZF_DEFAULT_OPTS='--height 40% --layout reverse --border rounded
  --color=bg+:#2b2f37,bg:-1,spinner:#f5e0dc,hl:#f38ba8
  --color=fg:#cdd6f4,header:#f38ba8,info:#cba6f7,pointer:#f5e0dc
  --color=marker:#b4befe,fg+:#cdd6f4,prompt:#cba6f7,hl+:#f38ba8'

command -v fzf >/dev/null && eval "$(fzf --bash)"
command -v zoxide >/dev/null && eval "$(zoxide init bash)"
command -v starship >/dev/null && eval "$(starship init bash)"

if command -v eza >/dev/null; then
    alias ls='eza --icons --group-directories-first'
    alias ll='eza -l --icons --git --group-directories-first'
    alias la='eza -la --icons --git --group-directories-first'
    alias lt='eza --tree --level=2 --icons'
fi
command -v bat >/dev/null && alias cat='bat --paging=never'
alias grep='grep --color=auto'
alias diff='diff --color=auto'
alias ip='ip -color=auto'
alias cls='clear'
alias n='nvim'
alias g='git'
alias lg='lazygit'
alias y='yazi'
alias ..='cd ..'
alias ...='cd ../..'

alias up='yay -Syu'
alias orphans='pacman -Qdtq | sudo pacman -Rns -'
alias mirrors='sudo reflector --latest 20 --protocol https --sort rate --save /etc/pacman.d/mirrorlist'
alias syslog='sudo dmesg --level=err,warn'
alias xlog='grep -E "\(EE\)|\(WW\)" ~/.local/share/xorg/Xorg.0.log'
alias vacuum='sudo journalctl --vacuum-time=2weeks'

mkcd() { mkdir -p -- "$1" && cd -- "$1"; }

ex() {
    [ -f "$1" ] || { echo "ex: '$1' — не файл"; return 1; }
    case $1 in
        *.tar.bz2|*.tar.gz|*.tar.xz|*.tar.zst|*.tbz2|*.tgz|*.txz|*.tar) tar xf "$1" ;;
        *.bz2) bunzip2 "$1" ;;
        *.gz) gunzip "$1" ;;
        *.xz) unxz "$1" ;;
        *.zst) unzstd "$1" ;;
        *.zip) unzip "$1" ;;
        *.rar) unrar x "$1" ;;
        *.7z) 7z x "$1" ;;
        *) echo "ex: не знаю как распаковать '$1'" ;;
    esac
}

[ -f ~/.bashrc.local ] && . ~/.bashrc.local
