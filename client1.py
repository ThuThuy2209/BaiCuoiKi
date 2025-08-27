import tkinter as tk
from tkinter import messagebox
import socket
import threading
from datetime import datetime

HOST = '127.0.0.1'
PORT = 5555

class ChatClientApp:
    """Tkinter chat client with Messenger-like chat bubbles,
    plus typing indicator and online presence list (Step 2+3).
    """

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Client Chat — Bubble UI")
        self.client_socket: socket.socket | None = None
        self.running = False
        self.typing_timer = None

        # Top controls
        top = tk.Frame(root)
        top.pack(fill=tk.X, pady=6)
        tk.Label(top, text="Tên:").pack(side=tk.LEFT)
        self.name_entry = tk.Entry(top)
        self.name_entry.pack(side=tk.LEFT, padx=6)
        self.connect_btn = tk.Button(top, text="Kết nối", command=self.connect_server)
        self.connect_btn.pack(side=tk.LEFT, padx=4)
        self.disconnect_btn = tk.Button(top, text="Ngắt", command=self.disconnect_server, state=tk.DISABLED)
        self.disconnect_btn.pack(side=tk.LEFT, padx=4)

        # Middle: messages + presence
        mid = tk.Frame(root)
        mid.pack(fill=tk.BOTH, expand=True)

        # Left: chat area (canvas)
        chat_area = tk.Frame(mid)
        chat_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(chat_area, highlightthickness=0, bg="#ffffff")
        self.vsb = tk.Scrollbar(chat_area, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.vsb.set)
        self.vsb.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.messages_frame = tk.Frame(self.canvas, bg="#ffffff")
        self.canvas.create_window((0, 0), window=self.messages_frame, anchor="nw")

        self.messages_frame.bind("<Configure>", lambda e: self._on_frame_configure())
        self.canvas.bind("<Configure>", lambda e: self._on_canvas_resize())

        # Right: online list
        right = tk.Frame(mid, width=150)
        right.pack(side=tk.RIGHT, fill=tk.Y)
        tk.Label(right, text="Đang online", font=(None, 10, "bold")).pack(pady=(6,0))
        self.online_listbox = tk.Listbox(right, width=20, height=20)
        self.online_listbox.pack(padx=6, pady=6, fill=tk.Y, expand=True)

        # Typing indicator under chat
        self.typing_label = tk.Label(root, text="", fg="gray", bg="#ffffff", font=(None, 9, "italic"))
        self.typing_label.pack(fill=tk.X, padx=8, pady=(0,4))

        # Bottom input
        bottom = tk.Frame(root)
        bottom.pack(fill=tk.X, pady=6)
        self.msg_entry = tk.Text(bottom, width=1, height=3)
        self.msg_entry.pack(side=tk.LEFT, padx=6, fill=tk.X, expand=True)
        self.msg_entry.bind("<Return>", self._on_enter)
        self.msg_entry.bind("<KeyPress>", self._on_keypress)
        self.send_btn = tk.Button(bottom, text="Gửi", command=self.send_message)
        self.send_btn.pack(side=tk.LEFT, padx=4)

        # Initial system message
        self._add_system("Chào mừng! Nhập tên và Kết nối để bắt đầu.")

        # Close protocol
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ---------------- Networking ----------------
    def connect_server(self) -> None:
        username = self.name_entry.get().strip()
        if not username:
            self._add_system("[CLIENT] Vui lòng nhập tên.")
            return
        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.connect((HOST, PORT))
            # send username as first message
            self.client_socket.send(username.encode('utf-8'))
            self.running = True
            self._add_system("[CLIENT] Đã kết nối tới server.")
            threading.Thread(target=self._receive_loop, daemon=True).start()
            self.connect_btn.config(state=tk.DISABLED)
            self.disconnect_btn.config(state=tk.NORMAL)
            self.msg_entry.focus()
            # notify presence locally until server broadcasts
            self._update_presence_local(username, online=True)
        except Exception as e:
            self._add_system(f"[ERROR] Không thể kết nối: {e}")

    def disconnect_server(self) -> None:
        self.running = False
        if self.client_socket:
            try:
                self.client_socket.shutdown(socket.SHUT_RDWR)
                self.client_socket.close()
            except Exception:
                pass
            self.client_socket = None
        self._add_system("[CLIENT] Đã ngắt kết nối.")
        self.connect_btn.config(state=tk.NORMAL)
        self.disconnect_btn.config(state=tk.DISABLED)
        # clear online list
        self.online_listbox.delete(0, tk.END)

    def send_message(self) -> None:
        if not self.running or not self.client_socket:
            self._add_system("[CLIENT] Bạn chưa kết nối tới server.")
            return
        msg = self.msg_entry.get("1.0", tk.END).strip()
        if msg:
            try:
                self.client_socket.send(msg.encode('utf-8'))
                self.msg_entry.delete("1.0", tk.END)
                self.msg_entry.mark_set("insert", "1.0")
                # after sending a message, also stop typing state
                self._send_typing(0)
            except Exception:
                self._add_system("[CLIENT] Lỗi khi gửi tin nhắn.")

    def _receive_loop(self) -> None:
        while self.running and self.client_socket:
            try:
                data = self.client_socket.recv(1024)
                if not data:
                    self._after(lambda: self._add_system("[CLIENT] Mất kết nối với server."))
                    self._after(self.disconnect_server)
                    break
                message = data.decode('utf-8')
                # handle special messages
                if message.startswith("TYPING|"):
                    try:
                        _, user, state = message.split("|", 2)
                        if user != self.name_entry.get().strip():
                            if state == "1":
                                self._after(lambda u=user: self.typing_label.config(text=f"{u} đang nhập..."))
                            else:
                                self._after(lambda: self.typing_label.config(text=""))
                    except Exception:
                        pass
                    continue

                if message.startswith("PRESENCE|"):
                    # PRESENCE|username|online/offline
                    try:
                        _, user, state = message.split("|", 2)
                        online = state == "online"
                        self._after(lambda u=user, o=online: self._update_presence_local(u, o))
                    except Exception:
                        pass
                    continue

                # normal chat message
                self._after(lambda m=message: self._log_message(m))

            except Exception as e:
                self._after(lambda: self._add_system(f"[ERROR] Lỗi khi nhận tin nhắn: {e}"))
                break

    # ---------------- UI helpers ----------------
    def _after(self, fn) -> None:
        self.root.after(0, fn)

    def _on_enter(self, event) -> str:
        if event.state & 0x0001:  # Shift to newline
            self.msg_entry.insert(tk.INSERT, "")
        else:
            self.send_message()
        return "break"

    def _on_frame_configure(self) -> None:
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        self._update_wrap_lengths()
        self._scroll_to_end()

    def _on_canvas_resize(self) -> None:
        self._update_wrap_lengths()

    def _scroll_to_end(self) -> None:
        self.canvas.yview_moveto(1.0)

    def _bubble_wrap_width(self) -> int:
        w = self.canvas.winfo_width() or 480
        return max(180, min(420, w - 140))

    def _update_wrap_lengths(self) -> None:
        wrap = self._bubble_wrap_width()
        for child in self.messages_frame.winfo_children():
            lbl = getattr(child, "_bubble_label", None)
            if isinstance(lbl, tk.Label):
                lbl.configure(wraplength=wrap)

    # ---------------- Message rendering ----------------
    def _log_message(self, message: str) -> None:
        timestamp = datetime.now().strftime("%H:%M")
        if message.startswith("["):
            self._add_system(message)
            return
        if ":" in message:
            sender, content = message.split(":", 1)
            sender = sender.strip()
            content = content.strip()
            is_self = (sender == self.name_entry.get().strip())
            self._add_message(sender, content, timestamp, is_self)
        else:
            self._add_system(message)

    def _add_system(self, text: str) -> None:
        row = tk.Frame(self.messages_frame, bg="#ffffff")
        row.pack(fill=tk.X, pady=4)
        lab = tk.Label(row, text=text, fg="#666", bg="#f2f2f2", padx=12, pady=6)
        lab.pack(padx=8, pady=2)
        self._scroll_to_end()

    def _add_message(self, sender: str, content: str, ts: str, is_self: bool) -> None:
        row = tk.Frame(self.messages_frame, bg="#ffffff")
        row.pack(fill=tk.X, pady=4, padx=6)

        bubble_bg = "#DCF8C6" if is_self else "#FFFFFF"
        bubble_fg = "#111111"
        time_fg = "#666666"

        avatar = self._avatar_widget(row, sender)

        bubble = tk.Label(
            row,
            text=content,
            justify=tk.LEFT,
            anchor="w",
            bg=bubble_bg,
            fg=bubble_fg,
            padx=10,
            pady=6,
            bd=0,
            wraplength=self._bubble_wrap_width(),
        )
        row._bubble_label = bubble

        time_label = tk.Label(row, text=ts, fg=time_fg, bg=self.root['bg'])

        if is_self:
            bubble.pack(side=tk.RIGHT, padx=(8, 6))
            avatar.pack(side=tk.RIGHT, padx=(0, 6))
            time_label.pack(anchor="e", padx=8)
        else:
            avatar.pack(side=tk.LEFT, padx=(6, 8))
            bubble.pack(side=tk.LEFT, padx=(6, 8))
            time_label.pack(anchor="w", padx=8)

        self._scroll_to_end()

    # ---------------- Avatar ----------------
    def _avatar_widget(self, parent: tk.Widget, name: str) -> tk.Canvas:
        initials = self._initials(name)
        color = self._name_color(name)
        size = 28
        c = tk.Canvas(parent, width=size, height=size, highlightthickness=0, bg=self.root['bg'])
        c.create_oval(2, 2, size-2, size-2, fill=color, outline=color)
        c.create_text(size/2, size/2, text=initials, fill="white", font=("Helvetica", 9, "bold"))
        return c

    @staticmethod
    def _initials(name: str) -> str:
        parts = [p for p in name.strip().split() if p]
        if not parts:
            return "?"
        if len(parts) == 1:
            return parts[0][:2].upper()
        return (parts[0][0] + parts[-1][0]).upper()

    @staticmethod
    def _name_color(name: str) -> str:
        h = sum(ord(ch) for ch in name) % 360
        s = 0.55
        l = 0.55
        r, g, b = ChatClientApp._hsl_to_rgb(h/360.0, s, l)
        return f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}"

    @staticmethod
    def _hsl_to_rgb(h: float, s: float, l: float) -> tuple[float, float, float]:
        def hue_to_rgb(p, q, t):
            if t < 0:
                t += 1
            if t > 1:
                t -= 1
            if t < 1/6:
                return p + (q - p) * 6 * t
            if t < 1/2:
                return q
            if t < 2/3:
                return p + (q - p) * (2/3 - t) * 6
            return p
        if s == 0:
            r = g = b = l
        else:
            q = l * (1 + s) if l < 0.5 else l + s - l * s
            p = 2 * l - q
            r = hue_to_rgb(p, q, h + 1/3)
            g = hue_to_rgb(p, q, h)
            b = hue_to_rgb(p, q, h - 1/3)
        return r, g, b

    # ---------------- Presence (online list) ----------------
    def _update_presence_local(self, username: str, online: bool) -> None:
        """Update the local online listbox. Thread-safe caller should use _after."""
        # Remove first if exists
        names = list(self.online_listbox.get(0, tk.END))
        if online:
            if username not in names:
                self.online_listbox.insert(tk.END, username)
        else:
            # remove if present
            try:
                idx = names.index(username)
                self.online_listbox.delete(idx)
            except ValueError:
                pass

    # ---------------- Typing indicator helpers ----------------
    def _send_typing(self, state: int) -> None:
        if self.running and self.client_socket:
            try:
                username = self.name_entry.get().strip()
                self.client_socket.send(f"TYPING|{username}|{state}".encode('utf-8'))
            except Exception:
                pass

    def _on_keypress(self, event) -> None:
        # Called on any key press inside msg_entry
        # start typing state and reset timer
        self._send_typing(1)
        if self.typing_timer:
            self.root.after_cancel(self.typing_timer)
        self.typing_timer = self.root.after(1500, lambda: self._send_typing(0))

    # ---------------- Close ----------------
    def _on_close(self) -> None:
        # best-effort notify server (server should broadcast presence if implemented)
        try:
            if self.client_socket:
                # optionally send PRESENCE logout message if server expects it
                self.client_socket.send(f"PRESENCE|{self.name_entry.get().strip()}|offline".encode('utf-8'))
        except Exception:
            pass
        self.disconnect_server()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    root.minsize(720, 480)
    app = ChatClientApp(root)
    root.mainloop()