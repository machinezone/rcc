'''Generic commands

Copyright (c) 2020 Machine Zone, Inc. All rights reserved.
'''
import asyncio


class GenericCommandsMixin:
    async def monitor(self, callback, obj):
        '''Will take over the connection.
           Do not send any other command while this is running.
        '''
        response = await self.send('MONITOR')
        self.connection.takeOver()

        try:
            while True:
                response = await self.readResponse(self.connection)
                await callback(self, obj, response)

        except asyncio.CancelledError:
            self.connection.release()
