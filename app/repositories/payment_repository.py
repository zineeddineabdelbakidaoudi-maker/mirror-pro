"""Payment repository."""
from typing import List
from sqlalchemy.orm import Session
from app.models.payment import Payment
from app.repositories.base_repository import BaseRepository


class PaymentRepository(BaseRepository[Payment]):
    def __init__(self, session: Session):
        super().__init__(session, Payment)

    def get_by_order(self, order_id: int) -> List[Payment]:
        return (
            self.session.query(Payment)
            .filter(Payment.order_id == order_id)
            .order_by(Payment.payment_date.asc())
            .all()
        )

    def get_total_for_order(self, order_id: int) -> float:
        payments = self.get_by_order(order_id)
        return sum(p.amount for p in payments)
