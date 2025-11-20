import asyncio
import json
import logging
import sys
import warnings
from collections.abc import Awaitable, Callable
from typing import Any, AnyStr

from vkmax.client import MaxClient, RPC_VERSION, _logger as vkmax_logger

logger = logging.getLogger(__name__)


class BetterMaxClient:
    def __init__(self) -> None:
        self.client = MaxClient()
        vkmax_logger.setLevel(logging.WARNING)

    async def connect(self) -> None:
        logger.info("Connecting")
        if self.client._connection:
            logger.warning("Tried to connect when already connected")
            return
        await self.client.connect()

    async def disconnect(self) -> None:
        logger.info("Disconnecting")
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
        logger.info("Reconnected")

    async def require_alive(self, timeout_s: float = 3) -> None:
        logger.info("Ping. Bomb armed")
        bomb = asyncio.create_task(_bomb_the_app(timeout_s))
        response = await self.client.invoke_method(
            opcode=1,
            payload={"interactive": True}
        )
        bomb.cancel()
        is_alive = response.get("opcode") == 1
        if not is_alive:
            logger.error("WS dead, dying with it.")
        else:
            logger.info("Pong.")

    async def is_alive(self, timeout_s: float = 3) -> bool:
        logger.info("Ping.")
        seq = next(self.client._seq)
        request = {
            "ver": RPC_VERSION,
            "cmd": 0,
            "seq": seq,
            "opcode": 1,
            "payload": {"interactive": True}
        }
        future = asyncio.get_event_loop().create_future()
        self.client._pending[seq] = future
        send_task = asyncio.create_task(
            self.client._connection.send(json.dumps(request))
        )
        try:
            await asyncio.wait_for(
                send_task,
                timeout=timeout_s
            )
            response = await asyncio.wait_for(
                future,
                timeout=timeout_s
            )
        except TimeoutError:
            #ping_task.cancel()
            logger.exception("Timeouted when pinging")
            return False
        else:
            is_alive = response.get("opcode") == 1
            if is_alive:
                logger.info("Pong.")
            else:
                logger.info("WS dead.")
            return is_alive

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


async def _bomb_the_app(timer_s: float) -> None:
    await asyncio.sleep(timer_s)
    logger.info("Kaboom.")
    sys.exit(1)
