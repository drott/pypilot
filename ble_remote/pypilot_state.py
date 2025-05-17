import asyncio
import logging
from enum import Enum

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

HOST = "localhost"
PORT = 23322

imu_values = []

ap_state = {
    "ap.enabled": False,
    "ap.heading_command": 0,
    "ap.heading": 0,
    "imu.heading": 0,
}

send_queue = asyncio.Queue()


async def connect_to_server():
    reader, writer = await asyncio.open_connection(HOST, PORT)
    logger.info(f"Connected to {HOST}:{PORT}")
    return reader, writer


async def update_state_from_readings(reader):
    while True:
        line = await reader.readuntil()
        if not line:
            return
        line = line.decode().strip()
        logger.debug(f"Received line: {line}")
        if "ap.heading=" in line:
            ap_state["ap.heading"] = float(line.split("=")[1])
        elif "ap.enabled=" in line:
            ap_state["ap.enabled"] = line.split("=")[1].lower() == "true"
        elif "imu.heading=" in line:
            ap_state["imu.heading"] = float(line.split("=")[1])
        elif "ap.heading_command=" in line:
            ap_state["ap.heading_command"] = float(line.split("=")[1])
        await asyncio.sleep(0)  # Yield to asyncio main loop


async def send_from_queue(writer):
    while True:
        pypilot_write_msg = await send_queue.get()
        logger.debug(f"Retrieved queue item: {pypilot_write_msg}")
        if pypilot_write_msg is None:
            break
        logger.debug(f"Sending to pypilot: {pypilot_write_msg}")
        writer.write(pypilot_write_msg)
        await writer.drain()
        send_queue.task_done()


async def init_watches(writer):
    watches = [
        "ap.heading",
        "ap.heading_command",
        "imu.heading",
        "ap.mode",
        "ap.enabled",
    ]
    watch_string = 'watch={{{}}}\n'.format( ", ".join([f"\"{watch}\" : 0" for watch in watches]))
    writer.write(
        watch_string.encode()
    )
    await writer.drain()


class Action(Enum):
    ENGAGE = "Engage"
    DISENGAGE = "Disengage"
    PLUS_ONE = "PlusOne"
    MINUS_ONE = "MinusOne"
    PLUS_FIVE = "PlusFive"
    MINUS_FIVE = "MinusFive"
    TOGGLE = "Toggle"

def queue_action(action: Action):
    logger.info(f"Queued action: {action}")
    # TODO: Handle wind mode, similar to hat.py
    # TODO: Handle servo command, when not engaged
    if action == Action.ENGAGE:
        send_queue.put_nowait(b"ap.heading_command=%f\n" % ap_state["ap.heading"])
        send_queue.put_nowait(b"ap.enabled=true\n")
    elif action == Action.DISENGAGE:
        send_queue.put_nowait(b"ap.enabled=false\n")
    elif action == Action.PLUS_ONE:
        send_queue.put_nowait(b"ap.heading_command=%f\n" % (ap_state["ap.heading_command"] + 1))
    elif action == Action.PLUS_FIVE:
        send_queue.put_nowait(b"ap.heading_command=%f\n" % (ap_state["ap.heading_command"] + 5))
    elif action == Action.MINUS_FIVE:
        send_queue.put_nowait(b"ap.heading_command=%f\n" % (ap_state["ap.heading_command"] - 5))
    elif action == Action.MINUS_ONE:
        send_queue.put_nowait(b"ap.heading_command=%f\n" % (ap_state["ap.heading_command"] - 1))
    elif action == Action.TOGGLE:
        if ap_state["ap.enabled"]:
            queue_action(Action.DISENGAGE)
        else:
            queue_action(Action.ENGAGE)


async def dump_ap_state():
    while True:
        await asyncio.sleep(0.5)
        logger.info(f"AP State: {ap_state}")


async def pypilot_comms_loop():
    backoff = 1
    while True:
        try:
            connect_task = asyncio.create_task(connect_to_server())
            logger.info("Attempting to connect...")
            reader, writer = await connect_task
            logger.info("Connected successfully.")
            backoff = 1
            async with asyncio.TaskGroup() as group:
                logger.info("Starting tasks...")
                for routine in [
                    init_watches(writer),
                    update_state_from_readings(reader),
                    send_from_queue(writer),
                    dump_ap_state(),
                ]:
                    group.create_task(routine)
            backoff = 1  # Reset backoff on successful connection
        except* Exception as e:
            logger.error(f"Error occurred: {e}\nReconnecting in {backoff} seconds...")
            await asyncio.sleep(backoff)
            backoff *= 2
            if backoff > 15:
                backoff = 15

if __name__ == "__main__":
    asyncio.run(pypilot_comms_loop())
