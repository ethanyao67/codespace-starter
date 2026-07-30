from pathlib import Path
import csv
import json
import math
import statistics
import zipfile
from collections import defaultdict

ROOT = Path(__file__).parent
ZIP_PATH = ROOT / "Elite Prospects Hockey Stats & Player Data.zip"
JSON_PATH = ROOT / "nhl_player_data.json"
HISTOGRAM_PATH = ROOT / "assets" / "histogram.svg"


def normalize_position(pos: str) -> str:
    value = (pos or "").strip().upper()
    if value in {"C", "LW", "RW", "W", "F", "L", "R", "LF", "RF"}:
        return "Forward"
    if value in {"D", "LD", "RD", "DD"}:
        return "Defense"
    if value in {"G", "GK", "GOALIE"}:
        return "Goalie"
    return "Other"


def build_svg(histogram: list[dict], title: str) -> str:
    width = 800
    height = 430
    margin = {"left": 70, "right": 30, "top": 40, "bottom": 70}
    chart_w = width - margin["left"] - margin["right"]
    chart_h = height - margin["top"] - margin["bottom"]
    max_count = max(item["count"] for item in histogram)
    bar_gap = 12
    bar_w = (chart_w - (len(histogram) - 1) * bar_gap) / len(histogram)

    bars = []
    for index, item in enumerate(histogram):
        value = item["count"]
        x = margin["left"] + index * (bar_w + bar_gap)
        h = (value / max_count) * chart_h if max_count else 0
        y = margin["top"] + chart_h - h
        bars.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{h:.1f}" rx="10" fill="#4fd1c5" opacity="0.95"/>'
        )
        bars.append(
            f'<text x="{x + bar_w / 2:.1f}" y="{height - 28}" text-anchor="middle" font-size="13" fill="#e6f7ff">{item["bin"]}</text>'
        )
        bars.append(
            f'<text x="{x + bar_w / 2:.1f}" y="{y - 8:.1f}" text-anchor="middle" font-size="12" fill="#f8fbff">{value}</text>'
        )

    axes = [
        f'<line x1="{margin["left"]}" y1="{margin["top"] + chart_h}" x2="{margin["left"]}" y2="{margin["top"]}" stroke="#e6f7ff" stroke-width="2"/>',
        f'<line x1="{margin["left"]}" y1="{margin["top"] + chart_h}" x2="{width - margin["right"]}" y2="{margin["top"] + chart_h}" stroke="#e6f7ff" stroke-width="2"/>',
        f'<text x="{width/2:.1f}" y="24" text-anchor="middle" font-size="24" font-weight="600" fill="#f8fbff">{title}</text>',
    ]

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="Histogram of NHL player heights">
  <rect width="{width}" height="{height}" rx="24" fill="#071b2f"/>
  {''.join(axes)}
  {''.join(bars)}
</svg>'''


def main() -> None:
    with zipfile.ZipFile(ZIP_PATH) as archive:
        dim_rows = csv.DictReader(archive.read("player_dim.csv").decode("latin-1").splitlines())
        stats_rows = csv.DictReader(archive.read("player_stats.csv").decode("latin-1").splitlines())

    players = {row["PLAYER_ID"]: row for row in dim_rows}
    for row in stats_rows:
        pid = row["PLAYER_ID"]
        if pid in players:
            players[pid].update(row)

    records = []
    for row in players.values():
        try:
            height = float(row.get("HEIGHT_CM", ""))
            if math.isfinite(height):
                records.append({
                    "height": height,
                    "position": normalize_position(row.get("PRIMARY_POS", "")),
                })
        except Exception:
            continue

    by_position = defaultdict(list)
    for record in records:
        by_position[record["position"]].append(record["height"])

    summary = []
    for position, values in sorted(by_position.items()):
        values = sorted(values)
        summary.append({
            "position": position,
            "count": len(values),
            "mean": round(statistics.mean(values), 1),
            "median": round(statistics.median(values), 1),
            "std": round(statistics.stdev(values), 1) if len(values) > 1 else 0.0,
        })

    bins = list(range(150, 211, 10))
    counts = [0] * (len(bins) - 1)
    for height in [record["height"] for record in records]:
        for idx in range(len(bins) - 1):
            if bins[idx] <= height < bins[idx + 1]:
                counts[idx] += 1
                break
        else:
            if height >= bins[-1]:
                counts[-1] += 1

    histogram = [{"bin": f"{bins[idx]}-{bins[idx + 1] - 1} cm", "count": counts[idx]} for idx in range(len(counts))]

    payload = {"summary": summary, "histogram": histogram, "records": records[:12]}
    JSON_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    HISTOGRAM_PATH.write_text(build_svg(histogram, "Distribution of NHL player heights"), encoding="utf-8")
    print(f"Wrote {JSON_PATH} and {HISTOGRAM_PATH}")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
