"""Settings repository."""
from typing import Optional
from sqlalchemy.orm import Session
from app.models.settings import AppSetting


class SettingsRepository:
    def __init__(self, session: Session):
        self.session = session

    def get(self, key: str, default: str = None) -> Optional[str]:
        setting = self.session.query(AppSetting).filter(AppSetting.key == key).first()
        return setting.value if setting else default

    def set(self, key: str, value: str) -> None:
        setting = self.session.query(AppSetting).filter(AppSetting.key == key).first()
        if setting:
            setting.value = value
        else:
            setting = AppSetting(key=key, value=value)
            self.session.add(setting)

    def get_all(self) -> dict:
        settings = self.session.query(AppSetting).all()
        return {s.key: s.value for s in settings}
