import socket

from support_calculator.dev_launcher import (
    DEFAULT_BACKEND_PORT,
    build_backend_command,
    build_backend_env,
    build_frontend_command,
    build_frontend_env,
    find_available_port,
    is_port_available,
)


def test_port_helpers_identify_busy_and_free_ports():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        sock.listen()
        busy_port = sock.getsockname()[1]
        discovered_port = find_available_port(busy_port)

        assert is_port_available(busy_port) is False
        assert discovered_port != busy_port
        assert discovered_port > busy_port
        assert is_port_available(discovered_port) is True


def test_build_backend_command_uses_module_entrypoint():
    command = build_backend_command()

    assert command[-2:] == ["-m", "support_calculator"]


def test_build_frontend_command_includes_host_and_port():
    command = build_frontend_command(6123)

    assert command == ["npm", "run", "dev", "--", "--host", "127.0.0.1", "--port", "6123"]


def test_build_backend_env_enables_flask_reload():
    env = build_backend_env(6124)

    assert env["HOST"] == "127.0.0.1"
    assert env["PORT"] == "6124"
    assert env["FLASK_DEBUG"] == "1"


def test_build_frontend_env_passes_backend_port():
    env = build_frontend_env(6125)

    assert env["BACKEND_PORT"] == "6125"


def test_default_backend_port_is_positive():
    assert DEFAULT_BACKEND_PORT > 0
