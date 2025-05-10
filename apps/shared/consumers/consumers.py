from channels.exceptions import StopConsumer
from channels.generic.websocket import AsyncJsonWebsocketConsumer


class SharedSocketConsumer(AsyncJsonWebsocketConsumer):

    async def connect(self):
        self.user = self.scope['user']
        if self.user.is_authenticated:
            self.room_group_name = f'user_{self.user.id}'
            await self.channel_layer.group_add(self.room_group_name, self.channel_name)
            print(f'connected user: {self.user}')
        await self.accept()

    async def disconnect(self, code):
        if hasattr(self, 'room_group_name'):
            if self.user:
                print(f'disconnected user: {self.user}')
            await self.channel_layer.group_discard(
                self.room_group_name, self.channel_name
            )

    def websocket_disconnect(self, event):
        print('websocket disconnected...', event)

        raise StopConsumer()

    async def broadcast(self, event):
        """
        Handler for the 'broadcast' message type.
        """
        print(f"Broadcast event received: {event}")
        # Remove any processing of the event that might cause errors
        try:
            await self.send_json({
                'message_type': event.get('message_type'),
                'message': event.get('message')
            })
            print("Message sent to client")
        except Exception as e:
            print(f"Error in broadcast handler: {e}")

    def format_time(self, seconds):
        """Utility method to format time duration nicely."""
        if seconds < 60:
            return f"{seconds:.2f} seconds"
        elif seconds < 3600:
            minutes = int(seconds / 60)
            seconds = seconds % 60
            return f"{minutes} minute(s) and {seconds:.2f} seconds"
        else:
            hours = int(seconds / 3600)
            minutes = (seconds % 3600) // 60
            seconds = seconds % 60
            return f"{hours} hour(s), {minutes} minute(s) and {seconds:.2f} seconds"
