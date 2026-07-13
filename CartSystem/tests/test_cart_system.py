"""
CartSystem.Tests — Unit tests with mocking
Run: python -m pytest tests/ -v
  or: python -m unittest discover -s tests -v
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import unittest
from unittest.mock import MagicMock, patch, call

from domain.models import Cart, Product, ICartRepository, INotificationService
from core.patterns import (
    StandardPricing, SeasonalDiscountPricing, BulkDiscountPricing, LoyaltyPricing,
    BaseCartService, LoggingDecorator, SecurityDecorator, AuditDecorator,
    AnalyticsVisitor, TaxVisitor,
    CloudAIServiceFactory, LocalAIServiceFactory,
)
from core.infrastructure import InMemoryCartRepository


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_cart(cart_id="C1", customer_id="U1") -> Cart:
    cart = Cart(cart_id=cart_id, customer_id=customer_id)
    cart.add_item(Product("P1", "Widget", 10.00, "electronics"), quantity=3)
    cart.add_item(Product("P2", "Gadget", 25.00, "electronics"), quantity=1)
    return cart


# ══════════════════════════════════════════════════════════════════════════════
# 1. Strategy Pattern Tests
# ══════════════════════════════════════════════════════════════════════════════

class TestPricingStrategies(unittest.TestCase):

    def setUp(self):
        self.cart = make_cart()
        # subtotal = (10 * 3) + (25 * 1) = 55.00

    def test_standard_pricing_returns_subtotal(self):
        strategy = StandardPricing()
        self.assertAlmostEqual(strategy.calculate_total(self.cart), 55.00)

    def test_seasonal_discount_10_pct(self):
        strategy = SeasonalDiscountPricing(discount_pct=0.10)
        self.assertAlmostEqual(strategy.calculate_total(self.cart), 49.50)

    def test_bulk_discount_applied_when_qty_ge_5(self):
        cart = Cart(cart_id="C2", customer_id="U2")
        cart.add_item(Product("P3", "Pen", 2.00, "stationery"), quantity=5)
        strategy = BulkDiscountPricing()
        # 2.00 * 5 = 10.00, minus 10% = 9.00
        self.assertAlmostEqual(strategy.calculate_total(cart), 9.00)

    def test_bulk_discount_not_applied_below_5(self):
        strategy = BulkDiscountPricing()
        # P1: qty=3 (no discount), P2: qty=1 (no discount) → 55.00
        self.assertAlmostEqual(strategy.calculate_total(self.cart), 55.00)

    def test_loyalty_pricing_caps_at_20_pct(self):
        strategy = LoyaltyPricing(loyalty_score=200)  # over 100 → cap at 20%
        self.assertAlmostEqual(strategy.calculate_total(self.cart), 55.00 * 0.80)

    def test_strategy_description_is_string(self):
        for strategy in [StandardPricing(), SeasonalDiscountPricing(), BulkDiscountPricing()]:
            self.assertIsInstance(strategy.description(), str)


# ══════════════════════════════════════════════════════════════════════════════
# 2. Decorator Pattern Tests (with Mocking)
# ══════════════════════════════════════════════════════════════════════════════

class TestDecoratorPattern(unittest.TestCase):

    def _make_service(self, audit_log=None):
        """Build the full decorator chain with a mock repository."""
        mock_repo = MagicMock(spec=ICartRepository)
        base = BaseCartService(mock_repo)
        secured = SecurityDecorator(base)
        logged = LoggingDecorator(secured)
        if audit_log is not None:
            return AuditDecorator(logged, audit_log), mock_repo
        return logged, mock_repo

    def test_checkout_calls_repository_save(self):
        service, mock_repo = self._make_service()
        cart = make_cart()
        service.checkout(cart, StandardPricing())
        mock_repo.save.assert_called_once_with(cart)

    def test_security_decorator_rejects_empty_cart(self):
        service, _ = self._make_service()
        empty_cart = Cart(cart_id="E1", customer_id="U1")
        with self.assertRaises(ValueError) as ctx:
            service.checkout(empty_cart, StandardPricing())
        self.assertIn("empty cart", str(ctx.exception))

    def test_security_decorator_rejects_large_orders(self):
        service, _ = self._make_service()
        cart = Cart(cart_id="BIG", customer_id="U1")
        cart.add_item(Product("EX", "Expensive", 15_000.00), quantity=1)
        with self.assertRaises(ValueError) as ctx:
            service.checkout(cart, StandardPricing())
        self.assertIn("£10,000", str(ctx.exception))

    def test_audit_decorator_records_entry(self):
        audit_log = []
        service, _ = self._make_service(audit_log=audit_log)
        cart = make_cart()
        service.checkout(cart, SeasonalDiscountPricing(0.10))
        self.assertEqual(len(audit_log), 1)
        self.assertIn("cart=C1", audit_log[0])
        self.assertIn("£49.50", audit_log[0])

    def test_logging_decorator_calls_through(self):
        """Mock the inner service to verify LoggingDecorator delegates correctly."""
        mock_inner = MagicMock()
        mock_inner.checkout.return_value = 42.00
        logged = LoggingDecorator(mock_inner)
        cart = make_cart()
        result = logged.checkout(cart, StandardPricing())
        mock_inner.checkout.assert_called_once()
        self.assertEqual(result, 42.00)


# ══════════════════════════════════════════════════════════════════════════════
# 3. Visitor Pattern Tests
# ══════════════════════════════════════════════════════════════════════════════

class TestVisitorPattern(unittest.TestCase):

    def setUp(self):
        self.cart = make_cart()

    def test_analytics_visitor_totals(self):
        visitor = AnalyticsVisitor()
        visitor.visit_cart(self.cart)
        self.assertEqual(visitor.total_items, 4)          # qty 3 + qty 1
        self.assertAlmostEqual(visitor.total_value, 55.00)

    def test_analytics_visitor_category_breakdown(self):
        visitor = AnalyticsVisitor()
        visitor.visit_cart(self.cart)
        self.assertIn("electronics", visitor.category_breakdown)
        self.assertAlmostEqual(visitor.category_breakdown["electronics"], 55.00)

    def test_tax_visitor_20_pct(self):
        visitor = TaxVisitor()
        visitor.visit_cart(self.cart)
        self.assertAlmostEqual(visitor.tax_total, 55.00 * 0.20)

    def test_visitor_report_returns_string(self):
        v = AnalyticsVisitor()
        v.visit_cart(self.cart)
        self.assertIsInstance(v.report(), str)


# ══════════════════════════════════════════════════════════════════════════════
# 4. Abstract Factory Tests (with Mocking AI-dependent components)
# ══════════════════════════════════════════════════════════════════════════════

class TestAbstractFactory(unittest.TestCase):

    def setUp(self):
        self.cart = make_cart()

    def test_cloud_factory_creates_recommendation_engine(self):
        factory = CloudAIServiceFactory()
        engine = factory.create_recommendation_engine()
        recs = engine.recommend(self.cart)
        self.assertIsInstance(recs, list)
        self.assertTrue(len(recs) > 0)

    def test_local_factory_creates_recommendation_engine(self):
        factory = LocalAIServiceFactory()
        engine = factory.create_recommendation_engine()
        recs = engine.recommend(self.cart)
        self.assertIsInstance(recs, list)

    def test_cloud_factory_payment_gateway_charges(self):
        factory = CloudAIServiceFactory()
        gateway = factory.create_payment_gateway()
        result = gateway.charge("U1", 55.00)
        self.assertTrue(result)

    def test_mocked_ai_engine_isolates_test(self):
        """Isolate the recommendation engine — no live AI call needed."""
        mock_engine = MagicMock()
        mock_engine.recommend.return_value = ["Mocked product suggestion"]
        recs = mock_engine.recommend(self.cart)
        mock_engine.recommend.assert_called_once_with(self.cart)
        self.assertEqual(recs[0], "Mocked product suggestion")

    def test_mocked_payment_gateway_failure(self):
        """Simulate payment failure without a real gateway."""
        mock_gateway = MagicMock()
        mock_gateway.charge.return_value = False
        result = mock_gateway.charge("U1", 55.00)
        self.assertFalse(result)


# ══════════════════════════════════════════════════════════════════════════════
# 5. Repository Tests
# ══════════════════════════════════════════════════════════════════════════════

class TestInMemoryRepository(unittest.TestCase):

    def test_save_and_find(self):
        repo = InMemoryCartRepository()
        cart = make_cart()
        repo.save(cart)
        found = repo.find_by_id("C1")
        self.assertIsNotNone(found)
        self.assertEqual(found.customer_id, "U1")

    def test_find_missing_returns_none(self):
        repo = InMemoryCartRepository()
        self.assertIsNone(repo.find_by_id("MISSING"))

    def test_save_overwrites_existing(self):
        repo = InMemoryCartRepository()
        cart = make_cart()
        repo.save(cart)
        cart.add_item(Product("P3", "Extra", 5.00), quantity=2)
        repo.save(cart)
        self.assertEqual(len(repo.find_by_id("C1").items), 3)


if __name__ == "__main__":
    unittest.main(verbosity=2)
