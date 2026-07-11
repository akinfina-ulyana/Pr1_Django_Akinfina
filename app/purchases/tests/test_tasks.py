import datetime
from decimal import Decimal
from unittest.mock import patch

import pytest
from buyers.tests.factories import BuyerProfileFactory, OfferFactory
from dealership.tests.factories import DealershipFactory, DealershipInventoryFactory

from purchases.tasks import generate_tick_id, process_offer, run_auto_purchase


class TestGenerateTickId:
    def test_prefix(self):
        tick_id = generate_tick_id(window_minutes=10)
        assert tick_id.startswith("auto-purchase-")

    def test_format(self):
        tick_id = generate_tick_id(window_minutes=10)
        # auto-purchase-YYYYMMDD-HHMM (16 chars after prefix)
        suffix = tick_id.replace("auto-purchase-", "")
        assert len(suffix) == 13
        date_part, time_part = suffix.split("-")
        assert len(date_part) == 8
        assert len(time_part) == 4

    def test_rounds_minute_to_window(self):
        with patch("purchases.tasks.timezone.now") as mock_now:
            mock_now.return_value = datetime.datetime(2026, 7, 9, 14, 37, 23)
            tick_id = generate_tick_id(window_minutes=10)

            assert "1430" in tick_id


@pytest.mark.celery
class TestRunAutoPurchase:
    def test_dispatches_one_task_per_active_dealership(self, db):
        DealershipFactory.create_batch(3, is_active=True)

        with patch("purchases.tasks.process_dealership_purchase.delay") as mock_delay:
            result = run_auto_purchase()

        assert mock_delay.call_count == 3
        assert result["dispatched"] == 3
        assert "tick_id" in result

    def test_skips_inactive_dealerships(self, db):
        DealershipFactory.create_batch(2, is_active=True)
        DealershipFactory.create_batch(3, is_active=False)

        with patch("purchases.tasks.process_dealership_purchase.delay") as mock_delay:
            result = run_auto_purchase()

        assert mock_delay.call_count == 2
        assert result["dispatched"] == 2

    def test_no_active_dealerships_dispatches_zero(self, db):
        DealershipFactory.create_batch(2, is_active=False)

        with patch("purchases.tasks.process_dealership_purchase.delay") as mock_delay:
            result = run_auto_purchase()

        assert mock_delay.call_count == 0
        assert result["dispatched"] == 0

    def test_subtask_not_executed_when_mocked(self, db):
        DealershipFactory(is_active=True)

        with patch("purchases.tasks.process_dealership_purchase.delay"):
            run_auto_purchase()

        from purchases.models import AutoPurchaseLog

        assert AutoPurchaseLog.objects.count() == 0


@pytest.mark.celery
class TestProcessOfferEager:
    def test_task_returns_paid_result(self, db):
        buyer = BuyerProfileFactory(balance=Decimal("50000"))
        inv = DealershipInventoryFactory(sale_price=Decimal("10000"), quantity=5)
        offer = OfferFactory(
            buyer=buyer,
            dealership_inventory=inv,
            final_price=Decimal("10000"),
            status="CREATED",
        )

        result = process_offer.apply(args=(offer.id,))

        assert result.result == {"offer_id": offer.id, "result": "paid"}

    def test_task_settles_offer(self, db):
        buyer = BuyerProfileFactory(balance=Decimal("50000"))
        inv = DealershipInventoryFactory(sale_price=Decimal("10000"), quantity=5)
        offer = OfferFactory(
            buyer=buyer,
            dealership_inventory=inv,
            final_price=Decimal("10000"),
            status="CREATED",
        )

        process_offer.apply(args=(offer.id,))

        offer.refresh_from_db()
        inv.refresh_from_db()
        buyer.refresh_from_db()

        assert offer.status == "PAID"
        assert inv.quantity == 4
        assert buyer.balance == Decimal("40000")

    def test_task_not_found(self, db):
        result = process_offer.apply(args=(99999,))
        assert result.result == {"offer_id": 99999, "result": "not_found"}

    def test_task_already_processed(self, db):
        offer = OfferFactory(status="PAID")
        result = process_offer.apply(args=(offer.id,))
        assert result.result["result"] == "already_processed"


@pytest.mark.celery
class TestProcessOfferRetry:
    def test_retry_on_exception(self, db, mocker):
        offer = OfferFactory(status="CREATED")

        mocker.patch(
            "buyers.services.OfferProcessingService.process",
            side_effect=Exception("DB connection lost"),
        )
        retry_mock = mocker.patch.object(process_offer, "retry", side_effect=Exception("retry called"))
        with pytest.raises(Exception, match="retry called"):
            process_offer.apply(args=(offer.id,))

        retry_mock.assert_called_once()

    def test_successful_no_retry(self, db, mocker):
        buyer = BuyerProfileFactory(balance=Decimal("50000"))
        inv = DealershipInventoryFactory(sale_price=Decimal("10000"), quantity=5)
        offer = OfferFactory(
            buyer=buyer,
            dealership_inventory=inv,
            final_price=Decimal("10000"),
        )

        spy = mocker.patch.object(process_offer, "retry")

        process_offer.apply(args=(offer.id,))

        spy.assert_not_called()
