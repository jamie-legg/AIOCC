"""Upload-time video inspection and platform optimization."""

import json
import subprocess
from pathlib import Path
from typing import Any, Optional


class VideoProcessor:
    """Keeps uploaded videos compatible with the target publishing APIs."""

    supported_formats = [".mp4", ".mov", ".avi", ".mkv", ".webm"]

    def optimize_for_platform(self, input_path: Path, platform: str, output_path: Optional[Path] = None) -> Path:
        if not input_path.exists():
            raise FileNotFoundError(f"Input video not found: {input_path}")

        if not self._is_supported_format(input_path):
            raise ValueError(f"Unsupported video format: {input_path.suffix}")

        profile = self._platform_profile(platform)
        if output_path is None:
            output_path = input_path.parent / f"{input_path.stem}_{platform}_optimized.mp4"

        info = self.get_video_info(input_path)
        current_fps = info.get("fps", 30.0)
        file_size_mb = input_path.stat().st_size / (1024 * 1024)

        needs_optimization = (
            info["width"] != profile["width"]
            or info["height"] != profile["height"]
            or abs(current_fps - profile["fps"]) > 0.1
            or (platform == "tiktok" and file_size_mb > 100)
            or input_path.suffix.lower() != ".mp4"
        )

        if not needs_optimization:
            return input_path

        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            str(input_path),
            "-vf",
            f"scale={profile['width']}:{profile['height']}:force_original_aspect_ratio=decrease,"
            f"pad={profile['width']}:{profile['height']}:(ow-iw)/2:(oh-ih)/2:black",
            "-c:v",
            "libx264",
            "-preset",
            "fast",
            "-crf",
            profile["crf"],
            "-maxrate",
            profile["video_bitrate"],
            "-bufsize",
            profile["buffer_size"],
            "-r",
            str(profile["fps"]),
            "-c:a",
            "aac",
            "-b:a",
            profile["audio_bitrate"],
            "-ar",
            "48000",
            "-ac",
            "2",
            "-movflags",
            "+faststart",
            str(output_path),
        ]

        try:
            subprocess.run(cmd, capture_output=True, text=True, check=True)
        except subprocess.CalledProcessError as error:
            raise RuntimeError(f"FFmpeg optimization failed: {error.stderr}") from error

        return output_path

    def get_video_info(self, video_path: Path) -> dict[str, Any]:
        if not video_path.exists():
            raise FileNotFoundError(f"Input video not found: {video_path}")

        cmd = [
            "ffprobe",
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_streams",
            "-show_format",
            str(video_path),
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            data = json.loads(result.stdout)
        except subprocess.CalledProcessError as error:
            raise RuntimeError(f"ffprobe failed: {error.stderr}") from error
        except json.JSONDecodeError as error:
            raise RuntimeError("ffprobe returned invalid JSON") from error

        video_stream = next((stream for stream in data.get("streams", []) if stream.get("codec_type") == "video"), {})
        audio_stream = next((stream for stream in data.get("streams", []) if stream.get("codec_type") == "audio"), {})
        format_info = data.get("format", {})

        fps = self._parse_fps(video_stream.get("avg_frame_rate") or video_stream.get("r_frame_rate"))

        return {
            "width": int(video_stream.get("width") or 0),
            "height": int(video_stream.get("height") or 0),
            "duration": float(format_info.get("duration") or video_stream.get("duration") or 0),
            "fps": fps,
            "codec": video_stream.get("codec_name", "unknown"),
            "bitrate": int(video_stream.get("bit_rate") or format_info.get("bit_rate") or 0),
            "file_size": int(format_info.get("size") or video_path.stat().st_size),
            "audio_codec": audio_stream.get("codec_name", "unknown"),
            "audio_bitrate": int(audio_stream.get("bit_rate") or 0),
            "sample_rate": int(audio_stream.get("sample_rate") or 0),
            "channels": int(audio_stream.get("channels") or 0),
        }

    def check_video_requirements(self, video_path: Path) -> dict[str, Any]:
        info = self.get_video_info(video_path)
        max_duration = 180
        target_ratio = 9 / 16
        current_ratio = info["width"] / info["height"] if info["height"] else 0

        return {
            "duration_ok": info["duration"] <= max_duration,
            "aspect_ratio_ok": abs(current_ratio - target_ratio) < 0.1,
            "needs_processing": not (info["duration"] <= max_duration and abs(current_ratio - target_ratio) < 0.1),
            "current_ratio": current_ratio,
            "target_ratio": target_ratio,
            "duration": info["duration"],
            "max_duration": max_duration,
        }

    def check_instagram_requirements(self, video_path: Path) -> dict[str, Any]:
        try:
            info = self.get_video_info(video_path)
        except Exception as error:
            return {"compliant": False, "issues": [f"Error: {error}"]}

        issues = []
        if info["duration"] < 3:
            issues.append(f"Too short ({info['duration']:.1f}s < 3s)")
        if info["duration"] > 90:
            issues.append(f"Too long ({info['duration']:.1f}s > 90s)")
        if info["file_size"] > 100 * 1024 * 1024:
            issues.append(f"File too large ({info['file_size'] / (1024 * 1024):.1f}MB > 100MB)")
        if info["bitrate"] > 8 * 1024 * 1024:
            issues.append(f"Video bitrate too high ({info['bitrate'] / (1024 * 1024):.1f}Mbps > 8Mbps)")
        if info["width"] < 540 or info["height"] < 960:
            issues.append(f"Resolution too low ({info['width']}x{info['height']} < 540x960)")
        if info["fps"] < 24 or info["fps"] > 60:
            issues.append(f"Frame rate out of range ({info['fps']:.1f}fps not in 24-60fps)")
        if info["codec"] not in ["h264", "h265"]:
            issues.append(f"Unsupported video codec ({info['codec']}, need h264/h265)")
        if info["audio_codec"] != "aac":
            issues.append(f"Wrong audio codec ({info['audio_codec']} != aac)")
        if info["audio_bitrate"] > 0 and info["audio_bitrate"] < 192 * 1000:
            issues.append(f"Audio bitrate too low ({info['audio_bitrate'] / 1000:.0f}kbps < 192kbps)")
        if info["sample_rate"] > 0 and info["sample_rate"] != 48000:
            issues.append(f"Wrong sample rate ({info['sample_rate']}Hz != 48000Hz)")
        if info["channels"] > 0 and info["channels"] != 2:
            issues.append(f"Wrong audio channels ({info['channels']} != 2 stereo)")

        return {**info, "issues": issues, "compliant": len(issues) == 0}

    def is_ffmpeg_available(self) -> bool:
        try:
            subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True, check=True)
            subprocess.run(["ffprobe", "-version"], capture_output=True, text=True, check=True)
            return True
        except (FileNotFoundError, subprocess.CalledProcessError):
            return False

    def _is_supported_format(self, path: Path) -> bool:
        return path.suffix.lower() in self.supported_formats

    def _platform_profile(self, platform: str) -> dict[str, Any]:
        profiles = {
            "instagram": {
                "width": 1080,
                "height": 1920,
                "fps": 60,
                "video_bitrate": "8M",
                "buffer_size": "16M",
                "audio_bitrate": "192k",
                "crf": "23",
            },
            "youtube": {
                "width": 1080,
                "height": 1920,
                "fps": 60,
                "video_bitrate": "12M",
                "buffer_size": "24M",
                "audio_bitrate": "192k",
                "crf": "23",
            },
            "tiktok": {
                "width": 1080,
                "height": 1920,
                "fps": 60,
                "video_bitrate": "8M",
                "buffer_size": "16M",
                "audio_bitrate": "192k",
                "crf": "23",
            },
        }

        if platform not in profiles:
            raise ValueError(f"Unsupported platform: {platform}")

        return profiles[platform]

    def _parse_fps(self, value: Optional[str]) -> float:
        if not value or value == "0/0":
            return 0.0
        if "/" not in value:
            return float(value)

        numerator, denominator = value.split("/", 1)
        denominator_value = float(denominator)
        return float(numerator) / denominator_value if denominator_value else 0.0
