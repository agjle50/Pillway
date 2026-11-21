import tkinter as tk
from tkinter import ttk


NAVY = "#0a0f42"
NAVY_DARK = "#080c38"
RED = "#ef3f3f"
TEXT_DARK = "#4a566f"
TEXT_MUTED = "#768197"
BORDER = "#dde2ea"
WHITE = "#ffffff"
SOFT_BLUE = "#eef2ff"

#to-find placest-launch popup.
VIRTUAL_ASSISTANT_POPUP_TEXT = (
    "Get a virtual assistant doctor to help you discover your condition today, live."
)

class PillwayApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Pillway")
        self.geometry("1500x900")
        self.minsize(1100, 700)
        self.configure(bg=WHITE)

        self.sidebar_width = 300
        self.create_sidebar()
        self.create_main()
        self.after(250, self.show_virtual_assistant_popup)

    def show_virtual_assistant_popup(self):
        popup = tk.Toplevel(self)
        popup.title("Virtual assistant doctor")
        popup.geometry("560x300")
        popup.resizable(False, False)
        popup.configure(bg=WHITE)
        popup.transient(self)
        popup.grab_set()

        tk.Label(
            popup,
            text="Virtual assistant",
            bg=WHITE,
            fg=TEXT_DARK,
            font=("Segoe UI", 20, "bold"),
        ).pack(pady=(28, 12))

        tk.Label(
            popup,
            text=VIRTUAL_ASSISTANT_POPUP_TEXT,
            bg=WHITE,
            fg="#71809a",
            font=("Segoe UI", 14),
            wraplength=470,
            justify="center",
        ).pack(pady=(8, 22), padx=40)

        tk.Button(
            popup,
            text="Continue",
            command=popup.destroy,
            bg=RED,
            fg=WHITE,
            activebackground="#d93636",
            activeforeground=WHITE,
            bd=0,
            font=("Segoe UI", 13, "bold"),
            width=24,
            height=2,
            cursor="hand2",
        ).pack()

    def create_sidebar(self):
        sidebar = tk.Frame(self, bg=NAVY, width=self.sidebar_width)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        brand = tk.Frame(sidebar, bg=NAVY_DARK, height=96)
        brand.pack(fill="x")
        brand.pack_propagate(False)
        tk.Label(
            brand,
            text="Pillway",
            bg=NAVY_DARK,
            fg=WHITE,
            font=("Segoe UI", 34, "bold"),
        ).place(x=66, y=24)

        nav_items = [
            ("Dashboard", "grid", True),
            ("Settings", "gear", False),
            ("Manage profiles", "person", False),
            ("Medications", "pills", False),
            ("Prescription", "rx", False),
            ("See a doctor", "stethoscope", False),
            ("Orders", "order", False),
            ("Tasks", "task", False),
        ]

        nav = tk.Frame(sidebar, bg=NAVY)
        nav.pack(fill="x")

        for index, (label, icon, selected) in enumerate(nav_items):
            row = tk.Frame(nav, bg=WHITE if selected else NAVY, height=58)
            row.pack(fill="x")
            row.pack_propagate(False)
            if selected:
                icon_color = RED
                text_color = RED
                row.configure(cursor="hand2")
            else:
                icon_color = "#9da9dc"
                text_color = "#edf0ff"

            canvas = tk.Canvas(
                row, width=28, height=28, bg=row["bg"],
                highlightthickness=0, bd=0,
            )
            canvas.place(x=12, y=12)
            self.draw_icon(canvas, icon, icon_color)
            tk.Label(
                row,
                text=label,
                bg=row["bg"],
                fg=text_color,
                font=("Segoe UI", 14),
                anchor="w",
            ).place(x=52, y=15)

            if label == "Dashboard":
                tk.Frame(nav, bg="#9098b8", height=1).pack(fill="x")

            if index in (1, 7):
                continue

        self.create_footer_menu(sidebar)

    def create_footer_menu(self, sidebar):
        separator = tk.Frame(sidebar, bg="#9098b8", height=1)
        separator.pack(side="bottom", before=None, fill="x", pady=(0, 0))

        footer = tk.Frame(sidebar, bg=NAVY)
        footer.pack(side="bottom", fill="x", pady=(0, 10))

        footer_items = [
            ("Contact us", "phone"),
            ("Account tour", "bulb"),
            ("FAQ", "question"),
        ]
        for label, icon in footer_items:
            row = tk.Frame(footer, bg=NAVY, height=58)
            row.pack(fill="x")
            row.pack_propagate(False)
            canvas = tk.Canvas(
                row, width=28, height=28, bg=NAVY,
                highlightthickness=0, bd=0,
            )
            canvas.place(x=12, y=12)
            self.draw_icon(canvas, icon, "#9da9dc")
            tk.Label(
                row,
                text=label,
                bg=NAVY,
                fg="#edf0ff",
                font=("Segoe UI", 12),
                anchor="w",
            ).place(x=52, y=15)

    def create_main(self):
        main = tk.Frame(self, bg=WHITE)
        main.pack(side="left", fill="both", expand=True)

        header = tk.Frame(main, bg=WHITE, height=82)
        header.pack(fill="x")
        header.pack_propagate(False)

        tk.Label(
            header,
            text="Dashboard",
            bg=WHITE,
            fg=TEXT_DARK,
            font=("Segoe UI", 26, "bold"),
        ).place(x=14, y=28)

        actions = tk.Frame(header, bg=WHITE)
        actions.place(relx=1.0, x=-18, y=8, anchor="ne")

        self.header_icon(actions, "bell")
        tk.Frame(actions, bg=WHITE, width=12).pack(side="left")
        self.header_icon(actions, "card")
        tk.Frame(actions, bg=WHITE, width=22).pack(side="left")

        profile = tk.Frame(actions, bg=WHITE)
        profile.pack(side="left")
        avatar = tk.Canvas(
            profile,
            width=62,
            height=62,
            bg=WHITE,
            highlightthickness=0,
            bd=0,
        )
        avatar.pack(side="left")
        avatar.create_oval(1, 1, 61, 61, fill="#080b32", outline="#080b32")
        avatar.create_text(31, 31, text="T A", fill=WHITE, font=("Segoe UI", 18, "bold"))
        tk.Label(
            profile,
            text="Team AGILE",
            bg=WHITE,
            fg="#101a3c",
            font=("Segoe UI", 17, "bold"),
        ).pack(side="left", padx=(12, 8))
        chevron = tk.Canvas(
            profile, width=24, height=24, bg=WHITE, highlightthickness=0, bd=0
        )
        chevron.pack(side="left", padx=(0, 4))
        chevron.create_line(3, 8, 12, 17, 21, 8, fill="#101a3c", width=2, smooth=True)

        content_border = tk.Canvas(main, bg=WHITE, highlightthickness=0, bd=0)
        content_border.pack(fill="both", expand=True, padx=(12, 12), pady=(0, 0))

        content = tk.Frame(content_border, bg=WHITE)
        content_window = content_border.create_window(
            1, 10, anchor="nw", window=content
        )

        def resize_content(event):
            radius = 12
            width = event.width
            height = event.height
            content_border.coords(content_window, 1, radius)
            content_border.itemconfigure(
                content_window,
                width=max(1, width - 2),
                height=max(1, height - radius - 1),
            )

            content_border.delete("panel-outline")
            content_border.create_arc(
                0, 0, radius * 2, radius * 2,
                start=90, extent=90, style="arc",
                outline=BORDER, tags="panel-outline",
            )
            content_border.create_arc(
                width - radius * 2, 0, width, radius * 2,
                start=0, extent=90, style="arc",
                outline=BORDER, tags="panel-outline",
            )
            content_border.create_line(
                radius, 0, width - radius, 0,
                fill=BORDER, tags="panel-outline",
            )
            content_border.create_line(
                0, radius, 0, height,
                fill=BORDER, tags="panel-outline",
            )
            content_border.create_line(
                width - 1, radius, width - 1, height,
                fill=BORDER, tags="panel-outline",
            )
            content_border.create_line(
                0, height - 1, width, height - 1,
                fill=BORDER, tags="panel-outline",
            )

        content_border.bind("<Configure>", resize_content)

        tabbar = tk.Frame(content, bg=WHITE, height=58)
        tabbar.pack(fill="x")
        tabbar.pack_propagate(False)

        tabs = tk.Frame(tabbar, bg=WHITE)
        tabs.place(relx=0.5, y=15, anchor="n")

        self.tab_buttons = {}
        for name in ("Medications", "Orders", "Tasks", "Check up"):
            button = tk.Label(
                tabs,
                text=name,
                bg=WHITE,
                fg=RED if name == "Medications" else TEXT_DARK,
                font=("Segoe UI", 14, "bold" if name == "Medications" else "normal"),
                cursor="hand2",
                padx=10,
                pady=6,
            )
            button.pack(side="left")
            button.bind("<Button-1>", lambda event, n=name: self.select_tab(n))
            self.tab_buttons[name] = button

        underline = tk.Frame(tabbar, bg=RED, height=2)
        underline.place(x=440, y=56, width=100)
        self.tab_underline = underline

        edit = tk.Frame(content, bg="#dfe4ff", width=44, height=52)
        edit.place(relx=1.0, x=-10, y=8, anchor="ne")
        edit.pack_propagate(False)
        edit_canvas = tk.Canvas(edit, width=44, height=52, bg="#dfe4ff", highlightthickness=0)
        edit_canvas.pack()
        edit_canvas.create_rectangle(6, 10, 30, 34, outline=WHITE, width=2)
        edit_canvas.create_line(12, 31, 30, 13, fill=WHITE, width=4)
        edit_canvas.create_line(30, 13, 33, 16, fill=WHITE, width=3)

        body = tk.Frame(content, bg=WHITE)
        body.pack(fill="both", expand=True)

        center = tk.Frame(body, bg=WHITE)
        center.place(relx=0.5, rely=0.50, anchor="center")

        self.empty_label = tk.Label(
            center,
            text="Let's add your first prescription!",
            bg=WHITE,
            fg="#71809a",
            font=("Segoe UI", 13),
        )
        self.empty_label.pack(pady=(0, 18))

        add_button = tk.Button(
            center,
            text="+  Add prescription",
            command=self.add_prescription,
            bg=RED,
            activebackground="#d93636",
            fg=WHITE,
            activeforeground=WHITE,
            bd=0,
            relief="flat",
            font=("Segoe UI", 13, "bold"),
            cursor="hand2",
            width=32,
            height=2,
        )
        add_button.pack()

        chat = tk.Canvas(main, width=58, height=58, bg=WHITE, highlightthickness=0)
        chat.place(relx=1.0, rely=1.0, x=-18, y=-18, anchor="se")
        chat.create_oval(2, 2, 56, 56, fill=RED, outline=RED)
        chat.create_rectangle(16, 17, 42, 40, fill=WHITE, outline=WHITE)
        chat.create_polygon(20, 39, 16, 47, 28, 40, fill=WHITE, outline=WHITE)

    def header_icon(self, parent, kind):
        size = 66
        canvas = tk.Canvas(
            parent,
            width=size,
            height=size,
            bg=WHITE,
            highlightthickness=0,
            bd=0,
        )
        canvas.pack(side="left")
        line = "#dfe1e8"
        ink = "#101a3c"
        self.draw_rounded_outline(canvas, 2, 8, 60, 60, 16, line, 2)

        if kind == "bell":
            center_x = 32
            canvas.create_arc(
                center_x - 8, 25, center_x + 8, 42,
                start=0, extent=180, style="arc", outline=ink, width=2,
            )
            canvas.create_line(center_x - 8, 33, center_x - 8, 45, fill=ink, width=2)
            canvas.create_line(center_x + 8, 33, center_x + 8, 45, fill=ink, width=2)
            canvas.create_line(center_x - 11, 45, center_x + 11, 45, fill=ink, width=2)
            canvas.create_arc(
                center_x - 3, 42, center_x + 3, 48,
                start=180, extent=180, style="arc", outline=ink, width=2,
            )
            canvas.create_oval(56, 0, 66, 10, fill=RED, outline=RED)
        else:
            self.draw_rounded_outline(canvas, 18, 27, 46, 42, 3, ink, 2)
            canvas.create_line(19, 34, 45, 34, fill=ink, width=2)

    @staticmethod
    def draw_rounded_outline(canvas, x, y, width, height, radius, color, line_width=1):
        canvas.create_arc(
            x, y, x + radius * 2, y + radius * 2,
            start=90, extent=90, style="arc", outline=color, width=line_width,
        )
        canvas.create_arc(
            x + width - radius * 2, y, x + width, y + radius * 2,
            start=0, extent=90, style="arc", outline=color, width=line_width,
        )
        canvas.create_arc(
            x + width - radius * 2, y + height - radius * 2, x + width, y + height,
            start=270, extent=90, style="arc", outline=color, width=line_width,
        )
        canvas.create_arc(
            x, y + height - radius * 2, x + radius * 2, y + height,
            start=180, extent=90, style="arc", outline=color, width=line_width,
        )
        canvas.create_line(x + radius, y, x + width - radius, y, fill=color, width=line_width)
        canvas.create_line(x + width, y + radius, x + width, y + height - radius, fill=color, width=line_width)
        canvas.create_line(x + width - radius, y + height, x + radius, y + height, fill=color, width=line_width)
        canvas.create_line(x, y + height - radius, x, y + radius, fill=color, width=line_width)

    def draw_icon(self, canvas, kind, color):
        if kind == "grid":
            for x, y in ((5, 5), (15, 5), (5, 15), (15, 15)):
                canvas.create_rectangle(x, y, x + 7, y + 7, outline=color, width=2)
        elif kind == "gear":
            canvas.create_oval(7, 7, 21, 21, outline=color, width=2)
            canvas.create_oval(12, 12, 16, 16, outline=color, width=1)
        elif kind == "person":
            canvas.create_oval(10, 5, 18, 13, outline=color, width=2)
            canvas.create_arc(4, 13, 24, 27, start=0, extent=-180, style="arc", outline=color, width=2)
            canvas.create_line(20, 14, 24, 18, fill=color, width=2)
        elif kind == "pills":
            canvas.create_line(7, 20, 18, 9, fill=color, width=5)
            canvas.create_line(12, 15, 15, 12, fill=WHITE, width=1)
        elif kind == "rx":
            canvas.create_rectangle(5, 7, 23, 21, outline=color, width=2)
            canvas.create_text(14, 14, text="Rx", fill=color, font=("Segoe UI", 7, "bold"))
        elif kind == "stethoscope":
            canvas.create_line(8, 7, 8, 16, 12, 20, fill=color, width=2)
            canvas.create_line(20, 7, 20, 16, 16, 20, fill=color, width=2)
            canvas.create_arc(8, 16, 20, 27, start=180, extent=180, style="arc", outline=color, width=2)
            canvas.create_oval(13, 20, 18, 25, outline=color, width=1)
        elif kind == "order":
            canvas.create_rectangle(5, 8, 23, 22, outline=color, width=2)
            canvas.create_line(5, 13, 23, 13, fill=color, width=2)
        elif kind == "task":
            canvas.create_rectangle(7, 6, 21, 22, outline=color, width=2)
            canvas.create_line(11, 11, 13, 13, 17, 9, fill=color, width=2)
            canvas.create_line(11, 18, 18, 18, fill=color, width=2)
        elif kind == "phone":
            canvas.create_oval(6, 7, 21, 22, outline=color, width=2)
            canvas.create_arc(8, 9, 19, 20, start=15, extent=250, style="arc", outline=color, width=2)
        elif kind == "bulb":
            canvas.create_arc(7, 5, 21, 20, start=0, extent=180, style="arc", outline=color, width=2)
            canvas.create_line(10, 18, 18, 18, fill=color, width=2)
            canvas.create_line(11, 21, 17, 21, fill=color, width=2)
        elif kind == "question":
            canvas.create_text(14, 14, text="?", fill=color, font=("Segoe UI", 17, "bold"))

    def select_tab(self, name):
        for tab_name, button in self.tab_buttons.items():
            if tab_name == name:
                button.configure(fg=RED, font=("Segoe UI", 14, "bold"))
                button.update_idletasks()
                x = button.winfo_x() + button.master.winfo_x() - 8
                width = button.winfo_width() + 16
                self.tab_underline.place_configure(x=x, width=width)
            else:
                button.configure(fg=TEXT_DARK, font=("Segoe UI", 14))
        if name == "Medications":
            self.empty_label.configure(text="Let's add your first prescription!")
        else:
            self.empty_label.configure(text=f"No {name.lower()} to show!")

    def add_prescription(self):
        dialog = tk.Toplevel(self)
        dialog.title("Add prescription")
        dialog.geometry("460x290")
        dialog.resizable(False, False)
        dialog.configure(bg=WHITE)
        dialog.transient(self)
        dialog.grab_set()

        tk.Label(
            dialog,
            text="Add prescription",
            bg=WHITE,
            fg=TEXT_DARK,
            font=("Segoe UI", 18, "bold"),
        ).pack(pady=(24, 12))

        tk.Label(dialog, text="Medication name", bg=WHITE, fg=TEXT_MUTED, font=("Segoe UI", 13)).pack(anchor="w", padx=32)
        entry = tk.Entry(dialog, font=("Segoe UI", 13), width=38)
        entry.pack(pady=(4, 18), padx=32)

        def save():
            if entry.get().strip():
                self.empty_label.configure(text=f"{entry.get().strip()} has been added.")
                dialog.destroy()

        tk.Button(
            dialog,
            text="Add prescription",
            command=save,
            bg=RED,
            fg=WHITE,
            activebackground="#d93636",
            activeforeground=WHITE,
            bd=0,
            font=("Segoe UI", 13, "bold"),
            width=24,
            height=2,
            cursor="hand2",
        ).pack()


if __name__ == "__main__":
    app = PillwayApp()
    app.mainloop()
