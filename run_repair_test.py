#!/usr/bin/env python3
"""
STL Repair Engine Comparison Test

Orchestrates repair testing for both engines (local/pymeshfix and windows/RepairAsync),
collects metrics using trimesh, and generates a markdown comparison report.
"""

import os
import sys
import subprocess
import shutil
import tempfile
import time
from pathlib import Path
from datetime import datetime
import platform

try:
    import trimesh
except ImportError:
    print("Error: trimesh is not installed. Install with: pip install trimesh")
    sys.exit(1)


def get_repair_command():
    """Get the command to run repair-stl.sh based on platform."""
    if platform.system() == "Windows":
        # On Windows, use Git Bash explicitly (not WSL bash)
        git_bash = r"C:\Program Files\Git\usr\bin\bash.exe"

        # Check using Windows path format, convert to Git Bash format for execution
        script_path_win = Path.home() / "Desktop" / "STLRepairTool" / "repair-stl.sh"

        if script_path_win.exists():
            # Convert Windows path to Git Bash path: C:\Users\... -> /c/Users/...
            script_path_bash = "/" + str(script_path_win).replace("\\", "/").replace(":", "")
            # Convert drive letter to lowercase
            parts = script_path_bash.split("/")
            if len(parts) > 1 and len(parts[1]) == 1 and parts[1].isalpha():
                parts[1] = parts[1].lower()
                script_path_bash = "/".join(parts)
            return [git_bash, script_path_bash]
        else:
            # Last resort: assume it's in PATH
            return [git_bash, "repair-stl.sh"]
    else:
        return ["repair-stl.sh"]


def validate_prerequisites():
    """Validate that repair-stl.sh is available and test files exist."""

    # Check repair-stl.sh is on PATH
    cmd = get_repair_command() + ["--help"]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        print("Error: repair-stl.sh not found on PATH")
        print(f"Command: {cmd}")
        print(f"Stderr: {result.stderr}")
        sys.exit(1)

    # Check test files exist
    test_file = "tests/non-manifold-test.stl"

    if not Path(test_file).exists():
        print(f"Error: Test file not found: {test_file}")
        sys.exit(1)

    print("[OK] Prerequisites validated")


def collect_metrics(stl_path):
    """Collect mesh metrics from an STL file using trimesh."""

    if not Path(stl_path).exists():
        return None

    try:
        mesh = trimesh.load(stl_path)

        return {
            "file_size": os.path.getsize(stl_path),
            "face_count": len(mesh.faces),
            "vertex_count": len(mesh.vertices),
            "is_watertight": mesh.is_watertight,
            "is_volume": mesh.is_volume,
            "euler_number": mesh.euler_number,
            "volume": mesh.volume if mesh.is_volume else None,
            "surface_area": mesh.area,
        }
    except Exception as e:
        print(f"Warning: Failed to load {stl_path}: {e}")
        return None


def run_repair_test(input_file, engine):
    """
    Run repair-stl.sh on a single file with the specified engine.

    Uses a temporary directory to isolate the file and avoid processing
    all files in the current directory.

    Returns: (repair_time, pre_metrics, post_metrics, stdout, stderr, temp_repaired_path)
    """

    print(f"\nTesting: {input_file} with engine={engine}")

    # Collect pre-repair metrics
    print("  Collecting pre-repair metrics...")
    pre_metrics = collect_metrics(input_file)

    # Create temp directory and copy file
    temp_dir = tempfile.mkdtemp(prefix="stl_repair_test_")
    temp_input = Path(temp_dir) / Path(input_file).name

    try:
        shutil.copy2(input_file, temp_input)
        print(f"  Copied to temp: {temp_dir}")

        # Run repair-stl.sh in the temp directory
        print(f"  Running repair-stl.sh --engine {engine}...")
        start_time = time.perf_counter()

        cmd = get_repair_command() + ["--engine", engine]
        result = subprocess.run(
            cmd,
            cwd=temp_dir,
            capture_output=True,
            text=True
        )

        end_time = time.perf_counter()
        repair_time = end_time - start_time

        print(f"  Repair completed in {repair_time:.3f}s")

        # The repair script saves back to the original file
        # So the repaired file is the same as the input file (in the temp dir)
        repaired_path = temp_input

        if not repaired_path.exists():
            print("  Warning: Repaired file not found")
            return repair_time, pre_metrics, None, result.stdout, result.stderr, None

        # Collect post-repair metrics
        print("  Collecting post-repair metrics...")
        post_metrics = collect_metrics(repaired_path)

        return repair_time, pre_metrics, post_metrics, result.stdout, result.stderr, str(repaired_path)

    finally:
        # Clean up temp directory
        shutil.rmtree(temp_dir, ignore_errors=True)
        print(f"  Cleaned up temp directory")


def format_metric_value(value):
    """Format a metric value for display."""
    if value is None:
        return "N/A"
    elif isinstance(value, bool):
        return "[OK]" if value else "[X]"
    elif isinstance(value, float):
        return f"{value:,.2f}"
    elif isinstance(value, int):
        return f"{value:,}"
    else:
        return str(value)


def generate_markdown_report(results):
    """Generate markdown report from test results."""

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    md = []
    md.append("# STL Repair Engine Comparison Test Results")
    md.append(f"\n**Generated:** {timestamp}")
    md.append(f"**Platform:** {platform.system()} {platform.release()}")
    md.append(f"**Python:** {sys.version.split()[0]}")
    md.append(f"**Trimesh:** {trimesh.__version__}\n")

    # Per-engine sections
    for test_name, result in results.items():
        engine = result["engine"]
        input_file = result["input_file"]
        repair_time = result["repair_time"]
        pre = result["pre_metrics"]
        post = result["post_metrics"]
        stdout = result["stdout"]
        stderr = result["stderr"]

        md.append(f"\n## {test_name}")
        md.append(f"\n**Engine:** `{engine}`")
        md.append(f"**Input File:** `{input_file}`")
        md.append(f"**Repair Time:** {repair_time:.3f}s\n")

        # Metrics table
        md.append("### Metrics Comparison\n")
        md.append("| Metric | Before | After | Delta |")
        md.append("|--------|--------|-------|-------|")

        if pre and post:
            for key in ["file_size", "face_count", "vertex_count", "is_watertight",
                       "is_volume", "euler_number", "volume", "surface_area"]:
                pre_val = pre.get(key)
                post_val = post.get(key)

                # Calculate delta
                if isinstance(pre_val, (int, float)) and isinstance(post_val, (int, float)):
                    delta = post_val - pre_val
                    delta_str = f"{delta:+,.2f}" if isinstance(delta, float) else f"{delta:+,}"
                elif isinstance(pre_val, bool) and isinstance(post_val, bool):
                    delta_str = "-> [OK]" if not pre_val and post_val else "-"
                else:
                    delta_str = "-"

                md.append(f"| {key.replace('_', ' ').title()} | "
                         f"{format_metric_value(pre_val)} | "
                         f"{format_metric_value(post_val)} | "
                         f"{delta_str} |")
        else:
            md.append("| *Error collecting metrics* | | | |")

        # Raw output (collapsible)
        md.append("\n<details>")
        md.append("<summary>Raw Repair Output</summary>\n")
        md.append("**stdout:**")
        md.append("```")
        md.append(stdout or "(empty)")
        md.append("```\n")
        md.append("**stderr:**")
        md.append("```")
        md.append(stderr or "(empty)")
        md.append("```")
        md.append("</details>\n")

    # Side-by-side comparison
    md.append("\n## Side-by-Side Comparison\n")

    test_names = list(results.keys())
    if len(test_names) == 2:
        result1 = results[test_names[0]]
        result2 = results[test_names[1]]

        md.append("| Metric | Local (pymeshfix) | Windows (RepairAsync) |")
        md.append("|--------|-------------------|------------------------|")

        for key in ["file_size", "face_count", "vertex_count", "is_watertight",
                   "is_volume", "euler_number", "volume", "surface_area"]:

            val1 = result1["post_metrics"].get(key) if result1["post_metrics"] else None
            val2 = result2["post_metrics"].get(key) if result2["post_metrics"] else None

            md.append(f"| {key.replace('_', ' ').title()} | "
                     f"{format_metric_value(val1)} | "
                     f"{format_metric_value(val2)} |")

        md.append(f"| **Repair Time** | {result1['repair_time']:.3f}s | {result2['repair_time']:.3f}s |")

        # Face count analysis
        md.append("\n### Face Count Analysis\n")

        if result1["post_metrics"] and result2["post_metrics"]:
            face1 = result1["post_metrics"]["face_count"]
            face2 = result2["post_metrics"]["face_count"]

            diff = abs(face1 - face2)
            avg = (face1 + face2) / 2
            pct_diff = (diff / avg * 100) if avg > 0 else 0

            md.append(f"- **Local engine face count:** {face1:,}")
            md.append(f"- **Windows engine face count:** {face2:,}")
            md.append(f"- **Absolute difference:** {diff:,}")
            md.append(f"- **Percentage difference:** {pct_diff:.2f}%")

            if pct_diff < 5.0:
                md.append(f"- **Assessment:** [OK] PASS (< 5% difference)")
            else:
                md.append(f"- **Assessment:** [X] FAIL (≥ 5% difference)")

        # Watertight status
        md.append("\n### Watertight Status\n")

        wt1 = result1["post_metrics"]["is_watertight"] if result1["post_metrics"] else False
        wt2 = result2["post_metrics"]["is_watertight"] if result2["post_metrics"] else False

        md.append(f"- **Local engine:** {'[OK] Watertight' if wt1 else '[X] Not watertight'}")
        md.append(f"- **Windows engine:** {'[OK] Watertight' if wt2 else '[X] Not watertight'}")

        if wt1 and wt2:
            md.append("- **Assessment:** [OK] Both engines produced watertight meshes")
        else:
            md.append("- **Assessment:** [X] One or both engines failed to produce watertight meshes")

    return "\n".join(md)


def main():
    """Main test orchestration."""

    print("=" * 60)
    print("STL Repair Engine Comparison Test")
    print("=" * 60)

    # Validate prerequisites
    validate_prerequisites()

    # Define test cases
    test_cases = [
        {
            "name": "Local Engine Test",
            "input_file": "tests/non-manifold-test.stl",
            "engine": "local"
        },
        {
            "name": "Windows Engine Test",
            "input_file": "tests/non-manifold-test.stl",
            "engine": "windows"
        }
    ]

    # Run tests
    results = {}

    for test_case in test_cases:
        repair_time, pre_metrics, post_metrics, stdout, stderr, repaired_path = run_repair_test(
            test_case["input_file"],
            test_case["engine"]
        )

        results[test_case["name"]] = {
            "engine": test_case["engine"],
            "input_file": test_case["input_file"],
            "repair_time": repair_time,
            "pre_metrics": pre_metrics,
            "post_metrics": post_metrics,
            "stdout": stdout,
            "stderr": stderr,
            "repaired_path": repaired_path
        }

    # Generate report
    print("\n" + "=" * 60)
    print("Generating report...")

    report = generate_markdown_report(results)

    output_file = "repair_test_results.md"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"[OK] Report written to: {output_file}")
    print("=" * 60)

    # Print summary
    print("\nSummary:")
    for test_name, result in results.items():
        print(f"  {test_name}: {result['repair_time']:.3f}s")
        if result['post_metrics']:
            print(f"    Faces: {result['post_metrics']['face_count']:,}")
            print(f"    Watertight: {'[OK]' if result['post_metrics']['is_watertight'] else '[X]'}")


if __name__ == "__main__":
    main()
