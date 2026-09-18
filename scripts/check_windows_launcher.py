"""Check real Windows startup, double clicks and reuse without stopping old copies.

Run with --keep-running to leave the corrected app available for the user.
Only a new fictitious document is uploaded. Startup uses the headless launcher flag.
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

import portable_smoke as smoke

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.config import APP_VERSION as VERSION
PACKAGE = ROOT / 'dist/AnonimizadorJudicial-NLP'


def listeners():
    output = subprocess.check_output(['netstat', '-ano', '-p', 'tcp'], text=True)
    return {int(port): int(pid) for port, pid in re.findall(
        r'^\s*TCP\s+127\.0\.0\.1:(878[7-9]|879[0-6])\s+\S+\s+LISTENING\s+(\d+)\s*$',
        output, re.M)}


def launcher(*flags):
    return subprocess.Popen(['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass',
                             '-File', str(PACKAGE / 'iniciar.ps1'), '-NoBrowser', *flags],
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                            creationflags=subprocess.CREATE_NO_WINDOW)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--keep-running', action='store_true')
    parser.add_argument('--package', type=Path, default=PACKAGE)
    args = parser.parse_args()
    globals()['PACKAGE'] = args.package.resolve()
    before = listeners()
    owned_pid = None
    checks = {}
    try:
        # These simultaneous invocations exercise the package mutex during startup.
        first = launcher()
        second = launcher()
        for process in (first, second):
            output, _ = process.communicate(timeout=90)
            print(output.strip(), flush=True)
            if process.returncode:
                raise RuntimeError(f'Launcher returned {process.returncode}')
        port = int((PACKAGE / 'PUERTO_ACTUAL.txt').read_text().strip())
        current = listeners()
        pid = current[port]
        if pid not in before.values():
            owned_pid = pid
        checks['existing_listeners_preserved'] = all(current.get(p) == value for p, value in before.items())
        checks['occupied_8787_uses_another_port'] = port != 8787 if (
            8787 in before and before[8787] != pid) else True
        smoke.BASE = f'http://127.0.0.1:{port}'
        health = json.loads(smoke.request('/health'))
        checks['correct_version_and_folder'] = (health['app_version'] == VERSION and
            Path(health['frontend_dir']).resolve() == (PACKAGE / 'frontend').resolve())
        boundary = 'launcher-fictitious-document'
        body = (f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="prueba_ficticia.docx"\r\nContent-Type: application/vnd.openxmlformats-officedocument.wordprocessingml.document\r\n\r\n'.encode()
                + smoke.fictitious_docx() + f'\r\n--{boundary}--\r\n'.encode())
        uploaded = json.loads(smoke.request('/api/upload', body,
                             {'Content-Type': 'multipart/form-data; boundary=' + boundary}))
        reopened = launcher()
        output, _ = reopened.communicate(timeout=90)
        print(output.strip(), flush=True)
        checks['reopen_keeps_same_process'] = reopened.returncode == 0 and listeners().get(port) == pid
        analyzed = smoke.post('/api/analyze', {'session_id': uploaded['session_id'],
            'label_mode': 'cat', 'enabled_categories': ['PERSONA']})
        checks['reopen_keeps_session'] = bool(analyzed['detections'])
        verified = launcher('-Verify')
        output, _ = verified.communicate(timeout=90)
        print(output.strip(), flush=True)
        checks['verify_uses_correct_port'] = verified.returncode == 0 and f':{port}/health' in output
        checks['double_click_creates_one_instance'] = len(set(listeners().values()) - set(before.values())) <= 1
        result = {'package': str(PACKAGE), 'port': port, 'pid': pid, 'checks': checks}
        results_dir = ROOT / 'build/validation'
        results_dir.mkdir(parents=True, exist_ok=True)
        (results_dir / 'windows_launcher_results.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
        print(json.dumps(result, indent=2), flush=True)
        if not all(checks.values()):
            raise RuntimeError('Failed launcher checks')
    finally:
        if owned_pid is not None and not args.keep_running:
            # Stop only the process created by this check, after verifying its path.
            script = (f'$owned = Get-Process -Id {owned_pid} -ErrorAction SilentlyContinue\n'
                      f"if ($owned -and $owned.Path -eq '{str(PACKAGE / 'AnonimizadorJudicial-NLP.exe').replace(chr(39), chr(39) * 2)}') {{ $owned | Stop-Process }}")
            subprocess.run(['powershell.exe', '-NoProfile', '-Command', script], check=True)


if __name__ == '__main__':
    main()
