#!/bin/bash

BOLD='\033[1m'
RED='\033[0;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
NC='\033[0m'

clear
echo -e "${CYAN}"
echo "  KAAI BACKEND SYSTEM"
echo "  MODE: Raw Download -> Local FFmpeg -> Stream Buffer"
echo -e "${NC}"
echo -e "${BOLD}------------------------------------------------------------${NC}"

echo -e "${CYAN}[SYSTEM]${NC} Preparing Environment..."

rm -rf __pycache__ .cache 2>/dev/null

mkdir -p .local/bin
mkdir -p .local/lib
mkdir -p logs
mkdir -p log_error
mkdir -p tmp
mkdir -p tmp/ytdl
mkdir -p tmp/ytdl_mentah
mkdir -p cache
mkdir -p engine

export PYTHONUSERBASE="$(pwd)/.local"
export PATH="$(pwd)/.local/bin:$PATH"
export PYTHONPATH="$(pwd)/.local/lib:$PYTHONPATH"
export PIP_DISABLE_PIP_VERSION_CHECK=1
export PIP_NO_CACHE_DIR=1

if [ -f "ffmpeg.tar.xz" ] && [ ! -d "ffmpeg-master-latest-linux64-gpl" ]; then
    echo -e "${CYAN}[SETUP]${NC} Extracting FFmpeg..."
    tar -xf ffmpeg.tar.xz
fi

FFMPEG_HOME="$(pwd)/ffmpeg-master-latest-linux64-gpl/bin"

if [ -d "$FFMPEG_HOME" ]; then
    chmod +x "$FFMPEG_HOME/ffmpeg"
    chmod +x "$FFMPEG_HOME/ffprobe"
    export PATH="$FFMPEG_HOME:$PATH"

    if command -v ffmpeg >/dev/null 2>&1; then
        VER=$(ffmpeg -version | head -n 1 | awk '{print $3}')
        echo -e "${GREEN}[OK]${NC} FFmpeg Ready: $VER"
    else
        echo -e "${RED}[FAIL]${NC} FFmpeg binary error"
        exit 1
    fi
else
    echo -e "${RED}[FAIL]${NC} FFmpeg folder not found"
    exit 1
fi

if [ ! -f ".local/.deps_installed" ]; then
    echo -e "${CYAN}[SETUP]${NC} Installing Python Dependencies to .local..."
    python3 -m pip install --upgrade pip --user --quiet
    python3 -m pip install --user -r requirements.txt
    touch .local/.deps_installed
fi

if [ -f "./cloudflared" ]; then
    chmod +x ./cloudflared
fi

echo -e "${GREEN}[START]${NC} Launching Backend..."
echo ""

exec python3 main.py