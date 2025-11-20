import logging
logging.basicConfig(level=logging.INFO)

import asyncio
import pprint
import sys

from maxtgfwd.config import arg_parser, get_config, load_config
from maxtgfwd.max_client import BetterMaxClient
from maxtgfwd.max_integration import start_max
from maxtgfwd.telegram_integration import start_telegram


async def main():
    load_config()
    print(ns)
    logging.info("Config loaded: %s", pprint.pformat(get_config()))
    await asyncio.gather(*(
        start_max(),
        start_telegram()
    ))


async def main_auth():
    client = BetterMaxClient()
    await client.connect()
    token = await client.send_code(ns.phone)
    print("Code sent.")
    code = input("input code> ")
    account_data = await client.sign_in(token, int(code))
    login_token = account_data['payload']['tokenAttrs']['LOGIN']['token']
    print(
        f'--max-token "{login_token}" '
        f'--max-device {client.client.device_id}'
    )


if __name__ == "__main__":
    ns = arg_parser.parse_args()
    if ns.mode == "run":
        asyncio.run(main())
    elif ns.mode == "auth":
        if not ns.phone:
            print("You must specify a phone number")
            sys.exit(1)
        asyncio.run(main_auth())
    else:
        print("Unknown mode")
