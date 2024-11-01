from dataclasses import dataclass
from typing import List, Tuple
import os
import asyncio
from concurrent.futures import ThreadPoolExecutor
from moviepy.editor import VideoFileClip
from .constants import *

@dataclass
class VideoSegment:
    """영상 세그먼트 정보.
    
    Attributes:
        start_time: 시작 시간(초)
        end_time: 종료 시간(초) 
        index: 세그먼트 인덱스
    """
    start_time: int
    end_time: int
    index: int

class VideoProcessor:
    """영상 처리 클래스."""

    def __init__(self, input_path: str):
        """
        Args:
            input_path: 입력 영상 경로
        """
        self.input_path = input_path
        self.output_dir = self._create_output_dir()

    def _create_output_dir(self) -> str:
        base_name = os.path.splitext(os.path.basename(self.input_path))[0]
        output_dir = os.path.join(OUTPUT_DIR, base_name)
        os.makedirs(output_dir, exist_ok=True)
        return output_dir

    async def process_segments(self, time_segments: List[Tuple[int, int]]) -> None:
        """영상 세그먼트 병렬 처리.
        
        Args:
            time_segments: 시작/종료 시간 튜플 리스트
        """
        tasks = []
        for idx, (start_t, end_t) in enumerate(time_segments):
            segment = VideoSegment(start_t, end_t, idx)
            task = self._process_segment(segment)
            tasks.append(task)
        await asyncio.gather(*tasks)

    async def _process_segment(self, segment: VideoSegment) -> None:
        """개별 세그먼트 처리.
        
        Args:
            segment: 처리할 세그먼트 정보
        """
        output_path = os.path.join(self.output_dir, f"output_{segment.index}.mp4")
        temp_path = f"{output_path}.temp.mp4"

        try:
            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor() as pool:
                await loop.run_in_executor(
                    pool,
                    self._process_clip,
                    segment,
                    temp_path,
                    output_path
                )
        except Exception as e:
            print(f"Error processing segment {segment.index}: {str(e)}")
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def _process_clip(self, segment: VideoSegment, temp_path: str, final_path: str) -> None:
        """클립 생성 처리.
        
        Args:
            segment: 세그먼트 정보
            temp_path: 임시 파일 경로
            final_path: 최종 파일 경로
        """
        with VideoFileClip(self.input_path) as video:
            duration = video.duration
            start_t = min(segment.start_time, duration - MIN_CLIP_LENGTH)
            end_t = min(segment.end_time, duration)

            if start_t >= end_t:
                raise ValueError("Invalid time segment")

            clip = video.subclip(start_t, end_t)
            clip.write_videofile(
                temp_path,
                codec='libx264',
                audio_codec='aac',
                temp_audiofile=None,
                remove_temp=True,
                threads=4
            )
            clip.close()

        if os.path.exists(temp_path):
            if os.path.exists(final_path):
                os.remove(final_path)
            os.rename(temp_path, final_path) 