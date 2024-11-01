from typing import List, Tuple
import asyncio
import time
import os
from util.chain import set_map_chain, set_reduce_chain
from util.youtube import YouTubeVideo, download_video
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


async def main(url: str) -> None:
    """메인 실행 함수.

    1. 유튜브 영상 메타데이터 추출
    2. 텍스트 청크 처리
    3. Map-Reduce로 하이라이트 구간 추출
    4. 영상 다운로드 및 클립 생성

    Args:
        url: 유튜브 영상 URL
    """
    try:
        # 유튜브 영상 메타데이터 추출
        video = YouTubeVideo(url)
        category = video.category
        shorts_group = video.shorts_group
        shorts_all_text = video.shorts_all_text

        # 텍스트 청크 처리
        text_splitter = RecursiveCharacterTextSplitter()
        chunks = text_splitter.split_text(shorts_all_text)
        print("Chunking done...")

        # Map phase
        map_chain = set_map_chain()
        map_results = map_chain.batch(
            [{"text": chunk, "category": category} for chunk in chunks]
        )
        map_results_list = []
        for result in map_results:
            map_results_list.extend(list(map(int, result.split(","))))
        print(f"Map results:\n{map_results_list}")

        # Reduce phase
        concat_map_results = "\n\n".join(shorts_group[idx] for idx in map_results_list)
        reduce_chain = set_reduce_chain()
        reduce_results = reduce_chain.invoke(
            {"text": concat_map_results, "category": category}
        ).split(",")
        reduce_results = list(map(int, reduce_results))
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

        # 영상 다운로드 및 클립 생성
        input_title = await download_video(url)
        await process_video_segments(time_segments, input_title)

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
