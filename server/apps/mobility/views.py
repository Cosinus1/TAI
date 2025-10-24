import json
import os
from django.http import JsonResponse
from django.conf import settings


def sample_taxi_point(request):
	"""Return a single sample taxi GPS point from the repository sample data.

	Endpoint: GET /api/mobility/sample_taxi/
	"""
	try:
		base = settings.BASE_DIR if hasattr(settings, 'BASE_DIR') else os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
		sample_path = os.path.join(base, 'database', 'sample_data', 'sample_gps_traces.json')
		with open(sample_path, 'r', encoding='utf-8') as f:
			data = json.load(f)
		# Return the first point (or an empty object)
		point = data[0] if isinstance(data, list) and data else {}
		return JsonResponse({'ok': True, 'point': point})
	except Exception as e:
		return JsonResponse({'ok': False, 'error': str(e)}, status=500)

