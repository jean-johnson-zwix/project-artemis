"""
Layer 1 Detection Rate Benchmark
Measures what % of 3M sensor readings are flagged by Layer 1 (threshold + Z-score),
proving the cost-reduction argument: only flagged readings reach the LLM (Layer 2+3).
"""

import pandas as pd
import numpy as np
import time
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"

print("Loading data...")
t0 = time.time()

# Load sensor metadata (175 sensors)
meta = pd.read_csv(DATA_DIR / "sensor_metadata.csv")
meta_map = meta.set_index("sensor_id").to_dict("index")

# Load timeseries — 3M rows, chunked for memory efficiency
ts = pd.read_csv(
    DATA_DIR / "timeseries.csv",
    parse_dates=["timestamp"],
)
load_time = time.time() - t0
print(f"  Loaded {len(ts):,} readings in {load_time:.1f}s")

# ── LAYER 1A: THRESHOLD DETECTION ──────────────────────────────────────────
print("\nRunning threshold detection...")
t1 = time.time()

# Merge alarm/trip limits onto timeseries
ts_merged = ts.merge(
    meta[["sensor_id", "alarm_low", "alarm_high", "trip_low", "trip_high"]],
    on="sensor_id",
    how="left",
)

threshold_flag = (
    (ts_merged["trip_high"].notna() & (ts_merged["value"] > ts_merged["trip_high"]))
    | (ts_merged["trip_low"].notna() & (ts_merged["value"] < ts_merged["trip_low"]))
    | (ts_merged["alarm_high"].notna() & (ts_merged["value"] > ts_merged["alarm_high"]))
    | (ts_merged["alarm_low"].notna() & (ts_merged["value"] < ts_merged["alarm_low"]))
)

critical_flag = (
    (ts_merged["trip_high"].notna() & (ts_merged["value"] > ts_merged["trip_high"]))
    | (ts_merged["trip_low"].notna() & (ts_merged["value"] < ts_merged["trip_low"]))
)

thresh_time = time.time() - t1
n_threshold = threshold_flag.sum()
n_critical = critical_flag.sum()
print(f"  Threshold detections: {n_threshold:,} ({n_threshold/len(ts)*100:.2f}%)")
print(f"    of which CRITICAL: {n_critical:,} ({n_critical/len(ts)*100:.3f}%)")
print(f"  Completed in {thresh_time:.2f}s")

# ── LAYER 1B: STATISTICAL (Z-SCORE) DETECTION ──────────────────────────────
print("\nRunning Z-score detection (24h rolling window, |Z| > 3.0)...")
t2 = time.time()

# Only GOOD quality readings
good_mask = ts["quality_flag"] == "GOOD"
ts_good = ts[good_mask].copy()
ts_good = ts_good.sort_values(["sensor_id", "timestamp"])
ts_good = ts_good.set_index("timestamp")

# Rolling 24h Z-score per sensor
# For efficiency, use a vectorised rolling approach per sensor group
zscore_flags = []

for sensor_id, group in ts_good.groupby("sensor_id"):
    vals = group["value"]
    roll = vals.rolling("24h", min_periods=30)
    roll_mean = roll.mean()
    roll_std = roll.std()
    z = (vals - roll_mean) / roll_std.replace(0, np.nan)
    flagged = (z.abs() > 3.0) & z.notna()
    zscore_flags.append(flagged)

zscore_series = pd.concat(zscore_flags)
n_zscore = zscore_series.sum()
zscore_time = time.time() - t2
print(f"  Z-score detections: {n_zscore:,} ({n_zscore/len(ts)*100:.2f}%)")
print(f"  Completed in {zscore_time:.2f}s")

# ── COMBINED LAYER 1 ────────────────────────────────────────────────────────
# Map zscore flags back to original index (good readings only)
zscore_flag_full = pd.Series(False, index=ts.index)
zscore_flag_full.loc[ts_good.reset_index().index] = zscore_series.values

any_detection = threshold_flag | zscore_flag_full
n_detected = any_detection.sum()
n_total = len(ts)
n_filtered = n_total - n_detected
pct_detected = n_detected / n_total * 100
pct_filtered = n_filtered / n_total * 100

print("\n" + "=" * 60)
print("LAYER 1 SUMMARY")
print("=" * 60)
print(f"Total readings:         {n_total:>12,}")
print(f"Threshold detections:   {n_threshold:>12,}  ({n_threshold/n_total*100:.2f}%)")
print(f"Z-score detections:     {n_zscore:>12,}  ({n_zscore/n_total*100:.2f}%)")
print(f"Any L1 detection:       {n_detected:>12,}  ({pct_detected:.2f}%)")
print(f"Filtered (no alert):    {n_filtered:>12,}  ({pct_filtered:.1f}%)")
print()
print(f">> Layer 1 gates {pct_filtered:.1f}% of readings from the LLM pipeline.")
print(f">> Only {pct_detected:.2f}% of readings reach Azure OpenAI (Layer 2+3).")
print(f">> Estimated LLM cost reduction: ~{pct_filtered:.0f}%")

# ── DETECTION BREAKDOWN BY TYPE ─────────────────────────────────────────────
print("\nDetection breakdown by sensor type:")
ts_merged["flagged"] = threshold_flag.values
breakdown = ts_merged.groupby("sensor_type")["flagged"].agg(["sum", "count"])
breakdown["rate%"] = (breakdown["sum"] / breakdown["count"] * 100).round(2)
breakdown.columns = ["detections", "readings", "rate%"]
print(breakdown.to_string())

# ── UNIQUE ASSETS WITH DETECTIONS ───────────────────────────────────────────
n_assets_flagged = ts_merged[threshold_flag]["asset_id"].nunique()
n_assets_total = ts_merged["asset_id"].nunique()
print(f"\nAssets with at least 1 threshold breach: {n_assets_flagged} / {n_assets_total}")

print("\nTotal benchmark time: {:.1f}s".format(time.time() - t0))
