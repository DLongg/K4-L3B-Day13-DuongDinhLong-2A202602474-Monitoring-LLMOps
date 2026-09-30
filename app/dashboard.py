from __future__ import annotations

import json
import os
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

from .metrics import percentile

LOG_PATH = Path(os.getenv("LOG_PATH", "data/logs.jsonl"))


def calculate_dashboard_data(minutes: int = 60) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(minutes=minutes)

    records: list[dict[str, Any]] = []
    if LOG_PATH.exists():
        for line in LOG_PATH.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
                records.append(rec)
            except Exception:
                continue

    # Filter within time window if timestamps valid, else fallback to all
    window_records = []
    for r in records:
        ts_str = r.get("ts")
        if ts_str:
            try:
                dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                if dt >= cutoff:
                    window_records.append((dt, r))
                continue
            except Exception:
                pass
        window_records.append((now, r))

    # Panel 1: Latency (P50, P95, P99, TTFT P95)
    latencies = [r["latency_ms"] for _, r in window_records if r.get("event") == "response_sent" and "latency_ms" in r]
    ttfts = [r["ttft_ms"] for _, r in window_records if r.get("event") == "response_sent" and "ttft_ms" in r]

    p50 = percentile(latencies, 50) if latencies else 0
    p95 = percentile(latencies, 95) if latencies else 0
    p99 = percentile(latencies, 99) if latencies else 0
    ttft_p95 = percentile(ttfts, 95) if ttfts else 0

    # Panel 2: Traffic (Requests by minute)
    traffic_by_min: dict[str, int] = defaultdict(int)
    for dt, r in window_records:
        if r.get("event") == "request_received":
            m_str = dt.strftime("%H:%M")
            traffic_by_min[m_str] += 1
    total_requests = sum(1 for _, r in window_records if r.get("event") == "request_received")
    active_minutes = max(1, len(traffic_by_min))
    req_per_min = round(total_requests / active_minutes, 2)

    # Panel 3: Errors & Retrieval Success
    failed_requests = sum(1 for _, r in window_records if r.get("event") == "request_failed")
    error_rate_pct = round((failed_requests / total_requests * 100), 2) if total_requests > 0 else 0.0

    tool_successes = sum(1 for _, r in window_records if r.get("tool_success") is True)
    tool_events = sum(1 for _, r in window_records if r.get("tool_success") is not None)
    retrieval_success_pct = round((tool_successes / tool_events * 100), 1) if tool_events > 0 else 100.0

    # Panel 4: Cost
    costs = [r["cost_usd"] for _, r in window_records if r.get("event") == "response_sent" and "cost_usd" in r]
    total_cost_usd = round(sum(costs), 6)

    # Panel 5: Tokens
    tokens_in = sum(r["tokens_in"] for _, r in window_records if r.get("event") == "response_sent" and "tokens_in" in r)
    tokens_out = sum(r["tokens_out"] for _, r in window_records if r.get("event") == "response_sent" and "tokens_out" in r)

    # Panel 6: Quality
    quality_scores = [r["quality_score"] for _, r in window_records if r.get("event") == "response_sent" and "quality_score" in r]
    avg_quality = round(sum(quality_scores) / len(quality_scores), 2) if quality_scores else 0.85

    return {
        "time_range_minutes": minutes,
        "refresh_seconds": 30,
        "latency": {"p50": p50, "p95": p95, "p99": p99, "ttft_p95": ttft_p95, "threshold": 3000, "unit": "ms"},
        "traffic": {"total": total_requests, "rate_per_min": req_per_min, "by_min": dict(sorted(traffic_by_min.items())), "threshold": 1.0, "unit": "req/min"},
        "errors": {"failed": failed_requests, "error_rate_pct": error_rate_pct, "retrieval_success_pct": retrieval_success_pct, "threshold": 2.0, "unit": "%"},
        "cost": {"total_usd": total_cost_usd, "threshold": 2.5, "unit": "USD"},
        "tokens": {"tokens_in": tokens_in, "tokens_out": tokens_out, "total": tokens_in + tokens_out, "threshold": 50000, "unit": "tokens"},
        "quality": {"avg_score": avg_quality, "threshold": 0.75, "unit": "score (0-1)"},
    }


def render_dashboard_html() -> str:
    data = calculate_dashboard_data(minutes=60)
    data_json = json.dumps(data)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta http-equiv="refresh" content="30">
  <title>K4-L3B Day 13 Monitoring & LLMOps Dashboard</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <style>
    :root {{
      --bg: #0b0f19;
      --card-bg: rgba(22, 30, 49, 0.85);
      --card-border: rgba(255, 255, 255, 0.08);
      --text: #f1f5f9;
      --text-muted: #94a3b8;
      --primary: #38bdf8;
      --success: #10b981;
      --warning: #f59e0b;
      --danger: #ef4444;
      --purple: #a855f7;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: 'Inter', sans-serif;
      background: var(--bg);
      color: var(--text);
      padding: 24px;
      min-height: 100vh;
    }}
    .header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 24px;
      border-bottom: 1px solid var(--card-border);
      padding-bottom: 16px;
    }}
    .header h1 {{
      font-size: 24px;
      font-weight: 700;
      background: linear-gradient(135deg, #38bdf8, #818cf8);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
    }}
    .header-badges {{
      display: flex;
      gap: 12px;
      align-items: center;
    }}
    .badge {{
      background: rgba(56, 189, 248, 0.12);
      color: #38bdf8;
      border: 1px solid rgba(56, 189, 248, 0.25);
      padding: 6px 12px;
      border-radius: 9999px;
      font-size: 13px;
      font-weight: 500;
    }}
    .badge-green {{
      background: rgba(16, 185, 129, 0.12);
      color: #10b981;
      border-color: rgba(16, 185, 129, 0.25);
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 20px;
    }}
    @media (max-width: 1024px) {{
      .grid {{ grid-template-columns: repeat(2, 1fr); }}
    }}
    @media (max-width: 640px) {{
      .grid {{ grid-template-columns: 1fr; }}
    }}
    .panel {{
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 12px;
      padding: 20px;
      backdrop-filter: blur(8px);
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      box-shadow: 0 4px 20px rgba(0, 0, 0, 0.25);
    }}
    .panel-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 16px;
    }}
    .panel-title {{
      font-size: 15px;
      font-weight: 600;
      color: var(--text);
    }}
    .panel-id {{
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: var(--text-muted);
      background: rgba(255, 255, 255, 0.05);
      padding: 3px 8px;
      border-radius: 4px;
    }}
    .metrics-row {{
      display: flex;
      gap: 16px;
      margin-bottom: 14px;
    }}
    .metric-box {{
      flex: 1;
    }}
    .metric-label {{
      font-size: 12px;
      color: var(--text-muted);
      margin-bottom: 4px;
    }}
    .metric-value {{
      font-size: 24px;
      font-weight: 700;
      color: var(--text);
    }}
    .threshold-badge {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      font-size: 12px;
      padding: 4px 10px;
      border-radius: 6px;
      background: rgba(255, 255, 255, 0.04);
      border: 1px solid var(--card-border);
      color: var(--text-muted);
      margin-top: 8px;
    }}
    .threshold-dot {{
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: var(--success);
    }}
    .chart-container {{
      height: 140px;
      position: relative;
      margin-top: 10px;
    }}
  </style>
</head>
<body>
  <div class="header">
    <div>
      <h1>K4-L3B Day 13 — Monitoring &amp; LLMOps Dashboard</h1>
      <p style="color: var(--text-muted); font-size: 13px; margin-top: 4px;">Source: <code>data/logs.jsonl</code> &bull; Student: Dương Đình Long (2A202602474)</p>
    </div>
    <div class="header-badges">
      <span class="badge">Range: 60m</span>
      <span class="badge">Auto-refresh: 30s</span>
      <span class="badge badge-green">&#9679; SLO: 99.5%</span>
    </div>
  </div>

  <div class="grid">
    <!-- Panel 1: Latency -->
    <div class="panel" id="panel-latency">
      <div class="panel-header">
        <span class="panel-title">1. Latency percentiles and TTFT</span>
        <span class="panel-id">latency</span>
      </div>
      <div class="metrics-row">
        <div class="metric-box">
          <div class="metric-label">P50</div>
          <div class="metric-value">{data['latency']['p50']} <span style="font-size: 13px; font-weight: normal; color: var(--text-muted);">ms</span></div>
        </div>
        <div class="metric-box">
          <div class="metric-label">P95</div>
          <div class="metric-value" style="color: #38bdf8;">{data['latency']['p95']} <span style="font-size: 13px; font-weight: normal; color: var(--text-muted);">ms</span></div>
        </div>
        <div class="metric-box">
          <div class="metric-label">P99</div>
          <div class="metric-value">{data['latency']['p99']} <span style="font-size: 13px; font-weight: normal; color: var(--text-muted);">ms</span></div>
        </div>
        <div class="metric-box">
          <div class="metric-label">TTFT P95</div>
          <div class="metric-value" style="color: #a855f7;">{data['latency']['ttft_p95']} <span style="font-size: 13px; font-weight: normal; color: var(--text-muted);">ms</span></div>
        </div>
      </div>
      <div class="chart-container"><canvas id="latencyChart"></canvas></div>
      <div class="threshold-badge">
        <span class="threshold-dot"></span> Threshold: P95 &le; 3000 ms (SLO Guardrail)
      </div>
    </div>

    <!-- Panel 2: Traffic -->
    <div class="panel" id="panel-traffic">
      <div class="panel-header">
        <span class="panel-title">2. Request traffic</span>
        <span class="panel-id">traffic</span>
      </div>
      <div class="metrics-row">
        <div class="metric-box">
          <div class="metric-label">Total Requests</div>
          <div class="metric-value">{data['traffic']['total']}</div>
        </div>
        <div class="metric-box">
          <div class="metric-label">Rate / Minute</div>
          <div class="metric-value" style="color: #38bdf8;">{data['traffic']['rate_per_min']} <span style="font-size: 13px; font-weight: normal; color: var(--text-muted);">req/min</span></div>
        </div>
      </div>
      <div class="chart-container"><canvas id="trafficChart"></canvas></div>
      <div class="threshold-badge">
        <span class="threshold-dot"></span> Threshold: Rate &ge; 1.0 req/min
      </div>
    </div>

    <!-- Panel 3: Errors -->
    <div class="panel" id="panel-errors">
      <div class="panel-header">
        <span class="panel-title">3. Error rate and retrieval success</span>
        <span class="panel-id">errors</span>
      </div>
      <div class="metrics-row">
        <div class="metric-box">
          <div class="metric-label">Error Rate</div>
          <div class="metric-value" style="color: {'#10b981' if data['errors']['error_rate_pct'] <= 2.0 else '#ef4444'};">{data['errors']['error_rate_pct']}%</div>
        </div>
        <div class="metric-box">
          <div class="metric-label">Retrieval Success</div>
          <div class="metric-value" style="color: #10b981;">{data['errors']['retrieval_success_pct']}%</div>
        </div>
      </div>
      <div class="chart-container"><canvas id="errorChart"></canvas></div>
      <div class="threshold-badge">
        <span class="threshold-dot"></span> Threshold: Error Rate &le; 2.0% &bull; Retrieval &ge; 90%
      </div>
    </div>

    <!-- Panel 4: Cost -->
    <div class="panel" id="panel-cost">
      <div class="panel-header">
        <span class="panel-title">4. Cost over time</span>
        <span class="panel-id">cost</span>
      </div>
      <div class="metrics-row">
        <div class="metric-box">
          <div class="metric-label">Total Cost</div>
          <div class="metric-value" style="color: #f59e0b;">${data['cost']['total_usd']:.5f}</div>
        </div>
        <div class="metric-box">
          <div class="metric-label">Daily Budget Guardrail</div>
          <div class="metric-value">$2.50000</div>
        </div>
      </div>
      <div class="chart-container"><canvas id="costChart"></canvas></div>
      <div class="threshold-badge">
        <span class="threshold-dot"></span> Threshold: Total &le; $2.5 USD
      </div>
    </div>

    <!-- Panel 5: Tokens -->
    <div class="panel" id="panel-tokens">
      <div class="panel-header">
        <span class="panel-title">5. Input and output tokens</span>
        <span class="panel-id">tokens</span>
      </div>
      <div class="metrics-row">
        <div class="metric-box">
          <div class="metric-label">Tokens In</div>
          <div class="metric-value">{data['tokens']['tokens_in']:,}</div>
        </div>
        <div class="metric-box">
          <div class="metric-label">Tokens Out</div>
          <div class="metric-value">{data['tokens']['tokens_out']:,}</div>
        </div>
        <div class="metric-box">
          <div class="metric-label">Total</div>
          <div class="metric-value" style="color: #38bdf8;">{data['tokens']['total']:,}</div>
        </div>
      </div>
      <div class="chart-container"><canvas id="tokenChart"></canvas></div>
      <div class="threshold-badge">
        <span class="threshold-dot"></span> Threshold: Total Tokens &le; 50,000
      </div>
    </div>

    <!-- Panel 6: Quality -->
    <div class="panel" id="panel-quality">
      <div class="panel-header">
        <span class="panel-title">6. Quality proxy</span>
        <span class="panel-id">quality</span>
      </div>
      <div class="metrics-row">
        <div class="metric-box">
          <div class="metric-label">Average Score</div>
          <div class="metric-value" style="color: #10b981;">{data['quality']['avg_score']} <span style="font-size: 13px; font-weight: normal; color: var(--text-muted);">/ 1.0</span></div>
        </div>
        <div class="metric-box">
          <div class="metric-label">Target Minimum</div>
          <div class="metric-value">0.75</div>
        </div>
      </div>
      <div class="chart-container"><canvas id="qualityChart"></canvas></div>
      <div class="threshold-badge">
        <span class="threshold-dot"></span> Threshold: Mean &ge; 0.75
      </div>
    </div>
  </div>

  <script>
    const data = {data_json};

    // Chart 1: Latency
    new Chart(document.getElementById('latencyChart'), {{
      type: 'bar',
      data: {{
        labels: ['P50', 'P95', 'P99', 'TTFT P95', 'Threshold'],
        datasets: [{{
          data: [data.latency.p50, data.latency.p95, data.latency.p99, data.latency.ttft_p95, 3000],
          backgroundColor: ['#64748b', '#38bdf8', '#818cf8', '#a855f7', 'rgba(239, 68, 68, 0.4)'],
          borderRadius: 4
        }}]
      }},
      options: {{
        responsive: true,
        maintainAspectRatio: false,
        plugins: {{ legend: {{ display: false }} }},
        scales: {{
          y: {{ grid: {{ color: 'rgba(255,255,255,0.05)' }}, ticks: {{ color: '#94a3b8' }} }},
          x: {{ grid: {{ display: false }}, ticks: {{ color: '#94a3b8' }} }}
        }}
      }}
    }});

    // Chart 2: Traffic
    const trafficLabels = Object.keys(data.traffic.by_min).length ? Object.keys(data.traffic.by_min) : ['Now'];
    const trafficValues = Object.values(data.traffic.by_min).length ? Object.values(data.traffic.by_min) : [data.traffic.total];
    new Chart(document.getElementById('trafficChart'), {{
      type: 'line',
      data: {{
        labels: trafficLabels,
        datasets: [{{
          label: 'Requests',
          data: trafficValues,
          borderColor: '#38bdf8',
          backgroundColor: 'rgba(56, 189, 248, 0.1)',
          fill: true,
          tension: 0.3
        }}]
      }},
      options: {{
        responsive: true,
        maintainAspectRatio: false,
        plugins: {{ legend: {{ display: false }} }},
        scales: {{
          y: {{ beginAtZero: true, grid: {{ color: 'rgba(255,255,255,0.05)' }}, ticks: {{ color: '#94a3b8' }} }},
          x: {{ grid: {{ display: false }}, ticks: {{ color: '#94a3b8' }} }}
        }}
      }}
    }});

    // Chart 3: Errors
    new Chart(document.getElementById('errorChart'), {{
      type: 'doughnut',
      data: {{
        labels: ['Success', 'Errors'],
        datasets: [{{
          data: [Math.max(1, 100 - data.errors.error_rate_pct), data.errors.error_rate_pct],
          backgroundColor: ['#10b981', '#ef4444'],
          borderWidth: 0
        }}]
      }},
      options: {{
        responsive: true,
        maintainAspectRatio: false,
        plugins: {{ legend: {{ position: 'bottom', labels: {{ color: '#94a3b8' }} }} }}
      }}
    }});

    // Chart 4: Cost
    new Chart(document.getElementById('costChart'), {{
      type: 'bar',
      data: {{
        labels: ['Current Cost', 'Budget Limit ($2.5)'],
        datasets: [{{
          data: [data.cost.total_usd, 2.5],
          backgroundColor: ['#f59e0b', 'rgba(255, 255, 255, 0.1)'],
          borderRadius: 4
        }}]
      }},
      options: {{
        responsive: true,
        maintainAspectRatio: false,
        plugins: {{ legend: {{ display: false }} }},
        scales: {{
          y: {{ beginAtZero: true, grid: {{ color: 'rgba(255,255,255,0.05)' }}, ticks: {{ color: '#94a3b8' }} }},
          x: {{ grid: {{ display: false }}, ticks: {{ color: '#94a3b8' }} }}
        }}
      }}
    }});

    // Chart 5: Tokens
    new Chart(document.getElementById('tokenChart'), {{
      type: 'bar',
      data: {{
        labels: ['Tokens In', 'Tokens Out'],
        datasets: [{{
          data: [data.tokens.tokens_in, data.tokens.tokens_out],
          backgroundColor: ['#38bdf8', '#818cf8'],
          borderRadius: 4
        }}]
      }},
      options: {{
        responsive: true,
        maintainAspectRatio: false,
        plugins: {{ legend: {{ display: false }} }},
        scales: {{
          y: {{ beginAtZero: true, grid: {{ color: 'rgba(255,255,255,0.05)' }}, ticks: {{ color: '#94a3b8' }} }},
          x: {{ grid: {{ display: false }}, ticks: {{ color: '#94a3b8' }} }}
        }}
      }}
    }});

    // Chart 6: Quality
    new Chart(document.getElementById('qualityChart'), {{
      type: 'bar',
      data: {{
        labels: ['Current Avg', 'Target Threshold'],
        datasets: [{{
          data: [data.quality.avg_score, 0.75],
          backgroundColor: ['#10b981', 'rgba(255, 255, 255, 0.2)'],
          borderRadius: 4
        }}]
      }},
      options: {{
        responsive: true,
        maintainAspectRatio: false,
        plugins: {{ legend: {{ display: false }} }},
        scales: {{
          y: {{ min: 0, max: 1, grid: {{ color: 'rgba(255,255,255,0.05)' }}, ticks: {{ color: '#94a3b8' }} }},
          x: {{ grid: {{ display: false }}, ticks: {{ color: '#94a3b8' }} }}
        }}
      }}
    }});
  </script>
</body>
</html>
"""
