#!/usr/bin/env python3
"""
AI Video Automation Workflow
Generates 2-3 videos daily using Grok API and Google Veo 3
"""

import os
import json
import time
from datetime import datetime
from typing import Dict, List, Optional
import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
import requests
from loguru import logger
from dotenv import load_dotenv
import fal_client

# Load environment variables
load_dotenv()

# Configure logging
logger.add("logs/video_automation_{time}.log", rotation="1 day", retention="7 days")

class VideoAutomation:
    def __init__(self):
        self.setup_google_sheets()
        self.setup_youtube()
        self.grok_api_key = os.getenv('GROK_API_KEY')
        self.grok_api_url = os.getenv('GROK_API_URL')
        self.fal_api_key = os.getenv('FAL_API_KEY')
        
    def setup_google_sheets(self):
        """Initialize Google Sheets connection"""
        creds = Credentials.from_service_account_file(
            os.getenv('GOOGLE_SHEETS_CREDENTIALS_PATH'),
            scopes=['https://www.googleapis.com/auth/spreadsheets']
        )
        self.gc = gspread.authorize(creds)
        self.spreadsheet = self.gc.open_by_key(os.getenv('SPREADSHEET_ID'))
        self.topics_sheet = self.spreadsheet.worksheet('Topics')
        self.videos_sheet = self.spreadsheet.worksheet('Published')
        
    def setup_youtube(self):
        """Initialize YouTube API connection"""
        SCOPES = ['https://www.googleapis.com/auth/youtube.upload']
        creds = None
        
        token_path = os.getenv('YOUTUBE_CREDENTIALS_PATH')
        if os.path.exists(token_path):
            with open(token_path, 'r') as token:
                creds_data = json.load(token)
                # Create credentials from saved token
                from google.oauth2.credentials import Credentials as OAuthCredentials
                creds = OAuthCredentials.from_authorized_user_info(creds_data, SCOPES)
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    os.getenv('YOUTUBE_CLIENT_SECRETS_PATH'), SCOPES)
                creds = flow.run_local_server(port=0)
            
            # Save credentials for next run
            with open(token_path, 'w') as token:
                token.write(creds.to_json())
        
        self.youtube = build('youtube', 'v3', credentials=creds)
        
    def get_next_topic(self) -> Optional[Dict]:
        """Get next unprocessed topic from Google Sheets"""
        all_records = self.topics_sheet.get_all_records()
        for idx, record in enumerate(all_records, start=2):  # Start at 2 (header is row 1)
            if record.get('Status') != 'Published':
                return {'row': idx, 'topic': record.get('Topic'), 'id': record.get('ID')}
        return None
        
    def generate_script(self, topic: str) -> Dict:
        """Generate video script using Grok API"""
        logger.info(f"Generating script for topic: {topic}")
        
        headers = {
            'Authorization': f'Bearer {self.grok_api_key}',
            'Content-Type': 'application/json'
        }
        
        prompt = f"""Create a compelling 8-second video script about: {topic}
        
        Format the response as JSON with:
        - title: Clear, descriptive title (max 100 chars)
        - description: YouTube video description with relevant keywords and hashtags
        - script: Concise narration (8 seconds - one key point or quick demonstration)
        - visual_prompts: One detailed visual scene description for horizontal video
        - hook: Opening text (first 2 seconds to introduce the topic)
        
        Note: This is for an 8-second video, so focus on one clear, valuable insight.
        """
        
        data = {
            'model': 'grok-3',
            'messages': [{'role': 'user', 'content': prompt}],
            'temperature': 0.7
        }
        
        response = requests.post(self.grok_api_url, headers=headers, json=data)
        response.raise_for_status()
        
        content = response.json()['choices'][0]['message']['content']
        # Parse JSON from response
        return json.loads(content)
        
    def generate_video(self, script_data: Dict) -> str:
        """Generate video using Google Veo 3 via FAL API"""
        logger.info("Generating video with Veo 3")
        
        # FAL client will use FAL_KEY from environment
        
        # Combine visual prompts into video generation prompt
        video_prompt = f"{script_data['title']}. " + " ".join(script_data['visual_prompts'])
        
        # Generate video using Google Veo 3
        def on_queue_update(update):
            if isinstance(update, fal_client.InProgress):
                for log in update.logs:
                    logger.info(f"Veo3 Progress: {log['message']}")
        
        # Standard horizontal video format
        
        result = fal_client.subscribe(
            "fal-ai/veo3/fast",
            arguments={
                "prompt": video_prompt,
                "aspect_ratio": "16:9",  # Horizontal standard YouTube
                "duration": "8s"  # Veo 3 currently only supports 8 seconds
            },
            with_logs=True,
            on_queue_update=on_queue_update
        )
        
        # Log the result to see structure
        logger.info(f"Veo3 result: {result}")
        
        # Download video - check for different possible keys
        video_url = result.get('video', {}).get('url') or result.get('url') or result.get('video_url')
        video_path = f"output/video_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
        
        response = requests.get(video_url)
        with open(video_path, 'wb') as f:
            f.write(response.content)
            
        logger.info(f"Video saved to: {video_path}")
        return video_path
        
    def upload_to_youtube(self, video_path: str, script_data: Dict) -> str:
        """Upload video to YouTube"""
        logger.info("Uploading to YouTube")
        
        body = {
            'snippet': {
                'title': script_data['title'][:100],  # YouTube title limit
                'description': script_data['description'],
                'categoryId': '28',  # Science & Technology
                'tags': ['AI', 'Claude Code', 'programming', 'coding', 'tutorial', 'tech']
            },
            'status': {
                'privacyStatus': 'public',
                'selfDeclaredMadeForKids': False
            }
        }
        
        media = MediaFileUpload(video_path, chunksize=-1, resumable=True)
        
        request = self.youtube.videos().insert(
            part='snippet,status',
            body=body,
            media_body=media
        )
        
        response = request.execute()
        video_id = response['id']
        video_url = f"https://youtube.com/watch?v={video_id}"
        
        logger.info(f"Video uploaded: {video_url}")
        return video_url
        
    def update_sheets(self, topic_data: Dict, video_url: str, script_data: Dict):
        """Update Google Sheets with published video info"""
        # Update topic status
        self.topics_sheet.update_cell(topic_data['row'], 2, 'Published')  # Assuming Status is column B
        
        # Add to published videos
        self.videos_sheet.append_row([
            topic_data['id'],
            topic_data['topic'],
            script_data['title'],
            video_url,
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            0  # Initial view count
        ])
        
    def process_video(self):
        """Main workflow: Topic → Script → Video → Upload"""
        try:
            # Get next topic
            topic_data = self.get_next_topic()
            if not topic_data:
                logger.info("No pending topics found")
                return
                
            logger.info(f"Processing topic: {topic_data['topic']}")
            
            # Update status to Processing
            self.topics_sheet.update_cell(topic_data['row'], 2, 'Processing')
            
            # Generate script
            script_data = self.generate_script(topic_data['topic'])
            
            # Generate video
            video_path = self.generate_video(script_data)
            
            # Upload to YouTube
            video_url = self.upload_to_youtube(video_path, script_data)
            
            # Update sheets
            self.update_sheets(topic_data, video_url, script_data)
            
            logger.success(f"Video published successfully: {video_url}")
            
        except Exception as e:
            logger.error(f"Error processing video: {str(e)}")
            # Update status back to Pending on error
            if 'topic_data' in locals():
                self.topics_sheet.update_cell(topic_data['row'], 2, 'Error')
            raise

def main():
    """Run video automation"""
    automation = VideoAutomation()
    automation.process_video()

if __name__ == "__main__":
    main()