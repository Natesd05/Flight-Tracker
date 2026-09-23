"""Create server-local secrets without printing them or overwriting existing files."""
from getpass import getpass
from pathlib import Path
import re
import secrets


def main():
    target = Path(__file__).resolve().parents[1] / 'deploy' / 'secrets'
    names = ('database_password', 'database_url', 'demo_auth')
    if any((target / name).exists() for name in names):
        raise SystemExit('Existing secrets found; refusing to overwrite. See docs/deployment.md for rotation.')
    password_hash = getpass('Paste the bcrypt hash from caddy hash-password (hidden): ').strip()
    if not re.fullmatch(r'\$2[aby]\$\d{2}\$[./A-Za-z0-9]{53}', password_hash):
        raise SystemExit('Expected a bcrypt hash from caddy hash-password.')
    password = secrets.token_hex(32)
    values = (
        password,
        f'postgresql+psycopg://planner:{password}@db:5432/flightplanner',
        'demo ' + password_hash + '\n',
    )
    target.mkdir(mode=0o700, parents=True, exist_ok=True)
    target.chmod(0o700)
    for name, value in zip(names, values):
        path = target / name
        # Exclusive creation also protects against a concurrent setup process.
        import os
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, 'w') as handle:
            handle.write(value)
    print('Created private secret files. No secret values were printed.')


if __name__ == '__main__':
    main()
