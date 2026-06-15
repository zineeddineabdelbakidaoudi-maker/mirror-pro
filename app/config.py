"""Application configuration."""
import os
import sys
from pathlib import Path


def get_app_dir() -> Path:
    """Return the application data directory."""
    if getattr(sys, 'frozen', False):
        # Running as PyInstaller bundle
        return Path(sys.executable).parent
    return Path(__file__).parent.parent

def get_logo_path() -> Path:
    """Return the path to the logo."""
    if getattr(sys, 'frozen', False):
        # PyInstaller bundled path
        base_path = Path(getattr(sys, '_MEIPASS', get_app_dir() / "_internal"))
        return base_path / "app" / "assets" / "logo.png"
    return Path(__file__).parent / "assets" / "logo.png"


APP_DIR = get_app_dir()
DATA_DIR = APP_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

DATABASE_PATH = DATA_DIR / "miroir_pro.db"
DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

BACKUP_DIR = DATA_DIR / "backups"
BACKUP_DIR.mkdir(exist_ok=True)

# Default company info
DEFAULT_COMPANY_NAME = "Atelier Glass Charaf"
DEFAULT_COMPANY_PHONE = "0555 000 000"
DEFAULT_COMPANY_ADDRESS = "Zone Industrielle, Alger, Algérie"
DEFAULT_CURRENCY = "DZD"
DEFAULT_RECEIPT_FOOTER = "Merci pour votre confiance ! — Atelier Glass Charaf"

# Printer defaults
DEFAULT_PAPER_WIDTH = 80  # mm
DEFAULT_ENCODING = "cp850"  # French character support
