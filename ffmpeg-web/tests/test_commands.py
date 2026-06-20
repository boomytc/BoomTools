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
                    operation="raw",
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


if __name__ == "__main__":
    unittest.main()

