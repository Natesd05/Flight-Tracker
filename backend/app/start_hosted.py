"""Validate config, migrate and seed, then start the single-service demo."""
import os
import subprocess
import sys
import uvicorn
from .hosted import create_app


def main():
    app = create_app()
    subprocess.run([sys.executable, '-m', 'alembic', 'upgrade', 'head'], check=True)
    subprocess.run([sys.executable, '-m', 'app.seed'], check=True)
    uvicorn.run(app, host=os.environ.get('HOST', '0.0.0.0'), port=int(os.environ.get('PORT', '10000')))


if __name__ == '__main__':
    main()
