
"""
D2R Join/Follow Tool v1.0 - lobby create/join helper

Use at your own risk. Not affiliated with Blizzard Entertainment.

GLOBAL HOTKEYS:
    HOME   = Create next game
    END    = Save and exit current game, then join next (follow mode)
    DELETE = Save and exit, then auto-create next game (host)

GAME NAMING:
    tombs-1
    tombs-2
    tombs-3
    ...
    tombs-100

Windows only. Hotkeys only act while the D2R window is focused.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import ctypes
from ctypes import wintypes
import sys
import os
import datetime

DEBUG = False
LOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hotkey_log.txt")


def log(msg):
    if not DEBUG:
        return
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(f"{datetime.datetime.now():%H:%M:%S.%f} {msg}\n")
    except Exception:
        pass

try:
    import pyautogui
except ImportError:
    pyautogui = None


# =============================================================
# CONFIGURATION
# =============================================================

BASE_WIDTH = 1648
BASE_HEIGHT = 924

D2R_WINDOW_TITLE = "Diablo II: Resurrected"

DEFAULT_GAME_PREFIX = "tombs-"
DEFAULT_START_NUMBER = 1

HOTKEY_HOME = 0x24
HOTKEY_END = 0x23
HOTKEY_DELETE = 0x2E

HOTKEY_ID_CREATE = 1001
HOTKEY_ID_JOIN = 1002
HOTKEY_ID_LEAVE = 1003

# Screenshot-derived D2R lobby coordinates.
CREATE_TAB = (1095, 68)
CREATE_NAME = (1260, 149)
CREATE_PASSWORD = (1260, 207)

CREATE_DIFFICULTY = {
    "Normal": (1158, 325),
    "Nightmare": (1260, 325),
    "Hell": (1365, 325),
}

CREATE_BUTTON = (1260, 574)

JOIN_TAB = (1260, 68)
JOIN_NAME = (1145, 129)
JOIN_PASSWORD = (1380, 129)
JOIN_BUTTON = (1260, 580)

# In-game ESC menu "Save and Exit" (from 1920x1080 screenshot, base-scaled).
SAVE_EXIT_BUTTON = (824, 406)

# Seconds to wait after Save and Exit before auto-creating the next game.
DEFAULT_LOBBY_DELAY = 6

# Join fail-safe: after clicking Join, wait this long, then check whether
# the lobby is still showing (join failed). If so, retry.
JOIN_CHECK_SECONDS = 5
JOIN_MAX_RETRIES = 3
# Region (base coords) around the Join button used to detect "still in lobby".
JOIN_CHECK_BOX = (1160, 550, 200, 60)


# =============================================================
# WINDOWS GLOBAL HOTKEY SUPPORT
# =============================================================

class GlobalHotkeys:

    def __init__(self, callback):
        self.callback = callback
        self.user32 = ctypes.windll.user32
        self.registered = []

        self.user32.GetForegroundWindow.restype = wintypes.HWND

    def register(self):
        # Key-state polling instead of RegisterHotKey (D2R swallows hotkeys).
        self.user32.GetAsyncKeyState.argtypes = [ctypes.c_int]
        self.user32.GetAsyncKeyState.restype = ctypes.c_short
        self.keys = {
            HOTKEY_ID_CREATE: HOTKEY_HOME,
            HOTKEY_ID_JOIN: HOTKEY_END,
            HOTKEY_ID_LEAVE: HOTKEY_DELETE,
        }
        self.was_down = {k: False for k in self.keys}
        log("key-state polling active for HOME, END, DELETE")
        return []

    def d2r_focused(self):
        hwnd = self.user32.GetForegroundWindow()
        if not hwnd:
            return False
        buf = ctypes.create_unicode_buffer(256)
        self.user32.GetWindowTextW(hwnd, buf, 256)
        return buf.value.startswith(D2R_WINDOW_TITLE)

    def poll(self):

        focused = self.d2r_focused()
        for hotkey_id, vk in self.keys.items():
            down = bool(self.user32.GetAsyncKeyState(vk) & 0x8000)
            if down and focused and not self.was_down[hotkey_id]:
                self.callback(hotkey_id)
            self.was_down[hotkey_id] = down

    def unregister(self):

        for hotkey_id in self.registered:
            self.user32.UnregisterHotKey(None, hotkey_id)

        self.registered.clear()


# =============================================================
# MAIN APPLICATION
# =============================================================

class D2RJoinFollowTool:

    def __init__(self, root):

        self.root = root

        root.title("D2R Join/Follow Tool")
        root.geometry("440x455")
        self._apply_icon()
        self._apply_theme()
        root.resizable(False, False)

        self.game_name = tk.StringVar(
            value=DEFAULT_GAME_PREFIX
        )

        self.password = tk.StringVar()

        self.start_number = tk.IntVar(
            value=DEFAULT_START_NUMBER
        )

        self.difficulty = tk.StringVar(value="Hell")

        self.auto_create = tk.BooleanVar(value=True)
        self.lobby_delay = tk.IntVar(value=DEFAULT_LOBBY_DELAY)
        self.end_leaves_first = tk.BooleanVar(value=True)
        self.join_retry = tk.BooleanVar(value=True)

        self.is_running = False
        self.is_closing = False

        self._build_ui()

        self.hotkeys = GlobalHotkeys(
            self.handle_hotkey
        )

        self._register_hotkeys()

        root.protocol(
            "WM_DELETE_WINDOW",
            self.close
        )

        self._poll_hotkeys()

    # ---------------------------------------------------------
    # ICON AND DARK D2R THEME
    # ---------------------------------------------------------

    def _apply_icon(self):
        here = os.path.dirname(os.path.abspath(__file__))
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("D2R.JoinFollowTool")
        except Exception:
            pass
        try:
            self.root.iconbitmap(default=os.path.join(here, "d2r_icon.ico"))
        except Exception as exc:
            log(f"ico error: {exc!r}")
        try:
            self._icon_img = tk.PhotoImage(file=os.path.join(here, "d2r_icon.png"))
            self.root.iconphoto(True, self._icon_img)
        except Exception as exc:
            log(f"png icon error: {exc!r}")

    def _apply_theme(self):
        BG = "#0e0b08"
        PANEL = "#1a140e"
        FIELD = "#241b12"
        GOLD = "#c7a35a"
        TEXT = "#d8cbb0"
        RED = "#8b1a10"
        RED_HI = "#b3261a"
        BORDER = "#5a4426"
        FONT = ("Georgia", 10)

        self.root.configure(bg=BG)
        try:
            # Dark title bar on Windows 10/11.
            hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())
            val = ctypes.c_int(1)
            for attr in (20, 19):
                ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, attr, ctypes.byref(val), ctypes.sizeof(val))
        except Exception:
            pass

        st = ttk.Style(self.root)
        st.theme_use("clam")
        st.configure(".", background=BG, foreground=TEXT, font=FONT,
                     bordercolor=BORDER, lightcolor=BORDER, darkcolor=BORDER,
                     fieldbackground=FIELD, insertcolor=GOLD, troughcolor=PANEL)
        st.configure("TFrame", background=BG)
        st.configure("TLabel", background=BG, foreground=GOLD)
        st.configure("TLabelframe", background=BG, bordercolor=BORDER)
        st.configure("TLabelframe.Label", background=BG, foreground=GOLD, font=("Georgia", 10, "bold"))
        st.configure("TEntry", fieldbackground=FIELD, foreground=TEXT)
        st.configure("TSpinbox", fieldbackground=FIELD, foreground=TEXT, arrowcolor=GOLD, background=PANEL)
        st.configure("TCombobox", fieldbackground=FIELD, foreground=TEXT, arrowcolor=GOLD, background=PANEL)
        st.map("TCombobox", fieldbackground=[("readonly", FIELD)], foreground=[("readonly", TEXT)],
               selectbackground=[("readonly", FIELD)], selectforeground=[("readonly", TEXT)])
        self.root.option_add("*TCombobox*Listbox.background", FIELD)
        self.root.option_add("*TCombobox*Listbox.foreground", TEXT)
        self.root.option_add("*TCombobox*Listbox.selectBackground", RED)
        st.configure("TCheckbutton", background=BG, foreground=TEXT, indicatorbackground=FIELD, indicatorforeground=GOLD)
        st.map("TCheckbutton", background=[("active", BG)], foreground=[("active", GOLD)])
        st.configure("TButton", background=RED, foreground=GOLD, bordercolor=GOLD,
                     font=("Georgia", 10, "bold"), padding=6, focuscolor=RED)
        st.map("TButton", background=[("pressed", "#5e120b"), ("active", RED_HI)], foreground=[("active", "#f0d48a")])
        st.configure("TSeparator", background=BORDER)

    # ---------------------------------------------------------
    # USER INTERFACE
    # ---------------------------------------------------------

    def _build_ui(self):

        main = ttk.Frame(
            self.root,
            padding=12
        )

        main.pack(fill="both", expand=True)

        ttk.Label(
            main,
            text="Game Prefix"
        ).grid(row=0, column=0, sticky="w")

        ttk.Label(
            main,
            text="Password"
        ).grid(row=0, column=1, sticky="w")

        ttk.Label(
            main,
            text="Start Number"
        ).grid(row=0, column=2, sticky="w")

        ttk.Entry(
            main,
            textvariable=self.game_name,
            width=16
        ).grid(
            row=1,
            column=0,
            padx=(0, 8),
            sticky="ew"
        )

        ttk.Entry(
            main,
            textvariable=self.password,
            width=14,
            show="*"
        ).grid(
            row=1,
            column=1,
            padx=(0, 8),
            sticky="ew"
        )

        ttk.Spinbox(
            main,
            from_=1,
            to=999999,
            textvariable=self.start_number,
            width=8
        ).grid(
            row=1,
            column=2,
            sticky="ew"
        )

        ttk.Label(
            main,
            text="Difficulty"
        ).grid(
            row=2,
            column=0,
            sticky="w",
            pady=(10, 0)
        )

        ttk.Combobox(
            main,
            textvariable=self.difficulty,
            values=("Normal", "Nightmare", "Hell"),
            state="readonly",
            width=14
        ).grid(
            row=3,
            column=0,
            sticky="ew",
            padx=(0, 8)
        )

        ttk.Checkbutton(
            main,
            text="Auto-create after exit",
            variable=self.auto_create
        ).grid(row=3, column=1, sticky="w")

        ttk.Spinbox(
            main,
            from_=2,
            to=60,
            textvariable=self.lobby_delay,
            width=6
        ).grid(row=3, column=2, sticky="w")

        ttk.Checkbutton(
            main,
            text="END leaves current game first (follow mode)",
            variable=self.end_leaves_first
        ).grid(row=8, column=0, columnspan=3, sticky="w", pady=(4, 0))

        ttk.Checkbutton(
            main,
            text=f"Retry join if it fails (up to {JOIN_MAX_RETRIES}x)",
            variable=self.join_retry
        ).grid(row=9, column=0, columnspan=3, sticky="w")

        ttk.Button(
            main,
            text="CREATE NEXT GAME",
            command=lambda: self.run_action("create")
        ).grid(
            row=4,
            column=0,
            columnspan=2,
            sticky="ew",
            padx=(0, 8),
            pady=15
        )

        ttk.Button(
            main,
            text="JOIN NEXT GAME",
            command=lambda: self.run_action("join")
        ).grid(
            row=4,
            column=2,
            sticky="ew",
            pady=15
        )

        ttk.Separator(
            main
        ).grid(
            row=5,
            column=0,
            columnspan=3,
            sticky="ew",
            pady=5
        )

        hotkeys = ttk.LabelFrame(
            main,
            text="Hotkeys (D2R window only)",
            padding=10
        )

        hotkeys.grid(
            row=6,
            column=0,
            columnspan=3,
            sticky="ew",
            pady=8
        )

        ttk.Label(
            hotkeys,
            text="HOME     - Create next game",
            foreground="#4fbf4f"
        ).pack(anchor="w")

        ttk.Label(
            hotkeys,
            text="END        - Save and exit, then join next game",
            foreground="#6c8cff"
        ).pack(anchor="w")

        ttk.Label(
            hotkeys,
            text="DELETE - Save and exit (then auto-create next)",
            foreground="#e04a3a"
        ).pack(anchor="w")

        ttk.Label(
            main,
            text=(
                "Hotkeys only work while D2R is the active window.\n"
                "DELETE / END open the ESC menu and click Save and Exit.\n"
                "Coordinates calibrated for 1648x924."
            ),
            justify="left",
            wraplength=400
        ).grid(
            row=7,
            column=0,
            columnspan=3,
            sticky="w",
            pady=5
        )

        main.columnconfigure(0, weight=1)
        main.columnconfigure(1, weight=1)

    # ---------------------------------------------------------
    # GLOBAL HOTKEY REGISTRATION
    # ---------------------------------------------------------

    def _register_hotkeys(self):

        failed = self.hotkeys.register()

        if failed:

            messagebox.showwarning(
                "Hotkey Registration",
                "Could not register these global hotkeys:\n\n"
                + ", ".join(failed)
                + "\n\nThey may already be in use by another program."
            )

    def _poll_hotkeys(self):

        if self.is_closing:
            return

        self.hotkeys.poll()

        self.root.after(
            30,
            self._poll_hotkeys
        )

    def handle_hotkey(self, hotkey_id):

        log(f"hotkey fired id={hotkey_id} running={self.is_running} fg={ctypes.windll.user32.GetForegroundWindow()}")

        if self.is_running:
            return

        if hotkey_id == HOTKEY_ID_CREATE:
            self.run_action("create", confirm=False)

        elif hotkey_id == HOTKEY_ID_JOIN:
            if self.end_leaves_first.get():
                # Following: save and exit current game, then join next.
                self.leave_game(next_action="join")
            else:
                self.run_action("join", confirm=False)

        elif hotkey_id == HOTKEY_ID_LEAVE:
            self.leave_game()

    # ---------------------------------------------------------
    # SCREEN COORDINATE HELPERS
    # ---------------------------------------------------------

    @staticmethod
    def scaled(point):

        width, height = pyautogui.size()

        return (
            round(point[0] * width / BASE_WIDTH),
            round(point[1] * height / BASE_HEIGHT),
        )

    @staticmethod
    def click(point):

        log(f"click {point} -> {D2RJoinFollowTool.scaled(point)} screen={pyautogui.size()}")
        pyautogui.click(
            *D2RJoinFollowTool.scaled(point)
        )

    @staticmethod
    def replace_text(point, value):

        D2RJoinFollowTool.click(point)

        pyautogui.hotkey("ctrl", "a")

        if value:
            pyautogui.write(
                value,
                interval=0.025
            )

    # ---------------------------------------------------------
    # LEAVE GAME
    # ---------------------------------------------------------

    def leave_game(self, next_action="create"):

        if pyautogui is None:
            return

        if self.is_running:
            return

        try:

            pyautogui.FAILSAFE = True

            # Open the ESC menu, then click Save and Exit.
            log("press esc")
            pyautogui.press("esc")
            pyautogui.sleep(0.5)
            self.click(SAVE_EXIT_BUTTON)

            if next_action == "join" or self.auto_create.get():
                try:
                    delay = max(2, int(self.lobby_delay.get()))
                except (ValueError, tk.TclError):
                    delay = DEFAULT_LOBBY_DELAY
                self.root.after(
                    delay * 1000,
                    lambda: self.run_action(next_action, confirm=False)
                )

        except Exception as exc:

            log(f"leave error: {exc!r}")
            self.root.after(
                0,
                lambda: messagebox.showerror(
                    "Leave Game Error",
                    str(exc)
                )
            )

    # ---------------------------------------------------------
    # CREATE / JOIN AUTOMATION
    # ---------------------------------------------------------

    # ---------------------------------------------------------
    # JOIN FAIL-SAFE
    # ---------------------------------------------------------

    @staticmethod
    def grab_join_box():
        try:
            x, y = D2RJoinFollowTool.scaled(JOIN_CHECK_BOX[:2])
            w, h = D2RJoinFollowTool.scaled(JOIN_CHECK_BOX[2:])
            return pyautogui.screenshot(region=(x, y, w, h)).convert("L").resize((40, 12))
        except Exception as exc:
            log(f"grab error: {exc!r}")
            return None

    @staticmethod
    def images_similar(a, b, threshold=12):
        if a is None or b is None:
            return False
        pa, pb = list(a.getdata()), list(b.getdata())
        diff = sum(abs(x - y) for x, y in zip(pa, pb)) / len(pa)
        log(f"join check diff={diff:.1f}")
        return diff < threshold

    def verify_join(self, number, lobby_snapshot, attempt):
        if self.is_closing:
            return
        now = self.grab_join_box()
        if not self.images_similar(lobby_snapshot, now):
            log(f"join looks successful (attempt {attempt})")
            self.start_number.set(number + 1)
            return
        if attempt >= JOIN_MAX_RETRIES:
            log("join failed after max retries")
            self.root.bell()
            return
        log(f"still in lobby, retrying join (attempt {attempt + 1})")
        self.run_action("join", confirm=False, retry_attempt=attempt + 1)

    def run_action(self, action, confirm=True, retry_attempt=0):

        if self.is_running:
            return

        if pyautogui is None:

            messagebox.showerror(
                "Missing Dependency",
                "Install PyAutoGUI:\n"
                "python -m pip install pyautogui"
            )
            return

        prefix = self.game_name.get().strip()

        if not prefix:
            messagebox.showwarning(
                "Missing Game Prefix",
                "Enter a game prefix."
            )
            return

        try:

            number = max(
                1,
                int(self.start_number.get())
            )

        except (ValueError, tk.TclError):

            messagebox.showwarning(
                "Invalid Number",
                "Enter a valid starting number."
            )
            return

        # No zero padding.
        # Example: tombs-1, tombs-2, tombs-10.
        game_name = f"{prefix}{number}"

        password = self.password.get()

        if confirm and not messagebox.askyesno(
            "D2R Join/Follow Tool",

            f"Action: {action.upper()}\n\n"
            f"Game: {game_name}\n"
            f"Password: {'(set)' if password else '(none)'}\n"
            f"{'Difficulty: ' + self.difficulty.get() if action == 'create' else ''}\n\n"
            "Make sure D2R is at the lobby screen.\n\n"
            "Proceed?"
        ):
            return

        self.is_running = True

        try:

            pyautogui.FAILSAFE = True
            pyautogui.PAUSE = 0.25

            if action == "create":

                self.click(CREATE_TAB)

                pyautogui.sleep(0.7)

                self.replace_text(
                    CREATE_NAME,
                    game_name
                )

                self.replace_text(
                    CREATE_PASSWORD,
                    password
                )

                self.click(
                    CREATE_DIFFICULTY[
                        self.difficulty.get()
                    ]
                )

                pyautogui.sleep(0.25)

                self.click(CREATE_BUTTON)

            elif action == "join":

                self.click(JOIN_TAB)

                pyautogui.sleep(0.7)

                self.replace_text(
                    JOIN_NAME,
                    game_name
                )

                self.replace_text(
                    JOIN_PASSWORD,
                    password
                )

                pyautogui.sleep(0.25)

                lobby_snapshot = (
                    self.grab_join_box() if self.join_retry.get() else None
                )

                self.click(JOIN_BUTTON)

                if lobby_snapshot is not None:
                    # Fail-safe: verify later; number increments on success.
                    self.root.after(
                        JOIN_CHECK_SECONDS * 1000,
                        lambda: self.verify_join(
                            number, lobby_snapshot, retry_attempt + 1
                        )
                    )
                    return

            else:
                raise ValueError(
                    f"Unknown action: {action}"
                )

            # Increment only after successful automation.
            self.start_number.set(number + 1)

        except Exception as exc:

            log(f"automation error: {exc!r}")
            messagebox.showerror(
                "Automation Failed",
                str(exc)
            )

        finally:

            self.is_running = False

    # ---------------------------------------------------------
    # SHUTDOWN
    # ---------------------------------------------------------

    def close(self):

        self.is_closing = True

        self.hotkeys.unregister()

        self.root.destroy()


# =============================================================
# APPLICATION ENTRY POINT
# =============================================================

if __name__ == "__main__":

    if sys.platform != "win32":
        raise SystemExit(
            "This version requires Windows for global hotkeys."
        )

    root = tk.Tk()

    app = D2RJoinFollowTool(root)

    root.mainloop()
