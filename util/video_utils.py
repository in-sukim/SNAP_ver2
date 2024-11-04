import subprocess
import json
from moviepy.editor import VideoFileClip


def get_video_duration(video_path: str) -> float:
    """
    비디오 파일의 재생 시간을 초 단위로 반환.

    Args:
        video_path (str): 비디오 파일 경로

    Returns:
        float: 비디오 재생 시간 (초)
    """
    try:
        # moviepy를 사용하여 비디오 정보 추출
        clip = VideoFileClip(video_path)
        duration = clip.duration
        clip.close()
        return duration

    except Exception as e:
        raise Exception(f"비디오 재생 시간을 가져오는데 실패했습니다: {str(e)}")
