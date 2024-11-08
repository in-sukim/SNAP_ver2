<div align="center">
  <h1>
    YouTube Highlight Extractor 🎬
  </h1>
</div>

<div align="center">

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![OpenAI](https://img.shields.io/badge/OpenAI-API-green.svg)](https://openai.com/)
[![FFmpeg](https://img.shields.io/badge/FFmpeg-required-red.svg)](https://ffmpeg.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

YouTube 영상의 하이라이트를 AI로 자동 추출하고 쇼츠(9:16) 형식으로 변환하는 도구입니다.  
20분 영상 기준 약 10초만에 5개의 하이라이트 클립을 추출합니다.

[주요 기능](#주요-기능) •
[설치 방법](#설치-방법) •
[사용 방법](#사용-방법) •

</div>

<br>

## 📌 주요 기능

<div align="center">
  
| 🤖 AI 기반 하이라이트 추출 | 📱 쇼츠 최적화 | ⚡ 고성능 처리 |
|---|---|---|
| GPT-4o 기반 영상 내용 분석 및 중요 구간 식별 | 9:16 비율 자동 변환 | 비디오 다운로드/분석 병렬 처리로 빠른 속도
| 영상 카테고리별 최적화된 하이라이트 선정 알고리즘 | 자막 기반 상단 텍스트 오버레이 | FFmpeg 기반 고효율 비디오 처리   
| 자동 클립 수 조절 | 구간별 미세 조정 지원 | GPU 가속 지원  

</div>

<br>

## ⚙️ 설치 방법

### 필수 요구사항
- Python 3.10.0 이상
- FFmpeg
- OpenAI API 키

### 설치 단계

1. 저장소 클론
```bash
git clone https://github.com/in-sukim/SNAP_ver2.git
cd SNAP_ver2
```

2. 의존성 설치
```bash
pip install -r requirements.txt
```

3. 환경 변수 설정  
프로젝트 루트에 `.env` 파일 생성:
```bash
OPENAI_API_KEY=your_api_key_here
```

<br>

## 🚀 사용 방법

1. 애플리케이션 실행
```bash
streamlit run app.py
```

2. 웹 인터페이스 사용

| YouTube URL 입력<br>폰트 파일 업로드 (선택사항)<br>"하이라이트 추출" 버튼 클릭 | 결과 |
|:---:|:---:|
| <img src="https://github.com/user-attachments/assets/2f120cfb-95e1-4abe-9fb1-9a514d0e65e4" height=350 width=720> | <img src="https://github.com/user-attachments/assets/ba53d9c1-ec79-4d6c-a058-bc47a316c259" height=350 width=720> |

3. 결과물 커스터마이징

| 텍스트 오버레이 편집<br>클립 구간 미세 조정(선택사항)<br>비율 조정 및 다운로드 | 결과 |
|:---:|:---:|
| <img src="https://github.com/user-attachments/assets/ba53d9c1-ec79-4d6c-a058-bc47a316c259" height=350 width=700> | <img src="https://github.com/user-attachments/assets/4dd8b394-0585-4491-b57e-ec26250495f6" height=430 width=300> |

<br>

## 🛠️ 기술 스택

- **프론트엔드**: Streamlit
- **AI/ML**: OpenAI GPT-4, LangChain
- **비디오 처리**: FFmpeg, MoviePy
- **유튜브 통합**: PyTubeFix, YouTube Transcript API
---

<div align="center">
Made with  by <a href="https://github.com/in-sukim">in-sukim</a>
</div>
