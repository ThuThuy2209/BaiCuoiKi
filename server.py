import tkinter as tk
from tkinter import scrolledtext
import socket
import threading
import mysql.connector
from datetime import datetime

HOST = '127.0.0.1'
PORT = 5555

clients = []
nicknames = []
server_socket = None
running = False

# ------------------ Database ------------------
def get_db():
    return mysql.connector.connect(
        host="localhost",
        user="root",        # mặc định XAMPP user là root
        password="",        # mặc định không có password
        database="chat_app" # tên database bạn đã tạo
    )

def save_message(sender: str, content: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO messages (sender, content, timestamp) VALUES (%s, %s, %s)", 
        (sender, content, ts)
    )
    conn.commit()
    cursor.close()
    conn.close()

def load_recent_messages(limit=20):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT sender, content, timestamp FROM messages ORDER BY id DESC LIMIT %s", (limit,))
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return rows[::-1]  # đảo ngược để tin cũ lên trước

# ---------------- SERVER LOGIC ----------------
def broadcast(message, exclude_client=None):
    for client in clients:
        if client != exclude_client:
            try:
                client.send(message.encode("utf-8"))
            except:
                pass

def handle_client(client):
    while running:
        try:
            msg = client.recv(1024).decode("utf-8")
            if msg:
                if msg.startswith("TYPING|"):
                    # Broadcast typing state tới các client khác
                    broadcast(msg, exclude_client=client)
                else:
                    idx = clients.index(client)
                    sender = nicknames[idx]
                    full_msg = f"{sender}: {msg}"
                    log(f"[CHAT] {full_msg}")
                    save_message(sender, msg)  # lưu MySQL
                    broadcast(full_msg, exclude_client=client)
        except:
            # nếu lỗi hoặc client ngắt kết nối
            if client in clients:
                idx = clients.index(client)
                nickname = nicknames[idx]
                client.close()
                log(f"❌ {nickname} đã ngắt kết nối.")
                clients.remove(client)
                nicknames.remove(nickname)
                update_client_list()
                broadcast(f"PRESENCE|{nickname}|offline")
            break

def accept_clients():
    while running:
        try:
            client, addr = server_socket.accept()
            nickname = client.recv(1024).decode("utf-8")
            clients.append(client)
            nicknames.append(nickname)
            log(f"✅ {nickname} đã kết nối từ {addr}")
            update_client_list()

            # Gửi 20 tin nhắn gần nhất cho client mới
            for sender, content, ts in load_recent_messages():
                try:
                    client.send(f"HISTORY|{sender}|{content}|{ts}".encode("utf-8"))
                except:
                    pass

            # Thông báo presence
            broadcast(f"PRESENCE|{nickname}|online", exclude_client=client)
            threading.Thread(target=handle_client, args=(client,), daemon=True).start()
        except:
            break

# ---------------- GUI CONTROL ----------------
def start_server():
    global server_socket, running
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((HOST, PORT))
    server_socket.listen()
    running = True
    log(f"[SERVER] Đang chạy trên {HOST}:{PORT}")
    threading.Thread(target=accept_clients, daemon=True).start()
    start_btn.config(state=tk.DISABLED)
    stop_btn.config(state=tk.NORMAL)

def stop_server():
    global running
    running = False
    for client in clients:
        client.close()
    if server_socket:
        server_socket.close()
    clients.clear()
    nicknames.clear()
    update_client_list()
    log("[SERVER] Đã dừng.")
    start_btn.config(state=tk.NORMAL)
    stop_btn.config(state=tk.DISABLED)

def log(message):
    log_box.config(state=tk.NORMAL)
    log_box.insert(tk.END, message + "\n")
    log_box.config(state=tk.DISABLED)
    log_box.yview(tk.END)

def update_client_list():
    client_list_box.delete(0, tk.END)
    for name in nicknames:
        client_list_box.insert(tk.END, name)

# ---------------- GUI ----------------
root = tk.Tk()
root.title("Server Chat GUI")

frame_top = tk.Frame(root)
frame_top.pack(pady=5)

start_btn = tk.Button(frame_top, text="Bắt đầu Server", command=start_server, bg="green", fg="white")
start_btn.pack(side=tk.LEFT, padx=5)

stop_btn = tk.Button(frame_top, text="Dừng Server", command=stop_server, bg="red", fg="white", state=tk.DISABLED)
stop_btn.pack(side=tk.LEFT, padx=5)

frame_main = tk.Frame(root)
frame_main.pack()

log_box = scrolledtext.ScrolledText(frame_main, wrap=tk.WORD, state=tk.DISABLED, width=60, height=20)
log_box.grid(row=0, column=0, padx=5, pady=5)

client_list_box = tk.Listbox(frame_main, width=20, height=20)
client_list_box.grid(row=0, column=1, padx=5, pady=5)

root.mainloop()