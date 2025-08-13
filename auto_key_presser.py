# auto_key_presser.py
import tkinter as tk
from tkinter import messagebox, Toplevel
import threading
import time
import atexit
from pynput import keyboard


# Configuration

MIN_INTERVAL_SECONDS = 0.05    # 50 ms safe default minimum
DEFAULT_MILLISECONDS = "100"   # shown in UI
ALLOW_DANGER_DEFAULT = False   # if True, allows < MIN_INTERVAL without prompt


# Global state

clicking_event = threading.Event()   # when set -> stop clicking
click_thread = None                  # reference to background thread
click_thread_lock = threading.Lock() # ensure only one thread starts

hold_active = False                  # whether target key currently held by our app
start_key_name = "f7"                # normalized start key string (e.g. 'f7', 'space', 'a')
target_key_obj = "a"                 # actual object passed to controller (Key or char)
target_key_name = "a"                # normalized name for comparisons
hold_mode = False
danger_mode_allowed = ALLOW_DANGER_DEFAULT

controller = keyboard.Controller()


# Special keys map (name -> pynput Key)
# include F1..F12

special_keys_map = {
    "shift": keyboard.Key.shift,
    "ctrl": keyboard.Key.ctrl,
    "alt": keyboard.Key.alt,
    "space": keyboard.Key.space,
    "enter": keyboard.Key.enter,
    "tab": keyboard.Key.tab,
    "esc": keyboard.Key.esc,
    "backspace": keyboard.Key.backspace,
}
# add function keys f1..f24 defensively (pynput supports many)
for i in range(1, 25):
    name = f"f{i}"
    if hasattr(keyboard.Key, name):
        special_keys_map[name] = getattr(keyboard.Key, name)


# Helpers: normalize keys

def normalize_key_name(s: str):
    """Return normalized key name (lowercase string) or None if empty."""
    if not s:
        return None
    return s.lower().strip()

def get_key_object_by_name(name: str):
    """Return a pynput Key object for special keys, or a single-char string for characters, or None."""
    if not name:
        return None
    name = name.lower().strip()
    if name in special_keys_map:
        return special_keys_map[name]
    # treat single character as char
    if len(name) == 1:
        return name
    # fallback: try first char
    return None

def pressed_key_to_name(pressed_key):
    """Convert a pynput 'key' from on_press to our normalized name string."""
    # printable char
    try:
        if hasattr(pressed_key, "char") and pressed_key.char:
            return pressed_key.char.lower()
    except Exception:
        pass
    # special key
    try:
        # match against special_keys_map values
        for nm, val in special_keys_map.items():
            if pressed_key == val:
                return nm
        # some keys expose .name attribute
        if hasattr(pressed_key, "name") and pressed_key.name:
            return pressed_key.name.lower()
    except Exception:
        pass
    return None

def same_identity(name1, name2):
    """Return True if two normalized key names represent the same key family (e.g., ctrl == ctrl_l)."""
    if not name1 or not name2:
        return False
    if name1 == name2:
        return True
    # Compare base part before '_' for keys like 'ctrl_l', 'ctrl_r'
    if "_" in name1 or "_" in name2:
        base1 = name1.split("_")[0]
        base2 = name2.split("_")[0]
        return base1 == base2
    return False


# UI-safe status update

def set_status(text, color=None):
    """Update the status label from any thread using root.after."""
    def _update():
        status_label.config(text=text)
        if color:
            status_label.config(fg=color)
        else:
            status_label.config(fg="#333")
    try:
        root.after(0, _update)
    except Exception:
        pass

# ----------------------------
# Clicking loop (normal mode)
# ----------------------------
def key_press_loop(interval_seconds, key_obj):
    """Background thread loop. Stops when clicking_event is set."""
    try:
        set_status("Running (Normal)", color="green")
        while not clicking_event.is_set():
            try:
                controller.press(key_obj)
                controller.release(key_obj)
            except Exception:
                # try safe fallback: convert to str
                try:
                    controller.press(str(key_obj))
                    controller.release(str(key_obj))
                except Exception:
                    # give up and stop
                    break
            # break early if event set during sleep
            # use small sleep slices to allow quick stop
            slept = 0.0
            chunk = 0.01
            while slept < interval_seconds:
                if clicking_event.is_set():
                    break
                to_sleep = min(chunk, interval_seconds - slept)
                time.sleep(to_sleep)
                slept += to_sleep
        set_status("Idle")
    except Exception as e:
        print("Exception in key_press_loop:", e)
        set_status("Error")
    finally:
        # ensure we clear event so new starts are possible
        clicking_event.clear()

# ----------------------------
# Thread-safe start/stop control
# ----------------------------
def start_normal_mode(interval_seconds):
    global click_thread
    with click_thread_lock:
        if click_thread and click_thread.is_alive():
            # already running
            return False
        clicking_event.clear()
        click_thread = threading.Thread(target=key_press_loop, args=(interval_seconds, target_key_obj), daemon=True)
        click_thread.start()
        return True

def stop_normal_mode():
    clicking_event.set()
    set_status("Stopping...", color="orange")
    # thread will clear event on exit; join briefly if present
    with click_thread_lock:
        t = None
        try:
            t = click_thread
        except NameError:
            t = None
    if t and t.is_alive():
        # don't block GUI long; wait briefly
        t.join(timeout=0.2)
    set_status("Idle")

# ----------------------------
# Keyboard listener callbacks
# ----------------------------
def on_press(key):
    global hold_active, hold_mode
    try:
        name = pressed_key_to_name(key)
    except Exception:
        name = None

    if name is None:
        return

    # Emergency stop: ESC always stops everything
    if name == "esc":
        safe_emergency_stop()
        return

    # if it matches start_key_name, toggle behavior
    if same_identity(name, start_key_name) or name == start_key_name:
        # debounce: ignore repeated key auto-repeat if needed by checking last action?
        # we keep simple toggle semantics
        if hold_mode:
            # toggle hold: press & keep, or release if already held
            if not hold_active:
                try:
                    controller.press(target_key_obj)
                    hold_active = True
                    set_status("Holding (Toggle)", color="green")
                except Exception:
                    set_status("Error holding key", color="red")
            else:
                try:
                    controller.release(target_key_obj)
                except Exception:
                    pass
                hold_active = False
                set_status("Idle")
        else:
            # toggle normal mode start/stop
            if not (click_thread and click_thread.is_alive()):
                # start
                interval = compute_interval_seconds()
                if interval is None:
                    return
                # enforce min unless danger mode allowed
                if interval < MIN_INTERVAL_SECONDS and not danger_mode_var.get():
                    # show warning modal on GUI thread
                    def warn_then():
                        ans = messagebox.askyesno("Very low interval",
                                                  f"Requested interval {interval*1000:.0f} ms is below safe minimum ({MIN_INTERVAL_SECONDS*1000:.0f} ms).\n\n"
                                                  "This may cause system instability. Continue?")
                        if ans:
                            danger_mode_var.set(True)
                            start_normal_mode(interval)
                    root.after(0, warn_then)
                else:
                    started = start_normal_mode(interval)
                    if not started:
                        set_status("Already Running", color="orange")
            else:
                stop_normal_mode()

# ----------------------------
# Utility: compute interval
# ----------------------------
def validate_numeric_field(var):
    """Return integer value or None if invalid (pop up error)."""
    v = var.get().strip()
    if v == "":
        return 0
    if not v.isdigit():
        return None
    return int(v)

def compute_interval_seconds():
    try:
        h = validate_numeric_field(hours_var)
        m = validate_numeric_field(minutes_var)
        s = validate_numeric_field(seconds_var)
        ms = validate_numeric_field(milliseconds_var)
    except Exception:
        h = m = s = ms = None

    if None in (h, m, s, ms):
        messagebox.showerror("Error", "Please enter only whole numbers for time fields.")
        return None

    total = h * 3600 + m * 60 + s + (ms / 1000.0)
    if total <= 0:
        messagebox.showerror("Error", "Interval must be greater than 0.")
        return None
    return total

# ----------------------------
# Save settings
# ----------------------------
def save_settings():
    global start_key_name, target_key_obj, target_key_name, hold_mode
    sk = normalize_key_name(key_var.get())
    tk_input = normalize_key_name(target_key_var.get())

    if not sk:
        messagebox.showerror("Error", "Please enter a start (initiate) key.")
        return
    if not tk_input:
        messagebox.showerror("Error", "Please enter a target key.")
        return

    # parse objects
    sk_parsed = get_key_object_by_name(sk)
    tk_parsed = get_key_object_by_name(tk_input)

    if tk_parsed is None:
        messagebox.showerror("Error", "Invalid target key. Use the selector or a single character, or special keys (space, ctrl...).")
        return

    # prevent same or same-family key
    if same_identity(sk, tk_input) or sk == tk_input:
        messagebox.showerror("Error", "Initiate key and target key cannot be the same (or same family).")
        return

    # apply settings
    start_key_name = sk
    target_key_obj = tk_parsed
    target_key_name = tk_input
    hold_mode = hold_var.get()
    # if something was held, release it
    release_held_target()
    stop_normal_mode()
    set_status("Idle")
    messagebox.showinfo("Settings Saved", f"Hotkey: {sk.upper()}\nTarget Key: {tk_input.upper()}\nMode: {'Hold (toggle)' if hold_mode else 'Normal'}")

# ----------------------------
# Emergency / cleanup routines
# ----------------------------
def safe_emergency_stop():
    """Stop everything and release keys immediately."""
    try:
        clicking_event.set()
        if hold_active:
            try:
                controller.release(target_key_obj)
            except Exception:
                pass
        # small UI feedback
        set_status("Emergency Stop", color="red")
    except Exception:
        pass

def release_held_target():
    global hold_active
    if hold_active:
        try:
            controller.release(target_key_obj)
        except Exception:
            pass
        hold_active = False

def on_closing():
    # stop clicking, release keys, cleanup
    clicking_event.set()
    release_held_target()
    try:
        listener.stop()
    except Exception:
        pass
    root.destroy()

# ensure release on process exit even if Python killed gracefully
def _atexit_release():
    try:
        release_held_target()
    except Exception:
        pass

atexit.register(_atexit_release)

# ----------------------------
# Popup key selector (modal)
# ----------------------------
def open_key_selector():
    popup = Toplevel(root)
    popup.title("Select Target Key")
    popup.configure(bg="#f0f2f5")
    popup.resizable(False, False)
    popup.grab_set()  # Make modal
    popup.geometry("300x440")

    def choose_key(k):
        target_key_var.set(k)
        popup.destroy()

    # Letters
    frame_letters = tk.LabelFrame(popup, text="Letters", bg="#f0f2f5")
    frame_letters.pack(padx=5, pady=5, fill="x")
    for i, letter in enumerate("abcdefghijklmnopqrstuvwxyz"):
        tk.Button(frame_letters, text=letter.upper(), width=4,
                  command=lambda l=letter: choose_key(l)).grid(row=i//6, column=i%6, padx=2, pady=2)

    # Numbers
    frame_nums = tk.LabelFrame(popup, text="Numbers", bg="#f0f2f5")
    frame_nums.pack(padx=5, pady=5, fill="x")
    for i in range(10):
        tk.Button(frame_nums, text=str(i), width=4,
                  command=lambda n=str(i): choose_key(n)).grid(row=i//5, column=i%5, padx=2, pady=2)

    # Special Keys
    frame_special = tk.LabelFrame(popup, text="Special Keys", bg="#f0f2f5")
    frame_special.pack(padx=5, pady=5, fill="x")
    specials = ["shift", "ctrl", "alt", "space", "enter", "tab", "esc", "backspace"] + [f"f{i}" for i in range(1, 13)]
    for i, sk in enumerate(specials):
        tk.Button(frame_special, text=sk.upper(), width=8,
                  command=lambda s=sk: choose_key(s)).grid(row=i//2, column=i%2, padx=2, pady=2)

# ----------------------------
# GUI (kept same look & layout)
# ----------------------------
root = tk.Tk()
root.title("Keyboard Auto Key Presser")
root.geometry("350x600")
root.configure(bg="#f0f2f5")

# Title
tk.Label(root, text="Keyboard Auto Key Presser", font=("Arial", 14, "bold"), bg="#f0f2f5").pack(pady=10)

# Interval Frame
interval_frame = tk.LabelFrame(root, text="Press Interval (Normal Mode)", font=("Arial", 10, "bold"), bg="#f0f2f5")
interval_frame.pack(padx=10, pady=10, fill="x")

hours_var = tk.StringVar(value="0")
minutes_var = tk.StringVar(value="0")
seconds_var = tk.StringVar(value="0")
milliseconds_var = tk.StringVar(value=DEFAULT_MILLISECONDS)  # default ms

interval_entries = []
for text, var in [("Hours", hours_var), ("Minutes", minutes_var), ("Seconds", seconds_var), ("Milliseconds", milliseconds_var)]:
    tk.Label(interval_frame, text=text, bg="#f0f2f5").pack()
    e = tk.Entry(interval_frame, textvariable=var, width=15)
    e.pack(pady=2)
    interval_entries.append(e)

# Key Settings Frame
key_frame = tk.LabelFrame(root, text="Hotkey & Target Key Settings", font=("Arial", 10, "bold"), bg="#f0f2f5")
key_frame.pack(padx=10, pady=10, fill="x")

key_var = tk.StringVar(value=start_key_name)
target_key_var = tk.StringVar(value="a")

tk.Label(key_frame, text="Start/Stop Key", bg="#f0f2f5").pack()
tk.Entry(key_frame, textvariable=key_var, width=15).pack(pady=2)

tk.Label(key_frame, text="Target Key", bg="#f0f2f5").pack()
frame_target = tk.Frame(key_frame, bg="#f0f2f5")
frame_target.pack()
tk.Entry(frame_target, textvariable=target_key_var, width=15).pack(side="left", padx=2)
tk.Button(frame_target, text="Select Key", command=open_key_selector, bg="#cccccc").pack(side="left", padx=2)

hold_var = tk.BooleanVar(value=False)
tk.Checkbutton(key_frame, text="Hold Mode", variable=hold_var, bg="#f0f2f5", command=lambda: None).pack(pady=5)

# Danger mode checkbox (allows intervals below MIN_INTERVAL_SECONDS after confirmation)
danger_mode_var = tk.BooleanVar(value=ALLOW_DANGER_DEFAULT)
tk.Checkbutton(root, text=f"Allow intervals < {int(MIN_INTERVAL_SECONDS*1000)} ms (Danger Mode)",
               variable=danger_mode_var, bg="#f0f2f5").pack(pady=5)

# Save Button
tk.Button(root, text="💾 Save Settings", font=("Arial", 11, "bold"), bg="#7EBA80", fg="white", command=save_settings).pack(pady=10, ipadx=5, ipady=3)

# Info label
tk.Label(root, text="Normal Mode: Press hotkey to start/stop\nHold Mode: Press once to hold, again to release",
         bg="#f0f2f5", fg="#333", wraplength=300, justify="center").pack(pady=5)

# Status label & emergency hint
status_label = tk.Label(root, text="Idle", font=("Arial", 10, "bold"), bg="#f0f2f5", fg="#333")
status_label.pack(pady=6)
tk.Label(root, text="Emergency stop: Press ESC anytime", bg="#f0f2f5", fg="#666").pack()

# Start keyboard listener
listener = keyboard.Listener(on_press=on_press)
listener.start()

# Closing behavior
root.protocol("WM_DELETE_WINDOW", on_closing)

# Run UI
root.mainloop()
