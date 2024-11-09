import subprocess
import json
from moviepy.editor import VideoFileClip
import logging

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def get_video_duration(video_path: str) -> float:
    """비디오 파일의 재생 시간을 초 단위로 반환."""
    try:
        clip = VideoFileClip(video_path)
        duration = clip.duration
        clip.close()
        logger.info(f"Video duration: {duration} seconds")
        return duration

    except Exception as e:
        logger.error(f"Failed to get video duration: {str(e)}")
        raise Exception(f"Failed to get video duration: {str(e)}")
