from apps.mobility.models import TDriveRawPoint, TDriveImportLog

# 1. Compter le nombre total de points
total_points = TDriveRawPoint.objects.count()
print(f"📊 Total points dans la base: {total_points}")

# 2. Compter les taxis distincts
taxis_count = TDriveRawPoint.objects.values('taxi_id').distinct().count()
print(f"🚕 Taxis distincts: {taxis_count}")

# 3. Vérifier les premiers points
print("\n📋 5 premiers points:")
points = TDriveRawPoint.objects.all()[:5]
for i, point in enumerate(points):
    print(f"  {i+1}. Taxi {point.taxi_id} - ({point.longitude}, {point.latitude}) - {point.timestamp}")

# 4. Vérifier les logs d'import
print("\n📝 Logs d'import:")
imports = TDriveImportLog.objects.all()
for imp in imports:
    print(f"  • {imp.file_name}: {imp.status} - {imp.successful_imports} points")

# 5. Statistiques de validation
from django.db.models import Count, Q
stats = TDriveRawPoint.objects.aggregate(
    total=Count('id'),
    valid=Count('id', filter=Q(is_valid=True)),
    invalid=Count('id', filter=Q(is_valid=False))
)
print(f"\n✅ Points valides: {stats['valid']}/{stats['total']}")
print(f"❌ Points invalides: {stats['invalid']}/{stats['total']}")

# 6. Vérifier la répartition par taxi
print(f"\n🚖 Top 5 taxis par nombre de points:")
taxi_stats = TDriveRawPoint.objects.values('taxi_id').annotate(
    point_count=Count('id')
).order_by('-point_count')[:5]
for taxi in taxi_stats:
    print(f"  • Taxi {taxi['taxi_id']}: {taxi['point_count']} points")