"""YouTube transcript extraction functionality."""
import re
import logging
from typing import Optional, Dict
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound

class TranscriptFetcher:
    def get_video_id(self, url: str) -> Optional[str]:
        """Extract video ID from YouTube URL."""
        try:
            video_id = re.search(r'(?:v=|\/|youtu\.be\/)([0-9A-Za-z_-]{11}).*', url)
            return video_id.group(1) if video_id else None
        except Exception as e:
            logging.error(f"Error extracting video ID: {str(e)}")
            return None

    def get_transcript(self, url: str) -> Optional[Dict]:
        """Get English transcript from YouTube."""
        try:
            video_id = self.get_video_id(url)
            if not video_id:
                logging.error(f"Could not extract video ID from URL: {url}")
                return None

            try:
                transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['en'])
                full_text = " ".join(segment['text'] for segment in transcript)
                logging.info(f"Successfully got YouTube transcript for video {video_id}")
                return {
                    'text': full_text,
                    'segments': transcript
                }
            except (TranscriptsDisabled, NoTranscriptFound) as e:
                logging.error(f"No transcript available for video {video_id}: {str(e)}")
                return None

        except Exception as e:
            logging.error(f"Error getting YouTube transcript: {str(e)}")
            return None
