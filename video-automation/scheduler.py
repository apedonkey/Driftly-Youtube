#!/usr/bin/env python3
"""
Video Automation Scheduler
Runs video generation at specified times
"""

import os
import schedule
import time
from datetime import datetime
from loguru import logger
from dotenv import load_dotenv
from video_automation import VideoAutomation

load_dotenv()

# Configure logging
logger.add("logs/scheduler_{time}.log", rotation="1 day", retention="7 days")

def run_video_generation():
    """Run the video generation process"""
    logger.info(f"Starting video generation at {datetime.now()}")
    try:
        automation = VideoAutomation()
        automation.process_video()
    except Exception as e:
        logger.error(f"Failed to generate video: {str(e)}")

def setup_schedule():
    """Set up the video generation schedule"""
    schedule_times = os.getenv('VIDEO_SCHEDULE_TIMES', '07:00,14:00,19:00').split(',')
    
    for time_str in schedule_times:
        schedule.every().day.at(time_str.strip()).do(run_video_generation)
        logger.info(f"Scheduled video generation at {time_str.strip()}")
    
    logger.info("Scheduler started. Waiting for scheduled times...")
    
    # Run immediately on start for testing
    if os.getenv('RUN_ON_START', 'false').lower() == 'true':
        run_video_generation()

def main():
    """Main scheduler loop"""
    setup_schedule()
    
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute

if __name__ == "__main__":
    main()