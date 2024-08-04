from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import sign_up, sign_in, save_client_data, get_runner_info, generate_training_plan, get_training_plan,  RunnerViewSet, PersonalRecordViewSet, TrainingPreferenceViewSet, TrainingPlanViewSet, TrainingSessionViewSet

router = DefaultRouter()
router.register(r'runners', RunnerViewSet)
router.register(r'personal-records', PersonalRecordViewSet)
router.register(r'training-preferences', TrainingPreferenceViewSet)
router.register(r'training-plans', TrainingPlanViewSet)
router.register(r'training-sessions', TrainingSessionViewSet)

urlpatterns = [
    path('api/', include(router.urls)),
    path('api/sign-up/', sign_up, name='sign_up'),
    path('api/sign-in/', sign_in, name='sign_in'),
    path('api/save-client-data/', save_client_data, name='save_client_data'),
    path('api/get-runner-info/', get_runner_info, name='get_runner_info'),
    path('api/generate-training-plan/', generate_training_plan, name='generate_training_plan'),
    path('api/get-training-plan/', get_training_plan, name='get_training_plan'),
]