import tkinter as tk
from tkinter import messagebox
import threading
import time
from pynput import keyboard

clicking = False
start_key = "f7"
target_key = "a"
hold_mode = False

controller = keyboard.Controller()
hold_active = False  # track if key is being held down

# Map special keys to pynput constants
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
    """Return the correct pynput key object (special or normal)."""
    key_name = key_name.lower().strip()
    if key_name in special_keys_map:
        return special_keys_map[key_name]
    elif len(key_name) == 1:
        return key_name  # single char key
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
            # Toggle hold mode
            if not hold_active:
                controller.press(target_key)
                hold_active = True
                print(f"Holding {target_key}")
            else:
                controller.release(target_key)
                hold_active = False
                print(f"Released {target_key}")
        else:
            toggle_clicking()

# Toggle start/stop in normal mode
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
        print("Started normal mode.")
    else:
        print("Stopped normal mode.")

# Save settings
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

    if hold_active:  # Release if changing settings
        controller.release(target_key)
        hold_active = False
    clicking = False

    mode_text = "Hold Mode (toggle)" if hold_mode else "Normal Mode"
    messagebox.showinfo("Settings Saved", f"Hotkey: {start_key.upper()}\nTarget Key: {tk_input.upper()}\nMode: {mode_text}")

# GUI setup
root = tk.Tk()
root.title("Keyboard Auto Key Presser")
root.geometry("300x420")

tk.Label(root, text="Press Interval (Normal Mode)").pack(pady=5)

hours_var = tk.StringVar()
minutes_var = tk.StringVar()
seconds_var = tk.StringVar()
milliseconds_var = tk.StringVar()
key_var = tk.StringVar(value=start_key)
target_key_var = tk.StringVar(value="a")

tk.Label(root, text="Hours").pack()
tk.Entry(root, textvariable=hours_var).pack()

tk.Label(root, text="Minutes").pack()
tk.Entry(root, textvariable=minutes_var).pack()

tk.Label(root, text="Seconds").pack()
tk.Entry(root, textvariable=seconds_var).pack()

tk.Label(root, text="Milliseconds").pack()
tk.Entry(root, textvariable=milliseconds_var).pack()

tk.Label(root, text="Start/Stop Key").pack(pady=5)
tk.Entry(root, textvariable=key_var).pack()

tk.Label(root, text="Target Key (e.g., a, space, ctrl)").pack(pady=5)
tk.Entry(root, textvariable=target_key_var).pack()

hold_var = tk.BooleanVar()
tk.Checkbutton(root, text="Hold Mode", variable=hold_var).pack(pady=5)

tk.Button(root, text="Save Settings", command=save_settings).pack(pady=10)
tk.Label(root, text="Normal Mode: Press hotkey to start/stop\nHold Mode: Press once to hold, again to release").pack(pady=5)

listener = keyboard.Listener(on_press=on_press)
listener.start()

root.mainloop()
