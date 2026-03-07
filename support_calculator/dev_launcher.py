import logging
import os
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_BACKEND_PORT = 5001
DEFAULT_FRONTEND_PORT = 5173
HOST = "127.0.0.1"


def is_port_available(port: int, host: str = HOST) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return sock.connect_ex((host, port)) != 0


def find_available_port(start_port: int, host: str = HOST) -> int:
    port = start_port
    while not is_port_available(port, host):
        logger.info("Port %s is busy on %s; trying %s", port, host, port + 1)
        port += 1

    return port


def build_backend_command() -> list[str]:
    return [sys.executable, "-m", "support_calculator"]


def build_frontend_command(port: int) -> list[str]:
    return ["npm", "run", "dev", "--", "--host", HOST, "--port", str(port)]


def terminate_process(process: subprocess.Popen) -> None:
    if process.poll() is not None:
        return

    logger.info("Stopping process %s", process.pid)
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        logger.warning("Process %s did not exit cleanly; killing it.", process.pid)
        process.kill()
        process.wait(timeout=5)


def run() -> int:
    if not logging.getLogger().handlers:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        )

    project_root = Path(__file__).resolve().parent.parent
    frontend_dir = project_root / "frontend"

    backend_port = find_available_port(DEFAULT_BACKEND_PORT)
    frontend_port = find_available_port(DEFAULT_FRONTEND_PORT)

    backend_env = os.environ.copy()
    backend_env["HOST"] = HOST
    backend_env["PORT"] = str(backend_port)

    frontend_env = os.environ.copy()
    frontend_env["BACKEND_PORT"] = str(backend_port)

    logger.info("Starting backend on http://%s:%s", HOST, backend_port)
    backend_process = subprocess.Popen(
        build_backend_command(),
        cwd=project_root,
        env=backend_env,
    )

    logger.info("Starting frontend on http://%s:%s", HOST, frontend_port)
    frontend_process = subprocess.Popen(
        build_frontend_command(frontend_port),
        cwd=frontend_dir,
        env=frontend_env,
    )

    processes = [backend_process, frontend_process]

    def handle_shutdown(signum, _frame):
        logger.info("Received signal %s; shutting down dev servers.", signum)
        for process in reversed(processes):
            terminate_process(process)
        raise SystemExit(0)

    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)

    print(f"Backend:  http://{HOST}:{backend_port}")
    print(f"Frontend: http://{HOST}:{frontend_port}")
    print("Press Ctrl+C to stop both servers.")

    try:
        while True:
            for process in processes:
                return_code = process.poll()
                if return_code is not None:
                    logger.warning(
                        "Process %s exited with status %s; stopping both servers.",
                        process.pid,
                        return_code,
                    )
                    for other_process in reversed(processes):
                        if other_process is not process:
                            terminate_process(other_process)
                    return return_code
            time.sleep(0.5)
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received; shutting down dev servers.")
        for process in reversed(processes):
            terminate_process(process)
        return 0


def main() -> int:
    return run()
