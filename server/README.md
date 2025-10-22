# Urban Mobility Analysis - Backend Server

Django backend for urban mobility analysis system.

## Features

- GPS trace management and processing
- Origin-Destination analysis
- Point of Interest (POI) management
- Machine Learning for transport mode classification
- Mobility analytics and visualization
- Integration with OpenStreetMap data

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

3. Run database migrations:
```bash
python manage.py migrate
```

4. Start development server:
```bash
python manage.py runserver
```

## Project Structure

- `apps/` - Django applications
  - `mobility/` - GPS traces and OD data
  - `poi/` - Points of Interest
  - `ml/` - Machine Learning models
  - `analytics/` - Analysis and visualization
- `database/` - Database scripts and sample data
- `notebooks/` - Jupyter notebooks for experimentation
- `utils/` - Utility functions
