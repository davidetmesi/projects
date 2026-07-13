"""
CartSystem.Demo — End-to-end walkthrough of all four design patterns.
Run: python demo/main.py
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from domain.models import Cart, Product
from core.infrastructure import InMemoryCartRepository, ConsoleNotificationService
from core.patterns import (
    # Strategies
    StandardPricing, SeasonalDiscountPricing, BulkDiscountPricing, LoyaltyPricing,
    # Decorators
    BaseCartService, LoggingDecorator, SecurityDecorator, AuditDecorator,
    # Visitors
    AnalyticsVisitor, TaxVisitor,
    # Factories
    CloudAIServiceFactory, LocalAIServiceFactory,
)

DIVIDER = "=" * 60


def demo_strategy_pattern():
    print(f"\n{DIVIDER}")
    print("  STRATEGY PATTERN — Interchangeable Pricing Algorithms")
    print(DIVIDER)

    cart = Cart(cart_id="CART-001", customer_id="ALICE")
    cart.add_item(Product("P1", "Laptop",  999.99, "electronics"), quantity=1)
    cart.add_item(Product("P2", "USB Hub",  29.99, "accessories"), quantity=6)
    print(cart)

    strategies = [
        StandardPricing(),
        SeasonalDiscountPricing(discount_pct=0.15),
        BulkDiscountPricing(),
        LoyaltyPricing(loyalty_score=75),
    ]
    print()
    for s in strategies:
        total = s.calculate_total(cart)
        print(f"  [{s.description():45s}]  Total = £{total:.2f}")


def demo_decorator_pattern():
    print(f"\n{DIVIDER}")
    print("  DECORATOR PATTERN — Dynamic Feature Layering")
    print(DIVIDER)

    repo = InMemoryCartRepository()
    audit_log: list[str] = []

    # Build decorated service: base → security → logging → audit
    service = AuditDecorator(
        LoggingDecorator(
            SecurityDecorator(
                BaseCartService(repo)
            )
        ),
        audit_log,
    )

    cart = Cart(cart_id="CART-002", customer_id="BOB")
    cart.add_item(Product("P3", "Monitor", 350.00, "electronics"), quantity=2)

    total = service.checkout(cart, SeasonalDiscountPricing(0.10))
    print(f"\n  Final total charged: £{total:.2f}")
    print(f"\n  Audit log entry:\n  {audit_log[0]}")

    # Demonstrate security rejection
    print("\n  Attempting checkout with empty cart…")
    try:
        service.checkout(Cart("EMPTY", "BOB"), StandardPricing())
    except ValueError as e:
        print(f"  ✗ Rejected: {e}")


def demo_visitor_pattern():
    print(f"\n{DIVIDER}")
    print("  VISITOR PATTERN — Analytics & Tax Reporting")
    print(DIVIDER)

    cart = Cart(cart_id="CART-003", customer_id="CAROL")
    cart.add_item(Product("P4", "Keyboard", 79.99, "accessories"), quantity=2)
    cart.add_item(Product("P5", "Headset",  49.99, "audio"),       quantity=3)
    cart.add_item(Product("P6", "Mousepad", 14.99, "accessories"), quantity=4)
    print(cart)

    analytics = AnalyticsVisitor()
    analytics.visit_cart(cart)
    print()
    print(analytics.report())

    tax = TaxVisitor()
    tax.visit_cart(cart)
    print(tax.report())


def demo_abstract_factory():
    print(f"\n{DIVIDER}")
    print("  ABSTRACT FACTORY — Pluggable AI & Payment Families")
    print(DIVIDER)

    cart = Cart(cart_id="CART-004", customer_id="DAN")
    cart.add_item(Product("P7", "Speaker", 199.99, "audio"), quantity=1)

    for label, factory in [
        ("Cloud AI (OpenAI + Stripe)", CloudAIServiceFactory()),
        ("Local AI  (Rules + PayPal)", LocalAIServiceFactory()),
    ]:
        engine  = factory.create_recommendation_engine()
        gateway = factory.create_payment_gateway()

        print(f"\n  ── {label} ──")
        recs = engine.recommend(cart)
        print("  Recommendations:")
        for r in recs:
            print(f"    • {r}")

        success = gateway.charge(cart.customer_id, 199.99)
        print(f"  Payment charged: {'✓' if success else '✗'}")


if __name__ == "__main__":
    print("\n" + DIVIDER)
    print("  CartSystem — Design Patterns Demo")
    print(DIVIDER)

    demo_strategy_pattern()
    demo_decorator_pattern()
    demo_visitor_pattern()
    demo_abstract_factory()

    print(f"\n{DIVIDER}")
    print("  Demo complete.")
    print(DIVIDER)
