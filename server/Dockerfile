FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg ca-certificates \
    && rm -rf /var/lib/apt/lists/* && pip install --no-cache-dir -U yt-dlp
WORKDIR /app
COPY fetch.py overrides.json ./
# yt-dlp is upgraded on every run: YouTube changes break old versions within weeks
CMD ["sh", "-c", "pip install -q --no-cache-dir -U yt-dlp >/dev/null 2>&1; python fetch.py"]
