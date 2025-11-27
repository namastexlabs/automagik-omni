#!/usr/bin/env python3
"""Startup time benchmark for automagik-omni.

This script measures:
1. App import time (cold start)
2. Channel factory initialization time
3. Import time breakdown by module

Tech Council requirement (oettam): Measure startup performance.

Usage:
    python benchmarks/startup_time.py
    python benchmarks/startup_time.py --runs 10
"""
import argparse
import subprocess
import sys
import time
import statistics
from pathlib import Path


def measure_import_time(module: str, runs: int = 5) -> dict:
    """Measure time to import a module."""
    times = []
    
    for _ in range(runs):
        result = subprocess.run(
            [
                sys.executable, "-c",
                f"import time; start = time.perf_counter(); {module}; end = time.perf_counter(); print(f'{{(end-start)*1000:.3f}}')"
            ],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
        )
        if result.returncode == 0:
            try:
                times.append(float(result.stdout.strip()))
            except ValueError:
                pass
    
    if not times:
        return {"error": "Failed to measure"}
    
    return {
        "min_ms": min(times),
        "max_ms": max(times),
        "mean_ms": statistics.mean(times),
        "median_ms": statistics.median(times),
        "stdev_ms": statistics.stdev(times) if len(times) > 1 else 0,
    }


def measure_app_startup(runs: int = 5) -> dict:
    """Measure full app startup time."""
    times = []
    
    for _ in range(runs):
        start = time.perf_counter()
        result = subprocess.run(
            [
                sys.executable, "-c",
                "from src.api.app import app"
            ],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
        )
        end = time.perf_counter()
        
        if result.returncode == 0:
            times.append((end - start) * 1000)
    
    if not times:
        return {"error": "Failed to measure"}
    
    return {
        "min_ms": min(times),
        "max_ms": max(times),
        "mean_ms": statistics.mean(times),
        "median_ms": statistics.median(times),
        "stdev_ms": statistics.stdev(times) if len(times) > 1 else 0,
    }


def main():
    parser = argparse.ArgumentParser(description="Measure startup time")
    parser.add_argument("--runs", type=int, default=5, help="Number of runs per measurement")
    args = parser.parse_args()
    
    print(f"=" * 60)
    print(f"Startup Time Benchmark (runs={args.runs})")
    print(f"=" * 60)
    print()
    
    # Measure full app startup
    print("1. Full App Startup (from src.api.app import app)")
    print("-" * 40)
    result = measure_app_startup(args.runs)
    if "error" not in result:
        print(f"   Min:    {result['min_ms']:>8.1f} ms")
        print(f"   Max:    {result['max_ms']:>8.1f} ms")
        print(f"   Mean:   {result['mean_ms']:>8.1f} ms")
        print(f"   Median: {result['median_ms']:>8.1f} ms")
        print(f"   StdDev: {result['stdev_ms']:>8.1f} ms")
    else:
        print(f"   Error: {result['error']}")
    print()
    
    # Measure channel factory
    print("2. Channel Factory (from src.channels import ChannelHandlerFactory)")
    print("-" * 40)
    result = measure_import_time("from src.channels import ChannelHandlerFactory", args.runs)
    if "error" not in result:
        print(f"   Min:    {result['min_ms']:>8.1f} ms")
        print(f"   Max:    {result['max_ms']:>8.1f} ms")
        print(f"   Mean:   {result['mean_ms']:>8.1f} ms")
        print(f"   Median: {result['median_ms']:>8.1f} ms")
    else:
        print(f"   Error: {result['error']}")
    print()
    
    # Measure Discord module (should be fast when unavailable)
    print("3. Discord Module (from src.channels.discord import DISCORD_COMPONENTS_AVAILABLE)")
    print("-" * 40)
    result = measure_import_time("from src.channels.discord import DISCORD_COMPONENTS_AVAILABLE", args.runs)
    if "error" not in result:
        print(f"   Min:    {result['min_ms']:>8.1f} ms")
        print(f"   Max:    {result['max_ms']:>8.1f} ms")
        print(f"   Mean:   {result['mean_ms']:>8.1f} ms")
        print(f"   Median: {result['median_ms']:>8.1f} ms")
    else:
        print(f"   Error: {result['error']}")
    print()
    
    # Performance targets
    print("4. Performance Targets")
    print("-" * 40)
    print("   Target: Full app startup < 3000ms")
    print("   Target: Channel factory < 500ms")
    print("   Target: Discord guard overhead < 10ms")
    print()
    
    print(f"=" * 60)
    print("Benchmark complete")


if __name__ == "__main__":
    main()
