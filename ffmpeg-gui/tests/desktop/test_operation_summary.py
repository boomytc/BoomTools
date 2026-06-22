from __future__ import annotations

from pathlib import Path

from desktop.app.ui.widgets.operation_summary import format_operation_summary, format_stack_summary
from shared.contracts import Operation


def test_operation_summary_includes_crop_region_and_output_format() -> None:
    summary = format_operation_summary(
        Operation.crop,
        {"width": 640, "height": 360, "x": 20, "y": 10, "output_format": "mp4"},
    )

    assert summary == "裁剪 · 640x360+20+10 · MP4"


def test_operation_summary_preserves_zero_values() -> None:
    crop_summary = format_operation_summary(
        Operation.crop,
        {"width": 320, "height": 180, "x": 0, "y": 0, "output_format": "mp4"},
    )
    loop_summary = format_operation_summary(Operation.loop, {"plays": 0, "output_format": "mp4"})

    assert crop_summary == "裁剪 · 320x180+0+0 · MP4"
    assert loop_summary == "循环 · 0次 · MP4"


def test_operation_summary_includes_range_and_extra_input_name() -> None:
    summary = format_operation_summary(
        Operation.overlay,
        {"position": "top_left", "width_percent": 22, "start_seconds": 1.5},
        {"secondary_input": Path("/tmp/logo.png")},
    )

    assert summary == "叠加 · 左上 · 22% · logo.png · 范围 1.5-结尾"


def test_stack_summary_uses_compact_step_parameters() -> None:
    stack = [
        (Operation.crop, {"width": 640, "height": 360, "x": 20, "y": 10, "output_format": "mp4"}, {}),
        (Operation.speed, {"factor": 1.25, "output_format": "mp4"}, {}),
    ]

    assert format_stack_summary(stack) == "Stack x2 · 裁剪 640x360+20+10 -> 速度调整 1.25x"
