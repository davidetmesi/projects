"""
CartSystem.Core — Infrastructure (in-memory adapters)
"""

from __future__ import annotations
from domain.models import Cart, ICartRepository, INotificationService


class InMemoryCartRepository(ICartRepository):
    """Simple dict-backed repository for development / testing."""

    def __init__(self):
        self._store: dict[str, Cart] = {}

    def save(self, cart: Cart) -> None:
        self._store[cart.cart_id] = cart

    def find_by_id(self, cart_id: str) -> Cart | None:
        return self._store.get(cart_id)

    def all_carts(self) -> list[Cart]:
        return list(self._store.values())


class ConsoleNotificationService(INotificationService):
    """Prints notifications to stdout (swap for email/SMS in production)."""

    def notify(self, customer_id: str, message: str) -> None:
        print(f"[NOTIFICATION → {customer_id}] {message}")
