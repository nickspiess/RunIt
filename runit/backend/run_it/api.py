from rest_framework.routers import DefaultRouter
from .views import (
    RunnerViewSet, PersonalRecordViewSet, TrainingPreferenceViewSet,
    TrainingPlanViewSet, TrainingSessionViewSet
)

router = DefaultRouter()
router.register(r'runners', RunnerViewSet)
router.register(r'personal_records', PersonalRecordViewSet)
router.register(r'training_preferences', TrainingPreferenceViewSet)
router.register(r'get_training_plan', TrainingPlanViewSet)
router.register(r'training_sessions', TrainingSessionViewSet)

urlpatterns = router.urls
