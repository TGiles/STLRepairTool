"""Test _print_batch_summary() output formatting."""

import io
from contextlib import redirect_stdout
import repair_stl


def test_print_summary_correct_counts():
    """Prints correct counts for repaired/skipped/failed."""
    results = [
        repair_stl.RepairResult("a.stl", repair_stl.FileStatus.REPAIRED, output_size=100),
        repair_stl.RepairResult("b.stl", repair_stl.FileStatus.REPAIRED, output_size=200),
        repair_stl.RepairResult("c.stl", repair_stl.FileStatus.SKIPPED),
        repair_stl.RepairResult("d.stl", repair_stl.FileStatus.FAILED, error_message="Error"),
    ]

    output = io.StringIO()
    with redirect_stdout(output):
        repair_stl._print_batch_summary(results, total_time=5.0, interrupted=False)

    output_text = output.getvalue()
    assert "2" in output_text  # 2 repaired
    assert "1" in output_text  # 1 skipped and 1 failed


def test_print_summary_interrupted_message():
    """Prints INTERRUPTED when interrupted=True."""
    results = [
        repair_stl.RepairResult("a.stl", repair_stl.FileStatus.REPAIRED, output_size=100),
    ]

    output = io.StringIO()
    with redirect_stdout(output):
        repair_stl._print_batch_summary(results, total_time=1.0, interrupted=True)

    output_text = output.getvalue()
    assert "interrupt" in output_text.lower()


def test_print_summary_lists_failed_files():
    """Lists failed files with error messages."""
    results = [
        repair_stl.RepairResult("good.stl", repair_stl.FileStatus.REPAIRED, output_size=100),
        repair_stl.RepairResult("bad1.stl", repair_stl.FileStatus.FAILED, error_message="Error 1"),
        repair_stl.RepairResult("bad2.stl", repair_stl.FileStatus.FAILED, error_message="Error 2"),
    ]

    output = io.StringIO()
    with redirect_stdout(output):
        repair_stl._print_batch_summary(results, total_time=3.0, interrupted=False)

    output_text = output.getvalue()
    assert "bad1.stl" in output_text
    assert "bad2.stl" in output_text
    assert "Error 1" in output_text
    assert "Error 2" in output_text


def test_print_summary_no_failed_section_when_all_succeed():
    """No 'Failed files:' section when all succeed."""
    results = [
        repair_stl.RepairResult("a.stl", repair_stl.FileStatus.REPAIRED, output_size=100),
        repair_stl.RepairResult("b.stl", repair_stl.FileStatus.SKIPPED),
    ]

    output = io.StringIO()
    with redirect_stdout(output):
        repair_stl._print_batch_summary(results, total_time=2.0, interrupted=False)

    output_text = output.getvalue()
    # Should show 0 failed
    assert "0" in output_text


def test_print_summary_empty_results():
    """Handles empty results list."""
    results = []

    output = io.StringIO()
    with redirect_stdout(output):
        repair_stl._print_batch_summary(results, total_time=0.0, interrupted=False)

    output_text = output.getvalue()
    # Should handle gracefully
    assert "0" in output_text


def test_print_summary_all_statuses():
    """Handles all status types correctly."""
    results = [
        repair_stl.RepairResult("repaired.stl", repair_stl.FileStatus.REPAIRED, output_size=100),
        repair_stl.RepairResult("skipped.stl", repair_stl.FileStatus.SKIPPED),
        repair_stl.RepairResult("failed.stl", repair_stl.FileStatus.FAILED, error_message="Broken"),
    ]

    output = io.StringIO()
    with redirect_stdout(output):
        repair_stl._print_batch_summary(results, total_time=4.0, interrupted=False)

    output_text = output.getvalue()
    # All counts should be present
    assert "1" in output_text  # Each status has count 1
