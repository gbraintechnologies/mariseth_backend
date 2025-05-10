import asyncio
from typing import Dict, List, Optional, Union

from celery import shared_task
from django.contrib.auth import get_user_model

from apps.communication.sms.service import send_bulk_messages
from mariseth.logging import logger
from apps.communication.models import Message

User = get_user_model()


@shared_task
def send_messages_async(
    recipients: Union[List[int], str],
    message_id: int,
    extra_context: Optional[Dict] = None
):
    """
    Task to send messages asynchronously.

    Args:
        recipients: A list of recipient IDs or 'all'.
        message_id: The ID of the Message instance.
        extra_context: Additional context for rendering message templates.
    """
    try:
        message = Message.objects.get(id=message_id)
        asyncio.run(
            send_bulk_messages(
                recipients=recipients,
                message=message,
                extra_context=extra_context
            )
        )
    except Exception as e:
        logger.error(f"Error in send_messages_async task: {e}")
        raise
