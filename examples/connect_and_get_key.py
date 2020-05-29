'''Connect and get a key

Copyright (c) 2020 Machine Zone, Inc. All rights reserved.
'''

import asyncio
import time
from rcc.client import RedisClient


async def getKey():
    client = RedisClient()

    start = time.time()
    res = await client.send('GET', 'testkey')
    print(res)
    print(time.time() - start)


if __name__ == '__main__':
    asyncio.get_event_loop().run_until_complete(getKey())
