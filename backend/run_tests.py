#!/usr/bin/env python3
"""
Test Runner for AI Analytics Platform

Usage:
    python run_tests.py              # Run all tests
    python run_tests.py -v           # Run with verbose output
    python run_tests.py -k history   # Run only history tests
    python run_tests.py --cov        # Run with coverage
"""

import subprocess
import sys
import argparse


def run_tests(args):
    """Run pytest with given arguments"""
    
    cmd = ["python", "-m", "pytest"]
    
    # Add test files
    test_files = [
        "tests/test_query_history.py",
        "tests/test_user_memory.py",
        "tests/test_subscriptions.py",
        "tests/test_api_integration.py"
    ]
    
    # Parse arguments
    if args.verbose:
        cmd.append("-v")
    
    if args.keyword:
        cmd.extend(["-k", args.keyword])
    
    if args.coverage:
        cmd.extend(["--cov=app", "--cov-report=term-missing"])
    
    if args.failfast:
        cmd.append("-x")
    
    cmd.extend(test_files)
    
    # Run tests
    print(f"Running: {' '.join(cmd)}")
    print("=" * 70)
    
    result = subprocess.run(cmd, cwd="/Users/sam-bot/.openclaw/workspace/ai-analytics-platform/backend")
    
    return result.returncode


def main():
    parser = argparse.ArgumentParser(description="Run AI Analytics Platform tests")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    parser.add_argument("-k", "--keyword", help="Only run tests matching keyword")
    parser.add_argument("--cov", dest="coverage", action="store_true", help="Run with coverage")
    parser.add_argument("-x", "--failfast", action="store_true", help="Stop on first failure")
    
    args = parser.parse_args()
    
    return_code = run_tests(args)
    sys.exit(return_code)


if __name__ == "__main__":
    main()
