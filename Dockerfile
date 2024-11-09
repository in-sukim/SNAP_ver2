FROM python:3.11
WORKDIR /app

# Install basic dependencies and Chromium
RUN apt-get update && apt-get install -y \
    wget \
    ffmpeg \
    gnupg \
    curl \
    unzip \
    dpkg \
    apt-utils \
    chromium \
    chromium-driver \
    # Build dependencies
    build-essential \
    python3-dev \
    pkg-config \
    # Basic fonts
    fonts-dejavu \
    fonts-liberation \
    # Korean fonts (minimal)
    fonts-noto-cjk

# Install additional dependencies
RUN apt-get install -y \
    fonts-liberation \
    libasound2 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libatspi2.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libxss1 \
    libxtst6 \
    xdg-utils

# Upgrade pip and install wheel
RUN python -m pip install --upgrade pip && \
    pip install wheel setuptools

# Install Python packages with more flexible version constraints
COPY requirements.txt .
RUN pip install -r requirements.txt --no-cache-dir --ignore-installed

COPY . .

# Set environment variables
ENV DISPLAY=:99
ENV CHROMIUM_PATH=/usr/bin/chromium
ENV CHROMEDRIVER_PATH=/usr/bin/chromedriver
ENV CHROME_BIN=/usr/bin/chromium
ENV SELENIUM_DRIVER_PATH=/usr/bin/chromedriver
# Disable Streamlit welcome message and telemetry
ENV STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
ENV STREAMLIT_SERVER_HEADLESS=true
# Prevent webdriver manager from downloading drivers
ENV WDM_LOCAL=1
ENV WDM_SSL_VERIFY=0
# 로깅 관련 환경변수 추가
ENV PYTHONUNBUFFERED=1
ENV STREAMLIT_SERVER_HEADLESS=true
ENV STREAMLIT_LOGGER=INFO
# 한글 환경 설정
ENV LANG=ko_KR.UTF-8
ENV LC_ALL=ko_KR.UTF-8

# Create directory for chrome user data
RUN mkdir -p /tmp/chrome-user-data

# Set permissions
RUN chmod -R 777 /tmp/chrome-user-data

CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0", "--server.port=8501"]