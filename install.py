#!/usr/bin/env python3
"""Установка bspwm-dots на Arch Linux.

Запуск от root, чтобы пароль не спрашивался по ходу:
    su -c 'python install.py'          всё
    su -c 'python install.py --lock'   только экран блокировки
    su -c 'python install.py --flameshot'   только скриншоты
"""

import argparse
import datetime
import grp
import os
import pwd
import re
import select
import shutil
import struct
import subprocess
import sys
import termios
import time
import urllib.request
from pathlib import Path

DIR = Path(__file__).resolve().parent
LOG = Path("/var/log/bspwm-dots-install.log")
SUDOERS = Path("/etc/sudoers.d/00-bspwm-dots-install")

SHELLS = {
    "zsh": {
        "pkgs": ["zsh", "zsh-completions", "zsh-autosuggestions",
                 "zsh-syntax-highlighting", "zsh-history-substring-search"],
        "files": [".zshrc", ".zprofile"],
    },
    "fish": {"pkgs": ["fish"], "files": [".config/fish/config.fish"]},
    "bash": {"pkgs": ["bash", "bash-completion"], "files": [".bashrc", ".bash_profile"]},
}

EXECUTABLE = {".xinitrc", ".config/bspwm/bspwmrc", ".config/bspwm/autostart",
              ".config/polybar/launch.sh"}

KEYS = {224: "XF86MonBrightnessDown", 225: "XF86MonBrightnessUp"}
KEYS.update({59 + i: f"F{i + 1}" for i in range(10)})
KEYS.update({87: "F11", 88: "F12"})
KEYS.update({183 + i: f"F{i + 13}" for i in range(12)})
# Enter, Fn и модификаторы при определении клавиш пропускаются
SKIP_KEYS = {28, 96, 29, 97, 42, 54, 56, 100, 125, 126, 464}

LANG_TO_LAYOUT = {
    "en": "ru", "C": "ru", "POSIX": "ru", "uk": "ua", "cs": "cz", "da": "dk",
    "el": "gr", "et": "ee", "sv": "se", "ja": "jp", "ko": "kr", "zh": "cn",
    "be": "by", "kk": "kz", "sr": "rs", "sl": "si", "he": "il", "fa": "ir",
}

TTY = sys.stdout.isatty()


def paint(code, text):
    return f"\033[{code}m{text}\033[0m" if TTY else text


class Log:
    def __init__(self):
        LOG.parent.mkdir(parents=True, exist_ok=True)
        self.f = open(LOG, "a", encoding="utf-8", errors="replace")
        self.f.write(f"\n==== {datetime.datetime.now():%Y-%m-%d %H:%M:%S} ====\n")

    def write(self, text):
        self.f.write(text)
        self.f.flush()


log = None


def out(text=""):
    print(text, flush=True)
    if log:
        log.write(re.sub(r"\033\[[0-9;]*m", "", text) + "\n")


def say(text):
    out(f"{paint('1;34', '::')} {text}")


def ok(text):
    out(f"{paint('1;32', ' ✓')} {text}")


def warn(text):
    out(f"{paint('1;33', ' !')} {text}")


def die(text):
    out(f"{paint('1;31', ' ✗')} {text}")
    sys.exit(1)


def run(cmd, check=False, quiet=False, env=None, cwd=None, stdin=subprocess.DEVNULL):
    """Команда с выводом в терминал и в лог. Возвращает (код, вывод)."""
    if log:
        log.write("$ " + " ".join(map(str, cmd)) + "\n")
    try:
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             stdin=stdin, env=env, cwd=cwd, text=True, errors="replace")
    except FileNotFoundError:
        if check:
            die(f"Не найдено: {cmd[0]}")
        return 127, ""
    lines = []
    for line in p.stdout:
        lines.append(line)
        if log:
            log.write(line)
        if not quiet:
            sys.stdout.write(line)
            sys.stdout.flush()
    code = p.wait()
    if check and code != 0:
        die(f"Ошибка ({code}): {' '.join(map(str, cmd))}. Лог: {LOG}")
    return code, "".join(lines)


def ok_run(cmd, **kw):
    return run(cmd, quiet=True, **kw)[0] == 0


def capture(cmd):
    try:
        return subprocess.run(cmd, capture_output=True, text=True).stdout.strip()
    except FileNotFoundError:
        return ""


def capture_rc(cmd):
    try:
        p = subprocess.run(cmd, capture_output=True, text=True)
        return p.returncode, p.stdout.strip()
    except FileNotFoundError:
        return 127, ""


def read(path, default=""):
    try:
        return Path(path).read_text(errors="replace").strip()
    except OSError:
        return default


class Ask:
    def __init__(self, yes):
        self.yes = yes or not sys.stdin.isatty()

    def _input(self, prompt):
        try:
            return input(prompt).strip()
        except EOFError:
            return ""

    def yes_no(self, question, default=True):
        if self.yes:
            return default
        hint = "[Y/n]" if default else "[y/N]"
        while True:
            ans = self._input(f"{question} {hint} ").lower()
            if not ans:
                return default
            if ans[0] in "yд":
                return True
            if ans[0] in "nн":
                return False

    def text(self, question, default=""):
        if self.yes:
            return default
        ans = self._input(f"{question} [{default}]: " if default else f"{question}: ")
        return ans or default

    def choice(self, question, options, default=0):
        """options: список (значение, подпись). Возвращает значение."""
        if self.yes or len(options) == 1:
            return options[default][0]
        out(question)
        for i, (_, label) in enumerate(options, 1):
            mark = paint("1;32", "*") if i - 1 == default else " "
            out(f"  {mark} {i}) {label}")
        while True:
            ans = self._input(f"Номер [{default + 1}]: ")
            if not ans:
                return options[default][0]
            if ans.isdigit() and 1 <= int(ans) <= len(options):
                return options[int(ans) - 1][0]

    def multi(self, question, groups, default_all=True):
        """groups: список (ключ, подпись, пакеты). Возвращает выбранные ключи."""
        keys = [g[0] for g in groups]
        if self.yes:
            return keys if default_all else []
        out(question)
        for i, (_, label, pkgs) in enumerate(groups, 1):
            out(f"  {i}) {label}  {paint('2', ' '.join(pkgs))}")
        hint = "все" if default_all else "ничего"
        while True:
            ans = self._input(f"Номера через пробел, Enter — {hint}, 0 — ничего: ")
            if not ans:
                return keys if default_all else []
            if ans == "0":
                return []
            nums = ans.replace(",", " ").split()
            if all(n.isdigit() and 1 <= int(n) <= len(groups) for n in nums):
                return [keys[int(n) - 1] for n in dict.fromkeys(nums)]


def read_list(name):
    pkgs = []
    for line in (DIR / "pkgs" / name).read_text().splitlines():
        line = line.split("#", 1)[0]
        if not line.strip().startswith("["):
            pkgs += line.split()
    return pkgs


def read_groups(name):
    groups = []
    for line in (DIR / "pkgs" / name).read_text().splitlines():
        line = line.split("#", 1)[0].strip()
        m = re.match(r"\[(\w+)\]\s*(.*)", line)
        if m:
            groups.append([m.group(1), m.group(2), []])
        elif line and groups:
            groups[-1][2] += line.split()
    return [tuple(g) for g in groups]


class User:
    def __init__(self, name):
        pw = pwd.getpwnam(name)
        self.name = name
        self.uid = pw.pw_uid
        self.gid = pw.pw_gid
        self.home = Path(pw.pw_dir)
        self.group = grp.getgrgid(pw.pw_gid).gr_name
        self.shell = pw.pw_shell

    def env(self):
        env = {
            "HOME": str(self.home), "USER": self.name, "LOGNAME": self.name,
            "XDG_CACHE_HOME": f"{self.home}/.cache", "XDG_CONFIG_HOME": f"{self.home}/.config",
            "XDG_DATA_HOME": f"{self.home}/.local/share", "PATH": "/usr/local/bin:/usr/bin:/bin",
            "LANG": os.environ.get("LANG", "C.UTF-8"),
        }
        for k in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY",
                  "all_proxy", "no_proxy", "NO_PROXY", "SSL_CERT_FILE", "GIT_SSL_CAINFO",
                  "CURL_CA_BUNDLE"):
            if os.environ.get(k):
                env[k] = os.environ[k]
        return env

    def cmd(self, *args):
        return ["runuser", "-u", self.name, "--", "env"] + \
            [f"{k}={v}" for k, v in self.env().items()] + list(map(str, args))

    def run(self, *args, **kw):
        return run(self.cmd(*args), cwd=str(self.home), **kw)

    def chown(self, path):
        os.chown(path, self.uid, self.gid, follow_symlinks=False)

    def makedirs(self, path):
        path = Path(path)
        missing = []
        while not path.exists():
            missing.append(path)
            path = path.parent
        for p in reversed(missing):
            p.mkdir()
            self.chown(p)

    def write(self, path, data, mode=0o644):
        path = Path(path)
        self.makedirs(path.parent)
        if path.is_symlink():
            path.unlink()
        tmp = path.with_name(f".{path.name}.new")
        if isinstance(data, str):
            data = data.encode()
        tmp.write_bytes(data)
        os.chmod(tmp, mode)
        self.chown(tmp)
        os.replace(tmp, path)


class Installer:
    def __init__(self, args):
        self.args = args
        self.ask = Ask(args.yes)
        self.user = None
        self.failed = []
        self.helper = None
        self.cfg = {}

    # ---------- проверки и выбор ----------

    def checks(self):
        if os.geteuid() != 0:
            die("Нужен root: su -c 'python install.py'")
        if not Path("/etc/arch-release").exists() or not shutil.which("pacman"):
            die("Это не Arch Linux")
        if self.args.lock or self.args.flameshot:
            return
        try:
            urllib.request.urlopen("https://archlinux.org", timeout=10)
        except Exception:
            die("Нет интернета (не открывается archlinux.org)")

    def guess_user(self):
        name = os.environ.get("SUDO_USER", "")
        if name and name != "root":
            return name
        uid = read("/proc/self/loginuid")
        if uid.isdigit() and uid not in ("0", "4294967295"):
            try:
                return pwd.getpwuid(int(uid)).pw_name
            except KeyError:
                pass
        users = [p.pw_name for p in pwd.getpwall()
                 if 1000 <= p.pw_uid < 60000 and not p.pw_shell.endswith(("nologin", "false"))]
        return users[0] if len(users) == 1 else ""

    def pick_user(self):
        default = self.args.user or self.guess_user()
        while True:
            name = self.args.user or self.ask.text("Имя пользователя", default)
            self.args.user = None
            if not re.fullmatch(r"[a-z_][a-z0-9_-]{0,31}", name or ""):
                if self.ask.yes:
                    die("Не удалось определить пользователя, укажи: python install.py -u ИМЯ")
                warn("Имя: латиница в нижнем регистре, цифры, _ и -")
                continue
            try:
                pw = pwd.getpwnam(name)
            except KeyError:
                if self.ask.yes or not self.ask.yes_no(f"Пользователя {name} нет. Создать?", True):
                    die(f"Пользователь {name} не существует")
                run(["useradd", "-m", "-G", "wheel", name], check=True)
                say(f"Пароль для {name}:")
                while subprocess.run(["passwd", name]).returncode != 0:
                    warn("Пароль не принят, ещё раз")
                pw = pwd.getpwnam(name)
            if pw.pw_uid == 0:
                if self.ask.yes:
                    die("Ставить надо для обычного пользователя, не для root")
                warn("Ставить надо для обычного пользователя, не для root")
                continue
            if not Path(pw.pw_dir).is_dir():
                die(f"Нет домашней папки {pw.pw_dir}")
            self.user = User(name)
            return

    def detect(self):
        cpu = ""
        for line in read("/proc/cpuinfo").splitlines():
            if line.startswith("vendor_id"):
                cpu = line.split(":", 1)[1].strip()
                break
        virt = capture(["systemd-detect-virt"]) or "none"
        gpus = set()
        for dev in Path("/sys/bus/pci/devices").glob("*"):
            if not read(dev / "class").startswith("0x03"):
                continue
            gpus.add({"0x8086": "intel", "0x1002": "amd", "0x10de": "nvidia",
                      "0x15ad": "vmware", "0x80ee": "virtualbox", "0x1af4": "virtio",
                      "0x1b36": "qxl"}.get(read(dev / "vendor"), "other"))
        self.hw = {
            "cpu": cpu, "virt": virt, "gpus": gpus,
            "bluetooth": any(Path("/sys/class/bluetooth").glob("*")),
        }

    def pick_power(self):
        bats, adapters = [], []
        for ps in sorted(Path("/sys/class/power_supply").glob("*")):
            kind = read(ps / "type")
            if kind == "Battery" and read(ps / "scope") != "Device":
                model = " ".join(filter(None, [read(ps / "manufacturer"), read(ps / "model_name")]))
                bats.append((ps.name, f"{ps.name}  {model}".strip()))
            elif kind == "Mains":
                adapters.append((ps.name, ps.name))
        if bats:
            say("Питание: " + ", ".join(b[0] for b in bats) +
                (" / адаптер " + ", ".join(a[0] for a in adapters) if adapters else ""))
        self.cfg["battery"] = self.ask.choice("Какая батарея показывается на панели:", bats) if bats else "none"
        self.cfg["adapter"] = self.ask.choice("Какой адаптер питания:", adapters) if adapters else "none"

    def pick_backlight(self):
        devs = []
        for d in sorted(Path("/sys/class/backlight").glob("*")):
            kind = read(d / "type") or "?"
            devs.append((d.name, kind, read(d / "max_brightness")))
        self.cfg["backlight"] = "none"
        self.cfg["brightness_devices"] = ""
        self.cfg["keys"] = None
        if not devs:
            return
        say("Подсветка: " + ", ".join(f"{n} ({t}, max {m})" for n, t, m in devs))
        order = {"raw": 0, "platform": 1, "firmware": 2}
        devs.sort(key=lambda d: order.get(d[1], 3))
        opts = [(n, f"{n} ({t})") for n, t, _ in devs]
        if len(devs) > 1:
            opts.append(("all", "все сразу"))
        dev = self.ask.choice("Какой подсветкой управлять:", opts)
        self.cfg["backlight"] = devs[0][0] if dev == "all" else dev
        self.cfg["brightness_devices"] = "" if dev == "all" else dev

        mode = self.ask.choice("Клавиши яркости:", [
            ("detect", "определить нажатием"),
            ("xf86", "XF86MonBrightnessUp/Down (обычно Fn + F-клавиша)"),
            ("f3f4", "F3 / F4 без Fn (займут F3/F4 во всех программах)"),
            ("keep", "как в конфиге"),
        ], default=0 if not self.ask.yes else 1)
        if mode == "xf86":
            self.cfg["keys"] = ("XF86MonBrightnessDown", "XF86MonBrightnessUp")
        elif mode == "f3f4":
            self.cfg["keys"] = ("F3", "F4")
        elif mode == "detect":
            self.cfg["keys"] = self.detect_keys()

    def detect_keys(self):
        devices = []
        block = []
        for line in read("/proc/bus/input/devices").splitlines() + [""]:
            if line:
                block.append(line)
                continue
            handlers = next((b for b in block if b.startswith("H: Handlers=")), "")
            ev = re.search(r"\bevent(\d+)\b", handlers)
            if ev and "kbd" in handlers.partition("=")[2].split():
                devices.append(f"/dev/input/event{ev.group(1)}")
            block = []
        fds = []
        for dev in devices:
            try:
                fds.append(os.open(dev, os.O_RDONLY | os.O_NONBLOCK))
            except OSError:
                pass
        if not fds:
            warn("Нет доступа к устройствам ввода, оставляю XF86MonBrightness")
            return ("XF86MonBrightnessDown", "XF86MonBrightnessUp")

        fmt = "llHHi"
        size = struct.calcsize(fmt)

        def wait_key(timeout=15):
            for fd in fds:
                try:
                    while os.read(fd, size * 64):
                        pass
                except BlockingIOError:
                    pass
            end = time.time() + timeout
            while time.time() < end:
                ready, _, _ = select.select(fds, [], [], max(0, end - time.time()))
                for fd in ready:
                    try:
                        data = os.read(fd, size * 64)
                    except BlockingIOError:
                        continue
                    for i in range(0, len(data) - size + 1, size):
                        _, _, etype, code, value = struct.unpack(fmt, data[i:i + size])
                        if etype == 1 and value == 1 and code not in SKIP_KEYS:
                            return code
            return None

        result = []
        try:
            for what in ("УМЕНЬШЕНИЯ", "УВЕЛИЧЕНИЯ"):
                out(f"Нажми клавишу {what} яркости (с Fn, если обычно жмёшь с ним), 15 секунд...")
                code = wait_key()
                if code is None:
                    warn("Клавиша не прислала событий: яркость, похоже, меняет сама прошивка")
                    return None
                name = KEYS.get(code)
                if not name:
                    warn(f"Код клавиши {code} не знаю, оставляю XF86MonBrightness")
                    return ("XF86MonBrightnessDown", "XF86MonBrightnessUp")
                ok(name)
                result.append(name)
        finally:
            for fd in fds:
                os.close(fd)
            if sys.stdin.isatty():
                termios.tcflush(sys.stdin, termios.TCIFLUSH)
        if result[0] == result[1]:
            warn("Обе клавиши дали одно и то же, оставляю XF86MonBrightness")
            return ("XF86MonBrightnessDown", "XF86MonBrightnessUp")
        return tuple(result)

    def pick_layouts(self):
        cur = ""
        m = re.search(r'XkbLayout"\s+"([^"]+)"', read("/etc/X11/xorg.conf.d/00-keyboard.conf"))
        if m and "," in m.group(1):
            cur = m.group(1)
        if not cur:
            lang = "en"
            for line in read("/etc/locale.conf").splitlines():
                if line.startswith("LANG="):
                    lang = line[5:].strip('"').split("_")[0].split(".")[0]
            cur = "us," + LANG_TO_LAYOUT.get(lang, lang)
        self.cfg["layouts"] = self.ask.text("Раскладки клавиатуры", cur).replace(" ", "")

    def plan(self):
        a = self.ask
        cfg = self.cfg
        out()
        self.pick_user()
        self.detect()

        cur_shell = Path(self.user.shell).name
        default = list(SHELLS).index(cur_shell) if cur_shell in SHELLS else 0
        cfg["shell"] = self.args.shell or a.choice("Оболочка:", [
            ("zsh", "zsh + автодополнение, подсветка, starship"),
            ("fish", "fish + starship"),
            ("bash", "bash + bash-completion, starship"),
        ], default)

        cfg["apps"] = a.multi("Программы:", read_groups("apps.txt"))
        cfg["dev"] = a.multi("Пакеты для разработки:", read_groups("dev.txt"))
        cfg["firefox_tweaks"] = "firefox" in cfg["apps"] and a.yes_no("Твики Firefox (userChrome, тёмная тема, без рекламы)?")
        cfg["thunar_tweaks"] = "thunar" in cfg["apps"] and a.yes_no("Твики Thunar (действия в меню, вид, закладки)?")
        cfg["dracula"] = (cfg["firefox_tweaks"] or cfg["thunar_tweaks"]) and a.yes_no("GTK-тема и иконки Dracula?")
        cfg["aur"] = not self.args.no_aur and a.yes_no("Пакеты из AUR (курсор Bibata, rofi-emoji и т.п.)?")
        cfg["walls"] = a.yes_no("Скачать набор обоев ZProger (~50 МБ)?")
        self.pick_layouts()
        self.pick_power()
        self.pick_backlight()

        cfg["nvidia"] = False
        if "nvidia" in self.hw["gpus"]:
            cfg["nvidia"] = a.yes_no("NVIDIA: ставить драйвер nvidia-open (GTX 16xx/RTX и новее)?")
        cfg["autologin"] = a.yes_no(f"Входить в SDDM без пароля под {self.user.name}?", False)

        keys = cfg["keys"]
        out()
        say(f"Пользователь:  {self.user.name} ({self.user.home}), оболочка {cfg['shell']}")
        say(f"Железо:        {self.hw['cpu'] or '?'}, видео: {', '.join(sorted(self.hw['gpus'])) or '?'}, виртуализация: {self.hw['virt']}")
        say(f"Батарея:       {cfg['battery']}, адаптер: {cfg['adapter']}, подсветка: {cfg['backlight']}")
        say(f"Яркость:       {' / '.join(keys) if keys else 'клавиши как в конфиге'}")
        say(f"Раскладки:     {cfg['layouts']} (Alt+Shift)")
        say(f"Программы:     {', '.join(cfg['apps']) or 'нет'}")
        say(f"Разработка:    {', '.join(cfg['dev']) or 'нет'}")
        say(f"Твики:         Firefox {'да' if cfg['firefox_tweaks'] else 'нет'}, Thunar {'да' if cfg['thunar_tweaks'] else 'нет'}, Dracula {'да' if cfg['dracula'] else 'нет'}")
        say(f"AUR:           {'да' if cfg['aur'] else 'нет'}, обои ZProger: {'да' if cfg['walls'] else 'нет'}")
        say(f"Вход:          SDDM{', автовход' if cfg['autologin'] else ''}")
        out()
        if not a.yes_no("Продолжить?"):
            sys.exit(0)

    # ---------- пакеты ----------

    def tune_pacman(self):
        f = Path("/etc/pacman.conf")
        bak = Path("/etc/pacman.conf.bspwm-dots.bak")
        if not bak.exists():
            shutil.copy2(f, bak)
        s = f.read_text()
        s = re.sub(r"(?m)^#Color$", "Color", s)
        s = re.sub(r"(?m)^#?ParallelDownloads.*$", "ParallelDownloads = 10", s)
        if not re.search(r"(?m)^ILoveCandy", s):
            s = re.sub(r"(?m)^Color$", "Color\nILoveCandy", s, count=1)
        s = re.sub(r"(?m)^#\[multilib\]\n#Include", "[multilib]\nInclude", s)
        f.write_text(s)
        ok("pacman.conf: цвет, параллельная загрузка, multilib")

    def upgrade(self):
        say("Обновление системы")
        if not ok_run(["pacman", "-Sy", "--noconfirm", "--needed", "archlinux-keyring"]):
            warn("archlinux-keyring не обновился")
        if run(["pacman", "-Su", "--noconfirm", "--ask=4"])[0] != 0:
            die(f"pacman -Syu завершился с ошибкой, смотри {LOG}")
        ok("Система обновлена")

    def hw_pkgs(self):
        hw = []
        cpu, gpus, virt = self.hw["cpu"], self.hw["gpus"], self.hw["virt"]
        hw += {"GenuineIntel": ["intel-ucode"], "AuthenticAMD": ["amd-ucode"]}.get(cpu, [])
        if "intel" in gpus:
            hw += ["vulkan-intel", "intel-media-driver"]
        if "amd" in gpus:
            hw += ["vulkan-radeon"]
        if "nvidia" in gpus:
            if self.cfg["nvidia"]:
                hw += ["nvidia-open-dkms", "nvidia-utils", "nvidia-settings"]
                for k in Path("/usr/lib/modules").glob("*/pkgbase"):
                    hw.append(read(k) + "-headers")
            else:
                hw += ["vulkan-nouveau"]
        hw += {"oracle": ["virtualbox-guest-utils"], "kvm": ["qemu-guest-agent", "spice-vdagent"],
               "qemu": ["qemu-guest-agent", "spice-vdagent"], "vmware": ["open-vm-tools", "gtkmm3"]}.get(virt, [])
        return hw + ["mesa"]

    def wanted(self):
        pkgs = read_list("core.txt") + SHELLS[self.cfg["shell"]]["pkgs"]
        for file, keys in (("apps.txt", self.cfg["apps"]), ("dev.txt", self.cfg["dev"])):
            for key, _, group in read_groups(file):
                if key in keys:
                    pkgs += group
        if self.hw["bluetooth"]:
            pkgs += read_list("bluetooth.txt")
        pkgs += self.hw_pkgs()
        return list(dict.fromkeys(pkgs))

    def pac_install(self, pkgs):
        if not pkgs:
            return
        say(f"pacman: {len(pkgs)} пакетов")
        if run(["pacman", "-S", "--needed", "--noconfirm", "--ask=4", *pkgs])[0] == 0:
            return
        warn("Общая установка не прошла, ставлю по одному")
        for p in pkgs:
            if run(["pacman", "-S", "--needed", "--noconfirm", "--ask=4", p])[0] != 0:
                self.failed.append(p)

    def aur_helper(self):
        for h in ("yay", "paru"):
            if shutil.which(h):
                self.helper = h
                return True
        say("Сборка yay")
        tmp = Path(capture(self.user.cmd("mktemp", "-d")))
        try:
            if self.user.run("git", "clone", "--depth", "1", "https://aur.archlinux.org/yay-bin.git", tmp / "yay")[0] == 0 \
                    and self.user.run("bash", "-c", 'cd "$1" && makepkg --noconfirm', "_", tmp / "yay")[0] == 0:
                built = sorted((tmp / "yay").glob("yay-bin-[0-9]*.pkg.tar.*"))
                if built and run(["pacman", "-U", "--noconfirm", str(built[0])])[0] == 0:
                    self.helper = "yay"
                    return True
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        warn("yay собрать не удалось, AUR-пакеты пропущены")
        return False

    def aur_install(self, pkgs):
        if not pkgs:
            return
        if not self.cfg["aur"]:
            warn("AUR отключён, пропущено: " + " ".join(pkgs))
            return
        if not self.helper and not self.aur_helper():
            self.failed += pkgs
            return
        SUDOERS.write_text(f"{self.user.name} ALL=(ALL:ALL) NOPASSWD: ALL\n")
        os.chmod(SUDOERS, 0o440)
        try:
            flags = ["-S", "--needed", "--noconfirm", "--removemake", "--cleanafter"]
            flags += ["--answerdiff", "None", "--answerclean", "None", "--answeredit", "None"] \
                if self.helper == "yay" else ["--skipreview"]
            say(f"AUR ({self.helper}): {' '.join(pkgs)}")
            for p in pkgs:
                if self.user.run(self.helper, *flags, p)[0] != 0:
                    self.failed.append(p)
        finally:
            SUDOERS.unlink(missing_ok=True)

    def install_packages(self):
        known = set(capture(["pacman", "-Slq"]).split())
        known |= {g.split()[0] for g in capture(["pacman", "-Sg"]).splitlines() if g.strip()}
        repo, aur = [], []
        for p in self.wanted():
            if p in known or ok_run(["pacman", "-Si", p]):
                repo.append(p)
            else:
                aur.append(p)
        self.pac_install(repo)
        self.aur_install(aur)

        self.i3lock_dots()

    def i3lock_dots(self):
        if run(["bash", str(DIR / "scripts/i3lock-dots.sh"), "-u", self.user.name])[0] == 0:
            return True
        warn("i3lock-dots не установился, блокировка будет без точек и Caps Lock")
        if not shutil.which("i3lock") and self.cfg.get("aur"):
            self.aur_install(["i3lock-color"])
        return False

    # ---------- система ----------

    def services(self):
        say("Службы")
        for s in ("dhcpcd", "systemd-networkd"):
            if ok_run(["systemctl", "is-enabled", s]):
                ok_run(["systemctl", "disable", s])
                warn(f"{s} отключён, сетью теперь управляет NetworkManager")
        for s in ("NetworkManager", "fstrim.timer", "paccache.timer"):
            ok_run(["systemctl", "enable", s])
        if self.hw["bluetooth"]:
            ok_run(["systemctl", "enable", "bluetooth"])
        if "docker" in self.cfg["dev"]:
            ok_run(["systemctl", "enable", "docker.socket"])
            ok_run(["usermod", "-aG", "docker", self.user.name])
        unit = {"oracle": "vboxservice", "kvm": "qemu-guest-agent", "qemu": "qemu-guest-agent",
                "vmware": "vmtoolsd"}.get(self.hw["virt"])
        if unit:
            ok_run(["systemctl", "enable", unit])
        ok("NetworkManager, fstrim, paccache" + (", bluetooth" if self.hw["bluetooth"] else ""))

    def keyboard(self):
        d = Path("/etc/X11/xorg.conf.d")
        d.mkdir(parents=True, exist_ok=True)
        f = d / "00-keyboard.conf"
        if f.exists():
            shutil.copy2(f, d / "00-keyboard.conf.bspwm-dots.bak")
        f.write_text(f'''Section "InputClass"
    Identifier "system-keyboard"
    MatchIsKeyboard "on"
    Option "XkbLayout" "{self.cfg["layouts"]}"
    Option "XkbOptions" "grp:alt_shift_toggle"
EndSection
''')
        t = d / "30-touchpad.conf"
        if not t.exists():
            t.write_text('''Section "InputClass"
    Identifier "touchpad"
    Driver "libinput"
    MatchIsTouchpad "on"
    Option "Tapping" "on"
    Option "NaturalScrolling" "false"
    Option "DisableWhileTyping" "on"
EndSection
''')
        ok(f"Клавиатура: {self.cfg['layouts']}, тачпад: тап-клик")

    def coords(self):
        tz = os.path.realpath("/etc/localtime").split("zoneinfo/")[-1]
        for tab in ("/usr/share/zoneinfo/zone1970.tab", "/usr/share/zoneinfo/zone.tab"):
            for line in read(tab).splitlines():
                cols = line.split("\t")
                if len(cols) > 2 and cols[2] == tz:
                    m = re.match(r"([+-]\d+)([+-]\d+)", cols[1])
                    if m:
                        return tuple(round(self.dms(v), 2) for v in m.groups())
        return 0.0, 0.0

    @staticmethod
    def dms(v):
        sign = -1 if v[0] == "-" else 1
        v = v[1:]
        deg_len = 2 if len(v) in (4, 6) else 3
        d = int(v[:deg_len]) + int(v[deg_len:deg_len + 2]) / 60
        if len(v) > deg_len + 2:
            d += int(v[deg_len + 2:]) / 3600
        return sign * d

    # ---------- файлы пользователя ----------

    def deploy(self):
        say("Копирование конфигов")
        u = self.user
        src_root = DIR / "home"
        skip = {f for name, s in SHELLS.items() if name != self.cfg["shell"] for f in s["files"]}
        cursor = "Bibata-Modern-Classic" if Path("/usr/share/icons/Bibata-Modern-Classic").is_dir() else "Adwaita"
        subst = {"@USER@": u.name, "@HOME@": str(u.home), "@CURSOR@": cursor}
        backup = u.home / ".dots-backup" / datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        backed = 0

        for src in sorted(src_root.rglob("*")):
            if not src.is_file():
                continue
            rel = src.relative_to(src_root).as_posix()
            if rel in skip:
                continue
            data = src.read_bytes()
            if b"@" in data:
                try:
                    text = data.decode()
                    for k, v in subst.items():
                        text = text.replace(k, v)
                    data = text.encode()
                except UnicodeDecodeError:
                    pass
            dst = u.home / rel
            if dst.is_file() and not dst.is_symlink() and dst.read_bytes() != data:
                u.write(backup / rel, dst.read_bytes())
                backed += 1
            mode = 0o755 if rel.startswith(".local/bin/") or rel in EXECUTABLE or os.access(src, os.X_OK) else 0o644
            u.write(dst, data, mode)

        u.write(u.home / ".gtkrc-2.0", f'''gtk-theme-name="Adwaita-dark"
gtk-icon-theme-name="Papirus-Dark"
gtk-font-name="Noto Sans 10"
gtk-cursor-theme-name="{cursor}"
gtk-cursor-theme-size=24
''')
        u.write(u.home / ".icons/default/index.theme", f"[Icon Theme]\nInherits={cursor}\n")

        lat, lon = self.coords()
        u.write(u.home / ".config/redshift/redshift.conf", f'''[redshift]
temp-day=6500
temp-night=4200
fade=1
gamma=0.9
location-provider=manual
adjustment-method=randr

[manual]
lat={lat}
lon={lon}
''')
        self.cursor = cursor
        if backed:
            ok(f"Старые конфиги ({backed}) сохранены в {backup}")
        ok(f"Конфиги установлены для {u.name} (курсор {cursor}, redshift {lat} {lon})")

    def hardware(self):
        cfg = self.cfg
        u = self.user
        u.write(u.home / ".config/bspwm/hardware", f'''# батарея, адаптер и подсветка для панели и клавиш яркости
# ls /sys/class/power_supply /sys/class/backlight
BATTERY={cfg["battery"]}
ADAPTER={cfg["adapter"]}
BACKLIGHT_CARD={cfg["backlight"]}
BRIGHTNESS_DEVICES="{cfg["brightness_devices"]}"
''')
        if cfg["keys"]:
            f = u.home / ".config/sxhkd/sxhkdrc"
            down, up = cfg["keys"]
            block = f"# brightness-keys\n{{{up},{down}}}\n    brightness {{up,down}}\n# brightness-keys-end"
            s = re.sub(r"# brightness-keys\n.*?# brightness-keys-end", block, f.read_text(), flags=re.DOTALL)
            u.write(f, s)
        ok(f"Железо: батарея {cfg['battery']}, адаптер {cfg['adapter']}, подсветка {cfg['backlight']}"
           + (f", клавиши {cfg['keys'][0]} / {cfg['keys'][1]}" if cfg["keys"] else ""))

    def wallpapers(self):
        u = self.user
        u.run("xdg-user-dirs-update", quiet=True)
        pics = capture(u.cmd("xdg-user-dir", "PICTURES"))
        pics = Path(pics) if pics and Path(pics) != u.home else u.home / "Pictures"
        dest = pics / "wallpapers"
        u.makedirs(dest)
        for w in (DIR / "wallpapers").iterdir():
            if w.is_file():
                u.write(dest / w.name, w.read_bytes())

        if self.cfg["walls"] and not (dest / "zproger").exists():
            say("Скачивание обоев ZProger")
            tmp = Path(capture(u.cmd("mktemp", "-d")))
            try:
                if u.run("git", "clone", "-q", "--depth", "1", "--filter=blob:none", "--sparse",
                         "https://github.com/Zproger/bspwm-dotfiles.git", tmp / "z")[0] == 0 \
                        and u.run("git", "-C", tmp / "z", "sparse-checkout", "set", "Images")[0] == 0:
                    n = 0
                    for img in (tmp / "z" / "Images").iterdir():
                        if img.suffix.lower() in (".jpg", ".jpeg", ".png") and img.is_file():
                            u.write(dest / "zproger" / img.name, img.read_bytes())
                            n += 1
                    ok(f"Обои ZProger: {n} шт. в {dest / 'zproger'}")
                else:
                    warn("Не удалось скачать обои ZProger")
            finally:
                shutil.rmtree(tmp, ignore_errors=True)

        state = u.home / ".cache/wallpaper"
        if not Path(read(state)).is_file():
            u.write(state, f"{dest / 'sunset.jpg'}\n")
        ok(f"Обои: {dest}")

    # ---------- экран блокировки ----------

    def session_env(self):
        code, out = capture_rc(["pgrep", "-u", str(self.user.uid), "-x", "bspwm"])
        if code != 0 or not out:
            return None
        try:
            raw = Path(f"/proc/{out.split()[0]}/environ").read_bytes().split(b"\0")
        except OSError:
            return None
        env = {}
        for item in raw:
            k, _, v = item.decode(errors="replace").partition("=")
            if k in ("DISPLAY", "XAUTHORITY", "PATH", "DBUS_SESSION_BUS_ADDRESS", "XDG_RUNTIME_DIR"):
                env[k] = v
        return env if "DISPLAY" in env else None

    def lock_check(self):
        """Свежий lock, сброс кэша картинки и проверка того, что запустится по Super + Shift + L."""
        u = self.user
        src = DIR / "home/.local/bin/lock"
        dst = u.home / ".local/bin/lock"
        if dst.is_file() and dst.read_bytes() != src.read_bytes():
            u.write(dst.with_name("lock.bak"), dst.read_bytes(), 0o755)
        u.write(dst, src.read_bytes(), 0o755)
        shutil.rmtree(u.home / ".cache/lock", ignore_errors=True)

        dots = Path("/usr/local/bin/i3lock-dots")
        if dots.is_file() and b"I3LOCK_DOTS" in dots.read_bytes():
            ok("Блокировка: i3lock-dots, точки в поле пароля и Caps Lock")
        else:
            warn("Блокировка без i3lock-dots: точек и Caps Lock не будет")

        env = self.session_env()
        if not env:
            say("Фон блокировки соберётся при первой блокировке")
            return
        cmd = ["runuser", "-u", u.name, "--", "env", f"HOME={u.home}"] + [f"{k}={v}" for k, v in env.items()]
        found = capture(cmd + ["sh", "-c", "command -v lock"])
        if found == str(dst):
            ok(f"Super + Shift + L запускает {dst}")
        else:
            warn(f"В сессии первым находится {found or 'ничего'}, а не {dst}")
        run(cmd + [str(dst), "--prepare"], quiet=True)
        if any((u.home / ".cache/lock").glob("*.png")):
            ok("Фон блокировки с полем пароля готов")
        else:
            warn("Фон блокировки не собрался: " + read(u.home / ".cache/lock/error.log"))

    def lock_only(self):
        say(f"Экран блокировки для {self.user.name}")
        self.i3lock_dots()
        self.lock_check()
        out()
        ok("Готово. Жми Super + Shift + L")
        say("Если что-то не так: cat ~/.cache/lock/last-run ~/.cache/lock/error.log")

    # ---------- скриншоты ----------

    def flameshot_fix(self):
        """Flameshot 14 снимает экран через xdg-desktop-portal, а у portal-gtk скриншотов нет,
        поэтому под X11 включаем старый способ захвата. Версии до 14 этот ключ не знают
        и при запуске показывают окно с ошибкой конфига, им его не пишем."""
        u = self.user
        f = u.home / ".config/flameshot/flameshot.ini"
        text = read(f) if f.is_file() else read(DIR / "home/.config/flameshot/flameshot.ini")
        if not re.search(r"(?m)^\[General\]", text):
            text = "[General]\n" + text
        text = re.sub(r"(?m)^useX11LegacyScreenshot=.*\n?", "", text)
        m = re.search(r"v(\d+)\.", capture(["flameshot", "--version"]))
        major = int(m.group(1)) if m else 0
        if major >= 14:
            text = re.sub(r"(?m)^\[General\]$", "[General]\nuseX11LegacyScreenshot=true", text, count=1)
        u.write(f, text.rstrip("\n") + "\n")
        if major >= 14:
            ok(f"flameshot {major}: захват экрана напрямую через X11, без xdg-desktop-portal")
        else:
            ok(f"flameshot {major or '?'}: конфиг без лишних ключей")

        env = self.session_env()
        if not env or not shutil.which("flameshot"):
            return
        ok_run(["pkill", "-u", str(u.uid), "-x", "flameshot"])
        cmd = ["runuser", "-u", u.name, "--", "env", f"HOME={u.home}"] + [f"{k}={v}" for k, v in env.items()]
        tmp = Path(capture(cmd + ["mktemp", "-d", "/tmp/flameshot-testXXXXXX"]))
        code, text = run(cmd + ["timeout", "40", "flameshot", "full", "-p", f"{tmp}/"], quiet=True)
        shots = list(tmp.glob("*.png"))
        if shots:
            ok("Проверочный скриншот снялся")
        else:
            warn("Проверочный скриншот не снялся:")
            for row in text.strip().splitlines()[-5:]:
                out(f"     {row}")
        shutil.rmtree(tmp, ignore_errors=True)

    def flameshot_only(self):
        say(f"Скриншоты (flameshot) для {self.user.name}")
        if not shutil.which("flameshot"):
            run(["pacman", "-S", "--needed", "--noconfirm", "flameshot"])
        if not shutil.which("flameshot"):
            die("flameshot не установился")
        self.flameshot_fix()
        out()
        ok("Готово. Print — область, Shift + Print — весь экран в буфер")

    def fix_only(self):
        name = self.args.user or self.guess_user()
        if name:
            self.args.user = name
        self.pick_user()
        if self.args.lock:
            self.lock_only()
        if self.args.flameshot:
            self.flameshot_only()

    # ---------- вход ----------

    def sddm(self):
        u = self.user
        if run(["bash", str(DIR / "scripts/sddm.sh"), "-u", u.name, "--no-home"])[0] != 0:
            warn("SDDM не настроился, смотри вывод выше")
            return
        state = Path("/var/lib/sddm/state.conf")
        if state.parent.is_dir():
            state.write_text(f"[Last]\nSession=/usr/share/xsessions/bspwm.desktop\nUser={u.name}\n")
            try:
                pw = pwd.getpwnam("sddm")
                os.chown(state, pw.pw_uid, pw.pw_gid)
            except KeyError:
                pass
        auto = Path("/etc/sddm.conf.d/20-autologin.conf")
        if self.cfg["autologin"]:
            auto.write_text(f"[Autologin]\nUser={u.name}\nSession=bspwm\n")
            ok(f"SDDM: автовход под {u.name}")
        else:
            auto.unlink(missing_ok=True)
            ok(f"SDDM: по умолчанию выбран {u.name} и сессия bspwm")

    # ---------- пользователь ----------

    def finish_user(self):
        say("Настройка пользователя")
        u = self.user
        shell = shutil.which(self.cfg["shell"])
        if shell and u.shell != shell:
            if ok_run(["chsh", "-s", shell, u.name]):
                ok(f"Оболочка: {self.cfg['shell']}")
            else:
                warn(f"Не удалось сменить оболочку на {shell}")

        if shutil.which("gsettings") and shutil.which("dbus-run-session"):
            u.run("dbus-run-session", "sh", "-c",
                  'gsettings set org.gnome.desktop.interface color-scheme prefer-dark; '
                  'gsettings set org.gnome.desktop.interface gtk-theme Adwaita-dark; '
                  'gsettings set org.gnome.desktop.interface icon-theme Papirus-Dark; '
                  'gsettings set org.gnome.desktop.interface cursor-theme "$1"', "_", self.cursor, quiet=True)
        if shutil.which("tldr"):
            u.run("timeout", "60", "tldr", "--update", quiet=True)
        if "rust" in self.cfg["dev"] and shutil.which("rustup"):
            u.run("rustup", "default", "stable", quiet=True)
        ok_run(["fc-cache", "-f"])

        if "editor" in self.cfg["dev"] and shutil.which("nvim"):
            say("Neovim: плагины (пару минут)")
            if u.run("timeout", "600", "nvim", "--headless", "+Lazy! sync", "+qa", quiet=True)[0] == 0:
                ok("Плагины Neovim")
            else:
                warn("Плагины Neovim доустановятся при первом запуске")

        if "wheel" not in capture(["id", "-nG", u.name]).split():
            ok_run(["usermod", "-aG", "wheel", u.name])
            warn(f"{u.name} добавлен в группу wheel")
        sudoers = "\n".join(read(f) for f in [Path("/etc/sudoers"), *Path("/etc/sudoers.d").glob("*")])
        if not re.search(r"(?m)^\s*%wheel\s+ALL=\(ALL(:ALL)?\)\s+ALL", sudoers):
            f = Path("/etc/sudoers.d/10-wheel")
            f.write_text("%wheel ALL=(ALL:ALL) ALL\n")
            os.chmod(f, 0o440)
            if not ok_run(["visudo", "-cf", str(f)]):
                f.unlink()
            else:
                ok("sudo для группы wheel")

    def tweaks(self):
        cfg = self.cfg
        if not (cfg["firefox_tweaks"] or cfg["thunar_tweaks"]):
            return
        cmd = ["bash", str(DIR / "scripts/tweaks.sh"), "-u", self.user.name]
        if not cfg["firefox_tweaks"]:
            cmd.append("--no-firefox")
        if not cfg["thunar_tweaks"]:
            cmd.append("--no-thunar")
        if not cfg["dracula"]:
            cmd.append("--no-dracula")
        if run(cmd)[0] != 0:
            warn("Твики применились не полностью")

    # ---------- запуск ----------

    def main(self):
        global log
        self.checks()
        log = Log()
        if self.args.lock or self.args.flameshot:
            try:
                self.fix_only()
            except KeyboardInterrupt:
                out()
                die("Прервано")
            return
        try:
            self.plan()
            self.tune_pacman()
            self.upgrade()
            self.install_packages()
            self.services()
            self.keyboard()
            self.deploy()
            self.hardware()
            self.wallpapers()
            self.lock_check()
            if shutil.which("flameshot"):
                self.flameshot_fix()
            self.sddm()
            say("Палитра консоли")
            run(["bash", str(DIR / "scripts/ly.sh"), str(self.user.home / ".Xresources")], quiet=True)
            self.finish_user()
            self.tweaks()
        except KeyboardInterrupt:
            out()
            die("Прервано")
        finally:
            SUDOERS.unlink(missing_ok=True)

        out()
        if self.failed:
            warn("Не установились: " + " ".join(self.failed))
            warn(f"Подробности в {LOG}")
        ok("Готово. Перезагрузись: reboot")
        say("Если что-то не работает: python debug.py (из-под пользователя, в сессии bspwm)")


def main():
    p = argparse.ArgumentParser(description="Установка bspwm-dots")
    p.add_argument("-u", "--user", help="пользователь (иначе спросит)")
    p.add_argument("-y", "--yes", action="store_true", help="без вопросов, всё по умолчанию")
    p.add_argument("--shell", choices=list(SHELLS), help="оболочка")
    p.add_argument("--no-aur", action="store_true", help="не трогать AUR")
    p.add_argument("--lock", action="store_true",
                   help="только экран блокировки: i3lock-dots с точками и Caps Lock, свежий lock")
    p.add_argument("--flameshot", action="store_true",
                   help="только скриншоты: flameshot снимает экран напрямую через X11")
    Installer(p.parse_args()).main()


if __name__ == "__main__":
    main()
