import base64
import io
import html
import math
import queue
from concurrent.futures import ThreadPoolExecutor
import json
import os
import tkinter as tk
from tkinter import colorchooser, filedialog, messagebox, ttk

from PIL import Image, ImageDraw, ImageEnhance, ImageFont, ImageTk, ImageOps

RAMPS = {
    "Klasik": "@%#*+=-:. ",
    "Nokta": ".:-=+*#%@",
    "Blok": "█▓▒░ ",
    "Minimum": "# ",
    "Yoğun": "@W#B$?wabhmZO0QLCJUYXzcvunxrjft/|()1{}[]?-_+~<>i!lI;:,\"^`'. ",
}

RES_PRESETS = {
    "Hızlı": {"font": 10, "scale": 1},
    "Standart": {"font": 14, "scale": 2},
    "Yüksek": {"font": 36, "scale": 1},
    "Çok Yüksek": {"font": 56, "scale": 1},
    "Ultra": {"font": 88, "scale": 1},
}

DETAIL_PRESETS = {
    "Düşük (40 krk)": 40,
    "Orta (80 krk)": 80,
    "Yüksek (140 krk)": 140,
    "Çok Yüksek (200 krk)": 200,
    "Ultra (300 krk)": 300,
}

ANSI16 = [
    (0, 0, 0), (128, 0, 0), (0, 128, 0), (128, 128, 0),
    (0, 0, 128), (128, 0, 128), (0, 128, 128), (192, 192, 192),
    (128, 128, 128), (255, 0, 0), (0, 255, 0), (255, 255, 0),
    (0, 0, 255), (255, 0, 255), (0, 255, 255), (255, 255, 255),
]

BG = "#10141c"
PANEL = "#181f2b"
EDGE = "#303e52"
TEXT = "#d8d8f0"
ACCENT = "#8b9cff"
GREEN = "#90e4c1"
PREVIEW_BG = "#0a0a14"
BTN = "#2a2a52"
BTN_ACT = "#3d3d78"

FONT_PATHS = [
    "C:/Windows/Fonts/consola.ttf",
    "C:/Windows/Fonts/cour.ttf",
    "C:/Windows/Fonts/arial.ttf",
]

LEGACY_SETTINGS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ascii_studio_settings.json")
SETTINGS_PATH = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~/.config")), "AsciiArtStudio", "settings.json")


def nearest_color(r, g, b, palette):
    best, bd = palette[0], 1 << 30
    for p in palette:
        d = (r - p[0]) ** 2 + (g - p[1]) ** 2 + (b - p[2]) ** 2
        if d < bd:
            best, bd = p, d
    return best


def rgb_to_ansi256(r, g, b):
    if abs(r - g) < 10 and abs(g - b) < 10:
        if r < 8:
            return 16
        if r > 248:
            return 231
        return max(232, min(255, round((r - 8) / 10) + 232))

    def to6(v):
        if v < 48:
            return 0
        if v < 115:
            return 1
        return (v - 35) // 40

    return 16 + 36 * to6(r) + 6 * to6(g) + to6(b)


def convert_image(img, width=100, ratio=0.5, ramp="@%#*+=-:. ", invert=False,
                  brightness=1.0, contrast=1.0, dither=False):
    if not isinstance(width, int) or not 1 <= width <= 500:
        raise ValueError("Genişlik 1–500 arasında olmalı")
    if not ramp or len(ramp) > 256 or any(c in ramp for c in "\n\r\t\x1b"):
        raise ValueError("Karakter seti 1–256 yazdırılabilir karakter içermeli")
    if not math.isfinite(ratio) or not 0.1 <= ratio <= 2:
        raise ValueError("Geçersiz en/boy oranı")
    if not all(math.isfinite(v) and 0 <= v <= 5 for v in (brightness, contrast)):
        raise ValueError("Geçersiz parlaklık veya kontrast")
    if round(img.height / max(img.width, 1) * width * ratio) * width > 250000:
        raise ValueError("Çıktı çok uzun; genişliği veya en/boy oranını azaltın")
    if img.mode in ("RGBA", "LA", "P"):
        img = img.convert("RGBA")
        bg = Image.new("RGBA", img.size, (0, 0, 0, 255))
        img = Image.alpha_composite(bg, img)
    img = img.convert("RGB")
    img = ImageEnhance.Brightness(img).enhance(brightness)
    img = ImageEnhance.Contrast(img).enhance(contrast)
    out_h = max(1, round(img.height / max(img.width, 1) * width * ratio))
    small = img.resize((width, out_h), Image.LANCZOS)
    lum = small.convert("L")
    if dither:
        lum = lum.convert("1", dither=Image.FLOYDSTEINBERG).convert("L")
        ramp = ramp[0] + ramp[-1]
    lums = list(lum.get_flattened_data())
    cols = list(small.get_flattened_data())
    n = max(1, len(ramp) - 1)
    rows, color_rows = [], []
    for y in range(out_h):
        line, crow = [], []
        base = y * width
        for x in range(width):
            v = lums[base + x]
            idx = round(v / 255 * n)
            if invert:
                idx = n - idx
            line.append(ramp[idx])
            crow.append(cols[base + x])
        rows.append("".join(line))
        color_rows.append(crow)
    return rows, color_rows


def make_txt(rows):
    return "\n".join(rows)


def make_ansi(rows, colors, mode):
    if mode == "Yok":
        return make_txt(rows)
    out = []
    for y, line in enumerate(rows):
        parts = []
        for x, ch in enumerate(line):
            r, g, b = colors[y][x]
            if mode == "TrueColor":
                parts.append(f"\x1b[38;2;{r};{g};{b}m{ch}")
            elif mode == "ANSI 256":
                parts.append(f"\x1b[38;5;{rgb_to_ansi256(r, g, b)}m{ch}")
            else:
                nr, ng, nb = nearest_color(r, g, b, ANSI16)
                idx = ANSI16.index((nr, ng, nb))
                parts.append(f"\x1b[38;5;{idx}m{ch}")
        out.append("".join(parts) + "\x1b[0m")
    return "\n".join(out)


def output_color(rgb, mode):
    if mode == "ANSI 16":
        return nearest_color(*rgb, ANSI16)
    if mode == "ANSI 256":
        index = rgb_to_ansi256(*rgb)
        if index >= 232:
            return (8 + 10 * (index - 232),) * 3
        index -= 16
        levels = (0, 95, 135, 175, 215, 255)
        return levels[index // 36], levels[(index // 6) % 6], levels[index % 6]
    return rgb


def make_html(rows, colors, mode="TrueColor"):
    lines = []
    for y, row in enumerate(rows):
        spans = []
        for x, char in enumerate(row):
            color = output_color(colors[y][x], mode) if mode != "Yok" else (220, 225, 235)
            spans.append('<span style="color:rgb(%d,%d,%d)">%s</span>' % (*color, html.escape(char)))
        lines.append("".join(spans))
    return '<!doctype html><html lang="tr"><meta charset="utf-8"><title>ASCII Art Studio</title><body style="background:#0a0a0e"><pre style="font:14px/1 monospace">' + "\n".join(lines) + '</pre></body></html>'


def make_svg(rows, colors, mode="TrueColor"):
    width = max((len(row) for row in rows), default=1) * 9
    height = max(1, len(rows)) * 16
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}">', '<rect width="100%" height="100%" fill="#0a0a0e"/>', '<g font-family="monospace" font-size="14" xml:space="preserve">']
    for y, row in enumerate(rows):
        for x, char in enumerate(row):
            if char == " ":
                continue
            rgb = output_color(colors[y][x], mode) if mode != "Yok" else (220, 225, 235)
            parts.append(f'<text x="{x * 9}" y="{y * 16 + 13}" fill="rgb{rgb}">{html.escape(char)}</text>')
    return "".join(parts) + '</g></svg>'


def load_font(size=12):
    for path in FONT_PATHS:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    return ImageFont.load_default()


def render_ascii_image(rows, colors=None, font_size=12, grayscale=False):
    font = load_font(font_size)
    if not rows:
        raise ValueError("Önce bir görsel dönüştürün")
    tmp = font.getbbox("Mg")
    cw = max(1, math.ceil(font.getlength("M")))
    chh = max(1, tmp[3] - min(0, tmp[1]) + 2)
    w, h = max(map(len, rows)) * cw, len(rows) * chh
    if w * h > 40000000:
        raise ValueError("PNG 40 megapiksel sınırını aşıyor; çözünürlüğü azaltın")
    image = Image.new("RGB", (max(1, w), max(1, h)), (10, 10, 14))
    draw = ImageDraw.Draw(image)
    for y, line in enumerate(rows):
        for x, chr_ in enumerate(line):
            if chr_ == " ":
                continue
            if grayscale or colors is None:
                fill = (200, 200, 210)
            else:
                fill = colors[y][x]
            draw.text((x * cw, y * chh), chr_, font=font, fill=fill)
    return image


def load_settings():
    try:
        path = SETTINGS_PATH if os.path.isfile(SETTINGS_PATH) else LEGACY_SETTINGS_PATH
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_settings(d):
    try:
        os.makedirs(os.path.dirname(SETTINGS_PATH), exist_ok=True)
        temporary = SETTINGS_PATH + ".tmp"
        with open(temporary, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False)
        os.replace(temporary, SETTINGS_PATH)
    except Exception:
        pass


class App:
    def __init__(self, standalone=True):
        self.root = tk.Tk()
        self.root.title("ASCII ART STUDIO")
        self.root.geometry("1240x820")
        self.root.minsize(1020, 640)
        self.root.configure(bg=BG)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        self.img = None
        self.rows = []
        self.colors = []
        self.photo = None
        self.canvas_img = None
        self._after_id = None
        self._executor = ThreadPoolExecutor(max_workers=1)
        self._results = queue.Queue()
        self._generation = 0
        self._busy = False
        self._closed = False
        self._source_photo = None
        self.zoom = 1.0

        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure("TScale", background=PANEL, troughcolor=BTN, bordercolor=EDGE)
        style.configure("TCheckbutton", background=PANEL, foreground=TEXT)
        style.map("TCheckbutton", background=[("active", PANEL)])
        style.configure("TCombobox", fieldbackground=BTN, background=BTN, foreground=TEXT)
        style.configure("TLabel", background=PANEL, foreground=TEXT)
        style.map("TCombobox", fieldbackground=[("readonly", BTN)], foreground=[("readonly", TEXT)], selectbackground=[("readonly", BTN)], selectforeground=[("readonly", TEXT)])
        style.configure("TNotebook", background=BG, borderwidth=0)
        style.configure("TNotebook.Tab", background=PANEL, foreground=TEXT, padding=(14, 8), font=("Segoe UI", 10))
        style.map("TNotebook.Tab", background=[("selected", BTN_ACT)], foreground=[("selected", "#ffffff")])
        style.configure("Vertical.TScrollbar", background=BTN, troughcolor=PANEL, arrowcolor=TEXT, borderwidth=0)
        style.configure("Horizontal.TScrollbar", background=BTN, troughcolor=PANEL, arrowcolor=TEXT, borderwidth=0)

        self._build_ui()
        self._load_prefs()

        self.root.after(60, self._poll_results)

        if standalone:
            self.root.mainloop()

    def _build_ui(self):
        menubar = tk.Menu(self.root)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Resim Aç...", accelerator="Ctrl+O", command=self.open_image)
        file_menu.add_command(label="Proje Aç…", command=self.open_project)
        file_menu.add_command(label="Proje Kaydet…", command=self.save_project)
        file_menu.add_command(label="SVG Kaydet…", command=self.save_svg)
        file_menu.add_separator()
        file_menu.add_command(label="Çık", command=self.on_close)
        menubar.add_cascade(label="Dosya", menu=file_menu)
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="Hakkında", command=self.show_about)
        menubar.add_cascade(label="Yardım", menu=help_menu)
        self.root.config(menu=menubar)
        self.root.bind("<Control-o>", lambda e: self.open_image())

        heading = tk.Frame(self.root, bg=BG)
        heading.pack(fill="x", padx=20, pady=(16, 8))
        tk.Label(heading, text="ASCII / ART STUDIO", bg=BG, fg=TEXT,
                 font=("Segoe UI", 22, "bold")).pack(side="left")
        tk.Label(heading, text="GÖRSELDEN KARAKTER SANATINA", bg=BG, fg=GREY_TXT,
                 font=("Segoe UI", 9)).pack(side="right")
        self.root.bind("<Control-s>", lambda e: self.save_png())
        top = tk.Frame(self.root, bg=BG, height=48)
        top.pack(fill="x", side="top")
        top.pack_propagate(False)
        for text, cmd in (
            ("Resim Aç...", self.open_image),
            ("Panoya Kopyala", self.copy_text),
            ("TXT Kaydet", self.save_txt),
            ("ANS Kaydet", self.save_ans),
            ("PNG Kaydet", self.save_png),
            ("HTML Kaydet", self.save_html),
            ("Sıfırla", self.reset_controls),
        ):
            b = tk.Button(top, text=text, command=cmd, bg=BTN, fg=TEXT, activebackground=BTN_ACT,
                          activeforeground=TEXT, relief="flat", padx=10, pady=4, font=("Consolas", 10, "bold"))
            b.pack(side="left", padx=6, pady=6)

        main = tk.Frame(self.root, bg=BG)
        main.pack(fill="both", expand=True)

        side_shell = tk.Frame(main, bg=PANEL, width=282)
        side_shell.pack(fill="y", side="left", padx=(16, 8), pady=8)
        side_shell.pack_propagate(False)
        side_canvas = tk.Canvas(side_shell, bg=PANEL, highlightthickness=0, width=260)
        side_scroll = ttk.Scrollbar(side_shell, orient="vertical", command=side_canvas.yview)
        side_canvas.configure(yscrollcommand=side_scroll.set)
        side_scroll.pack(side="right", fill="y")
        side_canvas.pack(side="left", fill="both", expand=True)
        side = tk.Frame(side_canvas, bg=PANEL)
        side_window = side_canvas.create_window((0, 0), window=side, anchor="nw")
        side.bind("<Configure>", lambda e: side_canvas.configure(scrollregion=side_canvas.bbox("all")))
        side_canvas.bind("<Configure>", lambda e: side_canvas.itemconfigure(side_window, width=e.width))
        def side_wheel(event):
            if str(event.widget).startswith(str(side_shell)):
                side_canvas.yview_scroll(-int(event.delta / 120), "units")
        self.root.bind_all("<MouseWheel>", side_wheel, add="+")

        def section(parent, title):
            tk.Label(parent, text=title, bg=PANEL, fg=GREEN, font=("Consolas", 10, "bold")).pack(
                anchor="w", padx=10, pady=(10, 2)
            )

        def slider(parent, label, from_, to, init, res=1, is_float=False):
            section(parent, label)
            frm = tk.Frame(parent, bg=PANEL)
            frm.pack(fill="x", padx=10)
            var = tk.DoubleVar(value=init) if is_float else tk.IntVar(value=init)
            sc = ttk.Scale(frm, from_=from_, to=to, variable=var, orient="horizontal",
                           command=lambda e: self.schedule_update())
            sc.pack(side="left", fill="x", expand=True)
            val = tk.Label(frm, text=str(init), bg=PANEL, fg=TEXT, width=5, font=("Consolas", 9))
            val.pack(side="left", padx=(6, 0))
            var.trace_add("write", lambda *a: val.config(text=f"{var.get():.2f}" if is_float else str(int(var.get()))))
            return var

        section(side, "Tek tık stiller")
        self.var_style = tk.StringVar(value="Bir stil seçin")
        styles = ttk.Combobox(side, textvariable=self.var_style, values=["Terminal", "Piksel afiş", "Mürekkep", "Renkli portre"], state="readonly")
        styles.pack(fill="x", padx=10, pady=4)
        styles.bind("<<ComboboxSelected>>", lambda e: self.apply_style())
        section(side, "Detay (karakter yoğunluğu)")
        self.var_detail = tk.StringVar(value="Orta (80 krk)")
        cb_det = ttk.Combobox(side, textvariable=self.var_detail,
                              values=list(DETAIL_PRESETS) + ["Özel"], state="readonly",
                              font=("Consolas", 10))
        cb_det.pack(fill="x", padx=10, pady=2)
        tk.Label(side, text="Arttıkça resim daha detaylı,\nkarakterler küçülür", bg=PANEL, fg=GREY_TXT,
                 font=("Consolas", 8), wraplength=210, justify="left").pack(anchor="w", padx=10)
        cb_det.bind("<<ComboboxSelected>>", lambda e: self._on_detail())

        self.var_width = slider(side, "İnce ayar (genişlik)", 20, 320, 80)
        self.var_width.trace_add("write", lambda *a: self._sync_detail())
        self.var_ratio = slider(side, "En/boy oranı", 30, 100, 50, is_float=True)

        section(side, "Karakter seti")
        self.var_ramp = tk.StringVar(value="Klasik")
        cb = ttk.Combobox(side, textvariable=self.var_ramp, values=list(RAMPS) + ["Özel"],
                          state="readonly", font=("Consolas", 10))
        cb.pack(fill="x", padx=10, pady=2)
        cb.bind("<<ComboboxSelected>>", lambda e: self.schedule_update())

        self.var_custom = tk.Entry(side, bg=BTN, fg=TEXT, insertbackground=TEXT, relief="flat",
                                   font=("Consolas", 10))
        self.var_custom.pack(fill="x", padx=10, pady=2)
        self.var_custom.insert(0, "@%#*+=-:. ")
        self.var_custom.bind("<KeyRelease>", lambda e: self.schedule_update())

        self.var_invert = tk.BooleanVar(value=False)
        tk.Checkbutton(side, text="Ters çevir (invert)", variable=self.var_invert, bg=PANEL, fg=TEXT,
                       selectcolor=BTN, activebackground=PANEL, activeforeground=TEXT,
                       command=self.schedule_update).pack(anchor="w", padx=10, pady=2)

        self.var_dither = tk.BooleanVar(value=False)
        tk.Checkbutton(side, text="Dither (1-bit serpiştirme)", variable=self.var_dither, bg=PANEL, fg=TEXT,
                       selectcolor=BTN, activebackground=PANEL, activeforeground=TEXT,
                       command=self.schedule_update).pack(anchor="w", padx=10, pady=2)

        self.var_bright = slider(side, "Parlaklık", 30, 200, 100, is_float=True)
        self.var_contrast = slider(side, "Kontrast", 30, 250, 100, is_float=True)

        section(side, "Renk modu")
        self.var_mode = tk.StringVar(value="TrueColor")
        for m in ("Yok", "ANSI 16", "ANSI 256", "TrueColor"):
            tk.Radiobutton(side, text=m, value=m, variable=self.var_mode, bg=PANEL, fg=TEXT,
                           selectcolor=BTN, activebackground=PANEL, activeforeground=TEXT,
                           command=self.schedule_update).pack(anchor="w", padx=14)

        section(side, "PNG çözünürlüğü")
        self.var_res = tk.StringVar(value="Standart")
        cb_res = ttk.Combobox(side, textvariable=self.var_res, values=list(RES_PRESETS),
                              state="readonly", font=("Consolas", 10))
        cb_res.pack(fill="x", padx=10, pady=2)
        res_hint = {
            "Hızlı": "Küçük PNG, hızlı kayıt",
            "Standart": "14px font + 2x büyütme",
            "Yüksek": "36px font, net çizim",
            "Çok Yüksek": "56px font, çok net",
            "Ultra": "88px font, poster boyu",
        }
        self.res_hint_lbl = tk.Label(side, text=res_hint["Standart"], bg=PANEL, fg=GREY_TXT,
                                     font=("Consolas", 8), wraplength=210, justify="left")
        self.res_hint_lbl.pack(anchor="w", padx=10)
        cb_res.bind("<<ComboboxSelected>>", lambda e: self.res_hint_lbl.config(
            text=res_hint.get(self.var_res.get(), "")))

        section(side, "Önizleme")
        self.var_view = tk.StringVar(value="text")
        for m, lbl in (("text", "Metin (yeşil ton)"), ("color", "Renkli görsel")):
            tk.Radiobutton(side, text=lbl, value=m, variable=self.var_view, bg=PANEL, fg=TEXT,
                           selectcolor=BTN, activebackground=PANEL, activeforeground=TEXT,
                           command=self.switch_view).pack(anchor="w", padx=14)

        right = tk.Frame(main, bg=BG)
        right.pack(fill="both", expand=True, padx=(4, 8), pady=8)

        zoom_bar = tk.Frame(right, bg=BG)
        zoom_bar.pack(fill="x", pady=(0, 6))
        tk.Label(zoom_bar, text="Önizleme yakınlığı", bg=BG, fg=TEXT).pack(side="left")
        for label, factor in (("−", 0.8), ("100%", 0), ("+", 1.25)):
            tk.Button(zoom_bar, text=label, command=lambda f=factor: self.change_zoom(f), bg=BTN, fg=TEXT, relief="flat", padx=12).pack(side="left", padx=4)
        self.notebook = ttk.Notebook(right)
        self.notebook.pack(fill="both", expand=True)
        output_tab = tk.Frame(self.notebook, bg=PREVIEW_BG)
        source_tab = tk.Frame(self.notebook, bg=PREVIEW_BG)
        self.notebook.add(output_tab, text="  ASCII önizleme  ")
        self.notebook.add(source_tab, text="  Kaynak görsel  ")
        self.source_label = tk.Label(source_tab, bg=PREVIEW_BG, fg=TEXT, text="Başlamak için bir görsel açın · Ctrl+O")
        self.source_label.pack(fill="both", expand=True, padx=16, pady=16)
        self.preview_frame = tk.Frame(output_tab, bg=PREVIEW_BG, highlightbackground=EDGE, highlightthickness=2)
        self.preview_frame.pack(fill="both", expand=True)

        self.text = tk.Text(self.preview_frame, bg=PREVIEW_BG, fg=GREEN, insertbackground=TEXT,
                            relief="flat", font=("Consolas", 10), wrap="none", state="disabled",
                            spacing1=0, spacing3=0)
        sy = ttk.Scrollbar(self.preview_frame, orient="vertical", command=self.text.yview)
        sx = ttk.Scrollbar(self.preview_frame, orient="horizontal", command=self.text.xview)
        self.text_scroll_y, self.text_scroll_x = sy, sx
        self.text.configure(yscrollcommand=sy.set, xscrollcommand=sx.set)
        self.text.grid(row=0, column=0, sticky="nsew")
        sy.grid(row=0, column=1, sticky="ns")
        sx.grid(row=1, column=0, sticky="ew")
        self.preview_frame.rowconfigure(0, weight=1)
        self.preview_frame.columnconfigure(0, weight=1)

        self.canvas = tk.Canvas(self.preview_frame, bg=PREVIEW_BG, highlightthickness=0)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.canvas.grid_remove()
        self._canvas_scroll_y = ttk.Scrollbar(self.preview_frame, orient="vertical", command=self.canvas.yview)
        self._canvas_scroll_x = ttk.Scrollbar(self.preview_frame, orient="horizontal", command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=self._canvas_scroll_y.set, xscrollcommand=self._canvas_scroll_x.set)

        self.status = tk.Label(self.root, text="Resim yükleyin...  (Ctrl+O)", bg=BG, fg=GREY_TXT,
                               anchor="w", padx=10, font=("Consolas", 9))
        self.status.pack(fill="x", side="bottom")

        self._build_tags()
        self.text.configure(state="normal")
        self.text.insert("1.0", "\n  Bir görsel açın.\n\n  1. Resim Aç ile PNG, JPEG veya WebP seçin.\n  2. Soldaki ayarlarla karakterleri düzenleyin.\n  3. TXT, ANS, PNG veya HTML olarak dışa aktarın.\n\n  Ctrl+O · Aç     Ctrl+S · PNG kaydet")
        self.text.configure(state="disabled")

    def _build_tags(self):
        for i in range(16):
            v = int(55 + i / 15 * 200)
            col = "#%02x%02x%02x" % (int(v * 0.35), v, int(v * 0.62))
            self.text.tag_configure(f"l{i}", foreground=col)

    def current_ramp(self):
        name = self.var_ramp.get()
        if name == "Özel":
            custom = self.var_custom.get()
            return custom if custom else RAMPS["Klasik"]
        return RAMPS.get(name, RAMPS["Klasik"])

    def _on_detail(self):
        name = self.var_detail.get()
        w = DETAIL_PRESETS.get(name)
        if w is not None and int(self.var_width.get()) != w:
            self.var_width.set(w)
            self.schedule_update()

    def _sync_detail(self):
        try:
            w = int(self.var_width.get())
        except Exception:
            return
        for name, val in DETAIL_PRESETS.items():
            if val == w:
                if self.var_detail.get() != name:
                    self.var_detail.set(name)
                return
        if self.var_detail.get() != "Özel":
            self.var_detail.set("Özel")

    def current_opts(self):
        return {
            "width": int(self.var_width.get()),
            "ratio": self.var_ratio.get() / 100.0,
            "ramp": self.current_ramp(),
            "invert": self.var_invert.get(),
            "brightness": self.var_bright.get() / 100.0,
            "contrast": self.var_contrast.get() / 100.0,
            "dither": self.var_dither.get(),
        }

    def schedule_update(self):
        if self._after_id is not None:
            try:
                self.root.after_cancel(self._after_id)
            except Exception:
                pass
        self._after_id = self.root.after(280, self.do_update)

    def open_image(self, path=None):
        path = path or filedialog.askopenfilename(
            title="Resim seç",
            filetypes=[
                ("Resimler", "*.png *.jpg *.jpeg *.bmp *.gif *.webp *.tga *.ico"),
                ("Tüm dosyalar", "*.*"),
            ],
        )
        if not path:
            return
        try:
            with Image.open(path) as source:
                img = ImageOps.exif_transpose(source).convert("RGBA")
            thumb = img.copy()
            thumb.thumbnail((850, 600), Image.Resampling.LANCZOS)
            self._source_photo = ImageTk.PhotoImage(thumb)
            self.source_label.configure(image=self._source_photo, text="")
        except Exception as ex:
            messagebox.showerror("Hata", f"Resim açılamadı:\n{ex}")
            return
        self.img = img
        self.image_path = path
        self.do_update()

    def do_update(self):
        self._after_id = None
        if self.img is None or self._closed:
            return
        self._generation += 1
        generation = self._generation
        try:
            opts = self.current_opts()
        except (ValueError, tk.TclError) as ex:
            self.status.config(text=f"Ayar hatası: {ex}")
            return
        self._busy = True
        self.status.config(text="Dönüştürülüyor…")
        image = self.img
        # Only the worker touches Pillow; all Tk operations stay on the main thread.
        def work():
            try:
                return convert_image(image, **opts), None
            except Exception as ex:
                return None, str(ex)
        if hasattr(self, "_future"):
            self._future.cancel()
        self._future = self._executor.submit(work)
        self._future.add_done_callback(lambda f: self._results.put((generation, f.result())) if not f.cancelled() else None)

    def _poll_results(self):
        if self._closed:
            return
        try:
            while True:
                generation, (result, error) = self._results.get_nowait()
                if generation != self._generation:
                    continue
                self._busy = False
                if error:
                    self.rows, self.colors = [], []
                    self.status.config(text=f"Dönüşüm hatası: {error}")
                    continue
                self.rows, self.colors = result
                try:
                    self._render_text() if self.var_view.get() == "text" else self._render_color()
                    self.status.config(text=f"{os.path.basename(getattr(self, 'image_path', 'Görsel'))}  •  {len(self.rows[0])} × {len(self.rows)} karakter  •  {self.var_mode.get()}")
                except Exception as ex:
                    self.status.config(text=f"Önizleme hatası: {ex}")
        except queue.Empty:
            pass
        self.root.after(60, self._poll_results)

    def _ready(self):
        if self._busy or self._after_id is not None:
            self.status.config(text="Ayarlar uygulanıyor; önizleme tamamlandığında tekrar deneyin.")
            return False
        if not self.rows:
            self.status.config(text="Önce bir görsel açın (Ctrl+O).")
            return False
        return True

    def reset_controls(self):
        for var, value in ((self.var_width, 100), (self.var_ratio, 50), (self.var_bright, 100),
                           (self.var_contrast, 100), (self.var_invert, False), (self.var_dither, False),
                           (self.var_ramp, "Klasik"), (self.var_mode, "TrueColor"), (self.var_res, "Standart")):
            var.set(value)
        self.schedule_update()

    def save_html(self):
        if not self._ready():
            return
        path = filedialog.asksaveasfilename(title="HTML kaydet", defaultextension=".html", filetypes=[("HTML", "*.html")])
        if path:
            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(make_html(self.rows, self.colors, self.var_mode.get()))
                self.status.config(text=f"HTML kaydedildi: {path}")
            except OSError as ex:
                messagebox.showerror("Kaydetme hatası", str(ex))

    def _render_text(self):
        self.canvas.grid_remove()
        self._canvas_scroll_y.grid_remove()
        self._canvas_scroll_x.grid_remove()
        self.text_scroll_y.grid(row=0, column=1, sticky="ns")
        self.text_scroll_x.grid(row=1, column=0, sticky="ew")
        self.text.grid()
        self.text.config(state="normal")
        self.text.delete("1.0", "end")
        for y, line in enumerate(self.rows):
            runs = []
            cur_tag, buf = None, []
            for x, ch in enumerate(line):
                r, g, b = self.colors[y][x]
                v = (r * 299 + g * 587 + b * 114) // 1000
                tag = f"l{min(15, v * 15 // 256)}"
                if tag != cur_tag:
                    if buf:
                        runs.append((cur_tag, "".join(buf)))
                    buf, cur_tag = [ch], tag
                else:
                    buf.append(ch)
            if buf:
                runs.append((cur_tag, "".join(buf)))
            for tag, txt in runs:
                self.text.insert("end", txt, tag)
            self.text.insert("end", "\n")
        self.text.config(state="disabled")

    def _render_color(self):
        self.text.grid_remove()
        self.text_scroll_y.grid_remove()
        self.text_scroll_x.grid_remove()
        self.canvas.grid()
        self._canvas_scroll_y.grid(row=0, column=1, sticky="ns")
        self._canvas_scroll_x.grid(row=1, column=0, sticky="ew")
        gray = self.var_mode.get() == "Yok"
        preset = RES_PRESETS.get(self.var_res.get(), RES_PRESETS["Standart"])
        preview_font = max(6, round(min(preset["font"], 16) * self.zoom))
        pil = render_ascii_image(self.rows, None if gray else [[output_color(c, self.var_mode.get()) for c in row] for row in self.colors],
                                 font_size=preview_font, grayscale=gray)
        self.photo = ImageTk.PhotoImage(pil)
        self.canvas.delete("all")
        self.canvas_img = self.canvas.create_image(0, 0, anchor="nw", image=self.photo)
        self.canvas.configure(scrollregion=(0, 0, pil.width, pil.height))

    def change_zoom(self, factor):
        self.zoom = 1.0 if factor == 0 else max(0.5, min(3.0, self.zoom * factor))
        self.text.configure(font=("Consolas", max(6, round(10 * self.zoom))))
        if self.rows and self.var_view.get() == "color":
            try:
                self._render_color()
            except (ValueError, MemoryError) as ex:
                self.status.config(text=str(ex))

    def switch_view(self):
        self.schedule_update()

    def copy_text(self):
        if not self._ready():
            return
        content = make_txt(self.rows)
        self.root.clipboard_clear()
        self.root.clipboard_append(content)
        self.status.config(text="Sade metin panoya kopyalandı. Renkli terminal çıktısı için ANS kaydedin.")

    def save_txt(self):
        if not self._ready():
            return
        path = filedialog.asksaveasfilename(title="TXT kaydet", defaultextension=".txt",
                                            filetypes=[("Metin", "*.txt")])
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8", newline="\n") as f:
                f.write(make_txt(self.rows))
            self.status.config(text=f"TXT kaydedildi: {path}")

        except (OSError, ValueError, MemoryError) as ex:
            messagebox.showerror("Kaydetme hatası", str(ex))

    def save_ans(self):
        if not self._ready():
            return
        path = filedialog.asksaveasfilename(title="ANS kaydet", defaultextension=".ans",
                                            filetypes=[("ANSI sanatı", "*.ans *.txt")])
        if not path:
            return
        content = make_ansi(self.rows, self.colors, self.var_mode.get())
        try:
            with open(path, "w", encoding="utf-8", newline="\n") as f:
                f.write(content)
            self.status.config(text=f"ANS kaydedildi: {path}  (Windows Terminal / ConEmu ile aç)")

        except (OSError, ValueError, MemoryError) as ex:
            messagebox.showerror("Kaydetme hatası", str(ex))

    def save_png(self):
        if not self._ready():
            return
        path = filedialog.asksaveasfilename(title="PNG kaydet", defaultextension=".png",
                                            filetypes=[("PNG", "*.png")])
        if not path:
            return
        try:
            gray = self.var_mode.get() == "Yok"
            preset = RES_PRESETS.get(self.var_res.get(), RES_PRESETS["Standart"])
            pil = render_ascii_image(self.rows, None if gray else [[output_color(c, self.var_mode.get()) for c in row] for row in self.colors],
                                     font_size=preset["font"], grayscale=gray)
            if preset["scale"] > 1:
                if pil.width * pil.height * preset["scale"] ** 2 > 40000000:
                    raise ValueError("PNG çok büyük; çözünürlüğü azaltın")
                pil = pil.resize((pil.width * preset["scale"], pil.height * preset["scale"]), Image.NEAREST)
            pil.save(path)
            self.status.config(text=f"PNG kaydedildi ({pil.width}x{pil.height}px, {self.var_res.get()}): {path}")

        except (OSError, ValueError, MemoryError) as ex:
            messagebox.showerror("Kaydetme hatası", str(ex))

    def show_about(self):
        messagebox.showinfo(
            "ASCII ART STUDIO",
            "Resmi ASCII/ANSI karakter sanatına dönüştürür.\n\n"
            "• TXT: sade metin\n"
            "• ANS: renkli ANSI escape kodları (Windows Terminal/ConEmu)\n"
            "• PNG: çizilmiş sanatın görseli — çözünürlük seçeneğine göre\n"
            "  (Yüksek/Ultra: karakterler büyük fontla doğrudan çizilir, bulanık olmaz)\n"
            "• Panoya kopyala: aktif renk moduyla birlikte\n\n"
            "İpucu: en/boy oranını 0.5 civarında tut, karakterler uzun olduğu için.",
        )

    def preferences(self):
        return {
            "width": int(self.var_width.get()),
            "ratio": self.var_ratio.get(),
            "ramp": self.var_ramp.get(),
            "custom": self.var_custom.get(),
            "invert": self.var_invert.get(),
            "dither": self.var_dither.get(),
            "bright": self.var_bright.get(),
            "contrast": self.var_contrast.get(),
            "mode": self.var_mode.get(),
            "view": self.var_view.get(),
            "res": self.var_res.get(),
        }

    def _save_prefs(self):
        save_settings(self.preferences())

    def _load_prefs(self):
        self.apply_preferences(load_settings())

    def apply_preferences(self, d):
        if not d:
            return
        try:
            self.var_width.set(max(20, min(320, int(d.get("width", 80)))))
            self.var_ratio.set(max(30, min(100, float(d.get("ratio", 50)))))
            self.var_ramp.set(d.get("ramp", "Klasik"))
            self.var_custom.delete(0, "end")
            self.var_custom.insert(0, d.get("custom", "@%#*+=-:. "))
            self.var_invert.set(d.get("invert", False))
            self.var_dither.set(d.get("dither", False))
            self.var_bright.set(d.get("bright", 100))
            self.var_contrast.set(d.get("contrast", 100))
            self.var_mode.set(d.get("mode", "TrueColor"))
            self.var_view.set(d.get("view", "text"))
            res = d.get("res", "Standart")
            if res in RES_PRESETS:
                self.var_res.set(res)
                hints = {"Hızlı": "Küçük PNG, hızlı kayıt", "Standart": "14px font + 2x büyütme",
                         "Yüksek": "36px font, net çizim", "Çok Yüksek": "56px font, çok net",
                         "Ultra": "88px font, poster boyu"}
                self.res_hint_lbl.config(text=hints.get(res, ""))
        except Exception:
            pass

    def apply_style(self):
        styles = {
            "Terminal": dict(width=100, ratio=50, ramp="Klasik", mode="ANSI 16", contrast=125, bright=110, invert=True, dither=False, view="text"),
            "Piksel afiş": dict(width=80, ratio=50, ramp="Blok", mode="ANSI 16", contrast=150, bright=100, invert=True, dither=False, view="color"),
            "Mürekkep": dict(width=140, ratio=50, ramp="Minimum", mode="Yok", contrast=150, bright=110, invert=True, dither=True, view="color"),
            "Renkli portre": dict(width=160, ratio=50, ramp="Yoğun", mode="TrueColor", contrast=115, bright=110, invert=True, dither=False, view="color"),
        }
        self.apply_preferences(styles[self.var_style.get()])
        self.schedule_update()

    def save_project(self):
        if self.img is None:
            self.status.config(text="Önce bir görsel açın.")
            return
        path = filedialog.asksaveasfilename(defaultextension=".asciiproject", filetypes=[("ASCII Studio projesi", "*.asciiproject")])
        if not path:
            return
        try:
            buffer = io.BytesIO()
            self.img.save(buffer, format="PNG")
            data = {"version": 1, "settings": self.preferences(), "image": base64.b64encode(buffer.getvalue()).decode("ascii")}
            temporary = path + ".tmp"
            with open(temporary, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)
            os.replace(temporary, path)
            self.status.config(text="Proje kaydedildi: görsel ve ayarlar tek dosyada.")
        except (OSError, ValueError) as ex:
            messagebox.showerror("Proje kaydedilemedi", str(ex))

    def open_project(self, path=None):
        path = path or filedialog.askopenfilename(filetypes=[("ASCII Studio projesi", "*.asciiproject")])
        if not path:
            return
        try:
            if os.path.getsize(path) > 100_000_000:
                raise ValueError("Proje 100 MB sınırını aşıyor")
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            if data.get("version") != 1 or not isinstance(data.get("settings"), dict):
                raise ValueError("Desteklenmeyen proje biçimi")
            with Image.open(io.BytesIO(base64.b64decode(data["image"], validate=True))) as source:
                img = source.convert("RGBA")
            self.img = img
            self.image_path = path
            thumb = img.copy()
            thumb.thumbnail((850, 600))
            self._source_photo = ImageTk.PhotoImage(thumb)
            self.source_label.configure(image=self._source_photo, text="")
            self.apply_preferences(data["settings"])
            self.schedule_update()
        except Exception as ex:
            messagebox.showerror("Proje açılamadı", str(ex))

    def save_svg(self):
        if not self._ready():
            return
        path = filedialog.asksaveasfilename(defaultextension=".svg", filetypes=[("SVG", "*.svg")])
        if path:
            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(make_svg(self.rows, self.colors, self.var_mode.get()))
                self.status.config(text="Ölçeklenebilir SVG kaydedildi.")
            except OSError as ex:
                messagebox.showerror("SVG kaydedilemedi", str(ex))

    def on_close(self):
        self._closed = True
        if self._after_id is not None:
            self.root.after_cancel(self._after_id)
        self._executor.shutdown(wait=False, cancel_futures=True)
        self._save_prefs()
        self.root.destroy()


GREY_TXT = "#8888aa"

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="ASCII Art Studio")
    parser.add_argument("file", nargs="?", help="Image or .asciiproject file")
    parser.add_argument("--smoke-test", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    app = App(standalone=False)
    if args.smoke_test:
        app.root.withdraw()
        app.img = Image.new("RGB", (32, 24), (120, 180, 240))
        app.rows, app.colors = convert_image(app.img, width=40)
        app._render_text()
        app._render_color()
        app.root.update()
        app._closed = True
        app._executor.shutdown(wait=False, cancel_futures=True)
        app.root.destroy()
    else:
        if args.file:
            if args.file.lower().endswith(".asciiproject"):
                app.open_project(args.file)
            else:
                app.open_image(args.file)
        app.root.mainloop()
