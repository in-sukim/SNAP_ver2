from youtube_transcript_api import YouTubeTranscriptApi
from kiwipiepy import Kiwi
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium import webdriver
import time
from functools import wraps
import logging

from pytubefix import YouTube
from pytubefix.cli import on_progress
import os
from moviepy.editor import VideoFileClip

import aiofiles
import asyncio
from concurrent.futures import ThreadPoolExecutor

import re
import unicodedata

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


def time_measure_decorator(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        logger.info(
            f"Execution time of {func.__name__}: {end_time - start_time:.4f} seconds"
        )
        return result

    return wrapper


@time_measure_decorator
class YouTubeVideo:
    def __init__(self, video_url):
        self.video_url = video_url
        self.video_id = self.get_video_id(video_url)
        self.category = self.get_category()
        self.transcript = self.get_transcript()
        self.duration = self.get_duration()
        self.shorts_group, self.shorts_all_text = self.get_shorts_group()

    def get_video_id(self, video_url):
        """비디오 ID 추출"""
        try:
            video_id = video_url.split("v=")[1][:11]
            logger.info(f"Extracted video ID: {video_id}")
            return video_id
        except Exception as e:
            logger.error(f"Failed to extract video ID from URL: {str(e)}")
            raise

    def get_transcript(self):
        """유튜브 영상 자막 가져오기"""
        try:
            logger.info(f"Attempting to fetch transcript for video ID: {self.video_id}")
            transcript = YouTubeTranscriptApi.get_transcript(
                self.video_id, languages=["ko", "en"]
            )
            logger.info(
                f"Successfully retrieved transcript with {len(transcript)} entries"
            )
            return transcript
        except Exception as e:
            logger.error(f"Failed to get transcript: {str(e)}")
            logger.warning("Returning empty transcript as fallback")
            return []

    def get_category(self):
        """유튜브 영상 카테고리 반환"""
        logger.info("Setting up Chrome options...")
        options = webdriver.ChromeOptions()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-software-rasterizer")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-dev-tools")
        options.add_argument("--no-zygote")
        options.add_argument("--single-process")
        options.add_argument("--ignore-certificate-errors")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--remote-debugging-port=9222")
        options.binary_location = "/usr/bin/chromium"

        logger.info("Chrome options configured with following arguments:")
        for arg in options.arguments:
            logger.info(f"  - {arg}")

        logger.info(f"Chrome binary location: {options.binary_location}")
        logger.info("Initializing Chrome service...")

        try:
            service = Service(
                executable_path="/usr/bin/chromedriver", service_args=["--verbose"]
            )
            logger.info(f"Chrome service initialized with path: {service.path}")

            logger.info("Attempting to start Chrome driver...")
            driver = webdriver.Chrome(service=service, options=options)
            logger.info("Chrome driver started successfully")

            logger.info(f"Fetching page content from: {self.video_url}")
            driver.get(self.video_url)
            logger.info("Page loaded successfully")

            logger.info("Extracting category from page source...")
            html = driver.page_source
            category = html.split('"category":"')[1].split('",')[0]
            logger.info(f"Successfully extracted category: {category}")

            return category
        except Exception as e:
            logger.error(f"Error getting category: {str(e)}")
            logger.error(f"Error type: {type(e).__name__}")
            logger.error(f"Error details: {str(e)}")
            # if isinstance(e, webdriver.WebDriverException):
            #     logger.error(f"WebDriver error message: {e.msg}")
            logger.warning("Returning 'Unknown' as fallback category")
            return "Unknown"
        finally:
            try:
                logger.info("Attempting to close Chrome driver...")
                driver.quit()
                logger.info("Chrome driver closed successfully")
            except Exception as e:
                logger.error(f"Error closing Chrome driver: {str(e)}")

    def get_shorts_group(self):
        """60초 이내 구간으로 스크립트 그룹화"""
        try:
            logger.info("Starting transcript grouping process...")
            shorts = {}
            shorts_all_text = ""

            logger.info(f"Processing {len(self.transcript)} transcript entries")
            for i in range(len(self.transcript)):
                trans = self.transcript[i]
                text, start, duration = trans["text"], trans["start"], trans["duration"]
                shorts_group = int(start // 60)
                if shorts_group not in shorts:
                    shorts[shorts_group] = []
                shorts[shorts_group] += [text]

            logger.info(f"Created {len(shorts)} groups")
            shorts = {key: f"[{key}] " + " ".join(text) for key, text in shorts.items()}
            shorts_all_text = "\n\n".join(shorts.values())

            logger.info("Successfully grouped transcripts")
            return shorts, shorts_all_text
        except Exception as e:
            logger.error(f"Error in transcript grouping: {str(e)}")
            return {}, ""

    def get_duration(self) -> int:
        """영상 길이(초) 반환"""
        try:
            logger.info(f"Getting duration for video: {self.video_url}")
            yt = YouTube(self.video_url)
            duration = yt.length
            logger.info(f"Video duration: {duration} seconds")
            return duration
        except Exception as e:
            logger.error(f"Failed to get video duration: {str(e)}")
            raise


def normalize_filename(title: str) -> str:
    """파일명 정규화.

    Args:
        title: 원본 파일명

    Returns:
        str: 정규화된 파일명
    """
    # 유니코드 정규화 (NFKD)
    title = unicodedata.normalize("NFKD", title)

    # 파일명으로 사용할 수 없는 문자 제거/변환
    title = re.sub(r'[\\/*?:"<>|]', "", title)  # Windows 금지 문자 제거
    title = re.sub(r"\s+", "_", title)  # 공백을 언더스코어로 변환
    title = re.sub(r"[^\w\-_.]", "", title)  # 알파벳, 숫자, 하이픈, 언더스코어만 허용

    # 길이 제한 (파일 시스템 제한 고려)
    if len(title) > 255:
        title = title[:255]
    return title


async def download_video(url: str) -> str:
    """유튜브 영상 다운로드"""
    try:
        logger.info(f"Starting download process for URL: {url}")
        yt = YouTube(url, on_progress_callback=on_progress)
        logger.info(f"Video title: {yt.title}")

        normalized_title = normalize_filename(yt.title)
        logger.info(f"Normalized title: {normalized_title}")

        ys = yt.streams.get_highest_resolution()
        logger.info(f"Selected stream resolution: {ys.resolution}")

        if not os.path.exists("input"):
            logger.info("Creating input directory")
            os.makedirs("input")

        logger.info("Starting download...")
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor() as pool:
            await loop.run_in_executor(
                pool,
                lambda: ys.download(
                    output_path="input", filename=f"{normalized_title}.mp4"
                ),
            )
        logger.info("Download completed successfully")
        return normalized_title
    except Exception as e:
        logger.error(f"Download failed: {str(e)}")
        raise


async def make_clip_video(path, save_path, start_t, end_t):
    """클립 비디오 생성"""
    try:
        logger.info(f"Processing clip: {save_path}")
        logger.info(f"Time range: {start_t} to {end_t}")

        input_file = path
        output_dir = os.path.join("output", os.path.splitext(os.path.basename(path))[0])
        os.makedirs(output_dir, exist_ok=True)
        final_save_path = os.path.join(output_dir, save_path)

        logger.info(f"Output directory: {output_dir}")
        logger.info(f"Final save path: {final_save_path}")

        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor() as pool:
            await loop.run_in_executor(
                pool,
                lambda: process_video_clip(input_file, final_save_path, start_t, end_t),
            )
        logger.info("Clip processing completed")
    except Exception as e:
        logger.error(f"Error processing video clip: {str(e)}")


def process_video_clip(path, final_save_path, start_t, end_t):
    try:
        video = VideoFileClip(path)
        duration = video.duration

        try:
            if start_t > duration or end_t > duration:
                logger.warning(
                    f"Start time or end time is greater than the video duration. Adjusting end time."
                )
                end_t = min(end_t, duration)
                start_t = min(start_t, duration - 10)

            clip = video.subclip(start_t, end_t)
            temp_path = final_save_path + ".temp.mp4"
            clip.write_videofile(
                temp_path,
                codec="libx264",
                audio_codec="aac",
                temp_audiofile=None,
                remove_temp=True,
                threads=4,
            )

            if os.path.exists(temp_path):
                if os.path.exists(final_save_path):
                    os.remove(final_save_path)
                os.rename(temp_path, final_save_path)

        finally:
            clip.close()
            video.close()

    except Exception as e:
        logger.error(f"Error in process_video_clip: {str(e)}")
        raise


if __name__ == "__main__":
    video_url = "https://www.youtube.com/watch?v=4JdzuB702wI"
    video = YouTubeVideo(video_url)
    video_id = video.video_id
    category = video.category
    transcript = video.transcript
    shorts_group = video.shorts_group

    logger.info(
        f"Video ID: {video_id}\nCategory: {category}\nShorts Group Example: {shorts_group[0]}"
    )
