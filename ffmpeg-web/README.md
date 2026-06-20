# ffmpeg-web

本机版 ffmpeg Web 工具。前端是静态 HTML/CSS/Vanilla JS，后端是 FastAPI，只提供 JSON API 和 SSE。媒体处理直接调用本机 `ffmpeg` / `ffprobe`，不使用浏览器端 ffmpeg.wasm，也不包含 Whisper 自动字幕。

## 功能

- 上传本机媒体文件
- 查看 `ffprobe` 媒体信息
- 转换视频格式：MP4、WebM、MOV、MKV
- 压缩视频：CRF、preset、可选宽度
- 抽取音频：MP3、WAV、AAC、FLAC
- 生成 GIF：帧率和宽度可调
- 任务进度、日志、下载输出、清理任务

## 安装

需要 `uv` 和 Python 3.14。

确认本机有 ffmpeg：

```bash
ffmpeg -version
ffprobe -version
```

创建虚拟环境并安装后端依赖：

```bash
cd /Users/boom/workspace/BoomTools/ffmpeg-web
uv venv --python 3.14
uv pip install -r requirements.txt
```

## 启动

```bash
cd /Users/boom/workspace/BoomTools/ffmpeg-web
uv run uvicorn backend.app.main:app --host 127.0.0.1 --port 7861 --reload
```

浏览器访问：

```text
http://127.0.0.1:7861/
```

如需指定 ffmpeg 路径：

```bash
FFMPEG_BIN=/opt/homebrew/bin/ffmpeg FFPROBE_BIN=/opt/homebrew/bin/ffprobe uv run uvicorn backend.app.main:app --host 127.0.0.1 --port 7861
```

## API

- `GET /api/health`
- `POST /api/uploads`
- `POST /api/jobs`
- `GET /api/jobs/{job_id}`
- `GET /api/jobs/{job_id}/events`
- `GET /api/jobs/{job_id}/download`
- `DELETE /api/jobs/{job_id}`

## 验证

```bash
cd /Users/boom/workspace/BoomTools/ffmpeg-web
uv run python -m compileall backend/app tests
uv run python -m unittest discover tests
```

上传和输出文件写入 `ffmpeg-web/data/`，该目录不会提交到 git。
