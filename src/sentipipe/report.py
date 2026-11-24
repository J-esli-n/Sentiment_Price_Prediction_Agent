from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd


def write_report(rows: list[dict[str, Any]], output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    frame = pd.DataFrame(rows)
    if not frame.empty:
        frame = frame.sort_values(
            ["exchange", "social_mentions", "social_sentiment"],
            ascending=[True, False, False],
        )
    csv_path = output_dir / "predictions.csv"
    html_path = output_dir / "report.html"
    json_path = output_dir / "predictions.json"
    frame.to_csv(csv_path, index=False)
    json_path.write_text(json.dumps(rows, indent=2, default=str), encoding="utf-8")
    table = frame.to_html(index=False, classes="data", border=0, na_rep="—", float_format=lambda x: f"{x:,.4f}")
    html_path.write_text(_html(table, frame), encoding="utf-8")
    return html_path, csv_path


def _html(table: str, frame: pd.DataFrame) -> str:
    if frame.empty:
        chart = "No predictions available."
    else:
        grouped = frame.groupby("exchange", sort=True)
        sections = []
        for exchange, rows in grouped:
            ordered = rows.sort_values("social_mentions", ascending=True)
            labels = json.dumps(ordered["ticker"].tolist())
            mentions = json.dumps(ordered["social_mentions"].fillna(0).tolist())
            sentiments = json.dumps(ordered["social_sentiment"].fillna(0).tolist())
            sections.append(
                f"<section><h2>{exchange}</h2><canvas id='chart-{exchange}'></canvas>"
                f"<script>new Chart(document.getElementById('chart-{exchange}'),{{type:'bar',"
                f"data:{{labels:{labels},datasets:[{{label:'Social mentions',data:{mentions},"
                f"backgroundColor:'#3984f5',yAxisID:'y'}},{{label:'Social sentiment',data:{sentiments},"
                "backgroundColor:'#f5a623',yAxisID:'y1'}]}},options:{scales:{y:{beginAtZero:true,"
                "title:{display:true,text:'Mentions'}},y1:{position:'right',min:-1,max:1,"
                "title:{display:true,text:'Sentiment'}}}}}});</script></section>"
            )
        chart = "".join(sections)
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>Asset sentiment and next-bar predictions</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
body{{font:15px system-ui,sans-serif;margin:2rem auto;max-width:1280px;padding:0 1rem;color:#172033}}
h1{{color:#16345a}} section{{margin:2rem 0}} canvas{{max-height:300px}}
.data{{border-collapse:collapse;width:100%;font-size:13px}} .data th,.data td{{padding:.6rem;
border-bottom:1px solid #dce3ed;text-align:left}} .data th{{background:#edf3fa;position:sticky;top:0}}
.data tr:hover{{background:#f6f9fc}}
</style></head><body><h1>Social &amp; news sentiment — next-bar forecast</h1>
<p>Sorted by exchange, then social mentions and sentiment. Predictions are estimates, not financial advice.
Metrics are from expanding-window, time-ordered out-of-sample validation.</p>{chart}<h2>Asset ranking and validation</h2>{table}
</body></html>"""
