# shellcheck shell=bash

c_b=$'\e[1;34m' c_g=$'\e[1;32m' c_y=$'\e[1;33m' c_r=$'\e[1;31m' c_0=$'\e[0m'
[ -t 1 ] || { c_b="" c_g="" c_y="" c_r="" c_0=""; }

say()  { printf '%s::%s %s\n' "$c_b" "$c_0" "$*"; }
ok()   { printf '%s ✓%s %s\n' "$c_g" "$c_0" "$*"; }
warn() { printf '%s !%s %s\n' "$c_y" "$c_0" "$*"; }
die()  { printf '%s ✗%s %s\n' "$c_r" "$c_0" "$*" >&2; exit 1; }

need_root() {
    [ "$(id -u)" -eq 0 ] || die "Нужен root: su -c '${BUNDLE_NAME:-$0}'   (или sudo ${BUNDLE_NAME:-$0})"
}

pick_user() {
    user=${user:-}
    if [ -z "$user" ]; then
        user=${SUDO_USER:-}
        [ "$user" = root ] && user=""
    fi
    if [ -z "$user" ] && [ -r /proc/self/loginuid ]; then
        local uid
        uid=$(cat /proc/self/loginuid)
        if [ "$uid" != 4294967295 ] && [ "$uid" != 0 ]; then
            user=$(id -nu "$uid" 2>/dev/null || true)
        fi
    fi
    if [ -z "$user" ]; then
        local list
        mapfile -t list < <(awk -F: '$3 >= 1000 && $3 < 60000 && $7 !~ /nologin|false/ {print $1}' /etc/passwd)
        [ "${#list[@]}" -eq 1 ] && user=${list[0]}
    fi
    [ -n "$user" ] || die "Не удалось определить пользователя, укажи: -u ИМЯ"
    id "$user" >/dev/null 2>&1 || die "Пользователь '$user' не существует"
    [ "$(id -u "$user")" -ne 0 ] || die "Нужен обычный пользователь, не root"
    home=$(getent passwd "$user" | cut -d: -f6)
    # shellcheck disable=SC2034
    group=$(id -gn "$user")
}

passenv() {
    local v
    for v in http_proxy https_proxy HTTP_PROXY HTTPS_PROXY ALL_PROXY all_proxy no_proxy NO_PROXY \
        SSL_CERT_FILE GIT_SSL_CAINFO CURL_CA_BUNDLE NODE_EXTRA_CA_CERTS; do
        [ -n "${!v:-}" ] && printf '%s=%s\n' "$v" "${!v}"
    done
}

as_user() {
    (
        cd "$home" 2>/dev/null || cd /
        mapfile -t extra < <(passenv)
        runuser -u "$user" -- env HOME="$home" USER="$user" LOGNAME="$user" \
            XDG_CACHE_HOME="$home/.cache" XDG_CONFIG_HOME="$home/.config" \
            XDG_DATA_HOME="$home/.local/share" PATH="/usr/local/bin:/usr/bin:/bin" \
            "${extra[@]}" "$@"
    )
}

put_user_file() {
    local src=$1 dst=$2 mode=${3:-644}
    as_user mkdir -p "$(dirname "$dst")"
    if [ -f "$dst" ] && ! cmp -s "$src" "$dst"; then
        as_user cp -f "$dst" "$dst.bak"
    fi
    as_user sh -c 'cat >"$1.new" && chmod "$2" "$1.new" && mv -f "$1.new" "$1"' _ "$dst" "$mode" <"$src"
}

pac_need() {
    local missing=() p
    for p in "$@"; do
        pacman -Qq "$p" >/dev/null 2>&1 || missing+=("$p")
    done
    [ ${#missing[@]} -eq 0 ] && return 0
    pacman -S --needed --noconfirm --ask=4 "${missing[@]}"
}
