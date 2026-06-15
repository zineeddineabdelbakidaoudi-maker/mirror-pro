"""Customer repository."""
from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.customer import Customer
from app.repositories.base_repository import BaseRepository


class CustomerRepository(BaseRepository[Customer]):
    def __init__(self, session: Session):
        super().__init__(session, Customer)

    def get_all_active(self) -> List[Customer]:
        """Return all non-deleted customers ordered by name."""
        return (
            self.session.query(Customer)
            .filter(Customer.is_deleted == False)
            .order_by(Customer.name)
            .all()
        )

    def search(self, term: str) -> List[Customer]:
        return (
            self.session.query(Customer)
            .filter(
                Customer.is_deleted == False,
                (Customer.name.ilike(f"%{term}%")) | (Customer.phone.ilike(f"%{term}%")),
            )
            .all()
        )

    def find_or_create(self, name: str, phone: str = None, address: str = None) -> Customer:
        """Find existing customer by name or create new one."""
        existing = (
            self.session.query(Customer)
            .filter(Customer.name == name, Customer.is_deleted == False)
            .first()
        )
        if existing:
            return existing
        customer = Customer(name=name, phone=phone, address=address)
        self.session.add(customer)
        self.session.flush()
        return customer

