"""
Python Background Continuous Scheduler for Happpy-Clone Agent.
Runs main.py daily at a specified time (default: 09:00 AM).
"""

import time
import schedule
import logging
from main import main as run_agent

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

TARGET_TIME = "09:00"

def job():
    logging.info("⏰ Triggering Scheduled Daily Execution of Happpy Job Agent...")
    try:
        run_agent()
    except Exception as e:
        logging.error(f"Error during scheduled execution: {e}")

if __name__ == "__main__":
    logging.info(f"🚀 Happpy-Clone Background Scheduler Started.")
    logging.info(f"📅 Agent scheduled to run automatically every day at {TARGET_TIME}.")
    
    # Run once immediately on start
    job()
    
    # Schedule daily run
    schedule.every().day.at(TARGET_TIME).do(job)
    
    while True:
        schedule.run_pending()
        time.sleep(60)
