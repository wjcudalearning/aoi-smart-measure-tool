import socket
import threading
from collections.abc import Callable
from typing import Any

from loguru import logger


class TcpSocketServer:
    """Industrial TCP/IP ASCII socket server for automated line robotic communications."""

    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 8000,
        trigger_handler: Callable[[int], bool] | None = None,
    ) -> None:
        self.host = host
        self._port = port
        self.trigger_handler = trigger_handler
        self._server_socket: socket.socket | None = None
        self._is_running = False
        self._server_thread: threading.Thread | None = None
        self._client_threads: list[threading.Thread] = []
        self._latest_results: dict[int, str] = {}

    @property
    def port(self) -> int:
        if self._server_socket:
            return int(self._server_socket.getsockname()[1])
        return self._port

    @property
    def is_running(self) -> bool:
        return self._is_running

    def start(self) -> bool:
        if self._is_running:
            return True

        try:
            self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._server_socket.bind((self.host, self._port))
            self._server_socket.listen(5)
            self._server_socket.settimeout(1.0)
            self._is_running = True

            self._server_thread = threading.Thread(target=self._listen_worker, daemon=True)
            self._server_thread.start()
            logger.info(f"TCP Socket Server listening on {self.host}:{self.port}")
            return True
        except Exception as e:
            logger.error(f"Failed to start TCP Socket Server: {e}")
            self._is_running = False
            return False

    def stop(self) -> None:
        if not self._is_running:
            return

        self._is_running = False
        if self._server_socket:
            try:
                self._server_socket.close()
            except Exception:
                pass
            self._server_socket = None

        if self._server_thread and self._server_thread.is_alive():
            self._server_thread.join(timeout=1.0)
        logger.info("TCP Socket Server stopped.")

    def set_slot_result(self, slot_index: int, grade: str) -> None:
        self._latest_results[slot_index] = grade

    def _listen_worker(self) -> None:
        while self._is_running and self._server_socket is not None:
            try:
                client_sock, client_addr = self._server_socket.accept()
                client_thread = threading.Thread(
                    target=self._client_handler, args=(client_sock, client_addr), daemon=True
                )
                client_thread.start()
                self._client_threads.append(client_thread)
            except TimeoutError:
                continue
            except Exception:
                break

    def _client_handler(self, sock: socket.socket, addr: Any) -> None:
        sock.settimeout(2.0)
        buffer = ""
        while self._is_running:
            try:
                data = sock.recv(1024)
                if not data:
                    break
                buffer += data.decode("utf-8", errors="ignore")
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    line = line.strip()
                    if not line:
                        continue
                    response = self._process_command(line)
                    sock.sendall((response + "\n").encode("utf-8"))
            except TimeoutError:
                continue
            except Exception:
                break
        try:
            sock.close()
        except Exception:
            pass

    def _process_command(self, cmd: str) -> str:
        parts = cmd.split()
        verb = parts[0].upper()

        if verb == "PING":
            return "PONG"
        elif verb == "STATUS":
            return "STATUS READY"
        elif verb == "TRIGGER":
            slot = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
            if self.trigger_handler:
                success = self.trigger_handler(slot)
                return f"ACK_TRIGGER {slot} {'OK' if success else 'FAIL'}"
            return f"ACK_TRIGGER {slot}"
        elif verb == "RESULT?":
            slot = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
            res = self._latest_results.get(slot, "UNKNOWN")
            return f"RESULT {slot} GRADE={res}"
        else:
            return f"ERR UNKNOWN_COMMAND {verb}"
