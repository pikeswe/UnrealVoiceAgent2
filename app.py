"""Entry point for launching the Nova control panel."""
from __future__ import annotations

import argparse
from pathlib import Path

from Interface.control_panel import launch_gui


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Local Unreal AI Companion")
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config/default_config.json"),
        help="Path to the orchestrator configuration JSON file.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    launch_gui(args.config)


if __name__ == "__main__":
    main()
