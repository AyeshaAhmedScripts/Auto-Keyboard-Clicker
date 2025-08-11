import tkinter as tk
from tkinter import messagebox
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

# GUI setup
root = tk.Tk()
root.title("Keyboard Auto Key Presser")
root.geometry("350x500")
root.configure(bg="#f0f2f5")

title_label = tk.Label(root, text="Keyboard Auto Key Presser", font=("Arial", 14, "bold"), bg="#f0f2f5")
title_label.pack(pady=10)

# Interval Frame
interval_frame = tk.LabelFrame(root, text="Press Interval (Normal Mode)", font=("Arial", 10, "bold"), bg="#f0f2f5")
interval_frame.pack(padx=10, pady=10, fill="x")

hours_var = tk.StringVar()
minutes_var = tk.StringVar()
seconds_var = tk.StringVar()
milliseconds_var = tk.StringVar(value="100") #the default value

for text, var in [("Hours", hours_var), ("Minutes", minutes_var), ("Seconds", seconds_var), ("Milliseconds", milliseconds_var)]:
    tk.Label(interval_frame, text=text, bg="#f0f2f5").pack()
    tk.Entry(interval_frame, textvariable=var, width=15).pack(pady=2)

# Key Settings Frame
key_frame = tk.LabelFrame(root, text="Hotkey & Target Key Settings", font=("Arial", 10, "bold"), bg="#f0f2f5")
key_frame.pack(padx=10, pady=10, fill="x")

key_var = tk.StringVar(value=start_key)
target_key_var = tk.StringVar(value="a")

tk.Label(key_frame, text="Start/Stop Key", bg="#f0f2f5").pack()
tk.Entry(key_frame, textvariable=key_var, width=15).pack(pady=2)

tk.Label(key_frame, text="Target Key (e.g., a, space, ctrl)", bg="#f0f2f5").pack()
tk.Entry(key_frame, textvariable=target_key_var, width=15).pack(pady=2)

hold_var = tk.BooleanVar()
tk.Checkbutton(key_frame, text="Hold Mode", variable=hold_var, bg="#f0f2f5").pack(pady=5)

# Save button
tk.Button(root, text="💾 Save Settings", font=("Arial", 11, "bold"), bg="#7EBA80", fg="white", command=save_settings).pack(pady=15, ipadx=5, ipady=3)

# Info label
info_label = tk.Label(root, text="Normal Mode: Press hotkey to start/stop\nHold Mode: Press once to hold, again to release", 
                      bg="#f0f2f5", fg="#333", wraplength=300, justify="center")
info_label.pack(pady=5)

listener = keyboard.Listener(on_press=on_press)
listener.start()

root.mainloop()
