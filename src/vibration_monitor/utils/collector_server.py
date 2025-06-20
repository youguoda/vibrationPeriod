
# comm_socket.py
import socket
import threading
import time


class SocketMaster:
    def __init__(self, host='127.0.0.1', port=50007, on_message=None):
        self.host = host
        self.port = port
        self.on_message = on_message
        self._running = False
        self._server_socket = None

    def start(self):
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        self._running = True
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            self._server_socket = s
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((self.host, self.port))
            s.listen()
            print(f"[主站] 监听中 {self.host}:{self.port}...")
            while self._running:
                try:
                    s.settimeout(1.0)  # 防止长时间阻塞
                    conn, addr = s.accept()
                    threading.Thread(target=self._handle_client, args=(conn,), daemon=True).start()
                except socket.timeout:
                    continue
                except OSError:
                    break  # socket 已关闭

    def _handle_client(self, conn):
        with conn:
            while self._running:
                try:
                    data = conn.recv(1024)
                    if not data:
                        break
                    message = data.decode()
                    print(f"[主站] 收到消息: {message}")
                    if self.on_message:
                        self.on_message(message)
                except:
                    break

    def stop(self):
        print("[主站] 正在关闭 socket...")
        self._running = False
        if self._server_socket:
            self._server_socket.close()
            self._server_socket = None
        print("[主站] socket 已关闭")

