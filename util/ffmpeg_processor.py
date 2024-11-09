from dataclasses import dataclass
from typing import List, Tuple
import os
import asyncio
import subprocess
from .constants import *
import json
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
        self.use_gpu = self._check_gpu_support()
        logger.info(f"GPU acceleration: {'enabled' if self.use_gpu else 'disabled'}")

    def _create_output_dir(self) -> str:
        """출력 디렉토리 생성."""
        base_name = os.path.splitext(os.path.basename(self.input_path))[0]
        output_dir = os.path.join(OUTPUT_DIR, base_name)
        os.makedirs(output_dir, exist_ok=True)
        return output_dir

    async def process_segments(self, time_segments: List[Tuple[int, int]], titles: List[str] = None) -> None:
        """영상 세그먼트 병렬 처리.

        Args:
            time_segments: 시작/종료 시간 튜플 리스트
            titles: 각 세그먼트의 제목 리스트 (선택사항)
        """
        tasks = []
        for idx, (start_t, end_t) in enumerate(time_segments):
            segment = VideoSegment(start_t, end_t, idx)
            title = titles[idx] if titles else None
            task = self._process_segment(segment, title)
            tasks.append(task)
        await asyncio.gather(*tasks)

    async def _process_segment(self, segment: VideoSegment, title: str = None) -> None:
        """개별 세그먼트 처리."""
        # 제목이 없으면 기본 번호 사용
        file_name = f"{title}.mp4" if title else f"output_{segment.index}.mp4"
        output_path = os.path.join(self.output_dir, file_name)
        temp_path = f"{output_path}.temp.mp4"

        try:
            duration = segment.end_time - segment.start_time
            cmd = [
                "ffmpeg",
                "-y",  # 기존 파일 덮어쓰기
                "-ss",
                str(segment.start_time),  # 시작 시간
                "-i",
                self.input_path,  # 입력 파일
                "-t",
                str(duration),  # 지속 시간
                "-c:v",
                "copy",  # 비디오 스트림 복사 (재인코딩 없음)
                "-c:a",
                "copy",  # 오디오 스트림 복사 (재인코딩 없음)
                "-avoid_negative_ts",
                "make_zero",
                temp_path,
            ]

            # GPU 가속 지원 확인 및 적용
            if self.use_gpu:
                cmd = self._add_gpu_options(cmd)

            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )

            await process.communicate()

            if process.returncode == 0 and os.path.exists(temp_path):
                if os.path.exists(output_path):
                    os.remove(output_path)
                os.rename(temp_path, output_path)
            else:
                raise RuntimeError(
                    f"FFmpeg failed with return code {process.returncode}"
                )

        except Exception as e:
            print(f"Error processing segment {segment.index}: {str(e)}")
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def _check_gpu_support(self) -> bool:
        """GPU 가속 지원 여부 확인."""
        try:
            # NVIDIA GPU 확인
            result = subprocess.run(["nvidia-smi"], capture_output=True)
            if result.returncode == 0:
                logger.info("NVIDIA GPU detected")
                return True

            # Apple Silicon 확인
            if os.path.exists("/usr/sbin/sysctl"):
                result = subprocess.run(
                    ["sysctl", "machdep.cpu.brand_string"], capture_output=True
                )
                if b"Apple" in result.stdout:
                    logger.info("Apple Silicon detected")
                    return True

            # GPU가 없는 경우 조용히 False 반환
            return False
        except:
            # 예외가 발생해도 조용히 False 반환
            return False

    def _add_gpu_options(self, cmd: list) -> list:
        """GPU 가속 옵션 추가."""
        try:
            # NVIDIA GPU용 옵션
            if subprocess.run(["nvidia-smi"], capture_output=True).returncode == 0:
                return [
                    "ffmpeg",
                    "-hwaccel",
                    "cuda",
                    "-hwaccel_output_format",
                    "cuda",
                ] + cmd[1:]

            # Apple Silicon용 옵션
            if os.path.exists("/usr/sbin/sysctl"):
                result = subprocess.run(
                    ["sysctl", "machdep.cpu.brand_string"], capture_output=True
                )
                if b"Apple" in result.stdout:
                    return ["ffmpeg", "-hwaccel", "videotoolbox"] + cmd[1:]

            return cmd
        except:
            return cmd
