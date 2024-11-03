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


async def process_video(url: str):
    """영상 처리 실행."""
    with st.spinner("영상 처리 중..."):
        try:
            # 이전 결과 정리
            clean_directories()

            await main(url)
            st.success("처리가 완료되었습니다!")

            # 결과 영상 표시
            output_files = []
            for root, dirs, files in os.walk(OUTPUT_DIR):
                for file in files:
                    if file.endswith(".mp4"):
                        output_files.append(os.path.join(root, file))

            if output_files:
                st.subheader("추출된 하이라이트 클립")
                for idx, file in enumerate(sorted(output_files), 1):
                    col1, col2 = st.columns([3, 1])

                    # 영상 표시
                    with col1:
                        with open(file, "rb") as f:
                            video_bytes = f.read()
                        st.video(video_bytes)

                    # 다운로드 버튼
                    with col2:
                        st.download_button(
                            label=f"클립 {idx} 다운로드",
                            data=video_bytes,
                            file_name=f"highlight_clip_{idx}.mp4",
                            mime="video/mp4",
                        )

        except Exception as e:
            st.error(f"오류가 발생했습니다: {str(e)}")


def main_app():
    """Streamlit 앱 메인 함수."""
    st.title("🎬 YouTube 하이라이트 추출기")

    st.markdown(
        """
    ### 사용 방법
    1. YouTube 영상 URL을 입력하세요
    2. '처리 시작' 버튼을 클릭하세요
    3. 처리가 완료되면 하이라이트 클립이 표시됩니다
    4. 원하는 클립의 다운로드 버튼을 클릭하여 저장하세요
    """
    )

    # 세션 상태 초기화
    if "processing" not in st.session_state:
        st.session_state.processing = False

    url = st.text_input("YouTube URL 입력")

    if st.button("처리 시작", disabled=not url or st.session_state.processing):
        if not validate_youtube_url(url):
            st.error("올바른 YouTube URL을 입력해주세요.")
            return

        st.session_state.processing = True
        asyncio.run(process_video(url))
        st.session_state.processing = False


if __name__ == "__main__":
    initialize_directories()
    main_app()
