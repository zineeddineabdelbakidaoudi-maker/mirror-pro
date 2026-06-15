"""Base repository with common CRUD operations."""
from typing import TypeVar, Generic, Type, List, Optional
from sqlalchemy.orm import Session
from app.database.base import Base

T = TypeVar("T", bound=Base)


class BaseRepository(Generic[T]):
    """Generic repository providing standard CRUD operations."""

    def __init__(self, session: Session, model_class: Type[T]):
        self.session = session
        self.model_class = model_class

    def get_by_id(self, entity_id: int) -> Optional[T]:
        return self.session.get(self.model_class, entity_id)

    def get_all(self, include_deleted: bool = False) -> List[T]:
        query = self.session.query(self.model_class)
        if hasattr(self.model_class, "is_deleted") and not include_deleted:
            query = query.filter(self.model_class.is_deleted == False)
        return query.order_by(self.model_class.id.desc()).all()

    def add(self, entity: T) -> T:
        self.session.add(entity)
        self.session.flush()
        return entity

    def delete(self, entity: T, soft: bool = True) -> None:
        if soft and hasattr(entity, "is_deleted"):
            entity.is_deleted = True
        else:
            self.session.delete(entity)

    def count(self, include_deleted: bool = False) -> int:
        query = self.session.query(self.model_class)
        if hasattr(self.model_class, "is_deleted") and not include_deleted:
            query = query.filter(self.model_class.is_deleted == False)
        return query.count()
