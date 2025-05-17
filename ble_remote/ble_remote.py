#!/usr/bin/env python3

import asyncio
import logging
import sys
import threading

from evdev import categorize, ecodes

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger(__name__)

from device_selection import select_device, select_device_interactive
from pypilot_state import Action, pypilot_comms_loop, queue_action

KEY_ACTION_MAP = {
    ecodes.KEY_UP: Action.PLUS_ONE,
    ecodes.KEY_DOWN: Action.MINUS_ONE,
    ecodes.KEY_SLASH: Action.PLUS_FIVE,
    ecodes.KEY_DOT: Action.MINUS_FIVE,
    ecodes.KEY_ENTER: Action.TOGGLE,
    ecodes.KEY_SPACE: Action.TOGGLE,
    # SmartRemote
    ecodes.KEY_PLAYPAUSE: Action.TOGGLE,
    ecodes.KEY_PREVIOUSSONG: Action.MINUS_ONE,
    ecodes.KEY_NEXTSONG: Action.PLUS_ONE,
    ecodes.KEY_VOLUMEUP: Action.PLUS_FIVE,
    ecodes.KEY_VOLUMEDOWN: Action.MINUS_FIVE,
    # Long right key press
    # ecodes.KEY_POWER: Action.TOGGLE,
    # Long left key press
    # ecodes.KEY_HOMEPAGE: Action.TOGGLE,
}


def pypilot_comms_asyncio():
    asyncio.run(pypilot_comms_loop())


def start_pypilot_comms():
    # Start the pypilot communication loop in a separate thread
    comms_thread = threading.Thread(target=pypilot_comms_asyncio, daemon=True)
    comms_thread.start()


async def grab_and_handle_events_for_device(device):
    device.grab()
    logger.debug(f"Device {device.name} {device.path} {device.uniq} grabbed.")
    async for event in device.async_read_loop():
        if event.type == ecodes.EV_KEY:
            key_event = categorize(event)
            logger.info(
                f"Key: {key_event.keycode}, State: {key_event.keystate} from {device.name}"
            )
            if key_event.keystate == 0:
                action = KEY_ACTION_MAP.get(ecodes.ecodes[key_event.keycode])
                if action:
                    queue_action(action)


def main():
    selected_devices = []
    if len(sys.argv) > 1:
        selected_devices = [select_device(arg) for arg in sys.argv[1:]]
        if not all(selected_devices):
            logger.error(
                "One or more devices could not be found. Please check the device paths."
            )
            sys.exit(1)
    else:
        selected_devices = [select_device_interactive()]

    logger.info("Listening for events. Press Ctrl+C to stop.")
    start_pypilot_comms()

    try:
        loop = asyncio.get_event_loop()
        tasks = [
            loop.create_task(grab_and_handle_events_for_device(device))
            for device in selected_devices
        ]
        loop.run_until_complete(asyncio.wait(tasks))
    except KeyboardInterrupt:
        logger.info("\nStopped listening for events.")
    except Exception as e:
        logger.info(f"An error occurred: {e}")


if __name__ == "__main__":
    main()
