import asyncio
import logging
from collections.abc import Iterable
from dataclasses import dataclass

from maxtgfwd.config import get_config

logger = logging.getLogger(__name__)


@dataclass
class Message:
    text: str
    photos: list[bytes]
    videos: list[bytes]
    files: list[tuple[str, bytes]]
    max_source_chat: int

    def __post_init__(self):
        if self.text:
            self.text = f"{self.text}\n__forwarded from MAX__"


def _all_tg_chats_for_max_source(source: int) -> Iterable[int]:
    for collector in get_config().collectors:
        if source in collector.sources:
            yield from collector.sinks


async def forward_to_all_telegram(message: Message) -> None:
    from maxtgfwd.telegram_integration import forward_to_telegram
    sinks = _all_tg_chats_for_max_source(message.max_source_chat)
    logger.info("Forwarding to sinks %s", str(sinks))
    await asyncio.gather(*(
        forward_to_telegram(message, chat) for chat in sinks
    ))
