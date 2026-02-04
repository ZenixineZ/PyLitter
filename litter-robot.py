#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import asyncio
import time
from pylitterbot import Account, enums
from datetime import datetime
import json
import sys
import os

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

async def main(user, pas) -> None:
    reset_mins = 10
    clean_hrs = 8
    max_retries = 3
    retry_count = 0
    
    # Validate configuration
    if reset_mins < 1:
        log("ERROR: reset_mins must be at least 1")
        sys.exit(1)
    
    check_interval = int(clean_hrs/(reset_mins/60))
    i = check_interval - 1  # Start with a clean
    
    while True:
        account = Account()
        try:
            log("Connect")
            await account.connect(
                username=user, password=pas, load_robots=True, load_pets=True
            )
            retry_count = 0  # Reset on successful connection
            
            log("Check")
            i += 1
            
            for robot in account.robots:
                await robot.refresh()
                
                # Clean robot every clean_hrs hours
                if i % check_interval == 0 and robot.status != enums.LitterBoxStatus.CLEAN_CYCLE:
                    await robot.start_cleaning()
                    log(f'Clean: {robot.name}')
                    i = 0
                    # Wait a bit before checking status
                    await asyncio.sleep(5)
                
                # Check status after potential cleaning
                await robot.refresh()
                stat = robot.status
                
                if stat == enums.LitterBoxStatus.PAUSED or stat == enums.LitterBoxStatus.CAT_SENSOR_INTERRUPTED:
                    await robot.reset()
                    log(f'Reset: {robot.name}')
                    
        except Exception as e:
            retry_count += 1
            log(f"Error: {e}")
            if retry_count >= max_retries:
                log(f"Max retries ({max_retries}) reached. Waiting before retry...")
                time.sleep(60 * 5)  # Wait 5 minutes on repeated failures
                retry_count = 0
        finally:
            log("Disconnect")
            try:
                await account.disconnect()
            except:
                pass  # Already disconnected or error
                
        time.sleep(60 * reset_mins)

if __name__ == "__main__":
    # Check if account_info.json exists
    if not os.path.exists('account_info.json'):
        print("ERROR: account_info.json not found!")
        print("Please copy account_info_sample.json to account_info.json and add your credentials.")
        sys.exit(1)
    
    try:
        with open('account_info.json') as f:
            account_info = json.load(f)
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON in account_info.json: {e}")
        sys.exit(1)
    
    # Validate required fields
    if 'user' not in account_info or 'password' not in account_info:
        print("ERROR: account_info.json must contain 'user' and 'password' fields")
        sys.exit(1)

    asyncio.run(main(account_info["user"], account_info["password"]))
