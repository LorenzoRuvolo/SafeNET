from tkinter import *
from tkinter import messagebox
import sqlite3
from datetime import datetime
import random

# ================= APP =================
app = Tk()
app.title("SafeNET")
app.state("zoomed")
app.resizable(False, False)

BG = "#667eea"
CARD = "#ffffff"
RED = "#ff4d6d"
TEXT = "#222"

app.configure(bg=BG)

# ================= DB =================
conn = sqlite3.connect("safenet.db")
c = conn.cursor()

c.execute("""CREATE TABLE IF NOT EXISTS posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user TEXT,
    text TEXT,
    likes INTEGER,
    time TEXT
)""")

c.execute("""CREATE TABLE IF NOT EXISTS comments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id INTEGER,
    user TEXT,
    text TEXT
)""")

c.execute("""CREATE TABLE IF NOT EXISTS users (
    username TEXT PRIMARY KEY,
    bio TEXT,
    created_at TEXT
)""")

conn.commit()

# ================= USER =================
user = "Anonyme"

def set_user():
    global user
    user = name_entry.get() or "Anonyme"

    c.execute("INSERT OR IGNORE INTO users VALUES (?, ?, ?)",
              (user, "Salut 👋", datetime.now().strftime("%Y-%m-%d")))
    conn.commit()

    messagebox.showinfo("SafeNET", f"Connecté : {user}")

# ================= BUTTON =================
def btn(p, t, cmd):
    b = Button(p, text=t, command=cmd,
               bg="white", fg="#222",
               relief="flat", bd=0,
               padx=14, pady=8,
               font=("Segoe UI", 10, "bold"),
               cursor="hand2")
    b.bind("<Enter>", lambda e: b.config(bg="#eaeaea"))
    b.bind("<Leave>", lambda e: b.config(bg="white"))
    return b

# ================= BOTS =================
bots = {
    "Alex": {"rate": 0.4, "style": ["Courage 💙", "Force à toi"]},
    "Maya": {"rate": 0.7, "style": ["Incroyable ✨", "Trop bien 🔥"]},
    "Liam": {"rate": 0.5, "style": ["Ok 👍", "Je comprends"]},
    "Sofia": {"rate": 0.6, "style": ["Je suis avec toi 💙", "🫶"]},
    "Emma": {"rate": 0.8, "style": ["Wow 😍", "🔥"]},
    "Noah": {"rate": 0.3, "style": ["💙", "🙏"]}
}

# ================= BOT LOOP =================
def bot_loop():
    c.execute("SELECT id FROM posts")
    posts = c.fetchall()

    if posts:
        pid = random.choice(posts)[0]

        for n, d in bots.items():
            if random.random() < d["rate"]:
                if random.random() < 0.5:
                    c.execute("UPDATE posts SET likes = likes + 1 WHERE id=?", (pid,))
                else:
                    c.execute("INSERT INTO comments VALUES (NULL, ?, ?, ?)",
                              (pid, n, random.choice(d["style"])))

    conn.commit()
    refresh_feed()
    app.after(random.randint(3000, 6000), bot_loop)

# ================= PROFILE =================
def open_profile(u):
    profil_frame.tkraise()

    for w in profil_frame.winfo_children():
        w.destroy()

    c.execute("SELECT bio FROM users WHERE username=?", (u,))
    bio = c.fetchone()
    bio = bio[0] if bio else "Pas de bio"

    c.execute("SELECT COUNT(*) FROM posts WHERE user=?", (u,))
    posts = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM comments WHERE user=?", (u,))
    comments = c.fetchone()[0]

    Label(profil_frame, text=u, bg=BG, fg="white",
          font=("Segoe UI", 28, "bold")).pack(pady=20)

    Label(profil_frame, text=bio, bg=BG, fg="white").pack()
    Label(profil_frame, text=f"Posts: {posts}", bg=BG, fg="white").pack()
    Label(profil_frame, text=f"Comments: {comments}", bg=BG, fg="white").pack()

    btn(profil_frame, "⬅ Retour", lambda: show(accueil)).pack(pady=20)

# ================= NAVBAR (FIXED) =================
nav = Frame(app, bg="white", height=70)
nav.pack(fill="x", side=TOP)

btn(nav, "🏠 Accueil", lambda: show(accueil)).pack(side=LEFT, padx=5)
btn(nav, "➕ Créer", lambda: show(creer)).pack(side=LEFT, padx=5)
btn(nav, "ℹ️ Aide", lambda: show(aide)).pack(side=LEFT, padx=5)

name_entry = Entry(nav)
name_entry.pack(side=RIGHT, padx=10)

btn(nav, "OK", set_user).pack(side=RIGHT, padx=5)

# ================= PAGES =================
container = Frame(app, bg=BG)
container.pack(fill="both", expand=True)

accueil = Frame(container, bg=BG)
creer = Frame(container, bg=BG)
aide = Frame(container, bg=BG)
profil_frame = Frame(container, bg=BG)

for f in (accueil, creer, aide, profil_frame):
    f.place(relwidth=1, relheight=1)

def show(frame):
    frame.tkraise()
    if frame == accueil:
        refresh_feed()

# ================= FEED =================
canvas = Canvas(accueil, bg=BG)
scroll = Scrollbar(accueil, command=canvas.yview)
feed = Frame(canvas, bg=BG)

feed.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

canvas.create_window((0, 0), window=feed, anchor="nw")
canvas.configure(yscrollcommand=scroll.set)

canvas.pack(side=LEFT, fill="both", expand=True)
scroll.pack(side=RIGHT, fill="y")

# ================= FEED =================
def refresh_feed():
    for w in feed.winfo_children():
        w.destroy()

    c.execute("SELECT * FROM posts ORDER BY id DESC")
    for pid, u, text, likes, time in c.fetchall():

        box = Frame(feed, bg=CARD, padx=15, pady=10)
        box.pack(fill="x", padx=100, pady=10)

        Label(box, text=f"{u} • {time}",
              bg=CARD, fg="gray",
              cursor="hand2",
              font=("Segoe UI", 10, "bold")).pack(anchor="w")

        Label(box, text=text,
              bg=CARD, fg=TEXT,
              font=("Segoe UI", 12)).pack(anchor="w")

        def like(p=pid):
            c.execute("UPDATE posts SET likes = likes + 1 WHERE id=?", (p,))
            conn.commit()
            refresh_feed()

        Button(box, text=f"❤️ {likes}",
               bg=RED, fg="white",
               command=like).pack(anchor="w")

        c.execute("SELECT user, text FROM comments WHERE post_id=?", (pid,))
        for cu, ct in c.fetchall():
            Label(box, text=f"↳ {cu}: {ct}",
                  bg=CARD, fg="#555").pack(anchor="w")

        entry = Entry(box)
        entry.pack(side=LEFT)

        def add(p=pid, e=entry):
            if e.get().strip():
                c.execute("INSERT INTO comments VALUES (NULL, ?, ?, ?)",
                          (p, user, e.get()))
                conn.commit()
                refresh_feed()

        Button(box, text="💬", command=add).pack(side=LEFT)

        # CLICK PROFILE
        box.bind("<Button-1>", lambda e, name=u: open_profile(name))

# ================= CREATE =================
Label(creer, text="Créer un post",
      bg=BG, fg="white",
      font=("Segoe UI", 26, "bold")).pack(pady=50)

entry_post = Entry(creer, width=50)
entry_post.pack()

def publish():
    if entry_post.get().strip():
        c.execute("INSERT INTO posts VALUES (NULL, ?, ?, 0, ?)",
                  (user, entry_post.get(), datetime.now().strftime("%H:%M")))
        conn.commit()
        entry_post.delete(0, END)
        show(accueil)

Button(creer, text="🚀 Publier",
       bg="#5a4bd6", fg="white",
       command=publish).pack(pady=10)

# ================= AIDE =================
Label(aide, text="Aide Belgique",
      bg=BG, fg="white",
      font=("Segoe UI", 26, "bold")).pack(pady=50)

for n in ["112 Urgence", "101 Police", "0800 32 123 Écoute"]:
    Label(aide, text=n, bg=BG, fg="white").pack()

Button(aide, text="🆘 SOS",
       bg=RED, fg="white").pack(pady=20)

# ================= START =================
show(accueil)
app.after(4000, bot_loop)
app.mainloop()