import asyncio
import json
import logging
import warnings
from collections.abc import Awaitable, Callable
from typing import Any, AnyStr

from vkmax.client import MaxClient, RPC_VERSION

logger = logging.getLogger(__name__)


class BetterMaxClient:
    def __init__(self) -> None:
        self.client = MaxClient()

    async def connect(self) -> None:
        if self.client._connection:
            logger.warning("Tried to connect when already connected")
            return
        await self.client.connect()

    async def disconnect(self) -> None:
        if not self.client._keepalive_task:
            logger.warning("Disconnecting with dead keepalive")
        else:
            self.client._keepalive_task.cancel()
            self.client._keepalive_task = None
        self.client._recv_task.cancel()
        if not self.client._connection:
            logger.warning("Tried to disconnect when already disconnected")
        else:
            await self.client._connection.close()
        if self.client._http_pool:
            await self.client._http_pool.close()

    async def reconnect(self) -> None:
        await self.disconnect()
        await self.connect()

    async def is_alive(self, timeout_s: float = 3) -> bool:
        try:
            response = await asyncio.wait_for(
                self.client.invoke_method(
                    opcode=1,
                    payload={"interactive": True}
                ),
                timeout=timeout_s
            )
            return response.get("opcode") == 1
        except TimeoutError:
            logger.exception("Timeouted when pinging")
            return False

    async def send_code(self, phone: str) -> str:
        return await self.client.send_code(phone)

    async def sign_in(self, sms_token: str, sms_code: int) -> dict[str, Any]:
        if self.client._keepalive_task:
            self.client._keepalive_task.cancel()
            self.client._keepalive_task = None
        return await self.client.sign_in(sms_token, sms_code)

    async def login_by_token(
        self,
        token: str,
        device_id: str | None = None
    ) -> dict[str, Any]:
        if self.client._keepalive_task:
            self.client._keepalive_task.cancel()
            self.client._keepalive_task = None
        return await self.client.login_by_token(token, device_id)

    async def set_callback(self, function: Callable[
        [MaxClient, dict[str, Any]], Awaitable[None]
    ]) -> None:
        await self.client.set_callback(function)
