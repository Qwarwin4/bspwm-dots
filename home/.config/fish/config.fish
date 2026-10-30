fish_add_path -g $HOME/.local/bin $HOME/.cargo/bin $HOME/go/bin

set -gx EDITOR nvim
set -gx VISUAL nvim
set -gx PAGER less
set -gx MANPAGER "sh -c 'col -bx | bat -l man -p'"
set -gx MANROFFOPT -c
set -gx BROWSER firefox
set -gx TERMINAL alacritty
set -gx XDG_CONFIG_HOME $HOME/.config
set -gx XDG_CACHE_HOME $HOME/.cache
set -gx XDG_DATA_HOME $HOME/.local/share
set -gx XDG_STATE_HOME $HOME/.local/state
set -gx LESSHISTFILE -
set -gx CM_LAUNCHER rofi

if not status is-interactive
    exit
end

set -g fish_greeting
set -gx FZF_DEFAULT_COMMAND 'fd --type f --hidden --exclude .git'
set -gx FZF_DEFAULT_OPTS '--height 40% --layout reverse --border rounded
  --color=bg+:#2b2f37,bg:-1,spinner:#f5e0dc,hl:#f38ba8
  --color=fg:#cdd6f4,header:#f38ba8,info:#cba6f7,pointer:#f5e0dc
  --color=marker:#b4befe,fg+:#cdd6f4,prompt:#cba6f7,hl+:#f38ba8'

type -q fzf; and fzf --fish | source
type -q zoxide; and zoxide init fish | source
type -q starship; and starship init fish | source

if type -q eza
    alias ls 'eza --icons --group-directories-first'
    alias ll 'eza -l --icons --git --group-directories-first'
    alias la 'eza -la --icons --git --group-directories-first'
    alias lt 'eza --tree --level=2 --icons'
end
type -q bat; and alias cat 'bat --paging=never'
alias ip 'ip -color=auto'
alias cls clear
abbr -a n nvim
abbr -a g git
abbr -a lg lazygit
abbr -a y yazi
abbr -a up 'yay -Syu'
abbr -a mirrors 'sudo reflector --latest 20 --protocol https --sort rate --save /etc/pacman.d/mirrorlist'
abbr -a vacuum 'sudo journalctl --vacuum-time=2weeks'
alias orphans 'pacman -Qdtq | sudo pacman -Rns -'

function mkcd
    mkdir -p -- $argv[1]; and cd -- $argv[1]
end

test -f ~/.config/fish/local.fish; and source ~/.config/fish/local.fish
