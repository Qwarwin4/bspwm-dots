#!/usr/bin/env bash
# собирает самодостаточные скрипты в dist/

set -euo pipefail

cd "$(dirname "$(readlink -f "$0")")/.."
mkdir -p dist

# bundle ИМЯ "ЗАПУСК" ФАЙЛЫ...   ЗАПУСК — команда относительно распакованного архива
bundle() {
    local out=$1 entry=$2
    shift 2
    {
        cat <<EOF
#!/usr/bin/env bash
set -e
self=\$(readlink -f "\$0")
if [ "\$(id -u)" -ne 0 ]; then
    echo ":: Нужны права root"
    if command -v sudo >/dev/null 2>&1 && sudo -v; then
        exec sudo -- "\$self" "\$@"
    fi
    echo ":: Через sudo не вышло, введи пароль root:"
    exec su root -c "\$(printf '%q ' "\$self" "\$@")"
fi
tmp=\$(mktemp -d)
trap 'rm -rf "\$tmp"' EXIT INT TERM
chmod 755 "\$tmp"
sed '1,/^__ARCHIVE__\$/d' "\$self" | base64 -d | tar xz -C "\$tmp"
cd "\$tmp"
BUNDLE_NAME=\$0 $entry "\$@"
exit \$?
__ARCHIVE__
EOF
        tar --owner=0 --group=0 -cz "$@" | base64
    } >"dist/$out"
    chmod 755 "dist/$out"
    echo "dist/$out"
}

bundle switch-to-sddm.sh "bash scripts/sddm.sh" \
    scripts/common.sh scripts/sddm.sh sddm home/.local/bin/wallpaper home/.local/bin/lock

bundle firefox-thunar-tweaks.sh "bash scripts/tweaks.sh" \
    scripts/common.sh scripts/tweaks.sh firefox thunar home/.config/xfce4/helpers.rc


bundle lock-fix.sh "python3 install.py --lock" \
    install.py scripts/common.sh scripts/i3lock-dots.sh pkgs/i3lock-dots home/.local/bin/lock

bundle flameshot-fix.sh "python3 install.py --flameshot" \
    install.py home/.config/flameshot/flameshot.ini
