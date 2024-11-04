import streamlit as st
import asyncio
from main import main
import os
import shutil
from util.constants import INPUT_DIR, OUTPUT_DIR

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


def display_results():
    """처리 결과 표시"""
    if st.session_state.output_files:
        st.subheader("추출된 하이라이트 클립")
        
        for idx, (file_path, title, video_bytes) in enumerate(st.session_state.output_files, 1):
            with st.container():
                st.markdown(f"### {title}")
                
                col1, col2 = st.columns([3, 1])

                with col1:
                    st.video(video_bytes)

                with col2:
                    st.download_button(
                        label=f"클립 다운로드",
                        data=video_bytes,
                        file_name=f"{title}.mp4",
                        mime="video/mp4",
                    )
                
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
