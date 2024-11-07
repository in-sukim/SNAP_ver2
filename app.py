import streamlit as st
import asyncio
from main import main
import os
import shutil
from util.constants import INPUT_DIR, OUTPUT_DIR
from typing import Tuple
from util.ffmpeg_processor import FFmpegProcessor, VideoSegment
from util.video_utils import get_video_duration
from datetime import datetime
import re

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
    # 기본 상태 초기화
    st.session_state.processing_complete = False
    st.session_state.output_files = []

    # 변환 관련 상태 초기화
    for idx in range(1, 11):  # 최대 10개의 클립을 가정
        if f"converted_video_{idx}" in st.session_state:
            del st.session_state[f"converted_video_{idx}"]
        if f"converting_{idx}" in st.session_state:
            del st.session_state[f"converting_{idx}"]

    # 폰트 파일 정리
    if st.session_state.font_file and os.path.exists(st.session_state.font_file):
        os.remove(st.session_state.font_file)
        st.session_state.font_file = None

    clean_directories()
    st.rerun()


async def process_video(url: str):
    """영상 처리 실행."""
    try:
        # 이전 결과 정리
        clean_directories()

        # 모든 상태 초기화
        if "clips_initialized" in st.session_state:
            del st.session_state.clips_initialized

        for idx in range(1, 11):
            if f"converted_video_{idx}" in st.session_state:
                del st.session_state[f"converted_video_{idx}"]
            if f"converting_{idx}" in st.session_state:
                del st.session_state[f"converting_{idx}"]
            if f"status_text_{idx}" in st.session_state:
                del st.session_state[f"status_text_{idx}"]
            if f"overlay_text_{idx}" in st.session_state:
                del st.session_state[f"overlay_text_{idx}"]

        # 중앙 정렬된 스피너와 로딩 메시지
        with st.spinner("🎬 영상 처리 중..."):
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


def process_video_segment_preview(
    video_bytes: bytes, start: float, end: float
) -> bytes:
    """비디오 세그먼트를 추출하는 함수 (미리보기용)"""
    # 임시 디렉토리 생성
    os.makedirs(INPUT_DIR, exist_ok=True)

    temp_input = os.path.join(INPUT_DIR, "temp_input.mp4")
    temp_output = os.path.join(INPUT_DIR, "temp_output.mp4")

    # 입력 비디오 저장
    with open(temp_input, "wb") as f:
        f.write(video_bytes)

    try:
        processor = FFmpegProcessor(temp_input)
        segment = VideoSegment(start_time=int(start), end_time=int(end), index=0)
        os.makedirs(os.path.dirname(temp_output), exist_ok=True)

        asyncio.run(
            processor._process_segment(segment, title=os.path.basename(temp_output))
        )

        if not os.path.exists(temp_output):
            temp_output = os.path.join(
                processor.output_dir, f"{os.path.basename(temp_output)}.mp4"
            )

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
        if os.path.exists(temp_input):
            os.remove(temp_input)
        if os.path.exists(temp_output):
            os.remove(temp_output)
        return video_bytes


async def process_video_segment(
    video_bytes: bytes, start: float, end: float, overlay_text: str
) -> bytes:
    """비디오 세그먼트를 9:16 비율로 변환하고 텍스트를 추가하여 추출하는 함수"""
    os.makedirs(INPUT_DIR, exist_ok=True)

    temp_input = os.path.join(INPUT_DIR, "temp_input.mp4")
    temp_output = os.path.join(INPUT_DIR, "temp_output.mp4")
    final_output = os.path.join(INPUT_DIR, "final_output.mp4")

    with open(temp_input, "wb") as f:
        f.write(video_bytes)

    try:
        processor = FFmpegProcessor(temp_input)
        segment = VideoSegment(start_time=int(start), end_time=int(end), index=0)
        os.makedirs(os.path.dirname(temp_output), exist_ok=True)

        await processor._process_segment(segment, title=os.path.basename(temp_output))

        if not os.path.exists(temp_output):
            temp_output = os.path.join(
                processor.output_dir, f"{os.path.basename(temp_output)}.mp4"
            )

        font_path = (
            st.session_state.font_file
            if st.session_state.font_file
            else "/System/Library/Fonts/AppleSDGothicNeoB.ttc"
        )

        drawtext_filter = (
            f"drawtext=text='{overlay_text}'"
            f":fontfile='{font_path}'"
            ":fontsize=48"
            ":fontcolor=white"
            ":box=1"
            ":boxcolor=black@0.5"
            ":boxborderw=5"
            ":x=(w-text_w)/2"
            ":y=h/4"
        )

        command = [
            "ffmpeg",
            "-i",
            temp_output,
            "-vf",
            f"scale=1080:607,pad=1080:1920:0:656:black,{drawtext_filter}",
            "-c:a",
            "copy",
            "-threads",
            "4",  # CPU 스레드 수 지정
            "-y",
            final_output,
        ]

        process = await asyncio.create_subprocess_exec(
            *command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )

        # 비동기로 프로세스 완료 대기
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            raise Exception(f"FFmpeg 오류: {stderr.decode()}")

        with open(final_output, "rb") as f:
            result = f.read()

        for file in [temp_input, temp_output, final_output]:
            if os.path.exists(file):
                os.remove(file)

        return result
    except Exception as e:
        st.error(f"비디오 변환 중 오류 발생: {e}")
        for file in [temp_input, temp_output, final_output]:
            if os.path.exists(file):
                os.remove(file)
        return video_bytes


def format_time(seconds: float) -> str:
    """초를 시:분:초 형식으로 포맷팅."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds = int(seconds % 60)
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:02d}:{seconds:02d}"


def display_results():
    """처리 결과 표시"""
    if st.session_state.output_files:
        # 전체를 감싸는 컨테이너 생성
        container = st.container()

        with container:
            # 실제 콘텐츠를 감싸는 열 생성
            col1, col2, col3 = st.columns([1, 6, 1])

            with col2:  # 중앙 열에 모든 콘텐츠 배치
                # 제목
                st.markdown(
                    '<h2 style="text-align: center; color: #1E88E5; margin: 2rem 0;">추출된 하이라이트 클립</h2>',
                    unsafe_allow_html=True,
                )

                # 세션 상태 초기화
                if "clips_initialized" not in st.session_state:
                    for idx, (_, title, _) in enumerate(
                        st.session_state.output_files, 1
                    ):
                        st.session_state[f"last_time_range_{idx}"] = (0.0, 0.0)
                        st.session_state[f"last_overlay_text_{idx}"] = title
                        st.session_state[f"converted_video_{idx}"] = None
                        st.session_state[f"converting_{idx}"] = False
                        st.session_state[f"status_text_{idx}"] = ""
                        st.session_state[f"overlay_text_{idx}"] = title
                    st.session_state.clips_initialized = True

                # 각 클립 처리
                for idx, (file_path, title, video_bytes) in enumerate(
                    st.session_state.output_files, 1
                ):
                    with st.container():

                        # 비디오 정보 추출
                        temp_path = os.path.join(INPUT_DIR, f"temp_{idx}.mp4")
                        with open(temp_path, "wb") as f:
                            f.write(video_bytes)

                        duration = get_video_duration(temp_path)

                        col1, col2 = st.columns([3, 1])

                        with col1:
                            overlay_text = st.text_input(
                                "상단 텍스트",
                                value=st.session_state[f"overlay_text_{idx}"],
                                key=f"overlay_text_input_{idx}",
                                help="영상 상단에 표시될 텍스트를 입력하세요",
                            )
                            st.session_state[f"overlay_text_{idx}"] = overlay_text

                            time_range = st.slider(
                                "클립 구간 설정",
                                min_value=0.0,
                                max_value=float(int(duration)),
                                value=(0.0, float(int(duration))),
                                step=1.0,
                                key=f"time_range_{idx}",
                            )

                            # 텍스트나 구이 변경되었는지 확인
                            current_time_range = st.session_state[
                                f"last_time_range_{idx}"
                            ]
                            current_overlay_text = st.session_state[
                                f"last_overlay_text_{idx}"
                            ]

                            if (
                                current_time_range != time_range
                                or current_overlay_text != overlay_text
                            ) and st.session_state[
                                f"converted_video_{idx}"
                            ] is not None:
                                st.session_state[f"converted_video_{idx}"] = None
                                st.session_state[f"status_text_{idx}"] = (
                                    "⚠️ 변경사항이 있습니다. 다시 변환해주세요."
                                )

                            # 현재 값을 저장
                            st.session_state[f"last_time_range_{idx}"] = time_range
                            st.session_state[f"last_overlay_text_{idx}"] = overlay_text

                            st.caption(
                                f"선택된 구간: {format_time(time_range[0])} ~ {format_time(time_range[1])} "
                                f"(총 {format_time(time_range[1] - time_range[0])})"
                            )

                            preview_video = process_video_segment_preview(
                                video_bytes, time_range[0], time_range[1]
                            )
                            st.video(preview_video)

                        with col2:
                            st.markdown(
                                '<div class="convert-button-container">',
                                unsafe_allow_html=True,
                            )
                            # 변환 버튼과 상태 표시
                            is_converting = st.session_state.get(
                                f"converting_{idx}", False
                            )
                            is_converted = (
                                st.session_state.get(f"converted_video_{idx}")
                                is not None
                            )

                            button_label = (
                                "변환 중..."
                                if is_converting
                                else (
                                    "9:16 재변환하기"
                                    if is_converted
                                    else "9:16 변환하기"
                                )
                            )

                            if convert_btn := st.button(
                                button_label,
                                key=f"convert_btn_{idx}",
                                disabled=is_converting,
                                use_container_width=True,
                            ):
                                st.session_state[f"converting_{idx}"] = True
                                st.rerun()
                            st.markdown("</div>", unsafe_allow_html=True)

                            # 변환 작업 실행
                            if st.session_state.get(f"converting_{idx}"):
                                try:
                                    with st.spinner("비디오 변환 중..."):
                                        converted_video = asyncio.run(
                                            process_video_segment(
                                                video_bytes,
                                                time_range[0],
                                                time_range[1],
                                                st.session_state[f"overlay_text_{idx}"],
                                            )
                                        )
                                        st.session_state[f"converted_video_{idx}"] = (
                                            converted_video
                                        )
                                        st.session_state[f"status_text_{idx}"] = (
                                            "✅ 변환 완료!"
                                        )
                                        st.session_state[f"converting_{idx}"] = False
                                except Exception as e:
                                    st.error(f"변환 중 오류 발생: {e}")
                                    st.session_state[f"status_text_{idx}"] = (
                                        "❌ 변환 실패"
                                    )
                                    st.session_state[f"converting_{idx}"] = False

                            # 상태 메시지 표시
                            if status_text := st.session_state.get(
                                f"status_text_{idx}"
                            ):
                                st.caption(status_text)

                            # 변환된 비디오가 있을 때만 다운로드 버튼 표시
                            if converted_video := st.session_state.get(
                                f"converted_video_{idx}"
                            ):
                                # 현재 시간 정보 가져오기
                                current_time = datetime.now().strftime("%Y%m%d_%H%M%S")

                                # 사용자가 입력한 텍스트에서 파일명에 적합하지 않은 문자 제거
                                safe_overlay_text = re.sub(
                                    r'[\\/*?:"<>|]', "", overlay_text
                                )[
                                    :30
                                ]  # 30자로 제한

                                download_filename = (
                                    f"{current_time}_{safe_overlay_text}.mp4"
                                )

                                st.download_button(
                                    label="변환된 클립 다운로드",
                                    data=converted_video,
                                    file_name=download_filename,
                                    mime="video/mp4",
                                    use_container_width=True,
                                )

                        # 임시 파일 삭제
                        os.remove(temp_path)

                        st.markdown("</div>", unsafe_allow_html=True)


# 커스텀 CSS 적용
def apply_custom_css():
    st.markdown(
        """
        <style>
        /* 메인 타이틀 스타일링 */
        .main-title {
            text-align: center;
            padding: 1rem 0 0.5rem 0;
            color: #1E88E5;
        }
        
        /* 서브 타이틀 스타일링 */
        .sub-title {
            text-align: center;
            color: #666;
            font-size: 1.1rem;
            margin-bottom: 2rem;
        }
        
        /* 입력 박스 스타일링 수정 */
        div[data-testid="stForm"] {
            background-color: #f8f9fa;
            padding: 2rem;
            border-radius: 10px;
            margin: 2rem auto;
            width: 90%;  /* 기본 너비 */
            max-width: 800px;  /* 최대 너비 */
            min-width: 320px;  /* 최소 너비 */
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }
        
        /* 입력 필드와 업로더 스타일링 */
        .stTextInput > div > div > input,
        .stFileUploader > div {
            background-color: white;
        }
        
        /* 상태 배지 스타일링 수정 */
        .status-badge {
            display: inline-flex;
            align-items: center;
            padding: 0.25rem 0.75rem;
            border-radius: 4px;
            font-size: 0.875rem;
            background-color: #e9ecef;
            color: #666;
            white-space: nowrap;
            margin-top: 1.5rem;  /* 상단 여백 추가 */
        }
        
        .status-badge.success {
            background-color: #d4edda;
            color: #155724;
        }
        
        /* 구분선 */
        .separator {
            margin: 1.5rem 0;
            border-top: 1px solid rgba(0,0,0,0.1);
        }
        
        /* 버튼 스타일링 */
        .stButton > button {
            height: 38px;
        }
        
        /* 폰트 상태 컨테이너 */
        .font-status-container {
            height: 100%;
            display: flex;
            align-items: center;
            justify-content: flex-start;
        }
        
        /* 파일 업로더 레이블 스타일링 */
        .uploadedFile > label {
            white-space: normal !important;  /* 줄 바꿈 허용 */
            min-height: 1.6em;  /* 최소 높이 설정 */
            line-height: 1.4;  /* 줄 간격 조정 */
        }
        
        /* 반응형 레이아웃 */
        @media (max-width: 768px) {
            div[data-testid="stForm"] {
                width: 95%;  /* 모바일에서 더 넓게 */
                padding: 1.5rem;  /* 패딩 축소 */
            }
            
            .row-widget.stButton {
                min-width: 100%;  /* 버튼 전체 너비 */
            }
        }
        
        @media (max-width: 480px) {
            div[data-testid="stForm"] {
                width: 98%;  /* 더 작 화면에서 더 넓게 */
                padding: 1rem;  /* 패딩 더 축소 */
            }
        }
        
        /* 폰트 업로더 섹션 스타일링 */
        .font-upload-section {
            width: 100%;
            max-width: 600px;
            margin: 0 auto;
            padding: 0;  /* 패딩 제거 */
        }
        
        /* 불필한 여백 제거 */
        .font-upload-section > * {
            margin-bottom: 0;
        }
        
        /* 업로드 레이블 스타일링 수정 */
        .upload-label {
            margin: 0;  /* 마진 제거 */
            padding: 0; /* 패딩 제거 */
            color: rgb(49, 51, 63);
            font-size: 14px;
            font-weight: 400;
        }
        
        .upload-sublabel {
            color: rgb(49, 51, 63);
            font-size: 14px;
            opacity: 0.7;
        }
        
        /* 일 업로더 상단 여백 조정 */
        .stFileUploader > div:first-child {
            margin-top: 0.5rem;  /* 상단 여백 최소화 */
        }

        /* 클립 섹션 컨테이너 스타일링 */
        .clip-section {
            max-width: 1200px;
            width: 90%;
            margin: 2rem auto;
            padding: 0 2rem;
            box-sizing: border-box;
        }

        /* 클립 컨테이너 스타일링 */
        .clip-container {
            background-color: #f8f9fa;
            padding: 2rem;
            border-radius: 10px;
            margin-bottom: 2rem;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
            width: 100%;
        }

        /* 반응형 조정 */
        @media (max-width: 1200px) {
            .clip-section {
                width: 95%;
                padding: 0 1.5rem;
            }
        }

        @media (max-width: 768px) {
            .clip-section {
                width: 100%;
                padding: 0 1rem;
            }
            
            .clip-container {
                padding: 1.5rem;
            }
        }

        /* 스피너 컨테이너 중앙 정렬 */
        .stSpinner > div {
            text-align: center;
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 150px;
        }
        
        /* 스피너 텍스트 스타일링 */
        .stSpinner > div > div,
        .stSpinner > div > div > div {
            font-size: 3.5rem !important;  /* 더 큰 폰트 사이즈로 변경 */
            color: #000000 !important;     /* 검은색 */
            font-weight: 500 !important;   /* 글씨 두께 */
            text-align: center !important; /* 중앙 정렬 강제 */
        }

        /* 스피너 아이콘 크기 조정 */
        .stSpinner > div > div > div > div {
            width: 3rem !important;
            height: 3rem !important;
        }
        </style>
    """,
        unsafe_allow_html=True,
    )


def app_main():
    """스트림릿 앱 메인 함수"""
    # 커스텀 CSS 적용
    apply_custom_css()

    # 세션 상태 초기화
    if "processing_complete" not in st.session_state:
        st.session_state.processing_complete = False
    if "output_files" not in st.session_state:
        st.session_state.output_files = []
    if "font_file" not in st.session_state:
        st.session_state.font_file = None

    # 메인 타이틀과 설명
    st.markdown(
        '<h1 class="main-title">YouTube Highlight Extractor</h1>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p class="sub-title">YouTube 영상의 하이라이트를 자동으로 추출하고 쇼츠 형식으로 변환하세요</p>',
        unsafe_allow_html=True,
    )

    # 모든 입력 요소를 form으로 감싸기
    with st.form("main_form", clear_on_submit=False):
        # URL 입력 필드
        url = st.text_input(
            "YouTube URL을 입력하세요",
            key="url_input",
            placeholder="https://youtube.com/watch?v=...",
        )

        # 구분선
        st.markdown('<div class="separator"></div>', unsafe_allow_html=True)

        # 폰트 파일 업로더 - 컬럼 제거하고 단일 컨테이너로 변경
        st.markdown('<div class="font-upload-section">', unsafe_allow_html=True)
        st.markdown(
            """
            <p class="upload-label">
                폰트 파일을 선택하세요 (TTF/OTF)<br>
                <span class="upload-sublabel">선택하지 않을 시 기본 폰트가 사용됩니다</span>
            </p>
            """,
            unsafe_allow_html=True,
        )
        font_file = st.file_uploader(
            " ",  # 레이블을 비워두고 위의 markdown으로 대체
            type=["ttf", "otf"],
            help="텍스트 오버레이에 사용할 폰트 파일을 업로드하세요",
            key="font_uploader",
        )

        if font_file is not None:
            font_path = os.path.join(
                INPUT_DIR, "custom_font" + os.path.splitext(font_file.name)[1]
            )
            os.makedirs(INPUT_DIR, exist_ok=True)
            with open(font_path, "wb") as f:
                f.write(font_file.getbuffer())
            st.session_state.font_file = font_path
        else:
            st.session_state.font_file = None
        st.markdown("</div>", unsafe_allow_html=True)

        # 구분선
        st.markdown('<div class="separator"></div>', unsafe_allow_html=True)

        # 버튼들
        col1, col2 = st.columns([1, 1])
        with col1:
            extract_button = st.form_submit_button(
                "하이라이트 추출", use_container_width=True
            )
        with col2:
            refresh_button = st.form_submit_button(
                "🔄 초기화", use_container_width=True
            )

    # 버튼 동작 처리
    if refresh_button:
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
