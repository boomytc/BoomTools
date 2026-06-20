from __future__ import annotations

from typing import Any

from shared.contracts import Operation


VIDEO_FORMAT_CHOICES = ["mp4", "webm", "mov", "mkv", "avi"]
AUDIO_FORMAT_CHOICES = ["mp3", "wav", "aac", "flac", "ogg"]
ROTATE_CHOICES = ["cw90", "ccw90", "180", "hflip", "vflip", "hvflip"]
RAW_PRESET_OPTIONS: list[tuple[str, str]] = [
    ("drawbox watermark", "-vf drawbox=x=40:y=40:w=160:h=80:color=black@0.5:t=4"),
    ("cap framerate", "-r 30"),
    ("grayscale", "-vf hue=s=0"),
    ("loudnorm", "-af loudnorm"),
    ("lossless remux", "-c copy"),
    ("letterbox", "-vf pad=ih*16/9:ih:(ow-iw)/2:(oh-ih)/2:color=black"),
    ("denoise", "-vf hqdn3d=2:2:3:3"),
    ("sharpen", "-vf unsharp=5:5:1.0:5:5:0.3"),
    ("deshake", "-vf deshake"),
    ("vignette", "-vf vignette=PI/4"),
    ("extract wav", "-vn -acodec pcm_s16le"),
    ("first frame", "-vframes 1 -q:v 2"),
    ("replace audio with second input", "-map 0:v -map 1:a -c:v copy -c:a copy -shortest"),
]

FIELD_SPECS: dict[Operation, list[dict[str, Any]]] = {
    Operation.convert: [
        {"name": "output_format", "label": "输出格式", "kind": "choice", "choices": VIDEO_FORMAT_CHOICES, "default": "mp4"},
    ],
    Operation.resize_compress: [
        {"name": "output_format", "label": "输出格式", "kind": "choice", "choices": VIDEO_FORMAT_CHOICES, "default": "mp4"},
        {"name": "width", "label": "宽度", "kind": "optional_int", "placeholder": "可选，例如 1280"},
        {"name": "height", "label": "高度", "kind": "optional_int", "placeholder": "可选，例如 720"},
        {"name": "crf", "label": "CRF", "kind": "int", "min": 18, "max": 51, "default": 23},
        {"name": "preset", "label": "Preset", "kind": "choice", "choices": [
            "ultrafast",
            "superfast",
            "veryfast",
            "faster",
            "fast",
            "medium",
            "slow",
            "slower",
            "veryslow",
        ], "default": "medium"},
    ],
    Operation.compress: [
        {"name": "output_format", "label": "输出格式", "kind": "choice", "choices": VIDEO_FORMAT_CHOICES, "default": "mp4"},
        {"name": "crf", "label": "CRF", "kind": "int", "min": 18, "max": 51, "default": 23},
        {"name": "preset", "label": "Preset", "kind": "choice", "choices": [
            "ultrafast",
            "superfast",
            "veryfast",
            "faster",
            "fast",
            "medium",
            "slow",
            "slower",
            "veryslow",
        ], "default": "medium"},
        {"name": "width", "label": "宽度", "kind": "optional_int", "placeholder": "可选，例如 1280"},
    ],
    Operation.extract_audio: [
        {"name": "audio_format", "label": "音频格式", "kind": "choice", "choices": AUDIO_FORMAT_CHOICES, "default": "mp3"},
    ],
    Operation.gif: [
        {"name": "fps", "label": "帧率", "kind": "int", "min": 1, "max": 30, "default": 10},
        {"name": "width", "label": "宽度", "kind": "int", "min": 64, "max": 1920, "default": 480},
    ],
    Operation.mute: [
        {"name": "output_format", "label": "输出格式", "kind": "choice", "choices": VIDEO_FORMAT_CHOICES, "default": "mp4"},
    ],
    Operation.rotate: [
        {"name": "mode", "label": "模式", "kind": "choice", "choices": ROTATE_CHOICES, "default": "cw90"},
        {"name": "output_format", "label": "输出格式", "kind": "choice", "choices": VIDEO_FORMAT_CHOICES, "default": "mp4"},
    ],
    Operation.crop: [
        {"name": "x", "label": "X", "kind": "int", "min": 0, "max": 7680, "default": 0},
        {"name": "y", "label": "Y", "kind": "int", "min": 0, "max": 4320, "default": 0},
        {"name": "width", "label": "宽度", "kind": "int", "min": 1, "max": 7680, "default": 320},
        {"name": "height", "label": "高度", "kind": "int", "min": 1, "max": 4320, "default": 180},
        {"name": "output_format", "label": "输出格式", "kind": "choice", "choices": VIDEO_FORMAT_CHOICES, "default": "mp4"},
    ],
    Operation.thumbnail: [
        {"name": "timestamp_seconds", "label": "时间点秒", "kind": "float", "min": 0.0, "max": 86400.0, "default": 0.0},
        {"name": "image_format", "label": "图片格式", "kind": "choice", "choices": ["jpg", "png"], "default": "jpg"},
    ],
    Operation.speed: [
        {"name": "factor", "label": "倍率", "kind": "float", "min": 0.25, "max": 4.0, "default": 1.0},
        {"name": "output_format", "label": "输出格式", "kind": "choice", "choices": VIDEO_FORMAT_CHOICES, "default": "mp4"},
    ],
    Operation.reverse: [
        {"name": "output_format", "label": "输出格式", "kind": "choice", "choices": VIDEO_FORMAT_CHOICES, "default": "mp4"},
        {"name": "include_audio", "label": "保留音频", "kind": "bool", "default": True},
    ],
    Operation.fade: [
        {"name": "fade_in_seconds", "label": "淡入秒数", "kind": "float", "min": 0.0, "max": 120.0, "default": 0.0},
        {"name": "fade_out_seconds", "label": "淡出秒数", "kind": "float", "min": 0.0, "max": 120.0, "default": 0.0},
        {"name": "output_format", "label": "输出格式", "kind": "choice", "choices": VIDEO_FORMAT_CHOICES, "default": "mp4"},
    ],
    Operation.adjust: [
        {"name": "brightness", "label": "亮度", "kind": "float", "min": -1.0, "max": 1.0, "default": 0.0},
        {"name": "contrast", "label": "对比度", "kind": "float", "min": 0.0, "max": 2.0, "default": 1.0},
        {"name": "saturation", "label": "饱和度", "kind": "float", "min": 0.0, "max": 3.0, "default": 1.0},
        {"name": "grayscale", "label": "黑白", "kind": "bool", "default": False},
        {"name": "output_format", "label": "输出格式", "kind": "choice", "choices": VIDEO_FORMAT_CHOICES, "default": "mp4"},
    ],
    Operation.loop: [
        {"name": "plays", "label": "循环次数", "kind": "int", "min": 2, "max": 50, "default": 2},
        {"name": "output_format", "label": "输出格式", "kind": "choice", "choices": ["mp4", "mkv", "mov"], "default": "mp4"},
    ],
    Operation.strip_metadata: [
        {"name": "output_format", "label": "输出格式", "kind": "choice", "choices": VIDEO_FORMAT_CHOICES, "default": "mp4"},
    ],
    Operation.pad: [
        {"name": "aspect_ratio", "label": "目标比例", "kind": "choice", "choices": ["16:9", "9:16", "1:1", "4:3", "4:5", "21:9"], "default": "16:9"},
        {"name": "color", "label": "背景颜色", "kind": "choice", "choices": ["black", "white", "gray"], "default": "black"},
        {"name": "output_format", "label": "输出格式", "kind": "choice", "choices": VIDEO_FORMAT_CHOICES, "default": "mp4"},
    ],
    Operation.denoise: [
        {"name": "strength", "label": "降噪强度", "kind": "choice", "choices": ["light", "medium", "heavy"], "default": "light"},
        {"name": "output_format", "label": "输出格式", "kind": "choice", "choices": VIDEO_FORMAT_CHOICES, "default": "mp4"},
    ],
    Operation.boomerang: [
        {"name": "output_format", "label": "输出格式", "kind": "choice", "choices": VIDEO_FORMAT_CHOICES, "default": "mp4"},
    ],
    Operation.sharpen_blur: [
        {"name": "mode", "label": "模式", "kind": "choice", "choices": ["sharpen", "blur"], "default": "sharpen"},
        {"name": "strength", "label": "强度", "kind": "choice", "choices": ["light", "medium", "heavy"], "default": "light"},
        {"name": "output_format", "label": "输出格式", "kind": "choice", "choices": VIDEO_FORMAT_CHOICES, "default": "mp4"},
    ],
    Operation.volume: [
        {"name": "multiplier", "label": "音量倍数", "kind": "float", "min": 0.0, "max": 4.0, "default": 1.0},
        {"name": "output_format", "label": "输出格式", "kind": "choice", "choices": VIDEO_FORMAT_CHOICES, "default": "mp4"},
    ],
    Operation.normalize_audio: [
        {"name": "target_lufs", "label": "目标 LUFS", "kind": "choice", "choices": ["-14", "-16", "-23"], "default": "-16"},
        {"name": "output_format", "label": "输出格式", "kind": "choice", "choices": VIDEO_FORMAT_CHOICES, "default": "mp4"},
    ],
    Operation.subtitles: [
        {"name": "subtitle", "label": "字幕文件", "kind": "file", "extensions": ["*.srt", "*.vtt", "*.ass", "*.ssa"], "filter": "Subtitles (*.srt *.vtt *.ass *.ssa)", "placeholder": "请先选择字幕文件"},
        {"name": "mode", "label": "字幕模式", "kind": "choice", "choices": ["soft", "burn"], "default": "soft"},
        {"name": "output_format", "label": "输出格式", "kind": "choice", "choices": ["mp4", "webm", "mov", "mkv"], "default": "mp4"},
        {"name": "font_size", "label": "文字大小", "kind": "choice", "choices": ["small", "medium", "large"], "default": "medium"},
    ],
    Operation.media_info: [],
    Operation.raw: [
        {"name": "raw_preset", "label": "示例命令", "kind": "raw_preset"},
        {"name": "raw_args", "label": "参数数组", "kind": "raw", "placeholder": "仅填写 ffmpeg 输入文件之后、输出文件之前的参数；不要包含 -i、输入路径或输出路径。"},
        {"name": "secondary_input", "label": "第二输入（可选）", "kind": "file", "filter": "媒体文件 (*.*)", "placeholder": "可选，用于复杂组合"},
        {"name": "output_extension", "label": "输出扩展名", "kind": "choice", "choices": ["mp4", "webm", "mov", "mkv", "avi", "mp3", "wav", "aac", "flac", "ogg", "jpg", "png", "gif"], "default": "mp4"},
    ],
    Operation.overlay: [
        {"name": "secondary_input", "label": "叠加图片", "kind": "file", "extensions": ["*.png", "*.jpg", "*.jpeg", "*.webp", "*.gif"], "filter": "Images (*.png *.jpg *.jpeg *.webp *.gif)"},
        {"name": "position", "label": "位置", "kind": "choice", "choices": ["bottom_right", "top_left", "top_right", "bottom_left", "center"], "default": "bottom_right"},
        {"name": "width_percent", "label": "缩放百分比", "kind": "int", "min": 1, "max": 100, "default": 15},
        {"name": "output_format", "label": "输出格式", "kind": "choice", "choices": VIDEO_FORMAT_CHOICES, "default": "mp4"},
    ],
    Operation.mix_audio: [
        {"name": "secondary_input", "label": "音频文件", "kind": "file", "extensions": ["*.mp3", "*.wav", "*.ogg", "*.aac", "*.flac", "*.m4a"], "filter": "Audio (*.mp3 *.wav *.ogg *.aac *.flac *.m4a)"},
        {"name": "original_volume", "label": "原音量", "kind": "float", "min": 0.0, "max": 2.0, "default": 1.0},
        {"name": "music_volume", "label": "混音音量", "kind": "float", "min": 0.0, "max": 2.0, "default": 1.0},
        {"name": "loop_music", "label": "循环音乐", "kind": "bool", "default": True},
        {"name": "output_format", "label": "输出格式", "kind": "choice", "choices": VIDEO_FORMAT_CHOICES, "default": "mp4"},
    ],
    Operation.concat: [
        {"name": "secondary_input", "label": "第二段视频", "kind": "file", "extensions": ["*.mp4", "*.mov", "*.mkv", "*.avi", "*.webm", "*.flv", "*.m4v", "*.mpg", "*.mpeg", "*.wmv", "*.ts", "*.m2ts"], "filter": "Videos (*.mp4 *.mov *.mkv *.avi *.webm *.flv *.m4v *.mpg *.mpeg *.wmv *.ts *.m2ts)"},
        {"name": "output_format", "label": "输出格式", "kind": "choice", "choices": VIDEO_FORMAT_CHOICES, "default": "mp4"},
    ],
    Operation.side_by_side: [
        {"name": "secondary_input", "label": "第二段视频", "kind": "file", "extensions": ["*.mp4", "*.mov", "*.mkv", "*.avi", "*.webm", "*.flv", "*.m4v", "*.mpg", "*.mpeg", "*.wmv", "*.ts", "*.m2ts"], "filter": "Videos (*.mp4 *.mov *.mkv *.avi *.webm *.flv *.m4v *.mpg *.mpeg *.wmv *.ts *.m2ts)"},
        {"name": "layout", "label": "布局", "kind": "choice", "choices": ["horizontal", "vertical"], "default": "horizontal"},
        {"name": "common_dimension", "label": "统一尺寸", "kind": "int", "min": 64, "max": 4320, "default": 720},
        {"name": "audio_source", "label": "音频来源", "kind": "choice", "choices": ["first", "second", "none"], "default": "first"},
        {"name": "output_format", "label": "输出格式", "kind": "choice", "choices": VIDEO_FORMAT_CHOICES, "default": "mp4"},
    ],
    Operation.picture_in_picture: [
        {"name": "secondary_input", "label": "覆盖画面", "kind": "file", "extensions": ["*.mp4", "*.mov", "*.mkv", "*.avi", "*.webm", "*.flv", "*.m4v", "*.mpg", "*.mpeg", "*.wmv", "*.ts", "*.m2ts"], "filter": "Videos (*.mp4 *.mov *.mkv *.avi *.webm *.flv *.m4v *.mpg *.mpeg *.wmv *.ts *.m2ts)"},
        {"name": "position", "label": "位置", "kind": "choice", "choices": ["bottom_right", "top_left", "top_right", "bottom_left", "center"], "default": "bottom_right"},
        {"name": "width_percent", "label": "缩放百分比", "kind": "int", "min": 1, "max": 100, "default": 30},
        {"name": "loop_overlay", "label": "循环覆盖视频", "kind": "bool", "default": True},
        {"name": "output_format", "label": "输出格式", "kind": "choice", "choices": VIDEO_FORMAT_CHOICES, "default": "mp4"},
    ],
}
