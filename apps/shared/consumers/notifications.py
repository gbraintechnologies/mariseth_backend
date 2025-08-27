from typing import List, Dict

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer



def send_client_notification(
        message_type: str,
        message: Dict,
        group_names: List[str]
):
    print("SENDING CLIENT NOTIFICATION")
    channel_layer = get_channel_layer()
    print(channel_layer)
    print(group_names)
    for group_name in group_names:
        async_to_sync(channel_layer.group_send)(
            group_name,
            {
                'type': 'broadcast',
                'message_type': message_type,
                'message': message,
            }
        )
    print("CLIENT NOTIFICATION SENT")
