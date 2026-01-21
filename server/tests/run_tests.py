#!/usr/bin/env python3
"""
============================================================================
Test Runner Script for Urban Mobility Analysis
============================================================================
File: server/tests/run_tests.py
Usage: python tests/run_tests.py [options]
============================================================================
"""

import os
import sys
import django
import argparse
from pathlib import Path

# Add server directory to path
server_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(server_dir))

# Configure Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.test.runner import DiscoverRunner
from django.conf import settings


def run_all_tests(verbosity=2):
    """Run all tests in the test suite."""
    print("=" * 70)
    print("RUNNING ALL TESTS")
    print("=" * 70)
    
    runner = DiscoverRunner(verbosity=verbosity, interactive=False)
    failures = runner.run_tests(['tests'])
    
    return failures


def run_import_tests(verbosity=2):
    """Run only import-related tests."""
    print("=" * 70)
    print("RUNNING IMPORT TESTS")
    print("=" * 70)
    
    runner = DiscoverRunner(verbosity=verbosity, interactive=False)
    failures = runner.run_tests(['tests.test_mobility.test_import'])
    
    return failures


def run_api_tests(verbosity=2):
    """Run only API tests."""
    print("=" * 70)
    print("RUNNING API TESTS")
    print("=" * 70)
    
    runner = DiscoverRunner(verbosity=verbosity, interactive=False)
    failures = runner.run_tests(['tests.test_mobility.test_api'])
    
    return failures


def run_model_tests(verbosity=2):
    """Run only model tests."""
    print("=" * 70)
    print("RUNNING MODEL TESTS")
    print("=" * 70)
    
    test_cases = [
        'tests.test_mobility.test_import.DatasetModelTestCase',
        'tests.test_mobility.test_import.GPSPointModelTestCase',
        'tests.test_mobility.test_import.ImportJobModelTestCase',
        'tests.test_mobility.test_import.ValidationErrorModelTestCase'
    ]
    
    runner = DiscoverRunner(verbosity=verbosity, interactive=False)
    failures = runner.run_tests(test_cases)
    
    return failures


def run_specific_test(test_path, verbosity=2):
    """Run a specific test case or test method."""
    print("=" * 70)
    print(f"RUNNING SPECIFIC TEST: {test_path}")
    print("=" * 70)
    
    runner = DiscoverRunner(verbosity=verbosity, interactive=False)
    failures = runner.run_tests([test_path])
    
    return failures


def run_coverage_tests():
    """Run tests with coverage reporting."""
    try:
        import coverage
    except ImportError:
        print("ERROR: coverage package not installed")
        print("Install with: pip install coverage")
        return 1
    
    print("=" * 70)
    print("RUNNING TESTS WITH COVERAGE")
    print("=" * 70)
    
    # Start coverage
    cov = coverage.Coverage(
        source=['apps'],
        omit=[
            '*/migrations/*',
            '*/tests/*',
            '*/admin.py',
            '*/__init__.py'
        ]
    )
    cov.start()
    
    # Run tests
    runner = DiscoverRunner(verbosity=2, interactive=False)
    failures = runner.run_tests(['tests'])
    
    # Stop coverage and report
    cov.stop()
    cov.save()
    
    print("\n" + "=" * 70)
    print("COVERAGE REPORT")
    print("=" * 70)
    cov.report()
    
    # Generate HTML report
    html_dir = server_dir / 'htmlcov'
    cov.html_report(directory=str(html_dir))
    print(f"\nHTML coverage report generated in: {html_dir}")
    
    return failures


def list_available_tests():
    """List all available test cases."""
    print("=" * 70)
    print("AVAILABLE TEST CASES")
    print("=" * 70)
    
    test_cases = [
        "Import Tests:",
        "  - tests.test_mobility.test_import.DatasetModelTestCase",
        "  - tests.test_mobility.test_import.GPSPointModelTestCase",
        "  - tests.test_mobility.test_import.DataValidatorTestCase",
        "  - tests.test_mobility.test_import.MobilityDataImporterTestCase",
        "  - tests.test_mobility.test_import.TDriveImporterTestCase",
        "  - tests.test_mobility.test_import.ImportJobModelTestCase",
        "  - tests.test_mobility.test_import.ValidationErrorModelTestCase",
        "  - tests.test_mobility.test_import.ImportIntegrationTestCase",
        "",
        "API Tests:",
        "  - tests.test_mobility.test_api.DatasetAPITestCase",
        "  - tests.test_mobility.test_api.GPSPointAPITestCase",
        "  - tests.test_mobility.test_api.TrajectoryAPITestCase",
        "  - tests.test_mobility.test_api.ImportJobAPITestCase",
        "  - tests.test_mobility.test_api.EntityAPITestCase",
        "  - tests.test_mobility.test_api.APIErrorHandlingTestCase",
    ]
    
    for line in test_cases:
        print(line)
    
    print("\n" + "=" * 70)
    print("TEST GROUPS")
    print("=" * 70)
    print("  all       - Run all tests")
    print("  import    - Run import tests only")
    print("  api       - Run API tests only")
    print("  models    - Run model tests only")
    print("  coverage  - Run tests with coverage report")
    print("\nRun specific test:")
    print("  python tests/run_tests.py --test <test_path>")
    print("  Example: python tests/run_tests.py --test tests.test_mobility.test_import.DatasetModelTestCase")


def main():
    """Main test runner function."""
    parser = argparse.ArgumentParser(
        description='Run tests for Urban Mobility Analysis'
    )
    
    parser.add_argument(
        'test_group',
        nargs='?',
        default='all',
        choices=['all', 'import', 'api', 'models', 'coverage', 'list'],
        help='Test group to run (default: all)'
    )
    
    parser.add_argument(
        '--test',
        type=str,
        help='Run specific test case or method'
    )
    
    parser.add_argument(
        '--verbosity',
        type=int,
        default=2,
        choices=[0, 1, 2, 3],
        help='Test output verbosity (default: 2)'
    )
    
    parser.add_argument(
        '--keepdb',
        action='store_true',
        help='Keep test database after tests complete'
    )
    
    args = parser.parse_args()
    
    # Handle list option
    if args.test_group == 'list':
        list_available_tests()
        return 0
    
    # Update settings if keepdb
    if args.keepdb:
        os.environ['DJANGO_TEST_KEEPDB'] = '1'
    
    # Run tests based on argument
    try:
        if args.test:
            failures = run_specific_test(args.test, args.verbosity)
        elif args.test_group == 'all':
            failures = run_all_tests(args.verbosity)
        elif args.test_group == 'import':
            failures = run_import_tests(args.verbosity)
        elif args.test_group == 'api':
            failures = run_api_tests(args.verbosity)
        elif args.test_group == 'models':
            failures = run_model_tests(args.verbosity)
        elif args.test_group == 'coverage':
            failures = run_coverage_tests()
        else:
            print(f"Unknown test group: {args.test_group}")
            return 1
        
        # Print summary
        print("\n" + "=" * 70)
        if failures == 0:
            print("✅ ALL TESTS PASSED")
        else:
            print(f"❌ {failures} TEST(S) FAILED")
        print("=" * 70)
        
        return 0 if failures == 0 else 1
    
    except KeyboardInterrupt:
        print("\n\nTests interrupted by user")
        return 1
    except Exception as e:
        print(f"\n\nERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())