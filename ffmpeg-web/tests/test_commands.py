from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from backend.app.ffmpeg import CommandError, build_command


class CommandBuilderTests(unittest.TestCase):
    def test_convert_uses_allowlisted_format_and_argument_array(self) -> None:
        with TemporaryDirectory() as tmp:
            spec = build_command(
                ffmpeg_bin="ffmpeg",
                operation="convert",
                options={"output_format": "mp4"},
                input_path=Path(tmp) / "input.mov",
                output_dir=Path(tmp) / "job",
            )

        self.assertIsInstance(spec.args, list)
        self.assertNotIn(";", spec.args)
        self.assertEqual(spec.output_name, "output.mp4")
        self.assertIn("-progress", spec.args)
        self.assertIn("pipe:1", spec.args)

    def test_rejects_unknown_operation(self) -> None:
        with TemporaryDirectory() as tmp:
            with self.assertRaises(CommandError):
                build_command(
                    ffmpeg_bin="ffmpeg",
                    operation="stack",
                    options={},
                    input_path=Path(tmp) / "input.mp4",
                    output_dir=Path(tmp) / "job",
                )

    def test_rejects_unknown_format(self) -> None:
        with TemporaryDirectory() as tmp:
            with self.assertRaises(CommandError):
                build_command(
                    ffmpeg_bin="ffmpeg",
                    operation="convert",
                    options={"output_format": "exe"},
                    input_path=Path(tmp) / "input.mp4",
                    output_dir=Path(tmp) / "job",
                )

    def test_extract_audio_uses_expected_extension(self) -> None:
        with TemporaryDirectory() as tmp:
            spec = build_command(
                ffmpeg_bin="ffmpeg",
                operation="extract_audio",
                options={"audio_format": "flac"},
                input_path=Path(tmp) / "input.mp4",
                output_dir=Path(tmp) / "job",
            )

        self.assertEqual(spec.output_name, "output.flac")
        self.assertIn("-vn", spec.args)

    def test_new_operations_build_argument_arrays(self) -> None:
        cases = [
            ("mute", {"output_format": "mp4"}, "output.mp4", "-an"),
            ("rotate", {"mode": "hflip", "output_format": "mp4"}, "output.mp4", "hflip"),
            ("crop", {"x": 0, "y": 0, "width": 320, "height": 180, "output_format": "mp4"}, "output.mp4", "crop=320:180:0:0"),
            ("thumbnail", {"timestamp_seconds": 0.5, "image_format": "png"}, "output.png", "-frames:v"),
            ("speed", {"factor": 2, "output_format": "mp4"}, "output.mp4", "setpts=0.5*PTS"),
            ("volume", {"multiplier": 0.5, "output_format": "mp4"}, "output.mp4", "volume=0.5"),
            ("strip_metadata", {"output_format": "mp4"}, "output.mp4", "-map_metadata"),
            ("normalize_audio", {"target_lufs": "-16", "output_format": "mp4"}, "output.mp4", "loudnorm=I=-16:LRA=11:TP=-1.5"),
            ("raw", {"raw_args": ["-vf", "scale=320:-2", "-c:v", "libx264"], "output_extension": "mp4"}, "output.mp4", "scale=320:-2"),
        ]

        with TemporaryDirectory() as tmp:
            for operation, options, output_name, expected_arg in cases:
                with self.subTest(operation=operation):
                    spec = build_command(
                        ffmpeg_bin="ffmpeg",
                        operation=operation,
                        options=options,
                        input_path=Path(tmp) / "input.mp4",
                        output_dir=Path(tmp) / operation,
                    )

                    self.assertIsInstance(spec.args, list)
                    self.assertEqual(spec.output_name, output_name)
                    self.assertIn(expected_arg, spec.args)

    def test_subtitles_requires_existing_asset(self) -> None:
        with TemporaryDirectory() as tmp:
            with self.assertRaises(CommandError):
                build_command(
                    ffmpeg_bin="ffmpeg",
                    operation="subtitles",
                    options={"output_format": "mp4"},
                    input_path=Path(tmp) / "input.mp4",
                    output_dir=Path(tmp) / "job",
                )

    def test_subtitles_uses_asset_path(self) -> None:
        with TemporaryDirectory() as tmp:
            asset_path = Path(tmp) / "caption.srt"
            asset_path.write_text("1\n00:00:00,000 --> 00:00:01,000\nHello\n", encoding="utf-8")
            spec = build_command(
                ffmpeg_bin="ffmpeg",
                operation="subtitles",
                options={"output_format": "mp4"},
                input_path=Path(tmp) / "input.mp4",
                output_dir=Path(tmp) / "job",
                asset_path=asset_path,
            )

        self.assertEqual(spec.output_name, "output.mp4")
        self.assertIn(str(asset_path), spec.args)
        self.assertIn("mov_text", spec.args)

    def test_rejects_invalid_new_operation_options(self) -> None:
        invalid_cases = [
            ("rotate", {"mode": "sideways"}),
            ("crop", {"x": 0, "y": 0, "width": 0, "height": 100}),
            ("speed", {"factor": 8}),
            ("volume", {"multiplier": 8}),
            ("normalize_audio", {"target_lufs": "-99"}),
            ("raw", {"raw_args": ["-i", "other.mp4"], "output_extension": "mp4"}),
            ("raw", {"raw_args": ["-vf", "scale=320:-2"], "output_extension": "sh"}),
        ]

        with TemporaryDirectory() as tmp:
            for operation, options in invalid_cases:
                with self.subTest(operation=operation):
                    with self.assertRaises(CommandError):
                        build_command(
                            ffmpeg_bin="ffmpeg",
                            operation=operation,
                            options=options,
                            input_path=Path(tmp) / "input.mp4",
                            output_dir=Path(tmp) / operation,
                        )


if __name__ == "__main__":
    unittest.main()
