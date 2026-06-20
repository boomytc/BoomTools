from __future__ import annotations

from enum import StrEnum


class Operation(StrEnum):
    convert = "convert"
    compress = "compress"
    extract_audio = "extract_audio"
    gif = "gif"
    mute = "mute"
    rotate = "rotate"
    crop = "crop"
    thumbnail = "thumbnail"
    speed = "speed"
    volume = "volume"
    strip_metadata = "strip_metadata"
    normalize_audio = "normalize_audio"
    subtitles = "subtitles"
    raw = "raw"


OPERATION_LABELS: dict[Operation, str] = {
    Operation.convert: "基础 - 转换格式",
    Operation.compress: "基础 - 压缩视频",
    Operation.extract_audio: "基础 - 抽取音频",
    Operation.gif: "基础 - 生成 GIF",
    Operation.mute: "视频编辑 - 静音",
    Operation.rotate: "视频编辑 - 旋转/翻转",
    Operation.crop: "视频编辑 - 裁剪",
    Operation.thumbnail: "视频编辑 - 提取封面",
    Operation.speed: "视频编辑 - 速度调整",
    Operation.strip_metadata: "视频编辑 - 移除元数据",
    Operation.volume: "音频 - 音量调整",
    Operation.normalize_audio: "音频 - 响度标准化",
    Operation.subtitles: "字幕 - 软字幕嵌入",
    Operation.raw: "高级 - Raw FFmpeg 参数",
}


def operation_label(operation: Operation) -> str:
    return OPERATION_LABELS.get(operation, operation.value)
