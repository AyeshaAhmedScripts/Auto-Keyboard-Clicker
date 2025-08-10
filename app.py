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

# Press key loop
def key_press_loop(interval):
    global clicking, hold_mode, target_key
    while clicking:
        if hold_mode:
            controller.press(target_key)
            time.sleep(0.01)  # short delay to avoid blocking
        else:
            controller.press(target_key)
            controller.release(target_key)
            time.sleep(interval)
    if hold_mode:
        controller.release(target_key)

# Toggle start/stop
def toggle_clicking():
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
        if not hold_mode and interval <= 0:
            messagebox.showerror("Error", "Interval must be greater than 0 in normal mode.")
            clicking = False
            return

        threading.Thread(target=key_press_loop, args=(interval,), daemon=True).start()
    else:
        print("Stopped.")

# Hotkey listener
def on_press(key):
    global start_key
    try:
        if hasattr(key, 'char'):
            if key.char == start_key:
                toggle_clicking()
        elif hasattr(key, 'name'):
            if key.name == start_key:
                toggle_clicking()
    except:
        pass

listener = keyboard.Listener(on_press=on_press)
listener.start()

# GUI
root = tk.Tk()
root.title("Keyboard Auto Key Presser")
root.geometry("300x400")

tk.Label(root, text="Press Interval").pack(pady=5)

hours_var = tk.StringVar()
minutes_var = tk.StringVar()
seconds_var = tk.StringVar()
milliseconds_var = tk.StringVar()
key_var = tk.StringVar(value=start_key)
target_key_var = tk.StringVar(value=target_key)

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

tk.Label(root, text="Target Key to Repeat").pack(pady=5)
tk.Entry(root, textvariable=target_key_var).pack()

# Save settings
def save_settings():
    global start_key, target_key, hold_mode
    start_key = key_var.get().lower().strip()
    target_key = target_key_var.get().lower().strip()
    hold_mode = hold_var.get()
    mode_text = "Hold Mode" if hold_mode else "Interval Mode"
    messagebox.showinfo("Settings Saved", f"Hotkey: {start_key.upper()}\nTarget Key: {target_key.upper()}\nMode: {mode_text}")

hold_var = tk.BooleanVar()
tk.Checkbutton(root, text="Hold Mode", variable=hold_var).pack(pady=5)

tk.Button(root, text="Save Settings", command=save_settings).pack(pady=10)
tk.Label(root, text="Press the hotkey to start/stop").pack(pady=5)

root.mainloop()
