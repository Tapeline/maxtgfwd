import asyncio
import logging
from typing import Any, Final

import aiohttp
from vkmax.client import MaxClient
from vkmax.functions.uploads import download_file, download_video

from maxtgfwd.config import get_config
from maxtgfwd.max_client import BetterMaxClient
from maxtgfwd.message import Message, forward_to_all_telegram

_OP_RECEIVE_MESSAGE: Final = {64, 128}

logger = logging.getLogger(__name__)
max_client = BetterMaxClient()


async def packet_callback(
    client: MaxClient,
    packet: dict[str, Any]
) -> None:
    if packet["opcode"] in _OP_RECEIVE_MESSAGE:
        logger.info("Got a message, opcode %d", packet["opcode"])
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
    logger.info("Retrieving files")
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
    logger.info("Retrieving photos")
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
    logger.info("Retrieving videos")
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


_running_hc_task = None


async def healthcheck_task():
    logger.info("Periodic healthcheck started")
    try:
        while True:
            is_alive = await max_client.is_alive()
            if not is_alive:
                logger.error("Max connection found dead, quitting")
                await stop_max()
                exit(1)
            await asyncio.sleep(get_config().healthcheck_period_s)
    except asyncio.CancelledError:
        logger.info("Periodic healthcheck task stopped")
        return


async def start_max():
    global _running_hc_task
    logger.info("Starting Max")
    await max_client.connect()
    logger.info("Connected")
    await max_client.login_by_token(
        get_config().auth.token, get_config().auth.device
    )
    _running_hc_task = asyncio.create_task(healthcheck_task())
    logger.info("Up and running")
    await max_client.set_callback(packet_callback)


async def restart_max():
    global _running_hc_task
    if _running_hc_task:
        _running_hc_task.cancel()
    await max_client.reconnect()
    await max_client.login_by_token(
        get_config().auth.token, get_config().auth.device
    )
    _running_hc_task = asyncio.create_task(healthcheck_task())
    logger.info("Restarted")


async def stop_max():
    await max_client.disconnect()
