import pytest
from rest_framework.exceptions import ValidationError

from suppliers.services import SupplierService
from suppliers.tests.factories import (
    SupplierInventoryFactory,
    SupplierPromotionFactory,
)


@pytest.mark.service
class TestInventoryAddStock:
    def test_add_positive_amount(self, db):
        inv = SupplierInventoryFactory(quantity=10)
        result = SupplierService.inventory_add_stock(inv, 5)
        assert result.quantity == 15

    def test_add_zero_raises(self, db):
        inv = SupplierInventoryFactory(quantity=10)
        with pytest.raises(ValidationError):
            SupplierService.inventory_add_stock(inv, 0)

    def test_add_negative_raises(self, db):
        inv = SupplierInventoryFactory(quantity=10)
        with pytest.raises(ValidationError):
            SupplierService.inventory_add_stock(inv, -3)


@pytest.mark.service
class TestInventoryRemoveStock:
    def test_remove_less_than_stock(self, db):
        inv = SupplierInventoryFactory(quantity=10)
        result = SupplierService.inventory_remove_stock(inv, 3)
        assert result.quantity == 7

    def test_remove_exact_stock(self, db):
        inv = SupplierInventoryFactory(quantity=10)
        result = SupplierService.inventory_remove_stock(inv, 10)
        assert result.quantity == 0

    def test_remove_more_than_stock_raises(self, db):
        inv = SupplierInventoryFactory(quantity=10)
        with pytest.raises(ValidationError):
            SupplierService.inventory_remove_stock(inv, 11)

    def test_remove_zero_raises(self, db):
        inv = SupplierInventoryFactory(quantity=10)
        with pytest.raises(ValidationError):
            SupplierService.inventory_remove_stock(inv, 0)


@pytest.mark.service
class TestPromotionActivate:
    def test_activate_from_draft(self, db):
        promo = SupplierPromotionFactory(status="DRAFT")
        result = SupplierService.promotion_activate(promo)
        assert result.status == "ACTIVE"

    def test_activate_from_active_raises(self, db):
        promo = SupplierPromotionFactory(status="ACTIVE")
        with pytest.raises(ValidationError):
            SupplierService.promotion_activate(promo)


@pytest.mark.service
class TestPromotionCancel:
    def test_cancel_from_draft(self, db):
        promo = SupplierPromotionFactory(status="DRAFT")
        result = SupplierService.promotion_cancel(promo)
        assert result.status == "CANCELED"

    def test_cancel_from_expired_raises(self, db):
        promo = SupplierPromotionFactory(status="EXPIRED")
        with pytest.raises(ValidationError):
            SupplierService.promotion_cancel(promo)

    def test_cancel_from_canceled_raises(self, db):
        promo = SupplierPromotionFactory(status="CANCELED")
        with pytest.raises(ValidationError):
            SupplierService.promotion_cancel(promo)
