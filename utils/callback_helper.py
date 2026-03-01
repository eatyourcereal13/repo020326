from aiogram.types import Message

def message_to_callback(message: Message, callback_data: str):
    class FakeCallback:
        def __init__(self, message, data):
            self.message = message
            self.from_user = message.from_user
            self.data = data
            self.id = "fake"
        
        async def answer(self, text=None, show_alert=False):
            if text:
                if show_alert:
                    await self.message.answer(f"⚠️ {text}")
                else:
                    pass
    
    return FakeCallback(message, callback_data)