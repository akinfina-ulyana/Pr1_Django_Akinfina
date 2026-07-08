import logging

from django.utils import timezone

from celery import shared_task
from dealership.models import Dealership

from purchases.services import AutoPurchaseService, PrioritySupplierRefresher


logger = logging.getLogger(__name__)


def generate_tick_id(window_minutes: int = 10) -> str:
    now = timezone.now()
    rounded_minute = (now.minute // window_minutes) * window_minutes
    rounded = now.replace(minute=rounded_minute, second=0, microsecond=0)
    return f"auto-purchase-{rounded.strftime('%Y%m%d-%H%M')}"


@shared_task(name="purchases.tasks.run_auto_purchase")
def run_auto_purchase():
    tick_id = generate_tick_id(window_minutes=10)
    logger.info("Auto-purchase orchestrator start, tick=%s", tick_id)

    dealership_ids = list(Dealership.objects.filter(is_active=True).values_list("id", flat=True))

    for dealership_id in dealership_ids:
        process_dealership_purchase.delay(dealership_id, tick_id)

    logger.info("Dispatched %d subtasks, tick=%s", len(dealership_ids), tick_id)
    return {"dispatched": len(dealership_ids), "tick_id": tick_id}


@shared_task(
    name="purchases.tasks.process_dealership_purchase",
    bind=True,
    max_retries=2,
    default_retry_delay=30,
)
def process_dealership_purchase(self, dealership_id: int, tick_id: str):
    try:
        return AutoPurchaseService.process_dealership(dealership_id, tick_id)
    except Exception as exc:
        logger.exception("process_dealership_purchase failed for %s", dealership_id)
        # Exponential backoff: 30s, 60s, 120s.
        raise self.retry(exc=exc, countdown=30 * (2**self.request.retries)) from exc


@shared_task(name="purchases.tasks.refresh_priority_suppliers")
def refresh_priority_suppliers():
    logger.info("Priority suppliers refresh: start")

    dealership_ids = list(Dealership.objects.filter(is_active=True).values_list("id", flat=True))

    for dealership_id in dealership_ids:
        process_dealership_priority_refresh.delay(dealership_id)

    return {"dispatched": len(dealership_ids)}


@shared_task(name="purchases.tasks.process_dealership_priority_refresh")
def process_dealership_priority_refresh(dealership_id: int):
    """PrioritySuppliers update for one dealership."""
    try:
        dealership = Dealership.objects.get(pk=dealership_id, is_active=True)
    except Dealership.DoesNotExist:
        logger.warning("Dealership %s not found", dealership_id)
        return {"added": 0, "removed": 0}

    return PrioritySupplierRefresher.refresh_for_dealership(dealership)


@shared_task(name="purchases.tasks.process_offer", bind=True, max_retries=3, default_retry_delay=10)
def process_offer(self, offer_id: int):
    from buyers.services import OfferProcessingService

    try:
        result = OfferProcessingService.process(offer_id)
        logger.info("process_offer offer_id=%s result=%s", offer_id, result)
        return {"offer_id": offer_id, "result": result}

    except Exception as exc:
        logger.exception("process_offer failed for %s", offer_id)
        raise self.retry(
            exc=exc,
            countdown=10 * (2**self.request.retries),
        ) from exc
