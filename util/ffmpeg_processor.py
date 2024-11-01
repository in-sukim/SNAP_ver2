from dataclasses import dataclass
from typing import List, Tuple
import os
import asyncio
import subprocess
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

class FFmpegProcessor:
    """FFmpeg 기반 영상 처리 클래스."""

    def __init__(self, input_path: str):
        """
        Args:
            input_path: 입력 영상 경로
        """
        self.input_path = input_path
        self.output_dir = self._create_output_dir()

    def _create_output_dir(self) -> str:
        """출력 디렉토리 생성."""
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
            duration = segment.end_time - segment.start_time
            cmd = [
                'ffmpeg',
                '-y',  # 기존 파일 덮어쓰기
                '-ss', str(segment.start_time),  # 시작 시간
                '-i', self.input_path,  # 입력 파일
                '-t', str(duration),  # 지속 시간
                '-c:v', 'libx264',  # 비디오 코덱
                '-c:a', 'aac',  # 오디오 코덱
                '-preset', 'ultrafast',  # 인코딩 속도 설정
                '-crf', '23',  # 화질 설정 (0-51, 낮을수록 좋음)
                '-avoid_negative_ts', 'make_zero',
                '-async', '1',
                temp_path
            ]

            # FFmpeg 명령 실행
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            await process.communicate()

            if process.returncode == 0 and os.path.exists(temp_path):
                if os.path.exists(output_path):
                    os.remove(output_path)
                os.rename(temp_path, output_path)
            else:
                raise RuntimeError(f"FFmpeg failed with return code {process.returncode}")

        except Exception as e:
            print(f"Error processing segment {segment.index}: {str(e)}")
            if os.path.exists(temp_path):
                os.remove(temp_path) 