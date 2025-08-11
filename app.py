import tkinter as tk
from tkinter import messagebox
import threading
import time
from pynput import keyboard

# ---- globals ----
clicking = False                 # normal-mode toggle
hold_mode = False                # set from GUI
pressed_in_hold_mode = False     # state flag while holding
controller = keyboard.Controller()

# parsed representations (set by Save Settings)
start_parsed = None   # ('char'|'special', value, name)
target_parsed = None  # same format


# ---- helper functions ----
def parse_key_string(s: str):
    """Return a parsed tuple: (kind, value, name)
       kind = 'char' or 'special'.
       value = keyboard.Key.* for special, or single-char string for char.
       name = normalized name used for comparison.
    """
    if not s:
        return None
    s = s.strip().lower()

    # Function keys like f1..f24
    if s.startswith('f') and s[1:].isdigit():
        attr = s
        if hasattr(keyboard.Key, attr):
            return ('special', getattr(keyboard.Key, attr), attr)

    # Common synonyms mapping to Key names
    synonyms = {
        'ctrl': 'ctrl', 'control': 'ctrl', 'alt': 'alt', 'shift': 'shift',
        'enter': 'enter', 'return': 'enter',
        'space': 'space', 'spacebar': 'space',
        'tab': 'tab', 'esc': 'esc', 'escape': 'esc',
        'backspace': 'backspace', 'delete': 'delete', 'del': 'delete',
        'up': 'up', 'down': 'down', 'left': 'left', 'right': 'right',
        'caps_lock': 'caps_lock', 'capslock': 'caps_lock',
        'home': 'home', 'end': 'end', 'page_up': 'page_up', 'pageup': 'page_up',
        'page_down': 'page_down', 'pagedown': 'page_down', 'insert': 'insert',
        'menu': 'menu', 'pause': 'pause', 'print_screen': 'print_screen', 'prtsc': 'print_screen',
        'cmd': 'cmd', 'command': 'cmd'
    }
    if s in synonyms and hasattr(keyboard.Key, synonyms[s]):
        name = synonyms[s]
        return ('special', getattr(keyboard.Key, name), name)

    # Direct Key attribute like ctrl_l, ctrl_r, shift_l, etc.
    if hasattr(keyboard.Key, s):
        return ('special', getattr(keyboard.Key, s), s)

    # If the input is a single character, treat it as char
    if len(s) == 1:
        return ('char', s, s)

    # fallback: treat first character as char
    return ('char', s[0], s[0])


def key_matches(pressed_key, parsed):
    """Return True if the pressed_key from pynput matches parsed representation."""
    if parsed is None:
        return False
    kind, value, name = parsed
    try:
        if kind == 'char':
            # pressed_key.char exists for printable characters
            return hasattr(pressed_key, 'char') and pressed_key.char and pressed_key.char.lower() == value
        else:
            # value is keyboard.Key.* object: compare directly or by name
            if pressed_key == value:
                return True
            if hasattr(pressed_key, 'name') and pressed_key.name == name:
                return True
    except Exception:
        return False
    return False


def same_identity(p1, p2):
    """Return True if two parsed keys represent the same physical key (e.g. 'ctrl' == 'ctrl_l')."""
    if p1 is None or p2 is None:
        return False
    if p1[0] == 'char' and p2[0] == 'char':
        return p1[1] == p2[1]
    if p1[0] == 'special' and p2[0] == 'special':
        base1 = p1[2].split('_')[0]
        base2 = p2[2].split('_')[0]
        return base1 == base2
    return False


# ---- key action loops / handlers ----
def key_press_loop(interval):
    """Normal mode: repeatedly press+release the target key at the given interval."""
    global clicking
    while clicking:
        # press & release target
        if target_parsed is None:
            break
        kind, val, _ = target_parsed
        try:
            controller.press(val)
            controller.release(val)
        except Exception:
            # fallback if val is char but controller expects str
            controller.press(str(val))
            controller.release(str(val))
        time.sleep(interval)


def toggle_clicking():
    """Start/stop normal (interval) mode loop."""
    global clicking
    clicking = not clicking
    if clicking:
        try:
            h = int(hours_var.get()) if hours_var.get() else 0
            m = int(minutes_var.get()) if minutes_var.get() else 0
            s = int(seconds_var.get()) if seconds_var.get() else 0
            ms = int(milliseconds_var.get()) if milliseconds_var.get() else 0
        except ValueError:
            messagebox.showerror("Error", "Please enter only numbers for time.")
            clicking = False
            return

        interval = h * 3600 + m * 60 + s + (ms / 1000)
        if interval <= 0:
            messagebox.showerror("Error", "Interval must be greater than 0 in normal mode.")
            clicking = False
            return

        threading.Thread(target=key_press_loop, args=(interval,), daemon=True).start()
    else:
        # stop clicking (the loop will exit automatically)
        pass


# ---- pynput listener callbacks ----
def on_press(key):
    global pressed_in_hold_mode, clicking, hold_mode
    if start_parsed is None or target_parsed is None:
        return

    # if pressed key matches the start key
    if key_matches(key, start_parsed):
        if hold_mode:
            # hold-mode: press target when start key is pressed (only once)
            if not pressed_in_hold_mode:
                pressed_in_hold_mode = True
                kind, val, _ = target_parsed
                controller.press(val)
        else:
            # normal toggle mode
            toggle_clicking()


def on_release(key):
    global pressed_in_hold_mode, hold_mode
    if start_parsed is None or target_parsed is None:
        return

    # release target when start key is released (hold-mode)
    if hold_mode and key_matches(key, start_parsed) and pressed_in_hold_mode:
        pressed_in_hold_mode = False
        kind, val, _ = target_parsed
        controller.release(val)


# ---- GUI & settings ----
def save_settings():
    global start_parsed, target_parsed, hold_mode
    sk_raw = key_var.get().strip()
    tk_raw = target_key_var.get().strip()

    p_sk = parse_key_string(sk_raw)
    p_tk = parse_key_string(tk_raw)

    if p_sk is None or p_tk is None:
        messagebox.showerror("Error", "Please enter valid key names.")
        return

    if same_identity(p_sk, p_tk):
        messagebox.showerror("Error", "Initiate key and target key cannot be the same (or same family).")
        return

    start_parsed = p_sk
    target_parsed = p_tk
    hold_mode = hold_var.get()

    mode_text = "Hold Mode (hold initiate key to hold target)" if hold_mode else "Normal Mode (toggle with initiate key)"
    display = f"Initiate: {sk_raw}  →  Target: {tk_raw}\nMode: {mode_text}"
    messagebox.showinfo("Settings Saved", display)


# ---- Build GUI ----
root = tk.Tk()
root.title("Keyboard Auto Key Presser")
root.geometry("360x470")

tk.Label(root, text="Press Interval (Normal Mode)").pack(pady=5)

hours_var = tk.StringVar()
minutes_var = tk.StringVar()
seconds_var = tk.StringVar()
milliseconds_var = tk.StringVar()
key_var = tk.StringVar(value="f7")
target_key_var = tk.StringVar(value="a")

tk.Label(root, text="Hours").pack()
tk.Entry(root, textvariable=hours_var).pack()

tk.Label(root, text="Minutes").pack()
tk.Entry(root, textvariable=minutes_var).pack()

tk.Label(root, text="Seconds").pack()
tk.Entry(root, textvariable=seconds_var).pack()

tk.Label(root, text="Milliseconds").pack()
tk.Entry(root, textvariable=milliseconds_var).pack()

tk.Label(root, text="Initiate (Start/Stop) Key").pack(pady=5)
tk.Entry(root, textvariable=key_var).pack()

tk.Label(root, text="Target Key (the key to press / hold)").pack(pady=5)
tk.Entry(root, textvariable=target_key_var).pack()

hold_var = tk.BooleanVar()
tk.Checkbutton(root, text="Hold Mode (press+hold initiate key)", variable=hold_var).pack(pady=6)

tk.Button(root, text="Save Settings", command=save_settings, width=20).pack(pady=8)
tk.Label(root, text="Usage:\nNormal mode: press initiate to toggle repeating.\nHold mode: hold initiate key to press (and hold) the target.\n\nMake sure to press Save Settings after changing keys.", justify="left").pack(padx=8, pady=6)

# start the global listener
listener = keyboard.Listener(on_press=on_press, on_release=on_release)
listener.start()

root.mainloop()
