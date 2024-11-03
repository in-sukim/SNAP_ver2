from typing import List, Tuple
import asyncio
import time
import os
from util.chain import set_map_chain, set_reduce_chain
from util.youtube import YouTubeVideo, download_video, time_measure_decorator
from util.ffmpeg_processor import FFmpegProcessor
from util.constants import *
from langchain.text_splitter import RecursiveCharacterTextSplitter


async def process_video_segments(segments: List[Tuple[int, int]], title: str) -> None:
    """영상 세그먼트 처리.

    Args:
        segments: 시작/종료 시간 튜플 리스트
        title: 영상 제목
    """
    input_path = os.path.join(INPUT_DIR, f"{title}.mp4")
    processor = FFmpegProcessor(input_path)
    await processor.process_segments(segments)


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
    """Map-Reduce 처리를 수행하는 비동기 함수.

    Args:
        video: YouTubeVideo 객체
        category: 영상 카테고리
        shorts_group: 60초 단위 스크립트 그룹
        shorts_all_text: 전체 스크립트 텍스트

    Returns:
        List[Tuple[int, int]]: 시간 세그먼트 리스트
    """
    # 텍스트 청크 처리
    text_splitter = RecursiveCharacterTextSplitter()
    chunks = text_splitter.split_text(shorts_all_text)
    print(f"Chunking done...\nNumber of chunks: {len(chunks)}")

    # Map phase
    map_chain = set_map_chain()
    map_results = map_chain.batch(
        [{"text": chunk, "category": category} for chunk in chunks]
    )
    map_results_list = []
    for result in map_results:
        temp_list = list(map(int, result.split(",")))
        temp_list = list(filter(lambda x: x != -1, temp_list))
        map_results_list.extend(temp_list)
    print(f"Map results:\n{map_results_list}")

    # 목표 클립 개수 계산
    target_count = get_target_clip_count(video.duration)
    
    if len(map_results_list) <= target_count:
        reduce_results = map_results_list
    else:
        # Reduce phase에서 목표 개수만큼만 선택하도록 수정
        concat_map_results = "\n\n".join(shorts_group[idx] for idx in map_results_list)
        reduce_chain = set_reduce_chain()
        reduce_results = reduce_chain.invoke({
            "text": concat_map_results,
            "category": category,
            "target_count": target_count  # 목표 개수 전달
        }).split(",")
        reduce_results = list(map(int, reduce_results))[:target_count]  # 최대 개수 제한
    
    print(f"Reduce results:\n{reduce_results}")

    # 시간 세그먼트 계산
    time_segments = [
        (
            (idx * VIDEO_SEGMENT_LENGTH) - CLIP_PADDING,
            ((idx + 1) * VIDEO_SEGMENT_LENGTH) + CLIP_PADDING,
        )
        for idx in reduce_results
    ]
    print(f"Time segments:\n{time_segments}")

    return time_segments


async def main(url: str) -> None:
    """메인 실행 함수."""
    try:
        start_time = time.time()

        # 유튜브 영상 메타데이터 추출
        video = YouTubeVideo(url)
        category = video.category
        shorts_group = video.shorts_group
        shorts_all_text = video.shorts_all_text

        # 다운로드와 Map-Reduce 처리를 병렬로 실행
        download_task = download_video(url)
        map_reduce_task = process_map_reduce(
            video, category, shorts_group, shorts_all_text
        )

        # 두 작업이 모두 완료될 때까지 대기
        input_title, time_segments = await asyncio.gather(
            download_task, map_reduce_task
        )

        # 클립 생성
        await process_video_segments(time_segments, input_title)
        print(f"Total execution time: {time.time() - start_time:.2f} seconds")

    except Exception as e:
        print(f"Error in main process: {str(e)}")
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
