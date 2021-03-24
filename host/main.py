import asyncio
from datetime import timedelta
import sys

sys.path.append("./host")

from host import gcal, pico

# TODO: Retrieve next calendar event.
# - If 5 minute reminder set top row yellow.
# - If 0 minute reminder set top row red.
# - If any button is pressed clear all

async def main():
    queue = asyncio.Queue()
    asyncio.create_task(gcal.send_events(queue))

    with pico.client() as client:
        print('Identifying as: {}'.format(await client.identify()))

        await client.set_key(12, [
            pico.Key.leds(pico.GREEN),
            pico.Key.key('COMMAND'),
            pico.Key.sleep(0.2),
            pico.Key.write('slack'),
            pico.Key.key('ENTER'),
            pico.Key.sleep(2.0),
            pico.Key.leds(pico.CYAN),
        ])
        await client.set_led(12, pico.CYAN, 0.5)

        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=10.0)
            except asyncio.TimeoutError:
                print('No new event')
            else:
                if isinstance(event, gcal.Event):
                    buttons = (0, 1, 2, 3)
                    if event.reminder == timedelta(0):
                        await client.set_led(buttons, pico.RED, 1.0)
                        await client.set_key(buttons, [
                            pico.Key.leds((0, 0, 0))
                        ])
                    if event.reminder <= timedelta(minutes=5):
                        pass



if __name__ == '__main__':
    asyncio.run(main())
