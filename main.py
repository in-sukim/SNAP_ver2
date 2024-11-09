from typing import List, Tuple
import asyncio
import time
import os
from util.chain import set_map_chain, set_reduce_chain, set_title_chain
from util.youtube import YouTubeVideo, download_video, time_measure_decorator
from util.ffmpeg_processor import FFmpegProcessor
from util.constants import *
from langchain.text_splitter import RecursiveCharacterTextSplitter
import logging

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


async def process_video_segments(
    segments: List[Tuple[int, int]], title: str, video: YouTubeVideo
) -> None:
    """영상 세그먼트 처리."""
    input_path = os.path.join(INPUT_DIR, f"{title}.mp4")
    processor = FFmpegProcessor(input_path)

    # 각 세그먼트별 제목 생성
    title_chain = set_title_chain()
    segment_titles = []

    for idx, (start_t, end_t) in enumerate(segments):
        logger.info(f"Processing segment {idx+1}/{len(segments)}")
        # 해당 구간의 자막 추출
        segment_text = ""
        for trans in video.transcript:
            if start_t <= trans["start"] <= end_t:
                segment_text += trans["text"] + " "

        # 제목 생성
        clip_title = title_chain.invoke(
            {"category": video.category, "text": segment_text}
        )
        segment_titles.append(clip_title)
        logger.info(f"Generated title for segment {idx+1}: {clip_title}")

    # 세그먼트 처리
    await processor.process_segments(segments, segment_titles)


def get_target_clip_count(duration: int) -> int:
    """영상 길이에 따른 목표 클립 개수 반환.

    Args:
        duration: 영상 길이(초)

    Returns:
        int: 목표 클립 개수
    """
    duration_minutes = duration / 60
    if duration_minutes < 20:  # 20분 미만
        return 3
    else:  # 20분 이상
        return 5


@time_measure_decorator
async def process_map_reduce(video, category, shorts_group, shorts_all_text):
    """Map-Reduce 처리를 수행하는 비동기 함수."""
    logger.info("Starting Map-Reduce process...")

    # 텍스트 청크 처리
    text_splitter = RecursiveCharacterTextSplitter()
    chunks = text_splitter.split_text(shorts_all_text)
    logger.info(f"Chunking completed. Number of chunks: {len(chunks)}")

    # Map phase
    logger.info("Starting Map phase...")
    map_chain = set_map_chain()
    map_results = map_chain.batch(
        [{"text": chunk, "category": category} for chunk in chunks]
    )
    map_results_list = []
    for result in map_results:
        temp_list = list(map(int, result.split(",")))
        temp_list = list(filter(lambda x: x != -1, temp_list))
        map_results_list.extend(temp_list)
    logger.info(f"Map results: {map_results_list}")

    # 목표 클립 개수 계산
    target_count = get_target_clip_count(video.duration)
    logger.info(f"Target clip count: {target_count}")

    if len(map_results_list) <= target_count:
        reduce_results = map_results_list
        logger.info("Using map results directly (no reduction needed)")
    else:
        # Reduce phase
        logger.info("Starting Reduce phase...")
        concat_map_results = "\n\n".join(shorts_group[idx] for idx in map_results_list)
        reduce_chain = set_reduce_chain()
        reduce_results = reduce_chain.invoke(
            {
                "text": concat_map_results,
                "category": category,
                "target_count": target_count,
            }
        ).split(",")
        reduce_results = list(map(int, reduce_results))[:target_count]

    logger.info(f"Reduce results: {reduce_results}")

    # 시간 세그먼트 계산
    time_segments = [
        (
            (idx * VIDEO_SEGMENT_LENGTH) - CLIP_PADDING,
            ((idx + 1) * VIDEO_SEGMENT_LENGTH) + CLIP_PADDING,
        )
        for idx in reduce_results
    ]
    logger.info(f"Generated time segments: {time_segments}")

    return time_segments


async def main(url: str) -> None:
    """메인 실행 함수."""
    try:
        start_time = time.time()
        logger.info(f"Starting processing for URL: {url}")

        # 유튜브 영상 메타데이터 추출
        logger.info("Extracting video metadata...")
        video = YouTubeVideo(url)
        category = video.category
        shorts_group = video.shorts_group
        shorts_all_text = video.shorts_all_text
        logger.info(f"Video category: {category}")

        # 다운로드와 Map-Reduce 처리를 병렬로 실행
        logger.info("Starting parallel download and Map-Reduce processing...")
        download_task = download_video(url)
        map_reduce_task = process_map_reduce(
            video, category, shorts_group, shorts_all_text
        )

        # 두 작업이 모두 완료될 때까지 대기
        input_title, time_segments = await asyncio.gather(
            download_task, map_reduce_task
        )
        logger.info("Download and Map-Reduce processing completed")

        # 클립 생성
        logger.info("Starting clip generation...")
        await process_video_segments(time_segments, input_title, video)
        logger.info(f"Total execution time: {time.time() - start_time:.2f} seconds")

    except Exception as e:
        logger.error(f"Error in main process: {str(e)}")
        raise


if __name__ == "__main__":
    url = "https://www.youtube.com/watch?v=4JdzuB702wI"
    try:
        start_time = time.time()
        asyncio.run(main(url))
        print(f"Total execution time: {time.time() - start_time:.2f} seconds")
    except KeyboardInterrupt:
        print("Process interrupted by user")
    except Exception as e:
        print(f"An error occurred: {e}")
