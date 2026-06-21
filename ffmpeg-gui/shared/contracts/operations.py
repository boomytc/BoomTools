from __future__ import annotations

from enum import StrEnum


class Operation(StrEnum):
    convert = "convert"
    resize_compress = "resize_compress"
    compress = "compress"
    extract_audio = "extract_audio"
    gif = "gif"
    mute = "mute"
    rotate = "rotate"
    crop = "crop"
    thumbnail = "thumbnail"
    reverse = "reverse"
    fade = "fade"
    adjust = "adjust"
    loop = "loop"
    strip_metadata = "strip_metadata"
    pad = "pad"
    denoise = "denoise"
    boomerang = "boomerang"
    sharpen_blur = "sharpen_blur"
    speed = "speed"
    volume = "volume"
    normalize_audio = "normalize_audio"
    subtitles = "subtitles"
    media_info = "media_info"
    raw = "raw"
    overlay = "overlay"
    mix_audio = "mix_audio"
    concat = "concat"
    side_by_side = "side_by_side"
    picture_in_picture = "picture_in_picture"


OPERATION_LABELS: dict[Operation, str] = {
    Operation.convert: "基础 - 转换格式",
    Operation.resize_compress: "基础 - 缩放+压缩",
    Operation.compress: "基础 - 压缩视频",
    Operation.extract_audio: "基础 - 抽取音频",
    Operation.gif: "基础 - 生成 GIF",
    Operation.mute: "视频编辑 - 静音",
    Operation.rotate: "视频编辑 - 旋转/翻转",
    Operation.crop: "视频编辑 - 裁剪",
    Operation.thumbnail: "视频编辑 - 提取封面",
    Operation.reverse: "视频编辑 - 倒放",
    Operation.fade: "视频编辑 - 淡入淡出",
    Operation.adjust: "视频编辑 - 亮度/对比/饱和度",
    Operation.loop: "视频编辑 - 循环",
    Operation.strip_metadata: "视频编辑 - 移除元数据",
    Operation.pad: "视频编辑 - 画布补边",
    Operation.denoise: "视频编辑 - 去噪",
    Operation.boomerang: "视频编辑 - 倒放回放",
    Operation.sharpen_blur: "视频编辑 - 锐化/模糊",
    Operation.speed: "视频编辑 - 速度调整",
    Operation.volume: "音频 - 音量调整",
    Operation.normalize_audio: "音频 - 响度标准化",
    Operation.subtitles: "字幕 - 嵌入字幕",
    Operation.media_info: "信息 - 媒体探测",
    Operation.raw: "高级 - Raw 参数",
    Operation.overlay: "高级 - 叠加",
    Operation.mix_audio: "音频 - 混音",
    Operation.concat: "高级 - 视频拼接",
    Operation.side_by_side: "高级 - 并排对比",
    Operation.picture_in_picture: "高级 - 画中画",
}


OPERATION_SHORT_LABELS: dict[Operation, str] = {
    Operation.convert: "转换格式",
    Operation.resize_compress: "缩放压缩",
    Operation.compress: "压缩视频",
    Operation.extract_audio: "抽取音频",
    Operation.gif: "生成 GIF",
    Operation.mute: "静音",
    Operation.rotate: "旋转翻转",
    Operation.crop: "裁剪",
    Operation.thumbnail: "提取封面",
    Operation.reverse: "倒放",
    Operation.fade: "淡入淡出",
    Operation.adjust: "画面调整",
    Operation.loop: "循环",
    Operation.strip_metadata: "移除元数据",
    Operation.pad: "画布补边",
    Operation.denoise: "去噪",
    Operation.boomerang: "倒放回放",
    Operation.sharpen_blur: "锐化模糊",
    Operation.speed: "速度调整",
    Operation.volume: "音量调整",
    Operation.normalize_audio: "响度标准化",
    Operation.subtitles: "嵌入字幕",
    Operation.media_info: "媒体探测",
    Operation.raw: "Raw 参数",
    Operation.overlay: "叠加",
    Operation.mix_audio: "混音",
    Operation.concat: "视频拼接",
    Operation.side_by_side: "并排对比",
    Operation.picture_in_picture: "画中画",
}


def operation_label(operation: Operation) -> str:
    return OPERATION_LABELS.get(operation, operation.value)


def operation_category_label(operation: Operation) -> str:
    label = operation_label(operation)
    if " - " not in label:
        return "未分类"
    return label.split(" - ", 1)[0]


def operation_short_label(operation: Operation) -> str:
    label = operation_label(operation)
    if operation in OPERATION_SHORT_LABELS:
        return OPERATION_SHORT_LABELS[operation]
    if " - " not in label:
        return label
    return label.split(" - ", 1)[1]


def operation_title_and_category(operation: Operation) -> tuple[str, str]:
    return operation_short_label(operation), operation_category_label(operation)
