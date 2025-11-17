import asyncio

from maxtgfwd.max_integration import start_max
from maxtgfwd.telegram_integration import start_telegram


async def main():
    await asyncio.gather(*(
        start_max(),
        start_telegram()
    ))


if __name__ == "__main__":
    asyncio.run(main())
