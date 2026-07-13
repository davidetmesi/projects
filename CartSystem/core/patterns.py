"""
CartSystem.Core — Business logic implementing the four design patterns.

Patterns implemented
--------------------
1. Strategy   — interchangeable pricing algorithms
2. Decorator  — dynamic feature layering (logging, security, caching)
3. Visitor    — analytics/reporting separated from domain objects
4. Abstract Factory — pluggable AI / payment service families
"""

from __future__ import annotations
import datetime
import logging
from abc import ABC, abstractmethod
from typing import List

from domain.models import Cart, CartItem, IPricingStrategy, ICartRepository, INotificationService

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════════
# 1. STRATEGY PATTERN — Pricing
# ══════════════════════════════════════════════════════════════════════════════

class StandardPricing(IPricingStrategy):
    """No discount — full price."""

    def calculate_total(self, cart: Cart) -> float:
        return cart.subtotal

    def description(self) -> str:
        return "Standard (no discount)"


class SeasonalDiscountPricing(IPricingStrategy):
    """Flat percentage discount on the whole cart."""

    def __init__(self, discount_pct: float = 0.10):
        self._discount = discount_pct

    def calculate_total(self, cart: Cart) -> float:
        return cart.subtotal * (1 - self._discount)

    def description(self) -> str:
        return f"Seasonal discount ({self._discount * 100:.0f}% off)"


class BulkDiscountPricing(IPricingStrategy):
    """10% off each line that has 5 or more units."""

    def calculate_total(self, cart: Cart) -> float:
        total = 0.0
        for item in cart.items:
            if item.quantity >= 5:
                total += item.line_total * 0.90
            else:
                total += item.line_total
        return total

    def description(self) -> str:
        return "Bulk discount (10% off lines with qty ≥ 5)"


class LoyaltyPricing(IPricingStrategy):
    """AI-inspired: discount scales with customer loyalty score."""

    def __init__(self, loyalty_score: int):
        # score 0-100 → up to 20% discount
        self._discount = min(loyalty_score / 100 * 0.20, 0.20)

    def calculate_total(self, cart: Cart) -> float:
        return cart.subtotal * (1 - self._discount)

    def description(self) -> str:
        return f"Loyalty pricing ({self._discount * 100:.1f}% personalised discount)"


# ══════════════════════════════════════════════════════════════════════════════
# 2. DECORATOR PATTERN — CartService layers
# ══════════════════════════════════════════════════════════════════════════════

class ICartService(ABC):
    """Component interface that all decorators wrap."""

    @abstractmethod
    def checkout(self, cart: Cart, strategy: IPricingStrategy) -> float: ...

    @abstractmethod
    def save_cart(self, cart: Cart) -> None: ...


class BaseCartService(ICartService):
    """Concrete component — the core checkout logic."""

    def __init__(self, repository: ICartRepository):
        self._repo = repository

    def checkout(self, cart: Cart, strategy: IPricingStrategy) -> float:
        total = strategy.calculate_total(cart)
        self._repo.save(cart)
        return total

    def save_cart(self, cart: Cart) -> None:
        self._repo.save(cart)


class CartServiceDecorator(ICartService, ABC):
    """Abstract decorator base."""

    def __init__(self, wrapped: ICartService):
        self._wrapped = wrapped

    def checkout(self, cart: Cart, strategy: IPricingStrategy) -> float:
        return self._wrapped.checkout(cart, strategy)

    def save_cart(self, cart: Cart) -> None:
        self._wrapped.save_cart(cart)


class LoggingDecorator(CartServiceDecorator):
    """Adds structured logging around every operation."""

    def checkout(self, cart: Cart, strategy: IPricingStrategy) -> float:
        logger.info("CHECKOUT START | cart=%s | strategy=%s", cart.cart_id, strategy.description())
        total = super().checkout(cart, strategy)
        logger.info("CHECKOUT END   | cart=%s | total=£%.2f", cart.cart_id, total)
        return total

    def save_cart(self, cart: Cart) -> None:
        logger.info("SAVE_CART | cart=%s", cart.cart_id)
        super().save_cart(cart)


class SecurityDecorator(CartServiceDecorator):
    """Validates the cart before allowing checkout."""

    def checkout(self, cart: Cart, strategy: IPricingStrategy) -> float:
        if not cart.items:
            raise ValueError("Security: cannot check out an empty cart.")
        if cart.subtotal > 10_000:
            raise ValueError("Security: order exceeds £10,000 limit — manual review required.")
        return super().checkout(cart, strategy)


class AuditDecorator(CartServiceDecorator):
    """Appends an audit trail entry after every checkout."""

    def __init__(self, wrapped: ICartService, audit_log: List[str]):
        super().__init__(wrapped)
        self._log = audit_log

    def checkout(self, cart: Cart, strategy: IPricingStrategy) -> float:
        total = super().checkout(cart, strategy)
        entry = (
            f"{datetime.datetime.now().isoformat()} | "
            f"cart={cart.cart_id} | customer={cart.customer_id} | "
            f"total=£{total:.2f} | strategy={strategy.description()}"
        )
        self._log.append(entry)
        return total


# ══════════════════════════════════════════════════════════════════════════════
# 3. VISITOR PATTERN — Analytics / Reporting
# ══════════════════════════════════════════════════════════════════════════════

class ICartVisitor(ABC):
    """Visitor interface — algorithms separated from domain objects."""

    @abstractmethod
    def visit_cart(self, cart: Cart) -> None: ...

    @abstractmethod
    def visit_item(self, item: CartItem) -> None: ...


class AnalyticsVisitor(ICartVisitor):
    """Collects aggregate metrics across the whole cart."""

    def __init__(self):
        self.total_items = 0
        self.total_value = 0.0
        self.category_breakdown: dict[str, float] = {}

    def visit_cart(self, cart: Cart) -> None:
        for item in cart.items:
            self.visit_item(item)

    def visit_item(self, item: CartItem) -> None:
        self.total_items += item.quantity
        self.total_value += item.line_total
        cat = item.product.category
        self.category_breakdown[cat] = (
            self.category_breakdown.get(cat, 0.0) + item.line_total
        )

    def report(self) -> str:
        lines = ["── Analytics Report ──"]
        lines.append(f"  Total items : {self.total_items}")
        lines.append(f"  Total value : £{self.total_value:.2f}")
        lines.append("  By category :")
        for cat, val in self.category_breakdown.items():
            lines.append(f"    {cat}: £{val:.2f}")
        return "\n".join(lines)


class TaxVisitor(ICartVisitor):
    """Computes VAT per item (20%)."""

    VAT_RATE = 0.20

    def __init__(self):
        self.tax_total = 0.0

    def visit_cart(self, cart: Cart) -> None:
        for item in cart.items:
            self.visit_item(item)

    def visit_item(self, item: CartItem) -> None:
        self.tax_total += item.line_total * self.VAT_RATE

    def report(self) -> str:
        return f"── Tax Report ── VAT (20%): £{self.tax_total:.2f}"


# ══════════════════════════════════════════════════════════════════════════════
# 4. ABSTRACT FACTORY — AI / Payment service families
# ══════════════════════════════════════════════════════════════════════════════

class IRecommendationEngine(ABC):
    @abstractmethod
    def recommend(self, cart: Cart) -> List[str]: ...


class IPaymentGateway(ABC):
    @abstractmethod
    def charge(self, customer_id: str, amount: float) -> bool: ...


class IServiceFactory(ABC):
    """Abstract Factory — produce a family of compatible services."""

    @abstractmethod
    def create_recommendation_engine(self) -> IRecommendationEngine: ...

    @abstractmethod
    def create_payment_gateway(self) -> IPaymentGateway: ...


# --- Family A: OpenAI-backed AI + Stripe payments ---

class OpenAIRecommendationEngine(IRecommendationEngine):
    def recommend(self, cart: Cart) -> List[str]:
        categories = {i.product.category for i in cart.items}
        # Simulates an OpenAI API call for product suggestions
        return [f"OpenAI suggested product for '{c}'" for c in categories]


class StripePaymentGateway(IPaymentGateway):
    def charge(self, customer_id: str, amount: float) -> bool:
        logger.info("Stripe: charging £%.2f to customer %s", amount, customer_id)
        return True  # simulated success


class CloudAIServiceFactory(IServiceFactory):
    """Produces OpenAI + Stripe services."""

    def create_recommendation_engine(self) -> IRecommendationEngine:
        return OpenAIRecommendationEngine()

    def create_payment_gateway(self) -> IPaymentGateway:
        return StripePaymentGateway()


# --- Family B: Local/offline AI + PayPal payments ---

class LocalRecommendationEngine(IRecommendationEngine):
    def recommend(self, cart: Cart) -> List[str]:
        return [f"Local rule: buy more of '{i.product.category}'" for i in cart.items]


class PayPalPaymentGateway(IPaymentGateway):
    def charge(self, customer_id: str, amount: float) -> bool:
        logger.info("PayPal: charging £%.2f to customer %s", amount, customer_id)
        return True


class LocalAIServiceFactory(IServiceFactory):
    """Produces local-model + PayPal services (no cloud dependency)."""

    def create_recommendation_engine(self) -> IRecommendationEngine:
        return LocalRecommendationEngine()

    def create_payment_gateway(self) -> IPaymentGateway:
        return PayPalPaymentGateway()
