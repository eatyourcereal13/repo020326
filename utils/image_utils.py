import os
from aiogram.types import FSInputFile
from typing import Optional, Dict
from config import config

_image_cache: Dict[str, FSInputFile] = {}

def get_image(image_name: str) -> Optional[FSInputFile]:
    if image_name in _image_cache:
        return _image_cache[image_name]
    
    image_path = os.path.join(config.BASE_DIR, 'static', image_name)
    
    if os.path.exists(image_path):
        photo = FSInputFile(image_path)
        _image_cache[image_name] = photo
        return photo
    
    return None


async def send_with_photo(message_or_callback, text: str, image_name: str, reply_markup=None):
    image = get_image(image_name)
    
    try:
        if image:
            if hasattr(message_or_callback, 'message'):
                await message_or_callback.message.answer_photo(
                    photo=image,
                    caption=text,
                    reply_markup=reply_markup
                )
            else:
                await message_or_callback.answer_photo(
                    photo=image,
                    caption=text,
                    reply_markup=reply_markup
                )
        else:
            if hasattr(message_or_callback, 'message'):
                await message_or_callback.message.answer(text, reply_markup=reply_markup)
            else:
                await message_or_callback.answer(text, reply_markup=reply_markup)
    except Exception as e:
        if hasattr(message_or_callback, 'message'):
            await message_or_callback.message.answer(text, reply_markup=reply_markup)
        else:
            await message_or_callback.answer(text, reply_markup=reply_markup)