"""
Python Background Continuous Scheduler for AutoJobs Agent.
Runs main.py daily at a specified time (default: 09:00 AM local time).
"""

import time
import schedule
import logging
from datetime import datetime
from main import main as run_agent

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

TARGET_TIME = "09:00"


def job():
    logging.info("⏰ Triggering Scheduled Daily Execution of AutoJobs Agent...")
    try:
        run_agent()
    except Exception as e:
        logging.error(f"Error during scheduled execution: {e}")


if __name__ == "__main__":
    logging.info(f"🚀 AutoJobs Background Scheduler Started.")
    logging.info(f"📅 Agent scheduled to run automatically every day at {TARGET_TIME} local time.")
    
    # Schedule daily run
    schedule.every().day.at(TARGET_TIME).do(job)
    
    next_run = schedule.next_run()
    logging.info(f"⏳ Next scheduled execution at: {next_run}")
    
    # Run once immediately on start if specified or run pending
    logging.info("Running initial startup pass...")
    job()
    
    while True:
        schedule.run_pending()
        time.sleep(30)
