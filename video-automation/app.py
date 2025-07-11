#!/usr/bin/env python3
"""
Video Automation Web UI
User-friendly interface for AI video generation
"""

from flask import Flask, render_template, request, jsonify, send_file
import os
import json
from datetime import datetime
import threading
from video_automation import VideoAutomation
from loguru import logger
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'

# Store job status
job_status = {}

def run_video_generation(job_id, topic, api_keys):
    """Run video generation in background thread"""
    try:
        job_status[job_id] = {
            'status': 'processing',
            'progress': 'Initializing...',
            'video_url': None,
            'error': None
        }
        
        # Create automation instance with custom API keys
        automation = VideoAutomation()
        automation.grok_api_key = api_keys['grokApiKey']
        os.environ['FAL_KEY'] = api_keys['falApiKey']
        
        # Handle YouTube credentials if provided
        if api_keys.get('useYoutube') and api_keys.get('youtubeClientSecrets'):
            try:
                # Save YouTube credentials temporarily
                os.makedirs('config', exist_ok=True)
                with open('config/youtube_client_secrets.json', 'w') as f:
                    f.write(api_keys['youtubeClientSecrets'])
                # Re-setup YouTube with new credentials
                automation.setup_youtube()
            except Exception as e:
                logger.error(f"Failed to setup YouTube: {str(e)}")
                automation.youtube = None
        
        # Override to use provided topic instead of Google Sheets
        job_status[job_id]['progress'] = 'Generating script with Grok...'
        script_data = automation.generate_script(topic)
        
        job_status[job_id]['progress'] = 'Creating video with Veo 3...'
        video_path = automation.generate_video(script_data)
        
        if api_keys.get('useYoutube') and automation.youtube:
            job_status[job_id]['progress'] = 'Uploading to YouTube...'
            video_url = automation.upload_to_youtube(video_path, script_data)
        else:
            job_status[job_id]['progress'] = 'Saving video locally...'
            video_url = None
        
        job_status[job_id] = {
            'status': 'completed',
            'progress': 'Video created successfully!',
            'video_url': video_url,
            'video_title': script_data['title'],
            'video_path': video_path,
            'error': None
        }
        
        # Save to recent videos in memory
        if not hasattr(app, 'recent_videos'):
            app.recent_videos = []
        app.recent_videos.insert(0, {
            'title': script_data['title'],
            'topic': topic,
            'video_url': video_url,
            'created_at': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error in job {job_id}: {str(e)}")
        job_status[job_id] = {
            'status': 'error',
            'progress': 'Failed to create video',
            'video_url': None,
            'error': str(e)
        }

@app.route('/')
def index():
    """Main page"""
    return render_template('index.html')

@app.route('/api/topics', methods=['GET'])
def get_topics():
    """Get topics from Google Sheets"""
    try:
        automation = VideoAutomation()
        all_records = automation.topics_sheet.get_all_records()
        topics = [
            {
                'id': record.get('ID'),
                'topic': record.get('Topic'),
                'status': record.get('Status', 'Pending')
            }
            for record in all_records if record.get('Topic')
        ]
        return jsonify({'success': True, 'topics': topics})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/generate', methods=['POST'])
def generate_video():
    """Start video generation"""
    data = request.json
    topic = data.get('topic')
    api_keys = {
        'grokApiKey': data.get('grokApiKey'),
        'falApiKey': data.get('falApiKey'),
        'useYoutube': data.get('useYoutube', False),
        'youtubeClientSecrets': data.get('youtubeClientSecrets')
    }
    
    if not topic:
        return jsonify({'success': False, 'error': 'Topic is required'})
    
    if not api_keys['grokApiKey'] or not api_keys['falApiKey']:
        return jsonify({'success': False, 'error': 'API keys are required'})
    
    # Create job ID
    job_id = f"job_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # Start background thread
    thread = threading.Thread(target=run_video_generation, args=(job_id, topic, api_keys))
    thread.start()
    
    return jsonify({'success': True, 'job_id': job_id})

@app.route('/api/status/<job_id>')
def get_status(job_id):
    """Get job status"""
    if job_id not in job_status:
        return jsonify({'success': False, 'error': 'Job not found'})
    
    return jsonify({'success': True, 'job': job_status[job_id]})

@app.route('/api/recent-videos')
def get_recent_videos():
    """Get recently created videos"""
    try:
        # Return videos from memory (doesn't require Google Sheets)
        videos = getattr(app, 'recent_videos', [])
        return jsonify({'success': True, 'videos': videos[:10]})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/add-topic', methods=['POST'])
def add_topic():
    """Add topic to Google Sheets"""
    data = request.json
    topic = data.get('topic')
    
    if not topic:
        return jsonify({'success': False, 'error': 'Topic is required'})
    
    try:
        automation = VideoAutomation()
        # Find next ID
        records = automation.topics_sheet.get_all_records()
        next_id = f"{len(records) + 1:03d}"
        
        # Add new row
        automation.topics_sheet.append_row([next_id, '', topic])
        
        return jsonify({'success': True, 'message': 'Topic added successfully'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/stats')
def get_stats():
    """Get video statistics"""
    try:
        videos = getattr(app, 'recent_videos', [])
        today_count = 0
        today = datetime.now().date()
        
        for video in videos:
            video_date = datetime.fromisoformat(video['created_at']).date()
            if video_date == today:
                today_count += 1
        
        return jsonify({
            'success': True,
            'total': len(videos),
            'today': today_count,
            'views': 0  # Would need YouTube API to get real views
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    app.run(debug=True, port=5000)