import tkinter as tk
from tkinter import scrolledtext
import socket
import threading

HOST = '127.0.0.1'
PORT = 5555

clients = []
nicknames = []
server_socket = None
running = False

# ---------------- SERVER LOGIC ----------------
def broadcast(message, sender=None):
    for client in clients:
        try:
            client.send(message.encode("utf-8"))
        except:
            pass

def handle_client(client):
    while running:
        try:
            msg = client.recv(1024).decode("utf-8")
            if msg:
                idx = clients.index(client)
                full_msg = f"{nicknames[idx]}: {msg}"
                log(f"[CHAT] {full_msg}")
                broadcast(full_msg)
        except:
            idx = clients.index(client)
            client.close()
            nickname = nicknames[idx]
            log(f"❌ {nickname} đã ngắt kết nối.")
            clients.remove(client)
            nicknames.remove(nickname)
            update_client_list()
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
            broadcast(f"🔔 {nickname} đã tham gia phòng chat!")
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
