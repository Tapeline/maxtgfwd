import asyncio
import itertools
import uuid

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import (
    BufferedInputFile,
    InputMediaPhoto,
    InputMediaVideo,
    Message as TgMessage
)

from maxtgfwd.config import config, session_file
from maxtgfwd.message import Message

bot = Bot(
    token=config.tg_token,
    default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN)
)
dp = Dispatcher()
current_login_token = None


async def forward_to_telegram(message: Message, chat_id: int) -> None:
    if message.files:
        await asyncio.gather(
            *(
                bot.send_document(
                    chat_id=chat_id,
                    caption=message.text,
                    document=BufferedInputFile(
                        filename=filename, file=contents
                    )
                )
                for filename, contents in message.files
            )
        )
        message.files.clear()
        message.text = ""
    if message.photos:
        await asyncio.gather(
            *(
                bot.send_media_group(
                    chat_id=chat_id,
                    media=[
                        InputMediaPhoto(
                            media=BufferedInputFile(photo, str(uuid.uuid4()))
                        )
                        for photo in batch
                    ]
                )
                for batch in itertools.batched(message.photos, 10)
            )
        )
        message.photos.clear()
    if message.videos:
        await asyncio.gather(
            *(
                bot.send_media_group(
                    chat_id=chat_id,
                    media=[
                        InputMediaVideo(
                            media=BufferedInputFile(video, str(uuid.uuid4()))
                        )
                        for video in batch
                    ]
                )
                for batch in itertools.batched(message.videos, 10)
            )
        )
        message.videos.clear()
    if message.text:
        await bot.send_message(
            chat_id=chat_id,
            text=message.text
        )


@dp.message(Command("login"))
async def send_code(message: TgMessage):
    from maxtgfwd.max_integration import max_client
    global current_login_token
    if message.chat.username != config.owner_handle:
        await message.reply("You don't have permission to do that.")
        return
    current_login_token = await max_client.send_code(config.auth_phone_number)
    await message.reply("SMS code sent.")


@dp.message(Command("sms"))
async def complete_auth(message: TgMessage):
    from maxtgfwd.max_integration import max_client
    global current_login_token
    if message.chat.username != config.owner_handle:
        await message.reply("You don't have permission to do that.")
        return
    if not current_login_token:
        await message.reply("Send an SMS code first.")
        return
    try:
        await max_client._stop_keepalive_task()
        account_data = await max_client.sign_in(
            current_login_token,
            int(message.text.split()[-1])
        )
    except Exception as exc:
        await message.reply(str(exc))
    else:
        login_token = account_data['payload']['tokenAttrs']['LOGIN']['token']
        session_file.write_text(f'{max_client.device_id}\n{login_token}')
        await max_client.disconnect()
        await max_client._stop_keepalive_task()
        await max_client.connect()
        await message.reply("Restarted max")
        await max_client.login_by_token(login_token, max_client.device_id)
        current_login_token = None
        await message.reply("Logged in.")


@dp.message(Command("thischatid"))
async def get_this_chat_id(message: TgMessage):
    await message.reply(f"This chat: `{message.chat.id}`")


async def start_telegram():
    await dp.start_polling(bot)
