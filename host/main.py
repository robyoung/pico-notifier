import asyncio
import sys

from loguru import logger

sys.path.append("./host")

from host import gcal, pico, github

logger.remove()
logger.add(sys.stderr, level="INFO")


async def handle_event(client, event):
    if isinstance(event, gcal.Event):
        buttons = (0, 1, 2, 3)
        await client.set_led(buttons, event.colour, 1.0)
        await client.set_key(buttons, [
            pico.Key.leds((0, 0, 0))
        ])
    elif isinstance(event, github.Event):
        button = event.offset + 4
        await client.set_led(button, event.colour, 1.0)
        await client.set_key(button, event.key_cmds)


@logger.catch
async def main():
    queue = asyncio.Queue()
    asyncio.create_task(gcal.send_events(queue))
    asyncio.create_task(github.send_events(queue))

    with pico.client() as client:
        print('Identifying as: {}'.format(await client.identify()))
        # clear all leds
        await client.set_led(tuple(range(16)), pico.OFF)

        # slack button
        await client.set_key(15, [
            pico.Key.leds(pico.GREEN),
            pico.Key.key('COMMAND'),
            pico.Key.sleep(0.2),
            pico.Key.write('slack'),
            pico.Key.key('ENTER'),
            pico.Key.sleep(2.0),
            pico.Key.leds(pico.CYAN),
        ])
        await client.set_led(15, pico.CYAN, 0.5)

        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=10.0)
            except asyncio.TimeoutError:
                logger.debug('No new event')
            else:
                await handle_event(client, event)


if __name__ == '__main__':
    asyncio.run(main())
