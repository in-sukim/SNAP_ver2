import streamlit as st
import asyncio
from main import main
import os
import shutil
from util.constants import INPUT_DIR, OUTPUT_DIR
from typing import Tuple
from util.ffmpeg_processor import FFmpegProcessor, VideoSegment
from util.video_utils import get_video_duration

st.set_page_config(
    page_title="YouTube Highlight Extractor", page_icon="🎬", layout="wide"
)


def initialize_directories():
    """입출력 디렉토리 초기화."""
    for dir_path in [INPUT_DIR, OUTPUT_DIR]:
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)


def clean_directories():
    """이전 처리 결과 정리."""
    for dir_path in [INPUT_DIR, OUTPUT_DIR]:
        if os.path.exists(dir_path):
            shutil.rmtree(dir_path)
    initialize_directories()


def validate_youtube_url(url: str) -> bool:
    """유튜브 URL 검증."""
    return "youtube.com/watch?v=" in url or "youtu.be/" in url


def reset_session_state():
    """세션 상태 초기화"""
    st.session_state.processing_complete = False
    st.session_state.output_files = []
    clean_directories()
    st.rerun()


async def process_video(url: str):
    """영상 처리 실행."""
    with st.spinner("영상 처리 중..."):
        try:
            # 이전 결과 정리
            clean_directories()

            await main(url)
            st.session_state.processing_complete = True
            st.success("처리가 완료되었습니다!")

            # 결과 영상 정보 저장
            output_files = []
            for root, dirs, files in os.walk(OUTPUT_DIR):
                for file in files:
                    if file.endswith(".mp4"):
                        file_path = os.path.join(root, file)
                        title = os.path.splitext(file)[0]
                        with open(file_path, "rb") as f:
                            video_bytes = f.read()
                        output_files.append((file_path, title, video_bytes))
            
            st.session_state.output_files = output_files

        except Exception as e:
            st.error(f"오류가 발생했습니다: {str(e)}")


def process_video_segment(video_bytes: bytes, start: float, end: float) -> bytes:
    """비디오 세그먼트를 추출하는 함수"""
    # 임시 디렉토리 생성
    os.makedirs(INPUT_DIR, exist_ok=True)
    
    temp_input = os.path.join(INPUT_DIR, "temp_input.mp4")
    temp_output = os.path.join(INPUT_DIR, "temp_output.mp4")
    
    # 입력 비디오 저장
    with open(temp_input, "wb") as f:
        f.write(video_bytes)
    
    try:
        processor = FFmpegProcessor(temp_input)
        # VideoSegment 객체 생성 및 _process_segment 호출
        segment = VideoSegment(start_time=int(start), end_time=int(end), index=0)
        # temp_output의 디렉토리가 존재하는지 확인
        os.makedirs(os.path.dirname(temp_output), exist_ok=True)
        
        asyncio.run(processor._process_segment(segment, title=os.path.basename(temp_output)))
        
        # 파일이 생성될 때까지 잠시 대기
        if not os.path.exists(temp_output):
            temp_output = os.path.join(processor.output_dir, f"{os.path.basename(temp_output)}.mp4")
        
        with open(temp_output, "rb") as f:
            result = f.read()
        
        # 임시 파일 삭제
        if os.path.exists(temp_input):
            os.remove(temp_input)
        if os.path.exists(temp_output):
            os.remove(temp_output)
        
        return result
    except Exception as e:
        st.error(f"비디오 세그먼트 추출 중 오류 발생: {e}")
        # 임시 파일 정리
        if os.path.exists(temp_input):
            os.remove(temp_input)
        if os.path.exists(temp_output):
            os.remove(temp_output)
        return video_bytes


def format_time(seconds: float) -> str:
    """초를 시:분:초 형식으로 변환"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds = int(seconds % 60)
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:02d}:{seconds:02d}"


def display_results():
    """처리 결과 표시"""
    if st.session_state.output_files:
        st.subheader("추출된 하이라이트 클립")
        
        for idx, (file_path, title, video_bytes) in enumerate(st.session_state.output_files, 1):
            with st.container():
                st.markdown(f"### {title}")
                
                # 비디오 정보 추출
                temp_path = os.path.join(INPUT_DIR, f"temp_{idx}.mp4")
                with open(temp_path, "wb") as f:
                    f.write(video_bytes)
                
                duration = get_video_duration(temp_path)
                
                col1, col2 = st.columns([3, 1])

                with col1:
                    # 시간 조절 슬라이더 (1초 단위로 조절)
                    time_range = st.slider(
                        "클립 구간 설정",
                        min_value=0.0,
                        max_value=float(int(duration)),  # 소수점 제거
                        value=(0.0, float(int(duration))),
                        step=1.0,  # 1초 단위로 변경
                        key=f"time_range_{idx}"
                    )
                    
                    # 선택된 구간 정보를 별도로 표시
                    st.caption(
                        f"선택된 구간: {format_time(time_range[0])} ~ {format_time(time_range[1])} "
                        f"(총 {format_time(time_range[1] - time_range[0])})"
                    )
                    
                    # 현재 선택된 구간의 비디오 표시
                    current_video = process_video_segment(video_bytes, time_range[0], time_range[1])
                    st.video(current_video)

                with col2:
                    # 현재 선택된 구간의 비디오 다운로드
                    st.download_button(
                        label=f"클립 다운로드",
                        data=current_video,
                        file_name=f"{title}.mp4",
                        mime="video/mp4",
                    )
                
                # 임시 파일 삭제
                os.remove(temp_path)
                
                st.divider()


def app_main():
    """스트림릿 앱 메인 함수"""
    # 세션 상태 초기화
    if 'processing_complete' not in st.session_state:
        st.session_state.processing_complete = False
    if 'output_files' not in st.session_state:
        st.session_state.output_files = []

    st.title("YouTube Highlight Extractor")
    st.markdown("YouTube 영상의 하이라이트를 자동으로 추출합니다.")

    # 상단 컨트롤 영역
    col1, col2, col3 = st.columns([4, 2, 1])
    
    with col1:
        url = st.text_input("YouTube URL을 입력하세요")
    with col2:
        extract_button = st.button("하이라이트 추출")
    with col3:
        if st.button("🔄 새로고침"):
            reset_session_state()

    if extract_button:
        if not url:
            st.warning("URL을 입력해주세요.")
        elif not validate_youtube_url(url):
            st.error("올바른 YouTube URL을 입력해주세요.")
        else:
            st.session_state.processing_complete = False
            st.session_state.output_files = []
            asyncio.run(process_video(url))

    # 처리 완료 후 결과 표시
    if st.session_state.processing_complete:
        display_results()


if __name__ == "__main__":
    app_main()
