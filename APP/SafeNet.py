import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
from datetime import datetime
import random
import time
import threading

# ═══════════════════════════════════════════════════════════
#  PALETTE & STYLE
# ═══════════════════════════════════════════════════════════
BG       = "#0d0f14"
SURFACE  = "#161a23"
SURFACE2 = "#1e2330"
BORDER   = "#252a38"
ACCENT   = "#6c63ff"
ACCENT2  = "#a78bfa"
RED      = "#ff4d6d"
GREEN    = "#34d399"
YELLOW   = "#fbbf24"
TEXT     = "#f0f0f5"
MUTED    = "#7a7f94"
WHITE    = "#ffffff"

FONT_BODY   = ("Segoe UI", 11)
FONT_BOLD   = ("Segoe UI", 11, "bold")
FONT_SMALL  = ("Segoe UI", 9)
FONT_LARGE  = ("Segoe UI", 16, "bold")
FONT_TITLE  = ("Segoe UI", 20, "bold")
FONT_MONO   = ("Consolas", 13, "bold")

BOT_COLORS = {
    "Alex":  "#6c63ff", "Maya":  "#f59e0b",
    "Liam":  "#10b981", "Sofia": "#ec4899",
    "Emma":  "#ef4444", "Noah":  "#3b82f6",
}

# ═══════════════════════════════════════════════════════════
#  DATABASE
# ═══════════════════════════════════════════════════════════
conn = sqlite3.connect("safenet.db", check_same_thread=False)
c    = conn.cursor()

c.executescript("""
    CREATE TABLE IF NOT EXISTS posts (
        id      INTEGER PRIMARY KEY AUTOINCREMENT,
        user    TEXT,
        text    TEXT,
        likes   INTEGER DEFAULT 0,
        ts      TEXT
    );
    CREATE TABLE IF NOT EXISTS comments (
        id      INTEGER PRIMARY KEY AUTOINCREMENT,
        post_id INTEGER,
        user    TEXT,
        text    TEXT
    );
    CREATE TABLE IF NOT EXISTS likes (
        post_id INTEGER,
        user    TEXT,
        PRIMARY KEY (post_id, user)
    );
    CREATE TABLE IF NOT EXISTS users (
        username   TEXT PRIMARY KEY,
        bio        TEXT DEFAULT 'Membre SafeNET 💙',
        created_at TEXT
    );
""")

# Migration: add missing columns if DB was created with old schema
for col, definition in [("ts", "TEXT"), ("likes", "INTEGER DEFAULT 0")]:
    try:
        c.execute(f"ALTER TABLE posts ADD COLUMN {col} {definition}")
        conn.commit()
    except Exception:
        pass  # column already exists

conn.commit()

# Seed demo posts
c.execute("SELECT COUNT(*) FROM posts")
if c.fetchone()[0] == 0:
    seeds = [
        ("Sofia",  "Rappel : vous n'êtes pas seuls 💙 SafeNET est là pour vous. N'hésitez pas à partager ce que vous ressentez."),
        ("Maya",   "Aujourd'hui j'ai réussi à parler à quelqu'un de ma situation. Difficile mais ça fait du bien. Merci à cette communauté 🙏"),
        ("Alex",   "Demander de l'aide c'est une force, pas une faiblesse. Prenez soin de vous ✨"),
    ]
    for u, t in seeds:
        c.execute("INSERT INTO posts (user, text, likes, ts) VALUES (?,?,?,?)",
                  (u, t, random.randint(3, 12), datetime.now().strftime("%H:%M")))
    conn.commit()

# ═══════════════════════════════════════════════════════════
#  HELPER: rounded rectangle on canvas
# ═══════════════════════════════════════════════════════════
def round_rect(canvas, x1, y1, x2, y2, r=12, **kw):
    points = [
        x1+r, y1,  x2-r, y1,
        x2,   y1,  x2,   y1+r,
        x2,   y2-r, x2,  y2,
        x2-r, y2,  x1+r, y2,
        x1,   y2,  x1,   y2-r,
        x1,   y1+r, x1,  y1,
        x1+r, y1,
    ]
    return canvas.create_polygon(points, smooth=True, **kw)

# ═══════════════════════════════════════════════════════════
#  SCROLLABLE FRAME
# ═══════════════════════════════════════════════════════════
class ScrollFrame(tk.Frame):
    def __init__(self, parent, **kw):
        bg = kw.pop("bg", BG)
        super().__init__(parent, bg=bg, **kw)
        self.canvas = tk.Canvas(self, bg=bg, highlightthickness=0, bd=0)
        self.scrollbar = tk.Scrollbar(self, orient="vertical",
                                      command=self.canvas.yview,
                                      width=6)
        self.inner = tk.Frame(self.canvas, bg=bg)
        self.canvas_window = self.canvas.create_window(
            (0, 0), window=self.inner, anchor="nw")

        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        self.inner.bind("<Configure>", self._on_inner_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

    def _on_inner_configure(self, _=None):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        self.canvas.itemconfig(self.canvas_window, width=event.width)

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(-1 * (event.delta // 120), "units")

    def scroll_top(self):
        self.canvas.yview_moveto(0)

# ═══════════════════════════════════════════════════════════
#  CUSTOM WIDGETS
# ═══════════════════════════════════════════════════════════
class PillButton(tk.Button):
    """Simple styled button — no Canvas tricks, no size leaking."""
    def __init__(self, parent, text, command=None, color=ACCENT,
                 fg=WHITE, width=None, height=None, radius=None, font=FONT_BOLD):
        try:
            parent_bg = parent.cget("bg")
        except Exception:
            parent_bg = BG
        super().__init__(
            parent,
            text=text,
            command=command,
            bg=color,
            fg=fg,
            font=font,
            relief="flat",
            bd=0,
            padx=12,
            pady=6,
            cursor="hand2",
            activebackground=self._darken_static(color),
            activeforeground=fg,
        )
        self._color = color
        self._hover = self._darken_static(color)
        self.bind("<Enter>", lambda e: self.config(bg=self._hover))
        self.bind("<Leave>", lambda e: self.config(bg=self._color))

    @staticmethod
    def _darken_static(hex_color):
        try:
            r = max(0, int(hex_color[1:3], 16) - 30)
            g = max(0, int(hex_color[3:5], 16) - 30)
            b = max(0, int(hex_color[5:7], 16) - 30)
            return f"#{r:02x}{g:02x}{b:02x}"
        except Exception:
            return hex_color



class Avatar(tk.Canvas):
    def __init__(self, parent, name, size=38, command=None, **kw):
        try:
            parent_bg = parent.cget("bg")
        except Exception:
            parent_bg = BG
        super().__init__(parent, width=size, height=size,
                         bg=parent_bg, highlightthickness=0, **kw)
        color = BOT_COLORS.get(name, ACCENT)
        initials = name[:2].upper()
        r = size // 2
        self.create_oval(1, 1, size-1, size-1, fill=color, outline="")
        self.create_text(r, r, text=initials, fill=WHITE,
                         font=("Segoe UI", max(8, size//3), "bold"))
        if command:
            self.bind("<Button-1>", lambda e: command(name))
            self.config(cursor="hand2")

class StyledEntry(tk.Frame):
    def __init__(self, parent, placeholder="", width=200, **kw):
        bg = kw.pop("bg", SURFACE2)
        fg = kw.pop("fg", TEXT)
        super().__init__(parent, bg=bg, padx=1, pady=1)
        self.configure(highlightbackground=BORDER, highlightthickness=1)
        self.entry = tk.Entry(self, bg=bg, fg=fg, insertbackground=TEXT,
                              relief="flat", font=FONT_BODY,
                              width=width, bd=4, **kw)
        self.entry.pack(fill="x")
        if placeholder:
            self._placeholder = placeholder
            self._fg = fg
            self.entry.insert(0, placeholder)
            self.entry.config(fg=MUTED)
            self.entry.bind("<FocusIn>",  self._clear_ph)
            self.entry.bind("<FocusOut>", self._restore_ph)

    def _clear_ph(self, _):
        if self.entry.get() == self._placeholder:
            self.entry.delete(0, "end")
            self.entry.config(fg=self._fg)

    def _restore_ph(self, _):
        if not self.entry.get():
            self.entry.insert(0, self._placeholder)
            self.entry.config(fg=MUTED)

    def get(self):
        val = self.entry.get()
        return "" if val == getattr(self, "_placeholder", None) else val

    def delete(self, *a): self.entry.delete(*a)
    def bind(self, *a, **k): self.entry.bind(*a, **k)
    def focus(self): self.entry.focus()

# ═══════════════════════════════════════════════════════════
#  SAFENET APP
# ═══════════════════════════════════════════════════════════
class SafeNetApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("SafeNET")
        self.geometry("1100x720")
        self.minsize(800, 600)
        self.configure(bg=BG)
        self.current_user = None

        self._build_nav()
        self._build_pages()
        self._show_page("feed")
        self.after(4000, self._bot_loop)

    # ─── NAVBAR ────────────────────────────────────────────
    def _build_nav(self):
        nav = tk.Frame(self, bg=SURFACE, height=60)
        nav.pack(fill="x", side="top")
        nav.pack_propagate(False)

        # Logo
        logo = tk.Frame(nav, bg=SURFACE)
        logo.pack(side="left", padx=20)
        tk.Label(logo, text="Safe", font=("Consolas", 16, "bold"),
                 bg=SURFACE, fg=ACCENT2).pack(side="left")
        tk.Label(logo, text="NET", font=("Consolas", 16, "bold"),
                 bg=SURFACE, fg=RED).pack(side="left")

        # Nav buttons
        nav_btns = tk.Frame(nav, bg=SURFACE)
        nav_btns.pack(side="left", padx=10)
        self._nav_buttons = {}

        for key, label in [("feed", "🏠  Accueil"), ("aide", "🆘  Aide & SOS")]:
            btn = tk.Label(nav_btns, text=label, font=FONT_BODY,
                           bg=SURFACE, fg=MUTED, cursor="hand2",
                           padx=14, pady=8)
            btn.pack(side="left", padx=2)
            btn.bind("<Button-1>", lambda e, k=key: self._show_page(k))
            btn.bind("<Enter>", lambda e, b=btn: b.config(fg=TEXT, bg=SURFACE2))
            btn.bind("<Leave>", lambda e, b=btn, k=key: self._nav_leave(b, k))
            self._nav_buttons[key] = btn

        # User area
        user_area = tk.Frame(nav, bg=SURFACE)
        user_area.pack(side="right", padx=20)

        self._login_frame = tk.Frame(user_area, bg=SURFACE)
        self._login_frame.pack(side="right")
        self._name_entry = StyledEntry(self._login_frame, placeholder="Votre pseudo...", width=14)
        self._name_entry.pack(side="left", padx=(0, 8))
        PillButton(self._login_frame, "Se connecter", command=self._set_user,
                   color=ACCENT, width=130, height=30).pack(side="left")

        self._user_frame = tk.Frame(user_area, bg=SURFACE)
        self._user_avatar = tk.Label(self._user_frame, bg=SURFACE, fg=WHITE,
                                      font=("Segoe UI", 9, "bold"))
        self._user_avatar.pack(side="left", padx=(0, 6))
        self._user_name_lbl = tk.Label(self._user_frame, bg=SURFACE,
                                        fg=ACCENT2, font=FONT_BOLD)
        self._user_name_lbl.pack(side="left")

        self._sep = tk.Frame(nav, bg=BORDER, width=1)
        self._sep.pack(side="bottom", fill="x")

    def _nav_leave(self, btn, key):
        active = getattr(self, "_active_page", None)
        if active == key:
            btn.config(fg=ACCENT2, bg=SURFACE)
        else:
            btn.config(fg=MUTED, bg=SURFACE)

    def _set_user(self):
        name = self._name_entry.get().strip()
        if not name:
            self._toast("Entre un pseudo d'abord !", "error")
            return
        self.current_user = name
        c.execute("INSERT OR IGNORE INTO users (username, created_at) VALUES (?,?)",
                  (name, datetime.now().strftime("%Y-%m-%d")))
        conn.commit()

        self._login_frame.pack_forget()
        self._user_frame.pack(side="right")
        self._user_name_lbl.config(text=name)
        self._user_avatar.config(text=f"  {name[:2].upper()}  ",
                                   bg=BOT_COLORS.get(name, ACCENT))
        self._toast(f"Bienvenue, {name} ! 👋")

    # ─── PAGES ─────────────────────────────────────────────
    def _build_pages(self):
        self._container = tk.Frame(self, bg=BG)
        self._container.pack(fill="both", expand=True)
        self._pages = {}

        self._build_feed_page()
        self._build_aide_page()
        self._build_profile_page()

    def _show_page(self, key):
        self._active_page = key
        for k, f in self._pages.items():
            f.pack_forget()
        self._pages[key].pack(fill="both", expand=True)

        for k, b in self._nav_buttons.items():
            if k == key:
                b.config(fg=ACCENT2, bg=SURFACE)
            else:
                b.config(fg=MUTED, bg=SURFACE)

        if key == "feed":
            self._refresh_feed()

    # ─── FEED PAGE ─────────────────────────────────────────
    def _build_feed_page(self):
        page = tk.Frame(self._container, bg=BG)
        self._pages["feed"] = page

        # Center column
        center = tk.Frame(page, bg=BG)
        center.place(relx=0.5, rely=0, anchor="n", relwidth=1, relheight=1)

        inner = tk.Frame(center, bg=BG)
        inner.pack(fill="both", expand=True, padx=0)

        # Header
        header = tk.Frame(inner, bg=BG)
        header.pack(fill="x", padx=60, pady=(28, 0))
        tk.Label(header, text="Fil d'actualité", font=FONT_TITLE,
                 bg=BG, fg=TEXT).pack(side="left")
        live = tk.Label(header, text=" ● LIVE ", font=("Segoe UI", 9, "bold"),
                        bg="#1a2e1e", fg=GREEN, padx=6, pady=2)
        live.pack(side="left", padx=10, pady=6)
        tk.Label(inner, text="Partagez vos pensées, soutenez la communauté 💙",
                 font=FONT_SMALL, bg=BG, fg=MUTED).pack(anchor="w", padx=60, pady=(4, 20))

        # Compose box
        compose = tk.Frame(inner, bg=SURFACE, padx=16, pady=14)
        compose.pack(fill="x", padx=60, pady=(0, 20))
        compose.configure(highlightbackground=BORDER, highlightthickness=1)

        self._post_text = tk.Text(compose, bg=SURFACE, fg=TEXT, insertbackground=TEXT,
                                   font=FONT_BODY, relief="flat", height=4, wrap="word",
                                   bd=0, padx=4)
        self._post_text.pack(fill="x")
        self._post_text.insert("1.0", "Quoi de neuf ? Partagez avec la communauté...")
        self._post_text.config(fg=MUTED)
        self._post_text.bind("<FocusIn>",  self._compose_focus_in)
        self._post_text.bind("<FocusOut>", self._compose_focus_out)
        self._post_text.bind("<KeyRelease>", self._update_char_count)

        sep = tk.Frame(compose, bg=BORDER, height=1)
        sep.pack(fill="x", pady=(10, 6))

        actions = tk.Frame(compose, bg=SURFACE)
        actions.pack(fill="x")
        self._char_label = tk.Label(actions, text="0/280", font=FONT_SMALL,
                                     bg=SURFACE, fg=MUTED)
        self._char_label.pack(side="left")
        PillButton(actions, "🚀 Publier", command=self._publish,
                   color=ACCENT, width=110, height=30).pack(side="right")

        tk.Label(inner, text="PUBLICATIONS RÉCENTES", font=("Segoe UI", 9, "bold"),
                 bg=BG, fg=MUTED).pack(anchor="w", padx=60, pady=(0, 8))

        self._scroll_feed = ScrollFrame(inner, bg=BG)
        self._scroll_feed.pack(fill="both", expand=True, padx=60)

    def _compose_focus_in(self, _):
        if self._post_text.get("1.0", "end-1c") == "Quoi de neuf ? Partagez avec la communauté...":
            self._post_text.delete("1.0", "end")
            self._post_text.config(fg=TEXT)

    def _compose_focus_out(self, _):
        if not self._post_text.get("1.0", "end-1c").strip():
            self._post_text.insert("1.0", "Quoi de neuf ? Partagez avec la communauté...")
            self._post_text.config(fg=MUTED)

    def _update_char_count(self, _=None):
        n = len(self._post_text.get("1.0", "end-1c"))
        color = RED if n > 260 else YELLOW if n > 220 else MUTED
        self._char_label.config(text=f"{n}/280", fg=color)

    def _publish(self):
        txt = self._post_text.get("1.0", "end-1c").strip()
        placeholder = "Quoi de neuf ? Partagez avec la communauté..."
        if txt == placeholder or not txt:
            self._toast("Écris quelque chose d'abord !", "error"); return
        if not self.current_user:
            self._toast("Connecte-toi d'abord !", "error"); return
        if len(txt) > 280:
            self._toast("280 caractères max !", "error"); return

        c.execute("INSERT INTO posts (user, text, likes, ts) VALUES (?,?,0,?)",
                  (self.current_user, txt, datetime.now().strftime("%H:%M")))
        conn.commit()
        self._post_text.delete("1.0", "end")
        self._compose_focus_out(None)
        self._refresh_feed()
        self._scroll_feed.scroll_top()
        self._toast("Post publié ! 🚀")

    def _refresh_feed(self):
        for w in self._scroll_feed.inner.winfo_children():
            w.destroy()

        c.execute("SELECT id, user, text, likes, ts FROM posts ORDER BY id DESC")
        rows = c.fetchall()

        if not rows:
            empty = tk.Frame(self._scroll_feed.inner, bg=BG)
            empty.pack(pady=60)
            tk.Label(empty, text="💬", font=("Segoe UI", 32), bg=BG, fg=MUTED).pack()
            tk.Label(empty, text="Aucun post pour l'instant.\nSois le premier à partager !",
                     font=FONT_BODY, bg=BG, fg=MUTED, justify="center").pack(pady=8)
            return

        for pid, user, text, likes, ts in rows:
            self._build_post_card(self._scroll_feed.inner, pid, user, text, likes, ts)

        self._scroll_feed.inner.update_idletasks()

    def _build_post_card(self, parent, pid, user, text, likes, ts):
        outer = tk.Frame(parent, bg=SURFACE, padx=16, pady=14)
        outer.pack(fill="x", pady=(0, 12))
        outer.configure(highlightbackground=BORDER, highlightthickness=1)

        # Header row
        head = tk.Frame(outer, bg=SURFACE)
        head.pack(fill="x", pady=(0, 8))

        Avatar(head, user, size=36, command=self._open_profile).pack(side="left")

        meta = tk.Frame(head, bg=SURFACE)
        meta.pack(side="left", padx=10)
        author = tk.Label(meta, text=user, font=FONT_BOLD, bg=SURFACE, fg=TEXT,
                           cursor="hand2")
        author.pack(anchor="w")
        author.bind("<Button-1>", lambda e, u=user: self._open_profile(u))
        author.bind("<Enter>", lambda e: author.config(fg=ACCENT2))
        author.bind("<Leave>", lambda e: author.config(fg=TEXT))
        tk.Label(meta, text=ts, font=FONT_SMALL, bg=SURFACE, fg=MUTED).pack(anchor="w")

        # Post text
        txt_lbl = tk.Label(outer, text=text, font=FONT_BODY, bg=SURFACE, fg=TEXT,
                           wraplength=560, justify="left", anchor="w")
        txt_lbl.pack(fill="x", pady=(0, 10))

        sep = tk.Frame(outer, bg=BORDER, height=1)
        sep.pack(fill="x", pady=(0, 10))

        # Action row
        actions = tk.Frame(outer, bg=SURFACE)
        actions.pack(fill="x")

        liked = self.current_user and self._user_liked(pid, self.current_user)
        like_color = RED if liked else MUTED
        like_bg    = "#2a1520" if liked else SURFACE2

        like_btn = tk.Label(actions, text=f"  ❤️  {likes}  ",
                            font=FONT_SMALL, bg=like_bg, fg=like_color,
                            cursor="hand2", padx=6, pady=4)
        like_btn.pack(side="left", padx=(0, 6))
        like_btn.bind("<Button-1>", lambda e, p=pid: self._toggle_like(p))

        c.execute("SELECT COUNT(*) FROM comments WHERE post_id=?", (pid,))
        n_comm = c.fetchone()[0]
        comm_btn = tk.Label(actions, text=f"  💬  {n_comm}  ",
                            font=FONT_SMALL, bg=SURFACE2, fg=MUTED,
                            cursor="hand2", padx=6, pady=4)
        comm_btn.pack(side="left")
        comm_btn.bind("<Button-1>",
                      lambda e, f=outer: self._toggle_comments(f, pid))

        # Comments section (collapsed by default)
        comm_frame = tk.Frame(outer, bg=SURFACE)
        comm_frame._visible = False
        comm_frame._pid = pid
        comm_frame.pack(fill="x")
        self._load_comments(comm_frame, pid)

        comm_btn.bind("<Button-1>", lambda e, cf=comm_frame, p=pid:
                      self._toggle_comments(cf, p))

    def _user_liked(self, post_id, user):
        c.execute("SELECT 1 FROM likes WHERE post_id=? AND user=?", (post_id, user))
        return c.fetchone() is not None

    def _toggle_like(self, pid):
        if not self.current_user:
            self._toast("Connecte-toi pour liker !", "error"); return
        if self._user_liked(pid, self.current_user):
            c.execute("DELETE FROM likes WHERE post_id=? AND user=?", (pid, self.current_user))
            c.execute("UPDATE posts SET likes = MAX(0, likes-1) WHERE id=?", (pid,))
        else:
            c.execute("INSERT OR IGNORE INTO likes VALUES (?,?)", (pid, self.current_user))
            c.execute("UPDATE posts SET likes = likes+1 WHERE id=?", (pid,))
        conn.commit()
        self._refresh_feed()

    def _toggle_comments(self, frame, pid):
        frame._visible = not frame._visible
        if frame._visible:
            self._load_comments(frame, pid)
        else:
            for w in frame.winfo_children():
                w.destroy()

    def _load_comments(self, frame, pid):
        for w in frame.winfo_children():
            w.destroy()

        if not frame._visible:
            return

        c.execute("SELECT user, text FROM comments WHERE post_id=?", (pid,))
        for cu, ct in c.fetchall():
            row = tk.Frame(frame, bg=SURFACE)
            row.pack(fill="x", pady=2)
            color = BOT_COLORS.get(cu, ACCENT)
            tk.Label(row, text=cu[:2].upper(), bg=color, fg=WHITE,
                     font=("Segoe UI", 8, "bold"), width=3, pady=3).pack(side="left", padx=(4, 6))
            bubble = tk.Frame(row, bg=SURFACE2)
            bubble.pack(side="left", fill="x", expand=True)
            tk.Label(bubble, text=cu, font=("Segoe UI", 9, "bold"),
                     bg=SURFACE2, fg=ACCENT2).pack(anchor="w", padx=8, pady=(4, 0))
            tk.Label(bubble, text=ct, font=FONT_SMALL, bg=SURFACE2, fg=TEXT,
                     wraplength=480, justify="left").pack(anchor="w", padx=8, pady=(0, 4))

        # Comment entry
        entry_row = tk.Frame(frame, bg=SURFACE)
        entry_row.pack(fill="x", pady=(6, 2))
        entry = StyledEntry(entry_row, placeholder="Ajouter un commentaire...",
                            bg=SURFACE2, fg=TEXT, width=40)
        entry.pack(side="left", padx=(4, 6), fill="x", expand=True)

        def send_comment():
            txt = entry.get().strip()
            if not txt: return
            user = self.current_user or "Anonyme"
            c.execute("INSERT INTO comments (post_id, user, text) VALUES (?,?,?)",
                      (pid, user, txt))
            conn.commit()
            entry.delete(0, "end")
            self._load_comments(frame, pid)

        entry.bind("<Return>", lambda e: send_comment())
        PillButton(entry_row, "↩ Envoyer", command=send_comment,
                   color=SURFACE2, fg=ACCENT2, width=100, height=28).pack(side="right", padx=4)

    # ─── PROFILE PAGE ──────────────────────────────────────
    def _build_profile_page(self):
        page = tk.Frame(self._container, bg=BG)
        self._pages["profile"] = page
        self._profile_content = tk.Frame(page, bg=BG)
        self._profile_content.pack(fill="both", expand=True)

    def _open_profile(self, username):
        for w in self._profile_content.winfo_children():
            w.destroy()

        # Back button
        back = tk.Frame(self._profile_content, bg=BG)
        back.pack(fill="x", padx=60, pady=(24, 0))
        back_btn = tk.Label(back, text="← Retour au fil", font=FONT_BODY,
                             bg=BG, fg=MUTED, cursor="hand2")
        back_btn.pack(side="left")
        back_btn.bind("<Button-1>", lambda e: self._show_page("feed"))
        back_btn.bind("<Enter>", lambda e: back_btn.config(fg=ACCENT2))
        back_btn.bind("<Leave>", lambda e: back_btn.config(fg=MUTED))

        # Card
        card = tk.Frame(self._profile_content, bg=SURFACE)
        card.pack(fill="x", padx=60, pady=16)
        card.configure(highlightbackground=BORDER, highlightthickness=1)

        inner = tk.Frame(card, bg=SURFACE, pady=28)
        inner.pack(fill="x", padx=28)

        Avatar(inner, username, size=64).pack()
        tk.Label(inner, text=username, font=("Segoe UI", 20, "bold"),
                 bg=SURFACE, fg=TEXT).pack(pady=(12, 4))
        tk.Label(inner, text="Membre SafeNET 💙", font=FONT_BODY,
                 bg=SURFACE, fg=MUTED).pack()

        c.execute("SELECT COUNT(*) FROM posts WHERE user=?", (username,))
        n_posts = c.fetchone()[0]
        c.execute("SELECT COALESCE(SUM(likes),0) FROM posts WHERE user=?", (username,))
        n_likes = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM comments WHERE user=?", (username,))
        n_comments = c.fetchone()[0]

        stats = tk.Frame(inner, bg=SURFACE)
        stats.pack(pady=16)
        for val, label in [(n_posts, "posts"), (n_likes, "❤️ reçus"), (n_comments, "commentaires")]:
            pill = tk.Frame(stats, bg=SURFACE2, padx=16, pady=6)
            pill.pack(side="left", padx=6)
            tk.Label(pill, text=str(val), font=FONT_BOLD, bg=SURFACE2, fg=TEXT).pack()
            tk.Label(pill, text=label, font=FONT_SMALL, bg=SURFACE2, fg=MUTED).pack()

        # Posts by user
        c.execute("SELECT text, likes, ts FROM posts WHERE user=? ORDER BY id DESC", (username,))
        user_posts = c.fetchall()

        if user_posts:
            tk.Label(self._profile_content, text="POSTS DE CET UTILISATEUR",
                     font=("Segoe UI", 9, "bold"), bg=BG, fg=MUTED).pack(
                     anchor="w", padx=60, pady=(8, 6))
            sf = ScrollFrame(self._profile_content, bg=BG)
            sf.pack(fill="both", expand=True, padx=60, pady=(0, 16))
            for txt, lks, ts in user_posts:
                pf = tk.Frame(sf.inner, bg=SURFACE)
                pf.pack(fill="x", pady=(0, 8))
                pf.configure(highlightbackground=BORDER, highlightthickness=1)
                tk.Label(pf, text=txt, font=FONT_BODY, bg=SURFACE, fg=TEXT,
                         wraplength=560, justify="left", padx=16, pady=10).pack(anchor="w")
                tk.Label(pf, text=f"❤️ {lks}   💬   {ts}",
                         font=FONT_SMALL, bg=SURFACE, fg=MUTED, padx=16, pady=6).pack(anchor="w")

        self._show_page("profile")

    # ─── AIDE PAGE ─────────────────────────────────────────
    def _build_aide_page(self):
        page = tk.Frame(self._container, bg=BG)
        self._pages["aide"] = page

        sf = ScrollFrame(page, bg=BG)
        sf.pack(fill="both", expand=True)
        inner = sf.inner

        tk.Frame(inner, bg=BG, height=32).pack()
        tk.Label(inner, text="🆘  Aide & Urgences", font=FONT_TITLE,
                 bg=BG, fg=TEXT).pack(anchor="w", padx=100)
        tk.Label(inner, text="En Belgique, ces numéros sont disponibles 24h/24. N'hésitez jamais à appeler.",
                 font=FONT_BODY, bg=BG, fg=MUTED).pack(anchor="w", padx=100, pady=(6, 24))

        tk.Label(inner, text="NUMÉROS D'URGENCE", font=("Segoe UI", 9, "bold"),
                 bg=BG, fg=MUTED).pack(anchor="w", padx=100, pady=(0, 10))

        urgences = [
            ("🚑", RED,    "#2a1520", "112",           "Urgences médicales",          "Ambulance, pompiers, secours immédiats"),
            ("🚔", "#3b82f6", "#121824", "101",         "Police secours",              "Intervention policière d'urgence"),
        ]

        soutien = [
            ("💜", ACCENT2, "#1a1730", "0800 32 123",  "Centre Prévention du Suicide", "Écoute anonyme, gratuit 24h/24"),
            ("🤝", GREEN,   "#0f2320", "0800 35 080",  "Télé-Accueil",                "Parlez à quelqu'un, n'importe quand"),
            ("👂", YELLOW,  "#231d10", "02 512 90 20", "SOS Jeunes",                  "Aide spécialisée pour les jeunes"),
        ]

        for items, section_label in [(urgences, None), (soutien, "SOUTIEN PSYCHOLOGIQUE")]:
            if section_label:
                tk.Label(inner, text=section_label, font=("Segoe UI", 9, "bold"),
                         bg=BG, fg=MUTED).pack(anchor="w", padx=100, pady=(20, 10))
            for emoji, fg_color, bg_color, number, title, desc in items:
                row = tk.Frame(inner, bg=SURFACE)
                row.pack(fill="x", padx=100, pady=(0, 8))
                row.configure(highlightbackground=BORDER, highlightthickness=1)

                # Icon
                icon_frame = tk.Frame(row, bg=bg_color, width=64, height=64)
                icon_frame.pack(side="left")
                icon_frame.pack_propagate(False)
                tk.Label(icon_frame, text=emoji, font=("Segoe UI", 22),
                         bg=bg_color).place(relx=0.5, rely=0.5, anchor="center")

                # Text
                info = tk.Frame(row, bg=SURFACE, padx=16, pady=12)
                info.pack(side="left", fill="both", expand=True)
                tk.Label(info, text=title, font=FONT_BOLD, bg=SURFACE, fg=TEXT).pack(anchor="w")
                tk.Label(info, text=desc, font=FONT_SMALL, bg=SURFACE, fg=MUTED).pack(anchor="w")

                # Number
                tk.Label(row, text=number, font=FONT_MONO, bg=SURFACE,
                         fg=fg_color, padx=20).pack(side="right")

        tk.Frame(inner, bg=BG, height=20).pack()

        # SOS button
        sos_outer = tk.Frame(inner, bg=BG)
        sos_outer.pack(padx=100, fill="x")
        PillButton(sos_outer, "🆘  Alerter mes proches — SOS",
                   command=self._sos_action,
                   color=RED, fg=WHITE, width=400, height=46,
                   font=("Segoe UI", 12, "bold")).pack(fill="x")
        tk.Frame(inner, bg=BG, height=32).pack()

    def _sos_action(self):
        messagebox.showinfo(
            "SafeNET — SOS",
            "En cas d'urgence immédiate :\n\n"
            "🚑  Urgences médicales : 112\n"
            "🚔  Police : 101\n"
            "💜  Prévention Suicide : 0800 32 123\n\n"
            "Vous n'êtes pas seul·e. 💙"
        )

    # ─── TOAST ─────────────────────────────────────────────
    def _toast(self, msg, kind="success"):
        color = GREEN if kind == "success" else RED
        toast = tk.Label(self, text=f"  {msg}  ", font=FONT_SMALL,
                         bg=SURFACE2, fg=color, pady=8, padx=4)
        toast.place(relx=1.0, rely=1.0, anchor="se", x=-24, y=-24)
        self.after(2600, toast.destroy)

    # ─── BOT LOOP ──────────────────────────────────────────
    def _bot_loop(self):
        bots = {
            "Alex":  {"rate": 0.35, "style": ["Courage 💙", "Force à toi ✊", "Je te comprends"]},
            "Maya":  {"rate": 0.65, "style": ["Incroyable ✨", "Trop bien 🔥", "Bravo !"]},
            "Liam":  {"rate": 0.45, "style": ["Intéressant 👀", "Je comprends tout à fait"]},
            "Sofia": {"rate": 0.55, "style": ["Je suis avec toi 💙", "🫶", "On est là"]},
            "Emma":  {"rate": 0.75, "style": ["Wow 😍", "🔥 vraiment !", "Super !"]},
            "Noah":  {"rate": 0.30, "style": ["💙", "🙏", "Merci de partager ça"]},
        }

        c.execute("SELECT id FROM posts")
        posts = c.fetchall()

        if posts:
            pid = random.choice(posts)[0]
            changed = False
            for name, data in bots.items():
                if random.random() < data["rate"]:
                    if random.random() < 0.45:
                        c.execute("INSERT OR IGNORE INTO likes VALUES (?,?)", (pid, name))
                        if c.rowcount:
                            c.execute("UPDATE posts SET likes = likes+1 WHERE id=?", (pid,))
                            changed = True
                    else:
                        c.execute("INSERT INTO comments (post_id, user, text) VALUES (?,?,?)",
                                  (pid, name, random.choice(data["style"])))
                        changed = True
            conn.commit()
            if changed and self._active_page == "feed":
                self._refresh_feed()

        delay = random.randint(3000, 7000)
        self.after(delay, self._bot_loop)


# ═══════════════════════════════════════════════════════════
#  LAUNCH
# ═══════════════════════════════════════════════════════════
if __name__ == "__main__":
    app = SafeNetApp()
    app.mainloop()