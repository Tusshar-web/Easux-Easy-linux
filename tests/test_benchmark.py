"""
Performance and latency benchmark tests.
Validates the PRD targets:
- Local completion p95 < 80ms, p99 < 150ms
- Smart suggestions p95 < 250ms
- Project scan < 100ms
"""

import time
from pathlib import Path
from ai_terminal.completion.engine import CompletionEngine
from ai_terminal.completion.suggester import ContextSuggester
from ai_terminal.context.detector import ProjectDetector


def test_local_completion_latency_p95(temp_repo, temp_dir):
    # Setup test workspace
    (temp_dir / "package.json").write_text('{"scripts": {"dev": "vite", "test": "vitest"}}')
    (temp_dir / "Makefile").write_text("build:\n\techo\n")

    engine = CompletionEngine(temp_repo)

    latencies_ms = []
    # Warm up
    engine.complete("git che", cursor=7, cwd=temp_dir)

    # Run 100 iterations
    for _ in range(100):
        t0 = time.perf_counter()
        engine.complete("git che", cursor=7, cwd=temp_dir)
        dt = (time.perf_counter() - t0) * 1000.0
        latencies_ms.append(dt)

    latencies_ms.sort()
    p95 = latencies_ms[int(len(latencies_ms) * 0.95)]
    p99 = latencies_ms[int(len(latencies_ms) * 0.99)]

    print(f"\nLocal completion latencies: p95={p95:.2f}ms, p99={p99:.2f}ms")
    assert p95 < 80.0, f"p95 latency {p95}ms exceeded 80ms target"
    assert p99 < 150.0, f"p99 latency {p99}ms exceeded 150ms target"


def test_smart_suggestions_latency_p95(temp_repo, temp_dir):
    (temp_dir / "package.json").write_text('{"scripts": {"dev": "vite", "test": "vitest"}}')
    suggester = ContextSuggester(temp_repo)

    latencies_ms = []
    for _ in range(30):
        t0 = time.perf_counter()
        suggester.suggest(cwd=temp_dir)
        dt = (time.perf_counter() - t0) * 1000.0
        latencies_ms.append(dt)

    latencies_ms.sort()
    p95 = latencies_ms[int(len(latencies_ms) * 0.95)]
    print(f"\nSmart suggestions latencies: p95={p95:.2f}ms")
    assert p95 < 250.0, f"p95 suggestions latency {p95}ms exceeded 250ms target"


def test_project_scan_latency(temp_repo, temp_dir):
    (temp_dir / "package.json").write_text('{"scripts": {"dev": "vite"}}')
    detector = ProjectDetector(temp_repo)

    t0 = time.perf_counter()
    ctx = detector.detect(temp_dir)
    dt = (time.perf_counter() - t0) * 1000.0

    print(f"\nProject scan latency: {dt:.2f}ms")
    assert dt < 100.0, f"Project scan latency {dt}ms exceeded 100ms target"
