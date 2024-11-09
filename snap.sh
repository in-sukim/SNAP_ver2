#!/bin/bash

# 기존 컨테이너 정리
docker stop $(docker ps -a -q) 2>/dev/null
docker rm $(docker ps -a -q) 2>/dev/null

# 호스트에 디렉토리 생성
mkdir -p "$(pwd)/input" "$(pwd)/output"

# 도커 이미지 빌드
docker build -t youtube-highlight-extractor .

# 도커 컨테이너 실행 (로그 출력 활성화)
docker run --name highlight-extractor \
  -p 8501:8501 \
  -e OPENAI_API_KEY=${OPENAI_API_KEY} \
  -e PYTHONUNBUFFERED=1 \
  -v "$(pwd)/input":/app/input \
  -v "$(pwd)/output":/app/output \
  youtube-highlight-extractor 2>&1 | tee docker.log

# 로그 실시간 확인 (백그라운드에서 실행되는 경우)
# docker logs -f highlight-extractor