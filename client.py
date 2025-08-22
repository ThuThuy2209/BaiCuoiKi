import tkinter as tk
from tkinter import scrolledtext
import socket
import threading
from datetime import datetime

HOST = '127.0.0.1'
PORT = 5555

client_socket = None
running = False

def connect_server():
    global client_socket, running
    username = name_entry.get().strip()
    if not username:
        log("[CLIENT] Vui lòng nhập tên:")
        return
    try:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect((HOST, PORT))
        client_socket.send(username.encode('utf-8'))
        running = True
        log(f"[CLIENT] Đã kết nối tới server.")
        threading.Thread(target=receive_messages, daemon=True).start()
        connect_btn.config(state=tk.DISABLED)
        disconnect_btn.config(state=tk.NORMAL)
        msg_entry.focus()
    except Exception as e:
        log(f"[ERROR] Không thể kết nối: {e}")

def disconnect_server():
    global running
    running = False
    if client_socket:
        try:
            client_socket.shutdown(socket.SHUT_RDWR)
            client_socket.close()
        except:
            pass
    log("[CLIENT] Đã ngắt kết nối.")
    connect_btn.config(state=tk.NORMAL)
    disconnect_btn.config(state=tk.DISABLED)

def send_message():
    if not running:
        log("[CLIENT] Bạn chưa kết nối tới server.")
        return
    msg = msg_entry.get("1.0", tk.END).strip()  # Lấy text từ Text widget
    if msg:
        try:
            client_socket.send(msg.encode('utf-8'))
            msg_entry.delete("1.0", tk.END)  # Xóa toàn bộ sau khi gửi
            msg_entry.mark_set("insert", "1.0")
        except:
            log("[CLIENT] Lỗi khi gửi tin nhắn.")

def receive_messages():
    global running
    while running:
        try:
            message = client_socket.recv(1024).decode('utf-8')
            if not message:  # server đóng kết nối
                log("[CLIENT] Mất kết nối với server.")
                disconnect_server()
                connect_btn.config(state=tk.NORMAL)
                disconnect_btn.config(state=tk.DISABLED)
                break
            log(message)
        except Exception as e:
            log(f"[ERROR] Lỗi khi nhận tin nhắn: {e}")
            break

def log(message):
    timestamp = datetime.now().strftime("%H:%M:%S")
    chat_box.config(state=tk.NORMAL)

    if ":" in message:
        sender, content = message.split(":", 1)
        sender = sender.strip()
        content = content.strip()
        if sender == name_entry.get().strip():
            chat_box.insert(tk.END, f"[{timestamp}] Bạn: {content}\n", "self")
        else:
            chat_box.insert(tk.END, f"[{timestamp}] {sender}: {content}\n", "other")
    else:
        chat_box.insert(tk.END, f"[{timestamp}] {message}\n")

    chat_box.config(state=tk.DISABLED)
    chat_box.yview(tk.END)


# ---------------- GUI ----------------
root = tk.Tk()
root.title("Client Chat")

frame_top = tk.Frame(root)
frame_top.pack(pady=5)

tk.Label(frame_top, text="Tên:").pack(side=tk.LEFT)
name_entry = tk.Entry(frame_top)
name_entry.pack(side=tk.LEFT, padx=5)

connect_btn = tk.Button(frame_top, text="Kết nối", command=connect_server)
connect_btn.pack(side=tk.LEFT, padx=5)

disconnect_btn = tk.Button(frame_top, text="Ngắt", command=disconnect_server, state=tk.DISABLED)
disconnect_btn.pack(side=tk.LEFT, padx=5)

chat_box = scrolledtext.ScrolledText(root, wrap=tk.WORD, state=tk.DISABLED, width=50, height=20)
chat_box.pack(padx=5, pady=5)
chat_box.tag_config("self", foreground="blue")
chat_box.tag_config("other", foreground="green")


frame_bottom = tk.Frame(root)
frame_bottom.pack(pady=5)

msg_entry = tk.Text(frame_bottom, width=40,height=3)
msg_entry.pack(side=tk.LEFT, padx=5)

def on_Enter(event):
    if event.state & 0x0001:  # Shift
        msg_entry.insert(tk.INSERT, "\n")
    else:
        send_message()
    return "break"

msg_entry.bind("<Return>", on_Enter)
send_btn = tk.Button(frame_bottom, text="Gửi", command=send_message)
send_btn.pack(side=tk.LEFT)

def on_close():
    disconnect_server()
    root.destroy()

root.protocol("WM_DELETE_WINDOW", on_close)

root.mainloop()
