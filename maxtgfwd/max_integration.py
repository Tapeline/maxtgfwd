import asyncio
from pathlib import Path
from typing import Any, Final

import aiohttp
from vkmax.client import MaxClient
from vkmax.functions.uploads import download_file, download_video

from maxtgfwd.config import session_file
from maxtgfwd.message import Message, forward_to_all_telegram

_OP_RECEIVE_MESSAGE: Final = {64, 128}

max_client = MaxClient()


async def packet_callback(
    client: MaxClient,
    packet: dict[str, Any]
) -> None:
    if packet["opcode"] in _OP_RECEIVE_MESSAGE:
        text = packet["payload"]["message"]["text"]
        attachments = packet["payload"]["message"]["attaches"]
        photos = await _get_photos(attachments)
        videos = await _get_videos(
            client,
            packet["payload"]["chatId"],
            packet["payload"]["message"]["id"],
            attachments
        )
        files = await _get_files(
            client,
            packet["payload"]["chatId"],
            packet["payload"]["message"]["id"],
            attachments
        )
        message = Message(
            text=text,
            videos=videos,
            files=files,
            photos=photos,
            max_source_chat=packet["payload"]["chatId"]
        )
        await forward_to_all_telegram(message)


async def _get_files(
    client: MaxClient,
    chat_id: int,
    message_id: str,
    attachments
) -> list[tuple[str, bytes]]:
    files = []
    for attachment in filter(
        lambda attachment: attachment["_type"] == "FILE", attachments
    ):
        url = await download_file(
            client=client,
            chat_id=chat_id,
            file_id=attachment["fileId"],
            message_id=message_id
        )
        filename = attachment["name"]
        async with (
            aiohttp.ClientSession() as session,
            session.get(url) as response,
        ):
            files.append((filename, await response.read()))
    return files


async def _get_photos(
    attachments,
) -> list[bytes]:
    files = []
    for attachment in filter(
        lambda attachment: attachment["_type"] == "PHOTO", attachments
    ):
        async with (
            aiohttp.ClientSession() as session,
            session.get(attachment["baseUrl"]) as response,
        ):
            files.append(await response.read())
    return files


async def _get_videos(
    client: MaxClient,
    chat_id: int,
    message_id: str,
    attachments,
) -> list[bytes]:
    files = []
    for attachment in filter(
        lambda attachment: attachment["_type"] == "VIDEO", attachments
    ):
        url = await download_video(
            client=client,
            chat_id=chat_id,
            video_id=attachment["videoId"],
            message_id=message_id
        )
        print(url)
        print(attachment)
        async with (
            aiohttp.ClientSession() as session,
            session.get(url) as response,
        ):
            files.append(await response.read())
    return files


async def start_max():
    await max_client.connect()
    if not session_file.exists():
        print("You need to login!")
    else:
        contents = session_file.read_text()
        device_id, login_token = contents.split('\n', maxsplit=1)
        try:
            await max_client.login_by_token(login_token, device_id)
        except:
            print("Couldn't login by token")
    await max_client.set_callback(packet_callback)
    #await asyncio.Future()
