import threading
import ctypes
import math
import json
import random
import time
from pathlib import Path
from ctypes import wintypes
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except (AttributeError, OSError):
    pass

from pynput import keyboard, mouse


USER32 = ctypes.windll.user32 if hasattr(ctypes, "windll") else None


def find_window_by_title(fragment):
    if USER32 is None:
        return None
    matches = []
    enum_callback_type = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

    @enum_callback_type
    def callback(hwnd, _lparam):
        if not USER32.IsWindowVisible(hwnd):
            return True
        length = USER32.GetWindowTextLengthW(hwnd)
        title = ctypes.create_unicode_buffer(length + 1)
        USER32.GetWindowTextW(hwnd, title, length + 1)
        if fragment.lower() in title.value.lower():
            matches.append((hwnd, title.value))
        return True

    USER32.EnumWindows(callback, 0)
    return matches[0] if matches else None


class AutoClicker:
    def __init__(self, root):
        self.root = root
        self.root.title("Click Assist")
        self.root.geometry("560x820")
        self.root.minsize(440, 580)
        self.root.configure(bg="#eef2ee")

        self.mouse_controller = mouse.Controller()
        self.stop_event = threading.Event()
        self.click_thread = None
        self.hotkey_listener = None
        self.pick_listener = None
        self.marker_window = None
        self.marker_size = 30
        self.spot_manager_window = None
        self.manager_spot_list = None
        self.is_running = False
        self.click_count = 0
        self.saved_spots = []
        self.scripts_dir = Path(__file__).with_name("scripts")
        self.target_hwnd = None

        self.interval_value = tk.StringVar(value="100")
        self.interval_unit = tk.StringVar(value="milliseconds")
        self.random_delay_enabled = tk.BooleanVar(value=False)
        self.random_delay_value = tk.StringVar(value="0")
        self.click_button = tk.StringVar(value="left")
        self.click_type = tk.StringVar(value="single")
        self.click_mode = tk.StringVar(value="current")
        self.position_x = tk.StringVar(value="0")
        self.position_y = tk.StringVar(value="0")
        self.spot_name = tk.StringVar(value="Spot 1")
        self.status_text = tk.StringVar(value="Ready")
        self.counter_text = tk.StringVar(value="0 clicks")
        self.target_text = tk.StringVar(value="Target not selected")
        self.spot_count_text = tk.StringVar(value="0 spots")
        self.background_clicks = tk.BooleanVar(value=True)
        self.show_crosshair = tk.BooleanVar(value=True)
        self.last_marker_position = None

        self.build_ui()
        self.start_hotkeys()
        self.root.protocol("WM_DELETE_WINDOW", self.close)

    def build_ui(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TFrame", background="#eef2ee")
        style.configure("Panel.TFrame", background="#ffffff")
        style.configure("TLabel", background="#eef2ee", foreground="#26332f", font=("Segoe UI", 10))
        style.configure("Title.TLabel", background="#173f38", foreground="#ffffff", font=("Segoe UI", 25, "bold"))
        style.configure("Subtitle.TLabel", background="#173f38", foreground="#c7ded5", font=("Segoe UI", 10))
        style.configure("Muted.TLabel", background="#eef2ee", foreground="#66736d", font=("Segoe UI", 9))
        style.configure("PanelLabel.TLabel", background="#ffffff", foreground="#173f38", font=("Segoe UI", 9, "bold"))
        style.configure("PanelMuted.TLabel", background="#ffffff", foreground="#66736d", font=("Segoe UI", 9))
        style.configure("TButton", font=("Segoe UI", 10), padding=(11, 8))
        style.configure("Primary.TButton", background="#e26643", foreground="white", font=("Segoe UI", 11, "bold"), padding=(14, 11))
        style.map("Primary.TButton", background=[("active", "#c95032")])
        style.configure("Stop.TButton", background="#f5e8e4", foreground="#9b3f2d", font=("Segoe UI", 10, "bold"), padding=(12, 11))
        style.map("Stop.TButton", background=[("active", "#ecd3cc")])
        style.configure("TEntry", padding=8)
        style.configure("TCombobox", padding=7)
        style.configure("Status.TLabel", background="#173f38", foreground="#ffffff", font=("Segoe UI", 10, "bold"), padding=10)
        style.configure("Spots.Treeview", background="#f5f8f6", fieldbackground="#f5f8f6", foreground="#26332f", rowheight=29, font=("Segoe UI", 9), borderwidth=0)
        style.configure("Spots.Treeview.Heading", background="#e8efeb", foreground="#34534a", font=("Segoe UI", 9, "bold"), padding=(8, 7))
        style.map("Spots.Treeview", background=[("selected", "#b8d8cc")], foreground=[("selected", "#173f38")])

        viewport = ttk.Frame(self.root)
        viewport.pack(fill="both", expand=True)
        canvas = tk.Canvas(viewport, bg="#eef2ee", highlightthickness=0)
        scrollbar = ttk.Scrollbar(viewport, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        outer = ttk.Frame(canvas, padding=22)
        outer_window = canvas.create_window((0, 0), window=outer, anchor="nw")

        def update_scroll_region(_event=None):
            canvas.configure(scrollregion=canvas.bbox("all"))

        def resize_content(event):
            canvas.itemconfigure(outer_window, width=event.width)

        outer.bind("<Configure>", update_scroll_region)
        canvas.bind("<Configure>", resize_content)
        canvas.bind_all("<MouseWheel>", lambda event: canvas.yview_scroll(int(-event.delta / 120), "units"))

        header = tk.Frame(outer, bg="#173f38", padx=20, pady=17)
        header.pack(fill="x", pady=(0, 18))
        ttk.Label(header, text="Click Assist", style="Title.TLabel").pack(anchor="w")
        ttk.Label(header, text="Automate precise, repeatable clicks", style="Subtitle.TLabel").pack(anchor="w", pady=(2, 0))

        controls = ttk.Frame(outer)
        controls.pack(fill="x", pady=(0, 12))
        self.toggle_button = ttk.Button(controls, text="Start clicking", style="Primary.TButton", command=self.toggle)
        self.toggle_button.pack(side="left", fill="x", expand=True)
        ttk.Button(controls, text="Stop", style="Stop.TButton", command=self.stop).pack(side="left", padx=(8, 0))

        info = ttk.Frame(outer)
        info.pack(fill="x", pady=(0, 14))
        ttk.Label(info, textvariable=self.status_text, style="Status.TLabel", anchor="center").pack(fill="x")
        ttk.Label(info, textvariable=self.counter_text, anchor="center").pack(fill="x", pady=(7, 0))

        target_bar = ttk.Frame(outer)
        target_bar.pack(fill="x", pady=(0, 14))
        ttk.Label(target_bar, text="TARGET WINDOW", style="Muted.TLabel").pack(side="left")
        ttk.Label(target_bar, textvariable=self.target_text, style="Muted.TLabel").pack(side="left", padx=(8, 0))
        ttk.Button(target_bar, text="Find Growtopia", command=self.find_target_window).pack(side="right")
        ttk.Checkbutton(target_bar, text="Background clicks", variable=self.background_clicks).pack(side="right", padx=(0, 12))

        script_panel = ttk.Frame(outer, style="Panel.TFrame", padding=14)
        script_panel.pack(fill="x", pady=(0, 14))
        script_header = ttk.Frame(script_panel, style="Panel.TFrame")
        script_header.pack(fill="x", pady=(0, 8))
        ttk.Label(script_header, text="SAVED SCRIPTS", style="PanelLabel.TLabel").pack(side="left")
        ttk.Label(script_header, text="Store and switch between setups", style="PanelMuted.TLabel").pack(side="right")
        self.script_name = tk.StringVar(value="my_script")
        self.script_picker = ttk.Combobox(script_panel, textvariable=self.script_name, state="normal")
        self.script_picker.pack(fill="x", expand=True)
        self.script_picker.bind("<Button-1>", lambda event: self.refresh_script_choices())
        script_actions = ttk.Frame(script_panel, style="Panel.TFrame")
        script_actions.pack(fill="x", pady=(8, 0))
        ttk.Button(script_actions, text="Load", command=self.load_script).pack(side="left", fill="x", expand=True)
        ttk.Button(script_actions, text="Save", command=self.save_script).pack(side="left", fill="x", expand=True, padx=6)
        ttk.Button(script_actions, text="Save as...", command=self.save_script_as).pack(side="left", fill="x", expand=True)
        self.refresh_script_choices()

        settings = ttk.Frame(outer, style="Panel.TFrame", padding=20)
        settings.pack(fill="x")

        ttk.Label(settings, text="CLICK INTERVAL", style="PanelLabel.TLabel", font=("Segoe UI", 8, "bold")).grid(row=0, column=0, columnspan=3, sticky="w")
        ttk.Entry(settings, textvariable=self.interval_value, width=9).grid(row=1, column=0, sticky="ew", pady=(6, 14))
        ttk.Combobox(settings, textvariable=self.interval_unit, values=("milliseconds", "seconds", "minutes"), state="readonly", width=14).grid(row=1, column=1, sticky="w", padx=(8, 0), pady=(6, 14))
        settings.columnconfigure(0, weight=1)
        ttk.Checkbutton(settings, text="Timing variation", variable=self.random_delay_enabled).grid(row=1, column=2, sticky="w", padx=(14, 0))
        ttk.Entry(settings, textvariable=self.random_delay_value, width=8).grid(row=1, column=3, sticky="w", padx=(8, 0))
        ttk.Label(settings, text="max extra ms", style="PanelLabel.TLabel").grid(row=2, column=2, columnspan=2, sticky="w", padx=(14, 0), pady=(0, 10))

        ttk.Label(settings, text="BUTTON", style="PanelLabel.TLabel", font=("Segoe UI", 8, "bold")).grid(row=2, column=0, sticky="w")
        ttk.Combobox(settings, textvariable=self.click_button, values=("left", "right", "middle"), state="readonly", width=12).grid(row=3, column=0, sticky="w", pady=(6, 14))
        ttk.Label(settings, text="ACTION", style="PanelLabel.TLabel", font=("Segoe UI", 8, "bold")).grid(row=2, column=1, sticky="w", padx=(8, 0))
        ttk.Combobox(settings, textvariable=self.click_type, values=("single", "double"), state="readonly", width=12).grid(row=3, column=1, sticky="w", padx=(8, 0), pady=(6, 14))

        ttk.Label(settings, text="POSITION", style="PanelLabel.TLabel", font=("Segoe UI", 8, "bold")).grid(row=4, column=0, columnspan=2, sticky="w")
        ttk.Radiobutton(settings, text="Current cursor position", variable=self.click_mode, value="current").grid(row=5, column=0, columnspan=2, sticky="w", pady=(6, 4))
        fixed_row = ttk.Frame(settings, style="Panel.TFrame")
        fixed_row.grid(row=6, column=0, columnspan=3, sticky="w")
        ttk.Radiobutton(fixed_row, text="Fixed position", variable=self.click_mode, value="fixed").pack(side="left")
        ttk.Label(fixed_row, text="X", style="PanelLabel.TLabel").pack(side="left", padx=(14, 4))
        ttk.Entry(fixed_row, textvariable=self.position_x, width=7).pack(side="left")
        ttk.Label(fixed_row, text="Y", style="PanelLabel.TLabel").pack(side="left", padx=(8, 4))
        ttk.Entry(fixed_row, textvariable=self.position_y, width=7).pack(side="left")
        ttk.Button(settings, text="Capture cursor", command=self.capture_position).grid(row=7, column=0, columnspan=2, sticky="w", pady=(10, 0))

        settings.columnconfigure(1, weight=1)

        spots_panel = ttk.Frame(outer, style="Panel.TFrame", padding=18)
        spots_panel.pack(fill="x", pady=(14, 0))
        spots_heading = ttk.Frame(spots_panel, style="Panel.TFrame")
        spots_heading.pack(fill="x")
        ttk.Label(spots_heading, text="CLICK SEQUENCE", style="PanelLabel.TLabel").pack(side="left")
        ttk.Label(spots_heading, textvariable=self.spot_count_text, style="PanelMuted.TLabel").pack(side="left", padx=(10, 0))
        ttk.Radiobutton(spots_heading, text="Run saved spots in order", variable=self.click_mode, value="saved").pack(side="right")
        ttk.Label(spots_panel, text="Select a spot to repick its location, edit its timing, or remove it. Double-click to edit.", style="PanelMuted.TLabel").pack(anchor="w", pady=(5, 12))
        ttk.Checkbutton(spots_panel, text="Show crosshair while running", variable=self.show_crosshair, command=self.toggle_crosshair).pack(anchor="w", pady=(0, 10))

        add_spot_row = ttk.Frame(spots_panel, style="Panel.TFrame")
        add_spot_row.pack(fill="x")
        ttk.Label(add_spot_row, text="New spot name", style="PanelLabel.TLabel").pack(side="left")
        ttk.Entry(add_spot_row, textvariable=self.spot_name, width=18).pack(side="left", padx=(9, 8))
        ttk.Button(add_spot_row, text="Pick and add", style="Primary.TButton", command=self.pick_spot).pack(side="left")

        table_frame = ttk.Frame(spots_panel, style="Panel.TFrame")
        table_frame.pack(fill="both", expand=True, pady=(4, 8))
        columns = ("name", "position", "delay", "duration")
        self.spot_list = ttk.Treeview(table_frame, columns=columns, show="headings", height=5, selectmode="browse", style="Spots.Treeview")
        self.spot_list.heading("name", text="Spot")
        self.spot_list.heading("position", text="Screen position")
        self.spot_list.heading("delay", text="Delay")
        self.spot_list.heading("duration", text="Hold")
        self.spot_list.column("name", width=150, minwidth=90, anchor="w", stretch=True)
        self.spot_list.column("position", width=120, minwidth=95, anchor="center", stretch=True)
        self.spot_list.column("delay", width=80, minwidth=65, anchor="center", stretch=False)
        self.spot_list.column("duration", width=80, minwidth=65, anchor="center", stretch=False)
        spot_scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.spot_list.yview)
        self.spot_list.configure(yscrollcommand=spot_scrollbar.set)
        self.spot_list.pack(side="left", fill="both", expand=True)
        spot_scrollbar.pack(side="right", fill="y")
        self.spot_list.tag_configure("odd", background="#f5f8f6")
        self.spot_list.tag_configure("even", background="#ffffff")
        self.spot_list.bind("<<TreeviewSelect>>", self.select_saved_spot)
        self.spot_list.bind("<Double-1>", lambda event: self.edit_spot())
        spot_actions = ttk.Frame(spots_panel, style="Panel.TFrame")
        spot_actions.pack(fill="x")
        ttk.Button(spot_actions, text="Repick location", command=self.repick_selected_spot).pack(side="left")
        ttk.Button(spot_actions, text="Edit settings", command=self.edit_spot).pack(side="left", padx=(7, 0))
        ttk.Button(spot_actions, text="Open large editor", command=self.open_spot_manager).pack(side="left", padx=(7, 0))
        ttk.Button(spot_actions, text="Remove", style="Stop.TButton", command=self.remove_spot).pack(side="right")

        ttk.Separator(outer).pack(fill="x", pady=18)
        ttk.Label(outer, text="F6  Start / pause\nF7  Stop immediately", style="Muted.TLabel", justify="left").pack(anchor="w")

    def start_hotkeys(self):
        self.hotkey_listener = keyboard.GlobalHotKeys({"<f6>": self.toggle_from_hotkey, "<f7>": self.stop_from_hotkey})
        self.hotkey_listener.start()

    def toggle_from_hotkey(self):
        self.root.after(0, self.toggle)

    def stop_from_hotkey(self):
        self.root.after(0, self.stop)

    def find_target_window(self):
        match = find_window_by_title("Growtopia")
        if match is None:
            self.target_hwnd = None
            self.target_text.set("Growtopia window not found")
            self.status_text.set("Open Growtopia, then try again")
            return
        self.target_hwnd, title = match
        self.target_text.set(f"{title}  (handle {self.target_hwnd})")
        self.status_text.set("Growtopia selected; activate it before starting")

    def script_path(self):
        name = self.script_name.get().strip()
        if not name:
            raise ValueError("Enter a script name.")
        safe_name = "".join(character for character in name if character.isalnum() or character in " _-").strip()
        if not safe_name:
            raise ValueError("Enter a valid script name.")
        return self.scripts_dir / f"{safe_name}.json"

    def refresh_script_choices(self):
        try:
            self.scripts_dir.mkdir(exist_ok=True)
            names = sorted(path.stem for path in self.scripts_dir.glob("*.json"))
        except OSError:
            names = []
        self.script_picker.configure(values=names)
        return names

    def script_data(self):
        return {
            "interval_value": self.interval_value.get(),
            "interval_unit": self.interval_unit.get(),
            "click_button": self.click_button.get(),
            "click_type": self.click_type.get(),
            "click_mode": self.click_mode.get(),
            "position_x": self.position_x.get(),
            "position_y": self.position_y.get(),
            "random_delay_enabled": self.random_delay_enabled.get(),
            "random_delay_value": self.random_delay_value.get(),
            "saved_spots": self.saved_spots,
        }

    def save_script(self):
        try:
            path = self.script_path()
            self.scripts_dir.mkdir(exist_ok=True)
            path.write_text(json.dumps(self.script_data(), indent=2), encoding="utf-8")
        except (OSError, ValueError) as error:
            messagebox.showerror("Save script", str(error))
            return
        self.refresh_script_choices()
        self.script_name.set(path.stem)
        self.status_text.set(f"Saved script: {path.stem}")

    def save_script_as(self):
        name = simpledialog.askstring("Save script as", "Name this script:", initialvalue=self.script_name.get(), parent=self.root)
        if name is None:
            return
        self.script_name.set(name)
        try:
            path = self.script_path()
            if path.exists() and not messagebox.askyesno("Replace script?", f"'{path.stem}' already exists. Replace it?", parent=self.root):
                return
            self.scripts_dir.mkdir(exist_ok=True)
            path.write_text(json.dumps(self.script_data(), indent=2), encoding="utf-8")
        except (OSError, ValueError) as error:
            messagebox.showerror("Save script", str(error))
            return
        self.refresh_script_choices()
        self.script_name.set(path.stem)
        self.status_text.set(f"Saved script: {path.stem}")

    def load_script(self):
        try:
            path = self.script_path()
            data = json.loads(path.read_text(encoding="utf-8"))
            self.interval_value.set(str(data["interval_value"]))
            self.interval_unit.set(data["interval_unit"])
            self.click_button.set(data["click_button"])
            self.click_type.set(data["click_type"])
            self.click_mode.set(data["click_mode"])
            self.position_x.set(str(data["position_x"]))
            self.position_y.set(str(data["position_y"]))
            self.random_delay_enabled.set(bool(data.get("random_delay_enabled", False)))
            self.random_delay_value.set(str(data.get("random_delay_value", "0")))
            self.saved_spots = data.get("saved_spots", [])
            self.refresh_spot_list()
        except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
            messagebox.showerror("Load script", f"Could not load script: {error}")
            return
        self.refresh_script_choices()
        self.script_name.set(path.stem)
        self.status_text.set(f"Loaded script: {path.stem}")

    def target_is_foreground(self):
        if USER32 is None or self.target_hwnd is None:
            return False
        return bool(USER32.IsWindow(self.target_hwnd)) and USER32.GetForegroundWindow() == self.target_hwnd

    def send_background_click(self, x, y, button, clicks_per_spot, duration):
        if USER32 is None or self.target_hwnd is None or x is None:
            return False
        point = wintypes.POINT(x, y)
        if not USER32.ScreenToClient(self.target_hwnd, ctypes.byref(point)):
            return False
        client_x = point.x & 0xFFFF
        client_y = point.y & 0xFFFF
        lparam = client_x | (client_y << 16)
        button_down, button_up = {
            mouse.Button.left: (0x0201, 0x0202),
            mouse.Button.right: (0x0204, 0x0205),
            mouse.Button.middle: (0x0207, 0x0208),
        }[button]
        for _ in range(clicks_per_spot):
            USER32.PostMessageW(self.target_hwnd, button_down, 0, lparam)
            if duration > 0:
                time.sleep(duration)
            USER32.PostMessageW(self.target_hwnd, button_up, 0, lparam)
        return True

    def capture_position(self):
        x, y = self.mouse_controller.position
        self.position_x.set(str(x))
        self.position_y.set(str(y))
        self.click_mode.set("fixed")
        self.status_text.set(f"Captured position: {x}, {y}")

    def pick_spot(self, spot_index=None):
        if spot_index is not None and not 0 <= spot_index < len(self.saved_spots):
            return
        self.status_text.set("Move to the target and left-click to confirm")
        if self.pick_listener is not None:
            self.pick_listener.stop()

        listener = None

        def on_click(x, y, button, pressed):
            if pressed and button == mouse.Button.left:
                listener.stop()
                if self.pick_listener is listener:
                    self.pick_listener = None
                self.root.after(0, lambda: self.confirm_spot_location(x, y, spot_index))
                return False

        listener = mouse.Listener(on_click=on_click)
        self.pick_listener = listener
        listener.start()

    def repick_selected_spot(self):
        selection = self.spot_list.selection()
        if not selection:
            messagebox.showinfo("Repick location", "Select a spot in the sequence first.")
            return
        self.pick_spot(int(selection[0]))

    def open_spot_manager(self):
        if self.spot_manager_window is not None and self.spot_manager_window.winfo_exists():
            self.spot_manager_window.deiconify()
            self.spot_manager_window.lift()
            return

        window = tk.Toplevel(self.root)
        window.title("Click Assist - Spot Manager")
        window.geometry("900x560")
        window.minsize(700, 420)
        window.transient(self.root)
        self.spot_manager_window = window

        content = ttk.Frame(window, padding=22)
        content.pack(fill="both", expand=True)
        title_row = ttk.Frame(content)
        title_row.pack(fill="x", pady=(0, 14))
        ttk.Label(title_row, text="Spot Manager", style="Title.TLabel").pack(side="left")
        ttk.Label(title_row, textvariable=self.spot_count_text, style="Muted.TLabel").pack(side="right")

        manager_frame = ttk.Frame(content, style="Panel.TFrame", padding=10)
        manager_frame.pack(fill="both", expand=True)
        columns = ("name", "position", "delay", "duration")
        self.manager_spot_list = ttk.Treeview(manager_frame, columns=columns, show="headings", selectmode="browse", style="Spots.Treeview")
        self.manager_spot_list.heading("name", text="Spot name")
        self.manager_spot_list.heading("position", text="Screen position")
        self.manager_spot_list.heading("delay", text="Delay before click")
        self.manager_spot_list.heading("duration", text="Button hold")
        self.manager_spot_list.column("name", width=260, minwidth=150, anchor="w", stretch=True)
        self.manager_spot_list.column("position", width=190, minwidth=130, anchor="center", stretch=True)
        self.manager_spot_list.column("delay", width=150, minwidth=110, anchor="center", stretch=True)
        self.manager_spot_list.column("duration", width=150, minwidth=110, anchor="center", stretch=True)
        manager_scrollbar = ttk.Scrollbar(manager_frame, orient="vertical", command=self.manager_spot_list.yview)
        self.manager_spot_list.configure(yscrollcommand=manager_scrollbar.set)
        self.manager_spot_list.pack(side="left", fill="both", expand=True)
        manager_scrollbar.pack(side="right", fill="y")
        self.manager_spot_list.tag_configure("odd", background="#f5f8f6")
        self.manager_spot_list.tag_configure("even", background="#ffffff")
        self.manager_spot_list.bind("<<TreeviewSelect>>", self.manager_spot_selected)
        self.manager_spot_list.bind("<Double-1>", lambda event: self.edit_manager_spot())

        actions = ttk.Frame(content)
        actions.pack(fill="x", pady=(14, 0))
        ttk.Button(actions, text="Repick location", command=self.repick_manager_spot).pack(side="left")
        ttk.Button(actions, text="Edit settings", command=self.edit_manager_spot).pack(side="left", padx=(8, 0))
        ttk.Button(actions, text="Remove spot", style="Stop.TButton", command=self.remove_manager_spot).pack(side="left", padx=(8, 0))
        ttk.Button(actions, text="Close", command=self.close_spot_manager).pack(side="right")

        self.refresh_spot_list()
        current_selection = self.spot_list.selection()
        if current_selection:
            self.manager_spot_list.selection_set(current_selection[0])
        window.protocol("WM_DELETE_WINDOW", self.close_spot_manager)

    def close_spot_manager(self):
        window = self.spot_manager_window
        self.spot_manager_window = None
        self.manager_spot_list = None
        if window is not None and window.winfo_exists():
            window.destroy()

    def manager_spot_selected(self, event=None):
        selection = self.manager_spot_list.selection()
        if not selection:
            return
        spot_id = selection[0]
        self.spot_list.selection_set(spot_id)
        self.spot_list.see(spot_id)
        self.select_saved_spot()

    def manager_selection_to_main(self):
        if self.manager_spot_list is None:
            return False
        selection = self.manager_spot_list.selection()
        if not selection:
            messagebox.showinfo("Spot Manager", "Select a spot first.", parent=self.spot_manager_window)
            return False
        self.spot_list.selection_set(selection[0])
        self.spot_list.see(selection[0])
        return True

    def repick_manager_spot(self):
        if self.manager_selection_to_main():
            self.repick_selected_spot()

    def edit_manager_spot(self):
        if self.manager_selection_to_main():
            self.edit_spot()

    def remove_manager_spot(self):
        if self.manager_selection_to_main():
            self.remove_spot(parent=self.spot_manager_window)

    def confirm_spot_location(self, x, y, spot_index):
        if spot_index is None:
            self.add_spot_at(x, y)
            return
        if spot_index >= len(self.saved_spots):
            return
        spot = self.saved_spots[spot_index]
        spot.update(x=x, y=y)
        self.refresh_spot_list()
        self.spot_list.selection_set(str(spot_index))
        self.click_mode.set("saved")
        self.show_spot_marker(x, y)
        self.status_text.set(f"Updated location for {spot['name']}: {x}, {y}")

    def add_spot_at(self, x, y):
        name = self.spot_name.get().strip() or f"Spot {len(self.saved_spots) + 1}"
        self.saved_spots.append({"name": name, "x": x, "y": y, "delay": 0.0, "duration": 0.0})
        self.refresh_spot_list()
        self.spot_list.selection_set(str(len(self.saved_spots) - 1))
        self.click_mode.set("saved")
        self.show_spot_marker(x, y)
        self.spot_name.set(f"Spot {len(self.saved_spots) + 1}")
        self.status_text.set(f"Added {name}")

    def refresh_spot_list(self):
        self.spot_count_text.set(f"{len(self.saved_spots)} spot" + ("s" if len(self.saved_spots) != 1 else ""))
        self.populate_spot_table(self.spot_list)
        if self.manager_spot_list is not None and self.manager_spot_list.winfo_exists():
            self.populate_spot_table(self.manager_spot_list)

    def populate_spot_table(self, table):
        table.delete(*table.get_children())
        for index, spot in enumerate(self.saved_spots):
            duration = spot.get("duration", 0.0)
            table.insert(
                "",
                "end",
                iid=str(index),
                values=(spot["name"], f"{spot['x']}, {spot['y']}", f"{spot['delay']:g}s", f"{duration:g}s"),
                tags=("even" if index % 2 == 0 else "odd",),
            )

    def select_saved_spot(self, event=None):
        selection = self.spot_list.selection()
        if selection:
            self.click_mode.set("saved")
            spot = self.saved_spots[int(selection[0])]
            self.show_spot_marker(spot["x"], spot["y"])
        else:
            self.hide_spot_marker()

    def show_spot_marker(self, x, y):
        self.last_marker_position = (x, y)
        if not self.show_crosshair.get():
            self.hide_spot_marker()
            return
        if self.marker_window is None or not self.marker_window.winfo_exists():
            marker = tk.Toplevel(self.root)
            marker.overrideredirect(True)
            marker.attributes("-topmost", True)
            marker.configure(bg="#ff00ff")
            try:
                marker.attributes("-transparentcolor", "#ff00ff")
            except tk.TclError:
                marker.attributes("-alpha", 0.94)
            size = self.marker_size
            canvas = tk.Canvas(marker, width=size, height=size, bg="#ff00ff", highlightthickness=0, bd=0)
            canvas.pack()
            center = size // 2
            canvas.create_line(1, center, size - 1, center, fill="#ffffff", width=2)
            canvas.create_line(center, 1, center, size - 1, fill="#ffffff", width=2)
            canvas.create_oval(4, 4, size - 4, size - 4, fill="#e2573f", outline="#ffffff", width=2)
            canvas.create_oval(center - 3, center - 3, center + 3, center + 3, fill="#ffffff", outline="#173f38", width=1)
            self.marker_window = marker
            marker.update_idletasks()
            self.make_marker_click_through()

        offset = self.marker_size // 2
        self.marker_window.geometry(f"{self.marker_size}x{self.marker_size}+{int(x) - offset}+{int(y) - offset}")
        self.marker_window.deiconify()
        self.marker_window.lift()

    def toggle_crosshair(self):
        if not self.show_crosshair.get():
            self.hide_spot_marker()
        elif self.last_marker_position is not None:
            self.show_spot_marker(*self.last_marker_position)
        else:
            selection = self.spot_list.selection()
            if selection:
                spot = self.saved_spots[int(selection[0])]
                self.show_spot_marker(spot["x"], spot["y"])

    def make_marker_click_through(self):
        if USER32 is None or self.marker_window is None:
            return
        hwnd = self.marker_window.winfo_id()
        get_window_long = USER32.GetWindowLongW
        get_window_long.argtypes = (wintypes.HWND, ctypes.c_int)
        get_window_long.restype = ctypes.c_long
        set_window_long = USER32.SetWindowLongW
        set_window_long.argtypes = (wintypes.HWND, ctypes.c_int, ctypes.c_long)
        set_window_long.restype = ctypes.c_long
        extended_style = get_window_long(hwnd, -20)
        set_window_long(hwnd, -20, extended_style | 0x00080000 | 0x00000020 | 0x00000080)

    def hide_spot_marker(self):
        if self.marker_window is not None and self.marker_window.winfo_exists():
            self.marker_window.withdraw()

    def edit_spot(self):
        selection = self.spot_list.selection()
        if not selection:
            messagebox.showinfo("Edit spot", "Select a saved spot first.")
            return
        index = int(selection[0])
        spot = self.saved_spots[index]
        dialog = tk.Toplevel(self.root)
        dialog.title("Edit click spot")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()
        frame = ttk.Frame(dialog, padding=16)
        frame.pack(fill="both", expand=True)
        name_var = tk.StringVar(value=spot["name"])
        x_var = tk.StringVar(value=str(spot["x"]))
        y_var = tk.StringVar(value=str(spot["y"]))
        delay_var = tk.StringVar(value=str(spot["delay"]))
        duration_var = tk.StringVar(value=str(spot.get("duration", 0.0)))
        fields = (("Name", name_var), ("X", x_var), ("Y", y_var), ("Delay before click (seconds)", delay_var), ("Click duration (seconds)", duration_var))
        for row, (label, variable) in enumerate(fields):
            ttk.Label(frame, text=label).grid(row=row, column=0, sticky="w", pady=4)
            ttk.Entry(frame, textvariable=variable, width=22).grid(row=row, column=1, sticky="ew", padx=(12, 0), pady=4)

        def save():
            try:
                delay = float(delay_var.get())
                duration = float(duration_var.get())
                x = int(x_var.get())
                y = int(y_var.get())
                if not math.isfinite(delay) or delay < 0 or not math.isfinite(duration) or duration < 0 or not name_var.get().strip():
                    raise ValueError
            except ValueError:
                messagebox.showerror("Check settings", "Use a name, integer coordinates, and non-negative delay and duration values.", parent=dialog)
                return
            spot.update(name=name_var.get().strip(), x=x, y=y, delay=delay, duration=duration)
            self.refresh_spot_list()
            self.spot_list.selection_set(str(index))
            self.status_text.set(f"Updated {spot['name']}")
            dialog.destroy()

        ttk.Button(frame, text="Save", command=save).grid(row=len(fields), column=1, sticky="e", pady=(12, 0))
        dialog.bind("<Return>", lambda event: save())
        dialog.bind("<Escape>", lambda event: dialog.destroy())

    def remove_spot(self, parent=None):
        selection = self.spot_list.selection()
        if not selection:
            return
        index = int(selection[0])
        spot_name = self.saved_spots[index]["name"]
        if not messagebox.askyesno(
            "Delete spot",
            f"Delete '{spot_name}' from this click sequence?",
            parent=parent or self.root,
        ):
            return
        removed_name = self.saved_spots.pop(index)["name"]
        self.refresh_spot_list()
        self.hide_spot_marker()
        self.status_text.set(f"Removed {removed_name}")

    def interval_seconds(self):
        value = float(self.interval_value.get())
        if not math.isfinite(value) or value <= 0:
            raise ValueError("Interval must be greater than zero.")
        multiplier = {"milliseconds": 0.001, "seconds": 1, "minutes": 60}[self.interval_unit.get()]
        return value * multiplier

    def random_delay_seconds(self):
        if not self.random_delay_enabled.get():
            return 0.0
        value = float(self.random_delay_value.get())
        if not math.isfinite(value) or value < 0:
            raise ValueError("Random variation must be zero or greater.")
        return value / 1000

    def target_positions(self):
        if self.click_mode.get() == "current":
            return [(None, None, 0.0, 0.0)]
        if self.click_mode.get() == "saved":
            return [(spot["x"], spot["y"], spot["delay"], spot.get("duration", 0.0)) for spot in self.saved_spots]
        return [(int(self.position_x.get()), int(self.position_y.get()), 0.0, 0.0)]

    def toggle(self):
        if self.is_running:
            self.stop()
        else:
            self.start()

    def start(self):
        if self.target_hwnd is None or not USER32.IsWindow(self.target_hwnd):
            messagebox.showerror("Target window required", "Find the Growtopia window before starting.")
            return
        try:
            interval = self.interval_seconds()
            random_delay = self.random_delay_seconds()
            positions = self.target_positions()
        except (ValueError, TypeError):
            messagebox.showerror("Check settings", "Enter a valid positive interval and integer coordinates.")
            return

        self.stop_event.clear()
        self.is_running = True
        self.click_count = 0
        self.toggle_button.configure(text="Pause clicking")
        self.status_text.set("Clicking")
        self.counter_text.set("0 clicks")
        if not positions:
            messagebox.showerror("No saved spots", "Add at least one saved spot before starting.")
            self.stop()
            return
        button = getattr(mouse.Button, self.click_button.get())
        clicks_per_spot = 2 if self.click_type.get() == "double" else 1
        self.click_thread = threading.Thread(target=self.click_loop, args=(interval, random_delay, positions, button, clicks_per_spot), daemon=True)
        self.click_thread.start()

    def click_loop(self, interval, random_delay, positions, button, clicks_per_spot):
        next_click_at = time.monotonic()
        first_click = True
        while not self.stop_event.is_set():
            for x, y, delay, duration in positions:
                wait_time = delay if delay > 0 else (0 if first_click else interval)
                if random_delay > 0 and not first_click:
                    wait_time += random.uniform(0, random_delay)
                next_click_at += wait_time
                remaining = next_click_at - time.monotonic()
                if remaining > 0 and self.stop_event.wait(remaining):
                    return
                if not self.target_is_foreground() and not self.background_clicks.get():
                    self.root.after(0, lambda: self.status_text.set("Waiting for Growtopia to be active"))
                    next_click_at = time.monotonic()
                    if self.stop_event.wait(interval):
                        return
                    continue
                click_x, click_y = (x, y) if x is not None else self.mouse_controller.position
                self.root.after(0, self.show_spot_marker, click_x, click_y)
                if x is not None:
                    if self.background_clicks.get() and not self.target_is_foreground():
                        if not self.send_background_click(x, y, button, clicks_per_spot, duration):
                            self.root.after(0, lambda: self.status_text.set("Growtopia handle is unavailable"))
                            next_click_at = time.monotonic()
                            if self.stop_event.wait(interval):
                                return
                            continue
                    else:
                        self.mouse_controller.position = (x, y)
                        self.perform_foreground_click(button, clicks_per_spot, duration)
                else:
                    if self.background_clicks.get() and not self.target_is_foreground():
                        self.send_background_click(click_x, click_y, button, clicks_per_spot, duration)
                    else:
                        self.perform_foreground_click(button, clicks_per_spot, duration)
                self.click_count += 1
                first_click = False
                self.root.after(0, lambda count=self.click_count: self.counter_text.set(f"{count:,} clicks"))

    def perform_foreground_click(self, button, clicks_per_spot, duration):
        if duration <= 0:
            self.mouse_controller.click(button, clicks_per_spot)
            return
        for _ in range(clicks_per_spot):
            self.mouse_controller.press(button)
            time.sleep(duration)
            self.mouse_controller.release(button)

    def stop(self):
        self.stop_event.set()
        self.is_running = False
        self.toggle_button.configure(text="Start clicking")
        self.status_text.set("Ready")

    def close(self):
        self.stop()
        if self.marker_window is not None and self.marker_window.winfo_exists():
            self.marker_window.destroy()
        if self.pick_listener is not None:
            self.pick_listener.stop()
        if self.hotkey_listener is not None:
            self.hotkey_listener.stop()
        self.root.destroy()


if __name__ == "__main__":
    app = tk.Tk()
    AutoClicker(app)
    app.mainloop()
