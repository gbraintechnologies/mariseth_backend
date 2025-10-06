from datetime import timedelta

from celery import shared_task
from django.db.models import Q
from django.utils import timezone

from apps.shared.models import IntegrationLog
from apps.shared.tasks.manager_tasks import (
    sync_customer_to_manager, sync_employee_to_manager, sync_inventory_item_to_manager, sync_supplier_to_manager, sync_purchase_invoice_to_manager, sync_sales_invoice_to_manager
)
from mariseth.logging import logger

# Dispatcher to map model names to their corresponding sync tasks
TASK_DISPATCHER = {
    'customer': sync_customer_to_manager,
    'employee': sync_employee_to_manager,
    'product': sync_inventory_item_to_manager,
    'farm': sync_supplier_to_manager,
    'infloworder': sync_purchase_invoice_to_manager,
    'outfloworder': sync_sales_invoice_to_manager,
    # As we add more integrations, we will add their tasks here, e.g.:
    # 'supplier': sync_supplier_to_manager,
}

# A cap on how many times the scheduler will try to re-queue a task
MAX_SCHEDULER_RETRIES = 5


@shared_task(bind=True)
def retry_failed_integrations(self):
    """
    A periodic task that finds failed or stuck integration logs and re-queues them.
    """
    logger.info("--- Running retry_failed_integrations task ---")

    # Define the cutoff for what we consider a "stuck" pending task
    stuck_cutoff_time = timezone.now() - timedelta(hours=1)

    # Find all logs that are failed OR have been pending for too long,
    # and haven't exceeded the max retry count.
    logs_to_retry = IntegrationLog.objects.filter(
        Q(status=IntegrationLog.Status.FAILED) |
        Q(status=IntegrationLog.Status.PENDING, date_created__lt=stuck_cutoff_time)
    ).filter(retry_count__lt=MAX_SCHEDULER_RETRIES).iterator(chunk_size=200) # Process in batches

    retried_count = 0
    for log in logs_to_retry:
        model_name = log.content_type.model
        task_to_run = TASK_DISPATCHER.get(model_name)

        if task_to_run:
            try:
                # Reset status to PENDING and increment retry count before dispatching
                log.status = IntegrationLog.Status.PENDING
                # Note: We don't increment retry_count here, as the task itself does.
                # The filter `retry_count__lt` handles the limit.
                log.save(update_fields=['status'])

                task_to_run.delay(log.id)
                logger.info(f"Re-queued task for IntegrationLog {log.id} ({model_name})")
                retried_count += 1
            except Exception as e:
                logger.error(f"Failed to re-queue task for IntegrationLog {log.id}. Error: {e}")
        else:
            logger.warning(f"No task found in TASK_DISPATCHER for model '{model_name}' in IntegrationLog {log.id}")

    logger.info(f"--- Finished retry_failed_integrations task. Re-queued {retried_count} tasks. ---")
