[[ $- != *i* ]] && return

HISTFILE="$XDG_STATE_HOME/zsh/history"
[[ -z $XDG_STATE_HOME ]] && HISTFILE="$HOME/.local/state/zsh/history"
mkdir -p "${HISTFILE:h}"
HISTSIZE=50000
SAVEHIST=50000

setopt autocd extendedglob nomatch interactivecomments
setopt hist_ignore_all_dups hist_ignore_space hist_reduce_blanks share_history inc_append_history
setopt auto_pushd pushd_ignore_dups pushd_silent
unsetopt beep

autoload -Uz compinit colors
colors
zstyle ':completion:*' menu select
zstyle ':completion:*' matcher-list 'm:{a-zA-Z}={A-Za-z}' 'r:|[._-]=* r:|=*'
zstyle ':completion:*' list-colors "${(s.:.)LS_COLORS}"
zstyle ':completion:*' rehash true
zstyle ':completion:*' cache-path "${XDG_CACHE_HOME:-$HOME/.cache}/zsh/zcompcache"
zstyle ':completion:*' use-cache on
zstyle ':completion:*:descriptions' format '%F{blue}-- %d --%f'
zmodload zsh/complist
mkdir -p "${XDG_CACHE_HOME:-$HOME/.cache}/zsh"
compinit -d "${XDG_CACHE_HOME:-$HOME/.cache}/zsh/zcompdump-$ZSH_VERSION"

bindkey -e
bindkey '^[[H' beginning-of-line
bindkey '^[[F' end-of-line
bindkey '^[[3~' delete-char
bindkey '^[[1;5C' forward-word
bindkey '^[[1;5D' backward-word
bindkey '^H' backward-kill-word
bindkey -M menuselect '^[[Z' reverse-menu-complete

autoload -Uz edit-command-line
zle -N edit-command-line
bindkey '^X^E' edit-command-line

plug=/usr/share/zsh/plugins
[[ -r $plug/zsh-autosuggestions/zsh-autosuggestions.zsh ]] && source $plug/zsh-autosuggestions/zsh-autosuggestions.zsh
[[ -r $plug/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh ]] && source $plug/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh
if [[ -r $plug/zsh-history-substring-search/zsh-history-substring-search.zsh ]]; then
    source $plug/zsh-history-substring-search/zsh-history-substring-search.zsh
    bindkey '^[[A' history-substring-search-up
    bindkey '^[[B' history-substring-search-down
fi
unset plug

ZSH_AUTOSUGGEST_STRATEGY=(history completion)
ZSH_AUTOSUGGEST_HIGHLIGHT_STYLE='fg=#585b70'

(( $+commands[fzf] )) && source <(fzf --zsh)
(( $+commands[zoxide] )) && eval "$(zoxide init zsh)"
(( $+commands[starship] )) && eval "$(starship init zsh)"

export FZF_DEFAULT_COMMAND='fd --type f --hidden --exclude .git'
export FZF_DEFAULT_OPTS='--height 40% --layout reverse --border rounded
  --color=bg+:#2b2f37,bg:-1,spinner:#f5e0dc,hl:#f38ba8
  --color=fg:#cdd6f4,header:#f38ba8,info:#cba6f7,pointer:#f5e0dc
  --color=marker:#b4befe,fg+:#cdd6f4,prompt:#cba6f7,hl+:#f38ba8'

if (( $+commands[eza] )); then
    alias ls='eza --icons --group-directories-first'
    alias ll='eza -l --icons --git --group-directories-first'
    alias la='eza -la --icons --git --group-directories-first'
    alias lt='eza --tree --level=2 --icons'
fi
(( $+commands[bat] )) && alias cat='bat --paging=never'
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
    [[ -f $1 ]] || { echo "ex: '$1' — не файл"; return 1; }
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

[[ -f ~/.zshrc.local ]] && source ~/.zshrc.local
