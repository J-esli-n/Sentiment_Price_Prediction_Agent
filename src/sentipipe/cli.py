from __future__ import annotations

import argparse
import logging
import sys

from sentipipe.config import load_config
from sentipipe.pipeline import run_pipeline


def main() -> int:
    parser = argparse.ArgumentParser(description="Run social/news sentiment price prediction")
    parser.add_argument("--config", default="config.yaml", help="Path to YAML configuration")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    try:
        config = load_config(args.config)
        paths, failures = run_pipeline(config)
    except Exception as exc:
        logging.error("%s", exc)
        return 1
    logging.info("Visual report: %s", paths[0])
    logging.info("CSV report: %s", paths[1])
    if failures:
        for failure in failures:
            logging.error("Asset failed: %s", failure)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
