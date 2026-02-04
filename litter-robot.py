#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import asyncio
import time
from pylitterbot import Account, enums
from datetime import datetime
import json

def get_time(t=None, frac=True):
    fmt_str = '%m/%d/%Y %H:%M:%S'
    if frac:
        fmt_str += '.%f'
    if t:
        return datetime.fromtimestamp(t).strftime(fmt_str)
    else:
        return datetime.fromtimestamp(time.time()).strftime(fmt_str)

def log(msg):
    print(f'{get_time(None, False)}: {msg}')

# Set email and password for initial authentication.
async def main(user, pas) -> None:
    reset_mins = 10
    clean_hrs = 8
    #start script with a clean
    i=int(clean_hrs/(reset_mins/60)) - 1
    temp_reset = None
    while True:
        """Run main function."""
        # Create an account.
        account = Account()
        try:
            # Connect to the API and load robots.
            log("Connect")
            await account.connect(
                username=user, password=pas, load_robots=True, load_pets=True
            )
            log("Check")
            # Clean robot every 12hrs and reset every 'reset_hrs' hrs
            i += 1
            for robot in account.robots:
                await robot.refresh()
                if i%int(clean_hrs/(reset_mins/60)) == 0 and robot.status != enums.LitterBoxStatus.CLEAN_CYCLE:
                    await robot.start_cleaning()
                    log(f'Clean: {robot.name}')
                    i = 0
                await robot.refresh()
                stat = robot.status
                if stat == enums.LitterBoxStatus.PAUSED or stat == enums.LitterBoxStatus.CAT_SENSOR_INTERRUPTED:
                    await robot.reset()
                    log(f'Reset: {robot.name}')
        finally:
            log("Disconnect")
            # Disconnect from the API.
            await account.disconnect()
        time.sleep(60*reset_mins)

if __name__ == "__main__":
    with open('account_info.json') as f:
        account_info = json.load(f)

    asyncio.run(main(account_info["user"], account_info["password"]))
