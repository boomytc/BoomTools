from __future__ import annotations

from .operations import Operation


STACK_FILTER_OPERATIONS = {
    Operation.resize_compress,
    Operation.crop,
    Operation.rotate,
    Operation.adjust,
    Operation.denoise,
    Operation.sharpen_blur,
    Operation.pad,
    Operation.volume,
    Operation.speed,
    Operation.fade,
}

BATCH_SUPPORTED_OPERATIONS = {
    Operation.convert,
    Operation.compress,
    Operation.resize_compress,
    Operation.extract_audio,
    Operation.gif,
    Operation.mute,
    Operation.speed,
    Operation.rotate,
    Operation.fade,
    Operation.adjust,
    Operation.strip_metadata,
    Operation.loop,
    Operation.pad,
    Operation.normalize_audio,
    Operation.volume,
    Operation.denoise,
    Operation.sharpen_blur,
}
