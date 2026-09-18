"""Start development on a free local port, keeping other processes intact."""
import os
import socket
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def available_port() -> int:
    requested = os.environ.get('ANON_PORT')
    try:
        ports = [int(requested)] if requested else range(8787, 8797)
    except ValueError as exc:
        raise SystemExit('ANON_PORT debe ser un número de puerto.') from exc
    for port in ports:
        if not 1 <= port <= 65535:
            raise SystemExit('ANON_PORT debe estar entre 1 y 65535.')
        with socket.socket() as probe:
            try:
                probe.bind(('127.0.0.1', port))
            except OSError:
                continue
            return port
    raise SystemExit('No hay un puerto disponible. Las aplicaciones abiertas se conservaron.')


def main() -> None:
    os.chdir(ROOT)
    sys.path.insert(0, str(ROOT))
    os.environ['ANON_PORT'] = str(available_port())
    from app.config import FRONTEND_DIR, HOST, PORT
    from app.main import run_server

    print(f'Frontend: {FRONTEND_DIR}')
    print(f'Servidor: http://{HOST}:{PORT}')
    run_server(open_browser=True)


if __name__ == '__main__':
    main()
