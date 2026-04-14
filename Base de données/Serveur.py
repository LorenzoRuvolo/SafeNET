from fastapi import FastAPI, WebSocket
import sqlite3
import json

app = FastAPI()

conn = sqlite3.connect("safenet.db", check_same_thread=False)
c = conn.cursor()

c.execute("""CREATE TABLE IF NOT EXISTS users (name TEXT UNIQUE)""")
c.execute("""CREATE TABLE IF NOT EXISTS posts (id INTEGER PRIMARY KEY, user TEXT, text TEXT, likes INTEGER)""")
conn.commit()

clients = []

# ================= POSTS =================
@app.get("/posts")
def get_posts():
    c.execute("SELECT * FROM posts ORDER BY id DESC")
    return c.fetchall()

@app.post("/post")
def add_post(data: dict):
    c.execute("INSERT INTO posts (user, text, likes) VALUES (?, ?, 0)",
              (data["user"], data["text"]))
    conn.commit()
    return {"ok": True}

@app.post("/like")
def like_post(data: dict):
    c.execute("UPDATE posts SET likes = likes + 1 WHERE id = ?", (data["id"],))
    conn.commit()
    return {"ok": True}

@app.post("/register")
def register(user: dict):
    try:
        c.execute("INSERT INTO users VALUES (?)", (user["name"],))
        conn.commit()
    except:
        pass
    return {"ok": True}

# ================= CHAT REALTIME =================
@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    clients.append(ws)

    try:
        while True:
            msg = await ws.receive_text()

            for cws in clients:
                await cws.send_text(msg)

    except:
        clients.remove(ws)

