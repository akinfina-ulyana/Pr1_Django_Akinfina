from decimal import Decimal

import pytest
from dealership.tests.factories import DealershipInventoryFactory
from rest_framework.exceptions import ValidationError

from buyers.services import BuyerService, OfferProcessingService, OfferService
from buyers.tests.factories import BuyerProfileFactory, OfferFactory


@pytest.mark.service
class TestBuyerServiceDeposit:
    def test_deposit_positive(self, db):
        profile = BuyerProfileFactory(balance=Decimal("0"))
        result = BuyerService.deposit(profile, Decimal("100.00"))
        assert result.balance == 100

    def test_deposit_zero_raises(self, db):
        profile = BuyerProfileFactory()
        with pytest.raises(ValidationError):
            BuyerService.deposit(profile, Decimal("0"))

    def test_deposit_negative_raises(self, db):
        profile = BuyerProfileFactory()
        with pytest.raises(ValidationError):
            BuyerService.deposit(profile, Decimal("-50"))


@pytest.mark.service
class TestBuyerServiceWithdraw:
    def test_withdraw_less_than_balance(self, db):
        profile = BuyerProfileFactory(balance=Decimal("500"))
        result = BuyerService.withdraw(profile, Decimal("200"))
        assert result.balance == 300

    def test_withdraw_exact_balance(self, db):
        profile = BuyerProfileFactory(balance=Decimal("500"))
        result = BuyerService.withdraw(profile, Decimal("500"))
        assert result.balance == 0

    def test_withdraw_more_than_balance_raises(self, db):
        profile = BuyerProfileFactory(balance=Decimal("100"))
        with pytest.raises(ValidationError):
            BuyerService.withdraw(profile, Decimal("500"))


@pytest.mark.service
class TestOfferServiceCreateOffer:
    def test_create_offer_success(self, db):
        buyer = BuyerProfileFactory(balance=Decimal("50000"))
        inv = DealershipInventoryFactory(sale_price="10000", quantity=5)

        offer = OfferService.create_offer(
            buyer=buyer,
            dealership_inventory_id=inv.id,
        )
        assert offer.status == "CREATED"
        assert offer.final_price is not None
        assert offer.buyer_id == buyer.id

    def test_create_offer_insufficient_funds(self, db):
        buyer = BuyerProfileFactory(balance=Decimal("100"))
        inv = DealershipInventoryFactory(sale_price="50000", quantity=5)

        with pytest.raises(ValidationError) as exc:
            OfferService.create_offer(buyer=buyer, dealership_inventory_id=inv.id)
        assert "Insufficient funds" in str(exc.value)

    def test_create_offer_out_of_stock(self, db):
        buyer = BuyerProfileFactory(balance=Decimal("50000"))
        inv = DealershipInventoryFactory(sale_price="10000", quantity=0)

        with pytest.raises(ValidationError) as exc:
            OfferService.create_offer(buyer=buyer, dealership_inventory_id=inv.id)
        assert "Out of stock" in str(exc.value)

    def test_create_offer_inventory_not_found(self, db):
        buyer = BuyerProfileFactory(balance=Decimal("50000"))
        with pytest.raises(ValidationError) as exc:
            OfferService.create_offer(buyer=buyer, dealership_inventory_id=99999)
        assert "not found" in str(exc.value)


@pytest.mark.service
class TestOfferProcessingServiceProcess:
    """offer CREATED → settle → PAID"""

    def test_process_paid_success(self, db):
        buyer = BuyerProfileFactory(balance=Decimal("50000"))
        inv = DealershipInventoryFactory(sale_price="10000", quantity=5)
        offer = OfferFactory(
            buyer=buyer,
            dealership_inventory=inv,
            final_price="10000",
            status="CREATED",
        )

        result = OfferProcessingService.process(offer.id)

        assert result == "paid"
        offer.refresh_from_db()
        assert offer.status == "PAID"
        inv.refresh_from_db()
        assert inv.quantity == 4
        buyer.refresh_from_db()
        assert buyer.balance == 40000  # 50000 - 10000

    def test_process_insufficient_funds_at_settle(self, db):
        buyer = BuyerProfileFactory(balance=Decimal("5000"))
        inv = DealershipInventoryFactory(sale_price="10000", quantity=5)
        offer = OfferFactory(
            buyer=buyer,
            dealership_inventory=inv,
            final_price="10000",
            status="CREATED",
        )

        result = OfferProcessingService.process(offer.id)

        assert result == "rejected"
        offer.refresh_from_db()
        assert offer.status == "REJECTED"
        assert offer.rejection_reason == "INSUFFICIENT_FUNDS"

    def test_process_out_of_stock_at_settle(self, db):
        buyer = BuyerProfileFactory(balance=Decimal("50000"))
        inv = DealershipInventoryFactory(sale_price="10000", quantity=0)
        offer = OfferFactory(
            buyer=buyer,
            dealership_inventory=inv,
            final_price="10000",
            status="CREATED",
        )

        result = OfferProcessingService.process(offer.id)

        assert result == "rejected"
        offer.refresh_from_db()
        assert offer.status == "REJECTED"
        assert offer.rejection_reason == "OUT_OF_STOCK"

    def test_process_already_processed(self, db):
        offer = OfferFactory(status="PAID")
        result = OfferProcessingService.process(offer.id)
        assert result == "already_processed"

    def test_process_not_found(self, db):
        result = OfferProcessingService.process(99999)
        assert result == "not_found"
