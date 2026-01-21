# Testing Documentation

## Overview

This document describes the testing infrastructure for the Urban Mobility Analysis backend system. The test suite covers data import functionality, REST API endpoints, and database operations.

## Test Structure

```
server/tests/
├── __init__.py
├── run_tests.py                    # Test runner script
├── fixtures/
│   ├── __init__.py
│   └── test_data.json             # Test data fixtures
├── test_mobility/
│   ├── __init__.py
│   ├── test_import.py             # Import functionality tests
│   └── test_api.py                # REST API tests
├── test_ml/
│   └── __init__.py
└── test_poi/
    └── __init__.py
```

## Test Categories

### 1. Model Tests

Tests for Django model functionality including validation, constraints, and relationships.

**Test Cases:**
- `DatasetModelTestCase` - Dataset creation, uniqueness, field mapping
- `GPSPointModelTestCase` - GPS point creation, geometry generation, validation
- `ImportJobModelTestCase` - Import job tracking and statistics
- `ValidationErrorModelTestCase` - Error logging functionality

**Run:**
```bash
python tests/run_tests.py models
```

### 2. Import Tests

Tests for data import functionality including file parsing, validation, and database insertion.

**Test Cases:**
- `DataValidatorTestCase` - Data validation logic
- `MobilityDataImporterTestCase` - Generic importer functionality
- `TDriveImporterTestCase` - T-Drive specific importer
- `ImportIntegrationTestCase` - End-to-end import workflows

**Run:**
```bash
python tests/run_tests.py import
```

### 3. API Tests

Tests for REST API endpoints including CRUD operations, filtering, and queries.

**Test Cases:**
- `DatasetAPITestCase` - Dataset management endpoints
- `GPSPointAPITestCase` - GPS point CRUD and queries
- `TrajectoryAPITestCase` - Trajectory endpoints
- `ImportJobAPITestCase` - Import job management
- `EntityAPITestCase` - Entity statistics
- `APIErrorHandlingTestCase` - Error handling

**Run:**
```bash
python tests/run_tests.py api
```

## Running Tests

### Quick Start

Run all tests:
```bash
python tests/run_tests.py
# or
python manage.py test
```

### Run Specific Test Groups

```bash
# Import tests only
python tests/run_tests.py import

# API tests only
python tests/run_tests.py api

# Model tests only
python tests/run_tests.py models
```

### Run Specific Test Case

```bash
python tests/run_tests.py --test tests.test_mobility.test_import.DatasetModelTestCase
```

### Run Specific Test Method

```bash
python tests/run_tests.py --test tests.test_mobility.test_import.DatasetModelTestCase.test_create_dataset
```

### Run with Coverage

```bash
# Install coverage first
pip install coverage

# Run tests with coverage
python tests/run_tests.py coverage

# View HTML coverage report
open htmlcov/index.html
```

### List Available Tests

```bash
python tests/run_tests.py list
```

## Test Configuration

### Database

Tests use a separate test database that is automatically created and destroyed. To keep the test database after tests complete:

```bash
python tests/run_tests.py --keepdb
```

### Verbosity

Control test output detail:

```bash
# Minimal output (0)
python tests/run_tests.py --verbosity 0

# Normal output (1)
python tests/run_tests.py --verbosity 1

# Verbose output (2, default)
python tests/run_tests.py --verbosity 2

# Very verbose output (3)
python tests/run_tests.py --verbosity 3
```

## Test Fixtures

### Test Data Files

Located in `server/tests/fixtures/test_data.json`:

- **test_datasets**: Sample dataset configurations
- **test_gps_points**: Sample GPS point data
- **test_trajectories**: Sample trajectory data
- **test_import_jobs**: Sample import job data
- **test_validation_errors**: Sample validation errors
- **test_raw_files**: Raw file format examples
- **test_query_parameters**: Common query parameters
- **test_statistics**: Expected statistics for validation

### Using Fixtures in Tests

```python
import json
from pathlib import Path

# Load test data
fixtures_dir = Path(__file__).parent.parent / 'fixtures'
with open(fixtures_dir / 'test_data.json', 'r') as f:
    test_data = json.load(f)

# Use in tests
gps_points = test_data['test_gps_points']
```

## Writing New Tests

### Test Case Template

```python
from django.test import TestCase
from apps.mobility.models import Dataset, GPSPoint

class MyTestCase(TestCase):
    """Description of test case."""
    
    def setUp(self):
        """Set up test data."""
        self.dataset = Dataset.objects.create(
            name='Test Dataset',
            dataset_type='gps_trace',
            data_format='txt'
        )
    
    def test_something(self):
        """Test description."""
        # Arrange
        data = {'key': 'value'}
        
        # Act
        result = some_function(data)
        
        # Assert
        self.assertEqual(result, expected_value)
    
    def tearDown(self):
        """Clean up after test."""
        pass
```

### API Test Template

```python
from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse

class MyAPITestCase(APITestCase):
    """Description of API test case."""
    
    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        # Create test data
    
    def test_api_endpoint(self):
        """Test API endpoint."""
        url = reverse('mobility:dataset-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)
```

## Test Best Practices

### 1. Test Isolation

Each test should be independent and not rely on other tests:

```python
def test_create_dataset(self):
    """Each test creates its own data."""
    dataset = Dataset.objects.create(name='Test')
    self.assertIsNotNone(dataset.id)
```

### 2. Descriptive Names

Use clear, descriptive test names:

```python
# Good
def test_dataset_unique_name_constraint(self):
    pass

# Bad
def test_1(self):
    pass
```

### 3. Arrange-Act-Assert Pattern

Structure tests clearly:

```python
def test_import_csv_file(self):
    # Arrange
    dataset = self.create_test_dataset()
    csv_file = self.create_test_csv()
    
    # Act
    result = importer.import_from_csv(csv_file)
    
    # Assert
    self.assertEqual(result.status, 'completed')
    self.assertEqual(result.successful_records, 10)
```

### 4. Test Edge Cases

Include tests for edge cases and error conditions:

```python
def test_invalid_coordinates(self):
    """Test handling of invalid coordinates."""
    with self.assertRaises(ValidationError):
        GPSPoint.objects.create(
            longitude=190.0,  # Invalid
            latitude=39.90
        )
```

### 5. Use Temporary Files

For file-based tests, use temporary files:

```python
import tempfile

def test_import_file(self):
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
        f.write('test data')
        temp_path = f.name
    
    try:
        result = importer.import_file(temp_path)
        self.assertTrue(result.success)
    finally:
        os.unlink(temp_path)
```

## Continuous Integration

### GitHub Actions Workflow

Create `.github/workflows/tests.yml`:

```yaml
name: Run Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgis/postgis:15-3.3
        env:
          POSTGRES_DB: test_db
          POSTGRES_USER: postgres
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
      
      - name: Run tests
        env:
          DB_HOST: localhost
          DB_NAME: test_db
          DB_USER: postgres
          DB_PASSWORD: postgres
        run: |
          python tests/run_tests.py coverage
```

## Troubleshooting

### Common Issues

**1. Database connection errors:**
```bash
# Check PostgreSQL is running
psql -U postgres -c "SELECT version();"

# Check PostGIS extension
psql -U postgres -d urban_mobility_db -c "SELECT PostGIS_version();"
```

**2. Import errors:**
```bash
# Ensure Django is configured
export DJANGO_SETTINGS_MODULE=config.settings
python -c "import django; django.setup()"
```

**3. Test database not cleaned:**
```bash
# Manually drop test database
psql -U postgres -c "DROP DATABASE IF EXISTS test_urban_mobility_db;"
```

**4. Coverage not installed:**
```bash
pip install coverage
```

### Debug Mode

Run tests with Python debugger:

```python
# In test file
import pdb; pdb.set_trace()
```

Then run:
```bash
python tests/run_tests.py --test <test_path>
```

## Performance Testing

### Benchmark Tests

For performance-critical operations:

```python
import time

def test_bulk_insert_performance(self):
    """Test bulk insert performance."""
    start_time = time.time()
    
    # Create 10000 points
    points = [
        GPSPoint(...)
        for i in range(10000)
    ]
    GPSPoint.objects.bulk_create(points)
    
    duration = time.time() - start_time
    
    # Assert completes in reasonable time
    self.assertLess(duration, 5.0)  # 5 seconds
```

## Test Coverage Goals

Target coverage levels:
- **Overall**: > 80%
- **Models**: > 90%
- **Services**: > 85%
- **API Views**: > 80%
- **Utils**: > 75%

## Resources

- [Django Testing Documentation](https://docs.djangoproject.com/en/stable/topics/testing/)
- [Django REST Framework Testing](https://www.django-rest-framework.org/api-guide/testing/)
- [Coverage.py Documentation](https://coverage.readthedocs.io/)
- [Python unittest Documentation](https://docs.python.org/3/library/unittest.html)

## Contact

For questions or issues with testing:
- Create an issue in the project repository
- Contact the development team
- Check the project wiki for additional resources