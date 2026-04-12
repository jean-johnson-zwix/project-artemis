"""
Pipeline orchestrator — runs Layer 1 → 2 → 3 for a given asset.

Called two ways:
  1. APScheduler tick (every 60 s) — scans all active assets
  2. Simulator endpoint (POST /simulate/event) — single asset, on demand

Flow for each asset:
  detections = detection.run_detection(asset_id)
  for each detection:
      context  = context.gather_context(detection)
      insight  = reasoning.run_reasoning(detection, context)
      # db writes and Teams notification happen inside reasoning.run_reasoning

TODO:
  - Wire APScheduler job to run() on startup (in main.py)
  - Handle partial failures per-asset without crashing the whole tick
  - Consider deduplication: skip if a Detection for same asset+type already
    exists within the last N minutes
"""

from __future__ import annotations


def run(asset_id: str) -> None:
    """
    Run the full detection pipeline for one asset.

    Calls Layer 1, then for each detection calls Layer 2 and Layer 3.
    Safe to call multiple times — Layer 1 is responsible for deduplication.
    """
    raise NotImplementedError


def run_all_assets() -> None:
    """
    Fetch all active assets from the DB and call run() for each.

    This is the function registered with APScheduler.
    """
    raise NotImplementedError
