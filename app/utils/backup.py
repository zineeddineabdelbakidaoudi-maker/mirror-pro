"""Database backup utility."""
import os
import shutil
from datetime import datetime


def get_db_path() -> str:
    """Return path to the active database file."""
    base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(base, "data", "miroir_pro.db")


def get_backup_dir() -> str:
    """Return the backup directory, creating it if needed."""
    base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    backup_dir = os.path.join(base, "data", "backups")
    os.makedirs(backup_dir, exist_ok=True)
    return backup_dir


def create_backup() -> str:
    """Create a timestamped backup of the database. Returns the backup file path."""
    db_path = get_db_path()
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"Base de donnees introuvable: {db_path}")

    backup_dir = get_backup_dir()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"miroir_pro_backup_{timestamp}.db"
    backup_path = os.path.join(backup_dir, backup_name)

    shutil.copy2(db_path, backup_path)
    return backup_path


def restore_backup(backup_path: str) -> bool:
    """Restore a backup file, overwriting the current database."""
    db_path = get_db_path()
    if not os.path.exists(backup_path):
        raise FileNotFoundError(f"Fichier de sauvegarde introuvable: {backup_path}")

    shutil.copy2(backup_path, db_path)
    return True


def list_backups() -> list:
    """List all available backups sorted newest first."""
    backup_dir = get_backup_dir()
    if not os.path.exists(backup_dir):
        return []

    backups = []
    for f in os.listdir(backup_dir):
        if f.endswith(".db"):
            path = os.path.join(backup_dir, f)
            size_mb = os.path.getsize(path) / (1024 * 1024)
            mtime = datetime.fromtimestamp(os.path.getmtime(path))
            backups.append({
                "filename": f,
                "path": path,
                "size_mb": round(size_mb, 2),
                "date": mtime.strftime("%Y-%m-%d %H:%M:%S"),
            })

    backups.sort(key=lambda b: b["date"], reverse=True)
    return backups
