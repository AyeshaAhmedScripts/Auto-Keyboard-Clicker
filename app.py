import tkinter as tk
from tkinter import messagebox, Toplevel
import threading
import time
from pynput import keyboard

# Variables
clicking = False
start_key = "f7"
target_key = "a"
hold_mode = False
hold_active = False

controller = keyboard.Controller()

# Special key mapping
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

def get_key_object(key_name):
    key_name = key_name.lower().strip()
    if key_name in special_keys_map:
        return special_keys_map[key_name]
    elif len(key_name) == 1:
        return key_name
    else:
        return None

# Normal mode loop
def key_press_loop(interval, key_obj):
    global clicking
    while clicking:
        controller.press(key_obj)
        controller.release(key_obj)
        time.sleep(interval)

# Keyboard listener
def on_press(key):
    global start_key, target_key, clicking, hold_mode, hold_active
    try:
        k = key.char.lower() if hasattr(key, 'char') and key.char else key.name.lower()
    except:
        return

    if k == start_key:
        if hold_mode:
            if not hold_active:
                controller.press(target_key)
                hold_active = True
            else:
                controller.release(target_key)
                hold_active = False
        else:
            toggle_clicking()

def toggle_clicking():
    global clicking, target_key
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

        threading.Thread(target=key_press_loop, args=(interval, target_key), daemon=True).start()
    else:
        pass

def save_settings():
    global start_key, target_key, hold_mode, hold_active, clicking
    sk = key_var.get().lower().strip()
    tk_input = target_key_var.get().lower().strip()

    key_obj = get_key_object(tk_input)
    if key_obj is None:
        messagebox.showerror("Error", "Invalid target key.")
        return

    if sk == tk_input:
        messagebox.showerror("Error", "Initiate key and target key cannot be the same.")
        return

    start_key = sk
    target_key = key_obj
    hold_mode = hold_var.get()

    if hold_active:
        controller.release(target_key)
        hold_active = False
    clicking = False

    mode_text = "Hold Mode (toggle)" if hold_mode else "Normal Mode"
    messagebox.showinfo("Settings Saved", f"Hotkey: {start_key.upper()}\nTarget Key: {tk_input.upper()}\nMode: {mode_text}")

# ---------------- POPUP KEY SELECTOR ----------------
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
    specials = ["shift", "ctrl", "alt", "space", "enter", "tab", "esc", "backspace"]
    for i, sk in enumerate(specials):
        tk.Button(frame_special, text=sk.title(), width=8,
                  command=lambda s=sk: choose_key(s)).grid(row=i//2, column=i%2, padx=2, pady=2)

# Disable interval fields in Hold Mode
def toggle_interval_fields():
    state = "disabled" if hold_var.get() else "normal"
    for entry in interval_entries:
        entry.config(state=state)

# ---------------- GUI ----------------
root = tk.Tk()
root.title("Keyboard Auto Key Presser")
root.geometry("350x560")
root.configure(bg="#f0f2f5")

# Title
tk.Label(root, text="Keyboard Auto Key Presser", font=("Arial", 14, "bold"), bg="#f0f2f5").pack(pady=10)

# Interval Frame
interval_frame = tk.LabelFrame(root, text="Press Interval (Normal Mode)", font=("Arial", 10, "bold"), bg="#f0f2f5")
interval_frame.pack(padx=10, pady=10, fill="x")

hours_var = tk.StringVar()
minutes_var = tk.StringVar()
seconds_var = tk.StringVar()
milliseconds_var = tk.StringVar(value="100")  # default 100 ms

interval_entries = []
for text, var in [("Hours", hours_var), ("Minutes", minutes_var), ("Seconds", seconds_var), ("Milliseconds", milliseconds_var)]:
    tk.Label(interval_frame, text=text, bg="#f0f2f5").pack()
    e = tk.Entry(interval_frame, textvariable=var, width=15)
    e.pack(pady=2)
    interval_entries.append(e)

# Key Settings Frame
key_frame = tk.LabelFrame(root, text="Hotkey & Target Key Settings", font=("Arial", 10, "bold"), bg="#f0f2f5")
key_frame.pack(padx=10, pady=10, fill="x")

key_var = tk.StringVar(value=start_key)
target_key_var = tk.StringVar(value="a")

tk.Label(key_frame, text="Start/Stop Key", bg="#f0f2f5").pack()
tk.Entry(key_frame, textvariable=key_var, width=15).pack(pady=2)

tk.Label(key_frame, text="Target Key", bg="#f0f2f5").pack()
frame_target = tk.Frame(key_frame, bg="#f0f2f5")
frame_target.pack()
tk.Entry(frame_target, textvariable=target_key_var, width=15).pack(side="left", padx=2)
tk.Button(frame_target, text="Select Key", command=open_key_selector, bg="#cccccc").pack(side="left", padx=2)

hold_var = tk.BooleanVar()
tk.Checkbutton(key_frame, text="Hold Mode", variable=hold_var, bg="#f0f2f5", command=toggle_interval_fields).pack(pady=5)

# Save Button
tk.Button(root, text="💾 Save Settings", font=("Arial", 11, "bold"), bg="#7EBA80", fg="white", command=save_settings).pack(pady=15, ipadx=5, ipady=3)

# Info label
tk.Label(root, text="Normal Mode: Press hotkey to start/stop\nHold Mode: Press once to hold, again to release",
         bg="#f0f2f5", fg="#333", wraplength=300, justify="center").pack(pady=5)

# Start Listener
listener = keyboard.Listener(on_press=on_press)
listener.start()

# Release held key on exit
def on_closing():
    if hold_active:
        controller.release(target_key)
    root.destroy()

root.protocol("WM_DELETE_WINDOW", on_closing)

root.mainloop()
