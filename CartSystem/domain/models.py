"""
CartSystem.Domain — Core entities and interfaces
Mirrors the CartSystem.Domain VB.NET project.
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List


# ── Entities ──────────────────────────────────────────────────────────────────

@dataclass
class Product:
    """Represents a product in the catalogue."""
    product_id: str
    name: str
    base_price: float
    category: str = "general"

    def __str__(self) -> str:
        return f"{self.name} (£{self.base_price:.2f})"


@dataclass
class CartItem:
    """A product line inside a shopping cart."""
    product: Product
    quantity: int

    @property
    def line_total(self) -> float:
        return self.product.base_price * self.quantity


@dataclass
class Cart:
    """The shopping cart aggregate root."""
    cart_id: str
    customer_id: str
    items: List[CartItem] = field(default_factory=list)

    def add_item(self, product: Product, quantity: int = 1) -> None:
        for item in self.items:
            if item.product.product_id == product.product_id:
                item.quantity += quantity
                return
        self.items.append(CartItem(product=product, quantity=quantity))

    def remove_item(self, product_id: str) -> None:
        self.items = [i for i in self.items if i.product.product_id != product_id]

    @property
    def subtotal(self) -> float:
        return sum(i.line_total for i in self.items)

    def __str__(self) -> str:
        lines = [f"Cart [{self.cart_id}] for customer {self.customer_id}"]
        for item in self.items:
            lines.append(f"  {item.product.name} x{item.quantity} = £{item.line_total:.2f}")
        lines.append(f"  Subtotal: £{self.subtotal:.2f}")
        return "\n".join(lines)


# ── Abstract interfaces (ports) ────────────────────────────────────────────────

class ICartRepository(ABC):
    """Persistence port for carts."""

    @abstractmethod
    def save(self, cart: Cart) -> None: ...

    @abstractmethod
    def find_by_id(self, cart_id: str) -> Cart | None: ...


class INotificationService(ABC):
    """Notification port."""

    @abstractmethod
    def notify(self, customer_id: str, message: str) -> None: ...


class IPricingStrategy(ABC):
    """Strategy pattern interface for pricing algorithms."""

    @abstractmethod
    def calculate_total(self, cart: Cart) -> float: ...

    @abstractmethod
    def description(self) -> str: ...
