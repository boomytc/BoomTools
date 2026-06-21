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

        assert spec.args[-1] == str(spec.output_path)
        vf_index = spec.args.index("-vf")
        vf_expr = spec.args[vf_index + 1]
        assert vf_expr.index("crop=") < vf_expr.index("eq=") < vf_expr.index("pad=")
        assert spec.output_path is not None
        assert spec.output_path.suffix == ".mp4"


def test_stack_crop_rejects_region_outside_media_size() -> None:
    with TemporaryDirectory() as tmp:
        stack = [
            (Operation.crop, {"x": 0, "y": 0, "width": 500, "height": 300, "output_format": "mp4"}, {}),
        ]

        with pytest.raises(CommandError, match="裁剪区域超出文件分辨率"):
            build_stack_command(
                ffmpeg_bin="ffmpeg",
                input_path=Path(tmp) / "input.mp4",
                output_dir=Path(tmp) / "outputs",
                stack=stack,
                media_info=MediaInfo(raw={"streams": [{"codec_type": "video", "width": 320, "height": 180}]}),
            )


def test_stack_crop_preflight_accounts_for_prior_resize() -> None:
    with TemporaryDirectory() as tmp:
        stack = [
            (Operation.resize_compress, {"width": 640, "height": 360, "output_format": "mp4"}, {}),
            (Operation.crop, {"x": 0, "y": 0, "width": 500, "height": 300, "output_format": "mp4"}, {}),
        ]

        spec = build_stack_command(
            ffmpeg_bin="ffmpeg",
            input_path=Path(tmp) / "input.mp4",
            output_dir=Path(tmp) / "outputs",
            stack=stack,
            media_info=MediaInfo(raw={"streams": [{"codec_type": "video", "width": 320, "height": 180}]}),
        )

        assert spec.output_path is not None


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
