#!/usr/bin/env python3
"""Plot response time vs time from a Locust stats-history CSV.

Usage examples:
  python3 plot_response_time.py t3-micro-1k-stats-history.csv
  python3 plot_response_time.py t3-micro-1k-stats-history.csv --name Aggregated --stat "Total Average Response Time" --out response_time.png
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Plot response time vs time from Locust CSV")
    p.add_argument("csv", help="Path to the stats-history CSV")
    p.add_argument("--name", default="Aggregated", help="Name field to filter (e.g. Aggregated or / or /product/xxxxx)")
    p.add_argument(
        "--stat",
        default="Response Time",
        help="Which column to plot (default: 'Total Average Response Time')",
    )
    p.add_argument("--out", default="response_time.png", help="Output image path")
    p.add_argument(
        "--datetime",
        action="store_true",
        help="Plot x-axis as absolute datetime instead of seconds since start",
    )
    p.add_argument("--show", action="store_true", help="Show the plot interactively")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    csv_path = Path(args.csv)
    if not csv_path.exists():
        print(f"CSV not found: {csv_path}", file=sys.stderr)
        return 2

    df = pd.read_csv(csv_path)

    # Ensure Timestamp present
    if "Timestamp" not in df.columns:
        print("CSV missing 'Timestamp' column", file=sys.stderr)
        return 2

    # Convert timestamp -> datetime
    try:
        df["Timestamp"] = pd.to_numeric(df["Timestamp"], errors="coerce")
        df = df.dropna(subset=["Timestamp"])  # remove bad rows
        df["ts"] = pd.to_datetime(df["Timestamp"], unit="s")
    except Exception as e:
        print("Failed to parse Timestamp column:", e, file=sys.stderr)
        return 2

    # Filter by Name
    name = args.name
    if name is None:
        df_name = df
    else:
        df_name = df[df["Name"] == name]

    if df_name.empty:
        available = sorted(df["Name"].dropna().unique())
        print(f"No rows found for Name={name}. Available sample names (first 20):", file=sys.stderr)
        for n in available[:20]:
            print(f"  {n}", file=sys.stderr)
        return 3

    stat_col = args.stat
    # If requested stat exists, prepare y; otherwise skip plotting the main stat
    if stat_col in df_name.columns:
        y = pd.to_numeric(df_name[stat_col], errors="coerce")
    else:
        y = None

    # Prepare x-axis: by default use seconds since start; --datetime will use absolute times
    if args.datetime:
        x = df_name["ts"]
        xlabel = "Time"
    else:
        start = float(df_name["Timestamp"].iloc[0])
        x = df_name["Timestamp"].astype(float) - start
        xlabel = "Time (s)"

    # Sort by time just in case
    order = x.argsort()
    x = x.iloc[order]
    if y is not None:
        y = y.iloc[order]

    # Create three subplots: top for response-time traces, middle for user count, bottom for reqs/failures
    fig, (ax1, ax2, ax3) = plt.subplots(
        3,
        1,
        figsize=(12, 10),
        sharex=True,
        gridspec_kw={"height_ratios": [3, 1, 1]},
    )

    color_rt = "tab:blue"
    # Top subplot: response time traces (percentiles + optional main stat)
    if y is not None and stat_col != "Total Average Response Time":
        ax1.plot(x, y, marker="o", linestyle="-", linewidth=1, color=color_rt, label=stat_col)
        ax1.set_ylabel(stat_col, color=color_rt)
    else:
        # user asked to remove/comment the Total Average Response Time trace
        ax1.set_ylabel("Response Time (ms)", color=color_rt)

    ax1.tick_params(axis="y", labelcolor=color_rt)
    ax1.grid(True, alpha=0.4)

    # Plot percentiles if present (50%, 95%, 99%) on top subplot
    pct_cols = ["50%", "95%", "99%"]
    pct_colors = {"50%": "tab:green", "95%": "tab:red", "99%": "tab:purple"}
    for pct in pct_cols:
        if pct in df_name.columns:
            pct_series = pd.to_numeric(df_name[pct], errors="coerce")
            pct_series = pct_series.iloc[order]
            ax1.plot(x, pct_series, linestyle="--", linewidth=1, color=pct_colors.get(pct, None), label=pct)

    # Prepare users series for middle subplot and compute peak
    users = None
    peak_idx = None
    peak_user_count = None
    if "User Count" in df_name.columns:
        users_raw = pd.to_numeric(df_name["User Count"], errors="coerce")
        try:
            peak_idx = users_raw.idxmax()
            peak_user_count = int(users_raw.loc[peak_idx])
        except Exception:
            peak_idx = None
            peak_user_count = None

        users = users_raw.iloc[order]
        # plot User Count on the bottom subplot (ax3)
        ax3.plot(x, users, marker="x", linestyle="--", color="tab:orange", label="User Count")
        ax3.set_ylabel("User Count")
        ax3.grid(False)
    else:
        ax2.text(0.5, 0.5, "No User Count column", ha="center", va="center", transform=ax2.transAxes)

    # Add vertical line at peak user count (annotate on top subplot)
    if users is not None and peak_idx is not None:
        try:
            peak_row = df_name.loc[peak_idx]
            if args.datetime:
                x_peak = peak_row["ts"]
            else:
                start = float(df_name["Timestamp"].iloc[0])
                x_peak = float(peak_row["Timestamp"]) - start
            ax1.axvline(x=x_peak, color="gray", linestyle=":", linewidth=1)
            # annotate on top subplot near top
            if y is not None:
                ymax = y.max(skipna=True) if hasattr(y, "max") else 1
            else:
                # if no main stat, derive reasonable ymax from percentiles
                ymax = None
                for pct in pct_cols:
                    if pct in df_name.columns:
                        candidate = pd.to_numeric(df_name[pct], errors="coerce").max()
                        if pd.notna(candidate):
                            ymax = candidate if ymax is None else max(ymax, candidate)
                if ymax is None:
                    ymax = 1
            ax1.annotate(f"peak users: {peak_user_count}", xy=(x_peak, ymax), xytext=(5, 5), textcoords="offset points", color="gray")
            # also mark on middle subplot (requests/failures)
            ax2.axvline(x=x_peak, color="gray", linestyle=":", linewidth=1)
            # mark and annotate on bottom subplot (user count)
            ax3.axvline(x=x_peak, color="gray", linestyle=":", linewidth=1)
            ax3.scatter([x_peak], [peak_user_count], color="gray")
        except Exception:
            pass

    # Add horizontal line at 200 ms on top subplot
    try:
        ax1.axhline(y=200, color="gray", linestyle="-.", linewidth=1)
        ax1.annotate("200 ms", xy=(0, 200), xytext=(5, 5), textcoords="offset points", color="gray")
    except Exception:
        pass

    # Legends
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    # Middle subplot: Requests/s and Failures/s
    reqs_lines = []
    reqs_labels = []
    if "Requests/s" in df_name.columns:
        reqs = pd.to_numeric(df_name["Requests/s"], errors="coerce")
        reqs = reqs.iloc[order]
        l_req, = ax2.plot(x, reqs, color="tab:blue", label="Requests/s")
        reqs_lines.append(l_req)
        reqs_labels.append("Requests/s")
        ax2.set_ylabel("Requests/s")
    else:
        ax2.text(0.5, 0.5, "No Requests/s column", ha="center", va="center", transform=ax2.transAxes)

    ax2_twin = None
    if "Failures/s" in df_name.columns:
        fails = pd.to_numeric(df_name["Failures/s"], errors="coerce")
        fails = fails.iloc[order]
        ax2_twin = ax2.twinx()
        l_fail, = ax2_twin.plot(x, fails, color="tab:red", linestyle="--", label="Failures/s")
        reqs_lines.append(l_fail)
        reqs_labels.append("Failures/s")
        ax2_twin.set_ylabel("Failures/s", color="tab:red")
        ax2_twin.tick_params(axis="y", labelcolor="tab:red")

    # Combined legend from all axes
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    lines3, labels3 = ax3.get_legend_handles_labels()
    all_lines = lines1 + lines2 + lines3
    all_labels = labels1 + labels2 + labels3
    if all_lines:
        ax1.legend(all_lines, all_labels, loc="upper left")

    ax3.set_xlabel(xlabel)
    plt.suptitle(f"{stat_col} and User Count over time (Name={name})")
    plt.tight_layout(rect=[0, 0.03, 1, 0.97])

    out_path = Path(args.out)
    plt.savefig(out_path, dpi=150)
    print(f"Saved plot to {out_path}")

    if args.show:
        plt.show()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
