from youtube_transcript_api import YouTubeTranscriptApi
from kiwipiepy import Kiwi
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium import webdriver
import time
from functools import wraps

from pytubefix import YouTube
from pytubefix.cli import on_progress
import os
from moviepy.editor import VideoFileClip

import aiofiles
import asyncio
from concurrent.futures import ThreadPoolExecutor

import re
import unicodedata


def time_measure_decorator(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        print(f"Execution time of {func.__name__}: {end_time - start_time:.4f} seconds")
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
        video_id = video_url.split("v=")[1][:11]
        return video_id

    def get_transcript(self):
        transcript = YouTubeTranscriptApi.get_transcript(
            self.video_id, languages=["ko", "en"]
        )
        return transcript

    def get_category(self):
        """
        유튜브 영상 카테고리 반환
        Args:
            video_url: 유튜브 영상 URL
            user_agent: User-Agent
        Returns:
            category: 유튜브 영상 카테고리
        """
        options = webdriver.ChromeOptions()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")

        # ChromeDriver를 자동으로 설치하고 관리
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)

        try:
            driver.get(self.video_url)
            html = driver.page_source
            category = html.split('"category":"')[1].split('",')[0]
        finally:
            driver.quit()

        return category

    def get_shorts_group(self):
        """
        60초 이내 구간으로 스크립트 그룹화.
        Args:
            transcript: 유튜브 영상 자막 (List of dictionary)
                - text: 자막 텍스트
                - start: 자막 시작 시간
                - duration: 자막 지속 시간
        Returns:
            shorts: 60초 이내 구간으로 스크립트 그룹화된 dictionary
                - key: 60초 이내 구간 index(0부터 시작)
                - value: 60초 이내 구간의 자막 텍스트
        """
        shorts = {}
        shorts_all_text = ""
        for i in range(len(self.transcript)):
            trans = self.transcript[i]
            text, start, duration = trans["text"], trans["start"], trans["duration"]
            shorts_group = int(start // 60)
            if shorts_group not in shorts:
                shorts[shorts_group] = []
            shorts[shorts_group] += [text]
        shorts = {key: f"[{key}] " + " ".join(text) for key, text in shorts.items()}
        shorts_all_text = "\n\n".join(shorts.values())
        return shorts, shorts_all_text

    def get_fix_sentences_shorts_group(self):
        """
        shorts_group 구간 별 text 문장 "\n"으로 구분하여 반환
        Args:
            shorts_group: 60초 이내 구간으로 스크립트 그룹화된 dictionary
                - key: 60초 이내 구간 index(0부터 시작)
                - value: 60초 이내 구간의 자막 텍스트
        Returns:
            fix_shorts_gorup: value 문장 "\n"으로 구분하여 반환
                - key: 60초 이내 구간 index(0부터 시작)
                - value: 60초 이내 구간의 자막 문장 분할(kiwi)을 통해 "\n"으로 구분된 텍스트
        """
        kiwi = Kiwi()
        for key, sentence in self.shorts_group.items():
            split_sentences = kiwi.split_into_sents(sentence)
            fix_sencences = ""
            for sen in split_sentences:
                fix_sencences += sen.text + "\n"
            self.shorts_group[key] = fix_sencences
        return self.shorts_group

    def get_duration(self) -> int:
        """영상 길이(초) 반환."""
        yt = YouTube(self.video_url)
        return yt.length  # 초 단위로 반환


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
    """유튜브 영상 다운로드.

    Args:
        url: 유튜브 영상 URL

    Returns:
        str: 다운로드된 영상의 제목
    """
    yt = YouTube(url, on_progress_callback=on_progress)
    print(yt.title)

    # 파일명 정규화
    normalized_title = normalize_filename(yt.title)
    ys = yt.streams.get_highest_resolution()

    if not os.path.exists("input"):
        os.makedirs("input")

    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor() as pool:
        # 정규화된 파일명으로 저장
        await loop.run_in_executor(
            pool,
            lambda: ys.download(
                output_path="input", filename=f"{normalized_title}.mp4"
            ),
        )

    return normalized_title


async def make_clip_video(path, save_path, start_t, end_t):
    try:
        # 입력 파일 경로
        input_file = path

        # 출력 디렉토리 생성 (output/영상제목/)
        output_dir = os.path.join("output", os.path.splitext(os.path.basename(path))[0])
        os.makedirs(output_dir, exist_ok=True)

        # 최종 저장 경로
        final_save_path = os.path.join(output_dir, save_path)

        # 클립 영상 생성 비동기 처리
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor() as pool:
            await loop.run_in_executor(
                pool,
                lambda: process_video_clip(input_file, final_save_path, start_t, end_t),
            )
    except Exception as e:
        print(f"Error processing video clip: {str(e)}")


def process_video_clip(path, final_save_path, start_t, end_t):
    try:
        video = VideoFileClip(path)
        duration = video.duration

        try:
            if start_t > duration or end_t > duration:
                print(
                    f"Start time or end time is greater than the video duration. Adjusting end time."
                )
                end_t = min(end_t, duration)
                start_t = min(start_t, duration - 10)  # 최소 10초 전까지 클립 생성

            clip = video.subclip(start_t, end_t)

            # 임시 파일명으로 먼저 저장
            temp_path = final_save_path + ".temp.mp4"
            clip.write_videofile(
                temp_path,
                codec="libx264",
                audio_codec="aac",
                temp_audiofile=None,
                remove_temp=True,
                threads=4,
            )

            # 성공적으로 생성되면 최종 파일명으로 변경
            if os.path.exists(temp_path):
                if os.path.exists(final_save_path):
                    os.remove(final_save_path)
                os.rename(temp_path, final_save_path)

        finally:
            clip.close()
            video.close()

    except Exception as e:
        print(f"Error in process_video_clip: {str(e)}")
        raise


if __name__ == "__main__":
    video_url = "https://www.youtube.com/watch?v=4JdzuB702wI"
    video = YouTubeVideo(video_url)
    video_id = video.video_id
    category = video.category
    transcript = video.transcript
    shorts_group = video.shorts_group

    print(
        f"Video ID: {video_id}\nCategory: {category}\nShorts Group Example: {shorts_group[0]}"
    )
