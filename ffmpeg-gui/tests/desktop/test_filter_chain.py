from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from desktop.app.runtime.filter_chain import CommandError, build_stack_command
from shared.contracts import MediaInfo, Operation


def test_crop_adjust_pad_keeps_filter_order() -> None:
    with TemporaryDirectory() as tmp:
        stack = [
            (Operation.crop, {"x": 0, "y": 0, "width": 320, "height": 180, "output_format": "mp4"}, {}),
            (Operation.adjust, {"brightness": 0.1, "contrast": 1.2, "saturation": 1.0, "output_format": "mp4"}, {}),
            (Operation.pad, {"aspect_ratio": "16:9", "color": "black", "output_format": "mp4"}, {}),
        ]

        spec = build_stack_command(
            ffmpeg_bin="ffmpeg",
            input_path=Path(tmp) / "input.mp4",
            output_dir=Path(tmp) / "outputs",
            stack=stack,
        )

        vf_index = spec.args.index("-vf")
        vf_expr = spec.args[vf_index + 1]
        assert vf_expr.index("crop=") < vf_expr.index("eq=") < vf_expr.index("pad=")
        assert spec.args[-1].endswith(".mp4")


def test_speed_fade_keeps_filter_order_and_separation() -> None:
    with TemporaryDirectory() as tmp:
        stack = [
            (Operation.speed, {"factor": 1.5, "output_format": "mp4"}, {}),
            (
                Operation.fade,
                {
                    "fade_in_seconds": 0.2,
                    "fade_out_seconds": 0.0,
                    "duration_seconds": 1.0,
                    "output_format": "mp4",
                },
                {},
            ),
        ]

        spec = build_stack_command(
            ffmpeg_bin="ffmpeg",
            input_path=Path(tmp) / "input.mp4",
            output_dir=Path(tmp) / "outputs",
            stack=stack,
            media_info=MediaInfo(raw={}, duration_seconds=2.0),
        )

        vf_index = spec.args.index("-vf")
        af_index = spec.args.index("-af")
        vf_expr = spec.args[vf_index + 1]
        af_expr = spec.args[af_index + 1]
        assert vf_expr.startswith("setpts=")
        assert "," in vf_expr
        assert vf_expr.index("setpts=") < vf_expr.index("fade=")
        assert af_expr.startswith("atempo=")
        assert "," in af_expr
        assert af_expr.index("atempo=") < af_expr.index("afade=")


def test_stack_rejects_unsupported_operation() -> None:
    with TemporaryDirectory() as tmp:
        with pytest.raises(CommandError):
            build_stack_command(
                ffmpeg_bin="ffmpeg",
                input_path=Path(tmp) / "input.mp4",
                output_dir=Path(tmp) / "outputs",
                stack=[(Operation.raw, {"raw_args": [], "output_extension": "mp4"}, {})],
            )
