#!/usr/bin/env python3
"""Поиск и исправление типичных проблем bspwm-dots.

    python debug.py              проверить всё и предложить исправления
    python debug.py lock panel   только выбранные разделы
    python debug.py --fix        исправить всё найденное без вопросов
    python debug.py --report     сохранить отчёт в ~/bspwm-debug.txt

Лучше запускать из-под пользователя в сессии bspwm. Исправления, которым
нужен root, попросят пароль через sudo (или su, если sudo нет).
"""

import argparse
import datetime
import os
import pwd
import re
import select
import shlex
import shutil
import struct
import subprocess
import sys
import time
from pathlib import Path

DIR = Path(__file__).resolve().parent
TTY = sys.stdout.isatty()

KEYS = {224: "XF86MonBrightnessDown", 225: "XF86MonBrightnessUp"}
KEYS.update({59 + i: f"F{i + 1}" for i in range(10)})
KEYS.update({87: "F11", 88: "F12"})
KEYS.update({183 + i: f"F{i + 13}" for i in range(12)})
SKIP_KEYS = {28, 96, 29, 97, 42, 54, 56, 100, 125, 126, 464}

CAPS_ICON = "\U000f0632"
SECTIONS = ["session", "lock", "brightness", "panel", "sddm", "system"]


def paint(code, text):
    return f"\033[{code}m{text}\033[0m" if TTY else text


def read(path, default=""):
    try:
        return Path(path).read_text(errors="replace").strip()
    except OSError:
        return default


def capture(cmd, env=None, timeout=30):
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=timeout)
        return p.returncode, (p.stdout + p.stderr).strip()
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        return 127, str(e)


def detect_keys():
    """Читает /dev/input напрямую (нужен root). Возвращает (down, up) или None."""
    devices, block = [], []
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
        print("нет доступа к /dev/input", file=sys.stderr)
        return None
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
            print(f"Нажми клавишу {what} яркости (с Fn, если обычно жмёшь с ним), 15 секунд...",
                  file=sys.stderr, flush=True)
            code = wait_key()
            if code is None:
                print("клавиша не прислала событий", file=sys.stderr)
                return None
            result.append(KEYS.get(code, f"code{code}"))
            print(f"  {result[-1]}", file=sys.stderr)
    finally:
        for fd in fds:
            os.close(fd)
        try:
            import termios
            termios.tcflush(sys.stdin, termios.TCIFLUSH)
        except Exception:
            pass
    return tuple(result)


class Problem:
    def __init__(self, text, fix=None, how=""):
        self.text = text
        self.fix = fix
        self.how = how


class Doctor:
    def __init__(self, args):
        self.args = args
        self.problems = []
        self.report = []
        self.root = os.geteuid() == 0
        self.user = self.find_user()
        self.home = Path(self.user.pw_dir)
        self.cfg = self.home / ".config"
        self.env = self.session_env()
        self.x = self.env is not None and capture(["xrandr", "--query"], env=self.env)[0] == 0

    # ---------- окружение ----------

    def find_user(self):
        if not self.root:
            return pwd.getpwuid(os.getuid())
        name = self.args.user or os.environ.get("SUDO_USER", "")
        if not name or name == "root":
            uid = read("/proc/self/loginuid")
            if uid.isdigit() and uid not in ("0", "4294967295"):
                name = pwd.getpwuid(int(uid)).pw_name
        if not name:
            users = [p.pw_name for p in pwd.getpwall()
                     if 1000 <= p.pw_uid < 60000 and not p.pw_shell.endswith(("nologin", "false"))]
            if len(users) == 1:
                name = users[0]
        if not name:
            sys.exit("Не понял, для какого пользователя проверять: python debug.py -u ИМЯ")
        return pwd.getpwnam(name)

    def pid_of(self, name):
        code, out = capture(["pgrep", "-u", str(self.user.pw_uid), "-x", name])
        return out.split()[0] if code == 0 and out else None

    def session_env(self):
        env = {"HOME": self.user.pw_dir, "USER": self.user.pw_name, "LOGNAME": self.user.pw_name,
               "PATH": f"{self.user.pw_dir}/.local/bin:/usr/local/bin:/usr/bin:/bin",
               "XDG_RUNTIME_DIR": f"/run/user/{self.user.pw_uid}", "LANG": os.environ.get("LANG", "C.UTF-8")}
        pid = self.pid_of("bspwm")
        if pid:
            try:
                raw = Path(f"/proc/{pid}/environ").read_bytes().split(b"\0")
                src = dict(item.decode(errors="replace").split("=", 1) for item in raw if b"=" in item)
            except OSError:
                src = {}
            for k in ("DISPLAY", "XAUTHORITY", "DBUS_SESSION_BUS_ADDRESS", "XDG_RUNTIME_DIR",
                      "XDG_SESSION_ID", "PATH", "XDG_CACHE_HOME", "XDG_CONFIG_HOME"):
                if src.get(k):
                    env[k] = src[k]
        for k in ("DISPLAY", "XAUTHORITY", "DBUS_SESSION_BUS_ADDRESS"):
            if not self.root and os.environ.get(k) and k not in env:
                env[k] = os.environ[k]
        if "DISPLAY" not in env:
            return None if not pid else env
        if f"{self.user.pw_dir}/.local/bin" not in env["PATH"].split(":"):
            env["PATH"] = f"{self.user.pw_dir}/.local/bin:" + env["PATH"]
        return env

    def user_env(self):
        return self.env or {"HOME": self.user.pw_dir, "PATH": "/usr/local/bin:/usr/bin:/bin",
                            "XDG_RUNTIME_DIR": f"/run/user/{self.user.pw_uid}"}

    def as_user(self, args):
        args = [str(a) for a in args]
        if not self.root:
            return args
        return ["runuser", "-u", self.user.pw_name, "--", "env"] + \
            [f"{k}={v}" for k, v in self.user_env().items()] + args

    def user_run(self, args, timeout=60):
        return capture(self.as_user(args), env=self.user_env(), timeout=timeout)

    def user_spawn(self, args):
        subprocess.Popen(self.as_user(args), env=self.user_env(), stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL, start_new_session=True)

    def as_root(self, args):
        args = [str(a) for a in args]
        if self.root:
            return args
        if shutil.which("sudo"):
            return ["sudo", *args]
        return ["su", "-c", shlex.join(args)]

    def root_run(self, args):
        """С выводом в терминал: здесь может спросить пароль."""
        return subprocess.run(self.as_root(args)).returncode == 0

    def write_user_file(self, path, text, mode=0o644):
        path = Path(path)
        if path.exists() and not path.with_name(path.name + ".bak").exists():
            shutil.copy2(path, path.with_name(path.name + ".bak"))
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(f".{path.name}.new")
        tmp.write_text(text)
        os.chmod(tmp, mode)
        if self.root:
            os.chown(tmp, self.user.pw_uid, self.user.pw_gid)
        os.replace(tmp, path)

    # ---------- вывод ----------

    def line(self, text):
        print(text, flush=True)
        self.report.append(re.sub(r"\033\[[0-9;]*m", "", text))

    def head(self, text):
        self.line("")
        self.line(paint("1;34", f":: {text}"))

    def good(self, text):
        self.line(f"{paint('1;32', '  ✓')} {text}")

    def info(self, text):
        self.line(f"{paint('2', '  ·')} {text}")

    def bad(self, text, fix=None, how=""):
        self.line(f"{paint('1;31', '  ✗')} {text}")
        if how:
            self.line(f"      {paint('2', '→ ' + how)}")
        self.problems.append(Problem(text, fix, how))

    def detail(self, text, lines=12):
        for row in text.strip().splitlines()[-lines:]:
            self.line(f"      {paint('2', row)}")

    # ---------- сессия ----------

    def check_session(self):
        self.head("Сессия")
        if not self.pid_of("bspwm"):
            self.info("bspwm не запущен: проверки окна, панели и блокировки ограничены")
        else:
            self.good("bspwm запущен")
        if not self.x:
            self.info("нет доступа к X (запусти из терминала в сессии bspwm)")
            return
        daemons = [
            ("sxhkd", ["sxhkd"], "горячие клавиши не работают"),
            ("polybar", [self.cfg / "polybar/launch.sh"], "нет панели"),
            ("picom", ["picom"], "нет прозрачности и скруглений"),
            ("dunst", ["dunst"], "нет уведомлений"),
            ("xss-lock", ["xss-lock", "--transfer-sleep-lock", "--", "lock"], "экран не блокируется сам и перед сном"),
        ]
        for name, cmd, why in daemons:
            if self.pid_of(name):
                self.good(f"{name} запущен")
            elif not shutil.which(name):
                self.bad(f"{name} не установлен: {why}", lambda n=name: self.root_run(["pacman", "-S", "--needed", n]),
                         f"pacman -S {name}")
            else:
                self.bad(f"{name} не запущен: {why}", lambda c=cmd: self.user_spawn(c) or True, "запустить")
        if shutil.which("flameshot"):
            ini = read(self.cfg / "flameshot/flameshot.ini")
            legacy = re.search(r"(?m)^useX11LegacyScreenshot=true", ini)
            m = re.search(r"v(\d+)\.", capture(["flameshot", "--version"])[1])
            major = int(m.group(1)) if m else 0
            if major >= 14 and not legacy:
                self.bad(f"flameshot {major} ищет xdg-desktop-portal и не снимает экран", self.fix_flameshot,
                         "включить захват через X11 (useX11LegacyScreenshot=true)")
            elif major and major < 14 and re.search(r"(?m)^useX11LegacyScreenshot=", ini):
                self.bad(f"flameshot {major} не знает useX11LegacyScreenshot и встаёт с окном ошибки",
                         self.fix_flameshot, "убрать ключ из flameshot.ini")
            else:
                self.good(f"flameshot {major or '?'}: конфиг в порядке")
        virt = capture(["systemd-detect-virt"])[1]
        if not self.pid_of("picom") and virt not in ("none", ""):
            self.info(f"виртуалка ({virt}): если picom падает, поставь backend = \"xrender\" в ~/.config/picom/picom.conf")

    def fix_flameshot(self):
        f = self.cfg / "flameshot/flameshot.ini"
        text = read(f) or "[General]"
        if not re.search(r"(?m)^\[General\]", text):
            text = "[General]\n" + text
        text = re.sub(r"(?m)^useX11LegacyScreenshot=.*\n?", "", text)
        m = re.search(r"v(\d+)\.", capture(["flameshot", "--version"])[1])
        if m and int(m.group(1)) >= 14:
            text = re.sub(r"(?m)^\[General\]$", "[General]\nuseX11LegacyScreenshot=true", text, count=1)
        self.write_user_file(f, text.rstrip("\n") + "\n")
        capture(["pkill", "-u", str(self.user.pw_uid), "-x", "flameshot"])
        return True

    # ---------- блокировка ----------

    def check_lock(self):
        self.head("Экран блокировки (Super + Shift + L)")
        dots = shutil.which("i3lock-dots")
        fix_build = self.fix_i3lock if (DIR / "scripts/i3lock-dots.sh").exists() else None
        if not dots:
            plain = shutil.which("i3lock")
            self.bad("нет i3lock-dots: поле без точек, Caps Lock только после неверного пароля"
                     + (f" (сейчас используется {plain})" if plain else ""),
                     fix_build, "собрать i3lock-dots (несколько секунд)")
            log = Path("/var/log/i3lock-dots-build.log")
            if log.exists():
                self.info(f"прошлая сборка: {log}")
                self.detail(read(log), 8)
        else:
            data = Path(dots).read_bytes()
            if b"I3LOCK_DOTS" not in data or b"I3LOCK_CAPS" not in data:
                self.bad(f"{dots} без патча", fix_build, "пересобрать i3lock-dots")
            else:
                self.good(f"{dots}: точки и индикатор Caps Lock")
            if not Path("/etc/pam.d/i3lock-dots").exists():
                self.bad("нет /etc/pam.d/i3lock-dots: пароль не примется", self.fix_pam,
                         "создать /etc/pam.d/i3lock-dots")
            code, out = capture([dots, "--version"])
            if "Cassandra Fox" not in out:
                self.bad(f"i3lock-dots не запускается: {out[:200]}", fix_build, "пересобрать")

        script = self.home / ".local/bin/lock"
        repo_script = DIR / "home/.local/bin/lock"
        text = read(script)
        if not text:
            self.bad("нет ~/.local/bin/lock", self.fix_lock_script if repo_script.exists() else None,
                     "скопировать из репозитория")
        elif "i3lock-dots" not in text:
            self.bad("~/.local/bin/lock старой версии, не знает про i3lock-dots",
                     self.fix_lock_script if repo_script.exists() else None, "обновить из репозитория (старый — lock.bak)")
        else:
            self.good("~/.local/bin/lock актуальный")

        found = shutil.which("lock", path=self.user_env()["PATH"])
        if found and Path(found) != script and script.exists():
            self.bad(f"в PATH сначала находится {found}, а не ~/.local/bin/lock", None,
                     f"удали или переименуй {found}")

        sxhkd = read(self.cfg / "sxhkd/sxhkdrc")
        if not re.search(r"(?m)^\s*lock\b|,\s*lock\s*[,}]|\block, \\", sxhkd):
            self.bad("в sxhkdrc нет команды lock", None, "добавь: super + shift + l → lock")

        if self.x and script.exists():
            cache = self.home / ".cache/lock"
            code, out = self.user_run([script, "--prepare"], timeout=120)
            pngs = list(cache.glob("*.png"))
            err = read(cache / "error.log")
            if pngs and not err:
                self.good(f"фон блокировки готов ({pngs[0].name})")
            else:
                self.bad("фон блокировки не собирается, будет однотонный", self.fix_lock_cache,
                         "пересобрать картинку")
                self.detail(err or out or "ошибок нет, но картинки тоже нет")
        wall = read(self.home / ".cache/wallpaper")
        if wall and not Path(wall).is_file():
            self.bad(f"текущие обои не найдены: {wall}", self.fix_wallpaper, "выбрать другие обои")

    def fix_i3lock(self):
        return self.root_run(["bash", DIR / "scripts/i3lock-dots.sh", "-u", self.user.pw_name])

    def fix_pam(self):
        return self.root_run(["sh", "-c", "printf 'auth include system-local-login\\n' >/etc/pam.d/i3lock-dots"])

    def fix_lock_script(self):
        self.write_user_file(self.home / ".local/bin/lock", read(DIR / "home/.local/bin/lock") + "\n", 0o755)
        return self.fix_lock_cache()

    def fix_lock_cache(self):
        shutil.rmtree(self.home / ".cache/lock", ignore_errors=True)
        if self.x:
            self.user_run([self.home / ".local/bin/lock", "--prepare"], timeout=120)
        return True

    def fix_wallpaper(self):
        if self.x:
            return self.user_run(["wallpaper", "-r"])[0] == 0
        return False

    # ---------- яркость ----------

    def hardware(self):
        conf = {}
        for line in read(self.cfg / "bspwm/hardware").splitlines():
            m = re.match(r"\s*(\w+)=\"?([^\"]*)\"?\s*$", line)
            if m:
                conf[m.group(1)] = m.group(2)
        return conf

    def check_brightness(self):
        self.head("Яркость")
        devs = sorted(p.name for p in Path("/sys/class/backlight").glob("*"))
        if not devs:
            self.info("подсветки нет (обычный монитор): яркость клавишами не меняется")
            return
        self.good("подсветка: " + ", ".join(
            f"{d} ({read(f'/sys/class/backlight/{d}/type')}, {read(f'/sys/class/backlight/{d}/brightness')}/"
            f"{read(f'/sys/class/backlight/{d}/max_brightness')})" for d in devs))
        hw = self.hardware()
        chosen = hw.get("BRIGHTNESS_DEVICES", "").split()
        missing = [d for d in chosen if d not in devs]
        if missing:
            self.bad(f"в ~/.config/bspwm/hardware указана подсветка {' '.join(missing)}, такой нет",
                     self.fix_hardware, "переписать hardware по найденному")

        target = chosen[0] if chosen and not missing else devs[0]
        cur = read(f"/sys/class/backlight/{target}/brightness")
        if self.root:
            self.info("сама смена яркости проверяется только из-под пользователя в сессии")
        else:
            code, out = self.user_run(["busctl", "call", "org.freedesktop.login1",
                                       "/org/freedesktop/login1/session/auto", "org.freedesktop.login1.Session",
                                       "SetBrightness", "ssu", "backlight", target, cur])
            if code == 0:
                self.good("systemd-logind даёт менять яркость без группы video")
            elif self.user_run(["brightnessctl", "-d", target, "set", cur])[0] == 0:
                self.good("logind отказал, но brightnessctl работает")
                self.detail(out, 2)
            else:
                self.bad("яркость не меняется ни через logind, ни через brightnessctl", None,
                         "запусти debug.py из терминала в сессии bspwm: logind пускает только активную сессию")
                self.detail(out, 3)

        sxhkd = read(self.cfg / "sxhkd/sxhkdrc")
        m = re.search(r"# brightness-keys\n(.*?)\n", sxhkd)
        bound = m.group(1) if m else ("XF86MonBrightness{Up,Down}" if "XF86MonBrightness" in sxhkd else "")
        if not re.search(r"(?m)^\s*brightness\s", sxhkd):
            self.bad("в sxhkdrc нет привязки яркости", self.fix_keys, "определить клавиши нажатием")
        else:
            self.good(f"клавиши яркости в sxhkdrc: {bound or '?'}")
            self.info("если клавиши не срабатывают: python debug.py --keys (определит их нажатием)")

    def fix_hardware(self):
        bats, adapters = [], []
        for ps in sorted(Path("/sys/class/power_supply").glob("*")):
            kind = read(ps / "type")
            if kind == "Battery" and read(ps / "scope") != "Device":
                bats.append(ps.name)
            elif kind == "Mains":
                adapters.append(ps.name)
        devs = sorted(Path("/sys/class/backlight").glob("*"),
                      key=lambda d: {"raw": 0, "platform": 1, "firmware": 2}.get(read(d / "type"), 3))
        hw = self.hardware()
        bl = hw.get("BACKLIGHT_CARD", "")
        if not (Path("/sys/class/backlight") / bl).exists() or not bl:
            bl = devs[0].name if devs else "none"
        bd = " ".join(d for d in hw.get("BRIGHTNESS_DEVICES", "").split() if (Path("/sys/class/backlight") / d).exists())
        bat = hw.get("BATTERY", "")
        bat = bat if bat in bats else (bats[0] if bats else "none")
        ad = hw.get("ADAPTER", "")
        ad = ad if ad in adapters else (adapters[0] if adapters else "none")
        self.write_user_file(self.cfg / "bspwm/hardware", f'''# батарея, адаптер и подсветка для панели и клавиш яркости
# ls /sys/class/power_supply /sys/class/backlight
BATTERY={bat}
ADAPTER={ad}
BACKLIGHT_CARD={bl}
BRIGHTNESS_DEVICES="{bd}"
''')
        self.restart_panel()
        return True

    def fix_keys(self):
        if self.root:
            keys = detect_keys()
        else:
            p = subprocess.run(self.as_root([sys.executable, Path(__file__).resolve(), "--detect-keys"]),
                               stdout=subprocess.PIPE, text=True)
            keys = tuple(p.stdout.split()) if p.returncode == 0 and len(p.stdout.split()) == 2 else None
        if not keys:
            print("Клавиши не определились. Если яркость меняется сама, привязка не нужна.")
            return False
        down, up = keys
        if down.startswith("code") or up.startswith("code"):
            print(f"Неизвестные коды {down} {up}, sxhkd их не поймёт.")
            return False
        f = self.cfg / "sxhkd/sxhkdrc"
        s = read(f)
        block = f"# brightness-keys\n{{{up},{down}}}\n    brightness {{up,down}}\n# brightness-keys-end"
        if "# brightness-keys" in s:
            s = re.sub(r"# brightness-keys\n.*?# brightness-keys-end", block, s, flags=re.DOTALL)
        else:
            s = re.sub(r"(?m)^XF86MonBrightness\{Up,Down\}\n\s+brightness \{up,down\}", block, s)
            if "# brightness-keys" not in s:
                s += "\n" + block + "\n"
        self.write_user_file(f, s + "\n")
        if self.pid_of("sxhkd"):
            capture(["pkill", "-USR1", "-u", str(self.user.pw_uid), "-x", "sxhkd"])
        print(f"Яркость: {down} / {up}")
        return True

    # ---------- панель ----------

    def restart_panel(self):
        if self.x:
            self.user_spawn([self.cfg / "polybar/launch.sh"])

    def check_panel(self):
        self.head("Панель")
        hw = self.hardware()
        if not hw:
            self.bad("нет ~/.config/bspwm/hardware (батарея, адаптер, подсветка)", self.fix_hardware,
                     "создать по найденному железу")
        ps = {p.name: read(p / "type") for p in Path("/sys/class/power_supply").glob("*")}
        bats = [n for n, t in ps.items() if t == "Battery" and read(f"/sys/class/power_supply/{n}/scope") != "Device"]
        for key, kind, found in (("BATTERY", "батарея", bats), ("ADAPTER", "адаптер", [n for n, t in ps.items() if t == "Mains"])):
            val = hw.get(key)
            if val and val != "none" and val not in ps:
                self.bad(f"{kind} {val} из hardware не существует, есть: {', '.join(found) or 'ничего'}",
                         self.fix_hardware, "переписать hardware")
            elif val == "none" and found:
                self.bad(f"{kind} отключена в hardware, но есть {', '.join(found)}", self.fix_hardware, "включить")
            elif val:
                self.good(f"{kind}: {val}")

        mod = self.cfg / "polybar/modules.ini"
        s = read(mod)
        m = re.search(r"(?m)^label-indicator-on-capslock\s*=\s*(.*)$", s)
        if m and not m.group(1).startswith('"'):
            self.bad("иконка Caps Lock на панели без отступов (наезжает на часы)", self.fix_caps_label,
                     "поставить пробелы вокруг иконки")
        elif m:
            self.good("иконка Caps Lock с отступами")

        code, fonts = capture(["fc-list", ":", "family"])
        for fam, pkg in (("JetBrainsMono Nerd Font", "ttf-jetbrains-mono-nerd"),
                         ("Symbols Nerd Font", "ttf-nerd-fonts-symbols")):
            if fam in fonts:
                self.good(f"шрифт {fam}")
            else:
                self.bad(f"нет шрифта {fam}: вместо иконок квадраты",
                         lambda p=pkg: self.root_run(["pacman", "-S", "--needed", p]), f"pacman -S {pkg}")
        bl = hw.get("BACKLIGHT_CARD")
        if bl and bl != "none" and not Path(f"/sys/class/backlight/{bl}").exists():
            self.bad(f"подсветка {bl} из hardware не существует", self.fix_hardware, "переписать hardware")

        for log in sorted(Path("/tmp").glob(f"polybar-{self.user.pw_uid}*.log")):
            rows = [row for row in read(log).splitlines() if re.search(r"\berror\b", row, re.I)]
            off = [row.split("(reason: ")[-1].rstrip(")") for row in rows if "Disabling module" in row]
            errs = [row for row in rows if "Disabling module" not in row]
            for row in off:
                self.info(f"модуль панели выключен: {row}")
            if errs:
                self.bad(f"polybar пишет ошибки ({log.name})", self.restart_panel, "перезапустить панель")
                self.detail("\n".join(errs), 6)

    def fix_caps_label(self):
        f = self.cfg / "polybar/modules.ini"
        s = re.sub(r"(?m)^label-indicator-on-capslock\s*=.*$",
                   f'label-indicator-on-capslock = " {CAPS_ICON} "', read(f))
        self.write_user_file(f, s + "\n")
        self.restart_panel()
        return True

    # ---------- вход ----------

    def check_sddm(self):
        self.head("SDDM")
        fix = (lambda: self.root_run(["bash", DIR / "scripts/sddm.sh", "-u", self.user.pw_name, "--no-home"])) \
            if (DIR / "scripts/sddm.sh").exists() else None
        if not shutil.which("sddm"):
            self.bad("SDDM не установлен", fix, "установить и настроить SDDM")
            return
        dm = os.path.basename(os.path.realpath("/etc/systemd/system/display-manager.service"))
        if dm != "sddm.service":
            self.bad(f"включён другой экран входа: {dm}", fix, "переключить на SDDM")
        else:
            self.good("sddm.service включён")
        for unit in ("ly@tty2.service", "ly.service"):
            if capture(["systemctl", "is-enabled", unit])[0] == 0:
                self.bad(f"{unit} всё ещё включён", lambda u=unit: self.root_run(["systemctl", "disable", u]),
                         f"systemctl disable {unit}")
        conf = "\n".join(read(f) for f in Path("/etc/sddm.conf.d").glob("*.conf")) + read("/etc/sddm.conf")
        theme = Path("/usr/share/sddm/themes/bspwm-dots")
        if not theme.is_dir() or "Current=bspwm-dots" not in conf:
            self.bad("тема bspwm-dots не выбрана", fix, "поставить тему")
        else:
            self.good("тема bspwm-dots")
        pub = Path("/var/lib/bspwm-dots/user")
        if not pub.is_dir() or pub.stat().st_uid != self.user.pw_uid:
            self.bad(f"{pub} не принадлежит {self.user.pw_name}: фон входа не обновляется", fix, "перенастроить")
        elif not (pub / "background.jpg").exists():
            self.bad("нет фона для экрана входа", self.fix_wallpaper, "обновить обои")
        else:
            self.good("фон входа синхронизирован с обоями")
        state = read("/var/lib/sddm/state.conf")
        m = re.search(r"(?m)^User=(.*)$", state)
        if m and m.group(1) != self.user.pw_name:
            self.info(f"SDDM по умолчанию предлагает {m.group(1)}")

    # ---------- система ----------

    def check_system(self):
        self.head("Система")
        shell = self.user.pw_shell
        rc = {"zsh": ".zshrc", "fish": ".config/fish/config.fish", "bash": ".bashrc"}.get(Path(shell).name)
        if not Path(shell).exists():
            self.bad(f"оболочка {shell} не установлена: войти не получится",
                     lambda: self.root_run(["chsh", "-s", "/bin/bash", self.user.pw_name]), "вернуть bash")
        elif rc and not (self.home / rc).exists():
            src = DIR / "home" / rc
            self.bad(f"оболочка {Path(shell).name} без конфига ~/{rc}",
                     (lambda: self.write_user_file(self.home / rc, read(src) + "\n") or True) if src.exists() else None,
                     "скопировать из репозитория")
        else:
            self.good(f"оболочка {Path(shell).name}")

        if self.env and f"{self.home}/.local/bin" not in self.env.get("PATH", "").split(":"):
            self.bad("~/.local/bin нет в PATH сессии: скрипты lock, brightness и др. не найдутся", None,
                     "перезайди в сессию; PATH задаётся в bspwmrc")

        for unit in ("pipewire", "pipewire-pulse", "wireplumber"):
            code, out = self.user_run(["systemctl", "--user", "is-active", unit])
            if out == "active":
                continue
            self.bad(f"{unit}: {out or 'не запущен'} — нет звука",
                     lambda u=unit: self.user_run(["systemctl", "--user", "restart", u])[0] == 0,
                     f"systemctl --user restart {unit}")
            break
        else:
            self.good("звук: pipewire, wireplumber")

        if capture(["systemctl", "is-active", "NetworkManager"])[1] == "active":
            self.good("NetworkManager")
        else:
            self.bad("NetworkManager не запущен", lambda: self.root_run(["systemctl", "enable", "--now", "NetworkManager"]),
                     "systemctl enable --now NetworkManager")

        if self.x:
            code, out = capture(["setxkbmap", "-query"], env=self.env)
            layout = re.search(r"(?m)^layout:\s*(\S+)", out)
            options = re.search(r"(?m)^options:\s*(\S+)", out)
            if layout and "," in layout.group(1):
                self.good(f"раскладки {layout.group(1)}, переключение {options.group(1) if options else 'не задано'}")
            else:
                self.info(f"одна раскладка: {layout.group(1) if layout else '?'} (/etc/X11/xorg.conf.d/00-keyboard.conf)")

        core = DIR / "pkgs/core.txt"
        if core.exists() and shutil.which("pacman"):
            want = []
            for row in read(core).splitlines():
                want += row.split("#", 1)[0].split()
            code, out = capture(["pacman", "-T", *want])
            missing = [p for p in out.split() if p in want]
            if missing:
                self.bad("не хватает пакетов: " + " ".join(missing),
                         lambda: self.root_run(["pacman", "-S", "--needed", *missing]), "доустановить")
            else:
                self.good("все основные пакеты на месте")

    # ---------- запуск ----------

    def run(self):
        who = f"{self.user.pw_name} ({'root' if self.root else 'пользователь'})"
        self.line(paint("1", f"bspwm-dots debug — {who}, {datetime.datetime.now():%Y-%m-%d %H:%M}"))
        wanted = self.args.sections or SECTIONS
        for name in SECTIONS:
            if name in wanted:
                getattr(self, f"check_{name}")()

        self.line("")
        if not self.problems:
            self.line(paint("1;32", "Проблем не найдено."))
        else:
            self.line(paint("1;33", f"Найдено проблем: {len(self.problems)}"))
            fixable = [p for p in self.problems if p.fix]
            if fixable and not self.args.fix and not sys.stdin.isatty():
                self.line("Исправить: python debug.py --fix")
                fixable = []
            for p in fixable:
                if not self.args.fix:
                    ans = input(f"\n{p.text}\n  Исправить ({p.how})? [Y/n] ").strip().lower()
                    if ans[:1] in ("n", "н"):
                        continue
                try:
                    done = p.fix()
                except Exception as e:
                    done = False
                    print(f"  ошибка: {e}")
                self.line(f"  {'✓ исправлено' if done is not False else '✗ не вышло'}: {p.text}")
            rest = [p for p in self.problems if not p.fix]
            if rest:
                self.line("\nЭто нужно поправить вручную:")
                for p in rest:
                    self.line(f"  • {p.text}" + (f" — {p.how}" if p.how else ""))

        if self.args.report:
            f = self.home / "bspwm-debug.txt"
            f.write_text("\n".join(self.report) + "\n")
            if self.root:
                os.chown(f, self.user.pw_uid, self.user.pw_gid)
            print(f"\nОтчёт: {f}")


def main():
    p = argparse.ArgumentParser(description="Поиск и исправление проблем bspwm-dots")
    p.add_argument("sections", nargs="*", metavar="раздел",
                   help="session lock brightness panel sddm system (по умолчанию все)")
    p.add_argument("--fix", action="store_true", help="исправить всё без вопросов")
    p.add_argument("--report", action="store_true", help="сохранить отчёт в ~/bspwm-debug.txt")
    p.add_argument("--keys", action="store_true", help="определить клавиши яркости нажатием")
    p.add_argument("-u", "--user", help="пользователь, если запуск от root")
    p.add_argument("--detect-keys", action="store_true", help=argparse.SUPPRESS)
    args = p.parse_args()
    bad = [x for x in args.sections if x not in SECTIONS]
    if bad:
        p.error(f"нет раздела {', '.join(bad)}; есть: {' '.join(SECTIONS)}")

    if args.detect_keys:
        keys = detect_keys()
        if not keys:
            sys.exit(1)
        print(*keys)
        return
    doc = Doctor(args)
    if args.keys:
        sys.exit(0 if doc.fix_keys() else 1)
    doc.run()


if __name__ == "__main__":
    main()
