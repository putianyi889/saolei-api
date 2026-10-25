"""Set SAOLEI_API_KEY, then run: python examples/quickstart.py."""

import os

from saolei_api import Client

with Client(os.environ["SAOLEI_API_KEY"]) as api:
    print(api.stats().model_dump_json(by_alias=True, indent=2))
    for user in api.user_list([1, 2]).users:
        print(user.id, user.name, user.scores.sum_time)
