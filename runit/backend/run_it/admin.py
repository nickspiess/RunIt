from django.contrib import admin
from .models import Runner, PersonalRecord, TrainingPreference, TrainingPlan, TrainingSession

admin.site.register(Runner)
admin.site.register(PersonalRecord)
admin.site.register(TrainingPreference)
admin.site.register(TrainingPlan)
admin.site.register(TrainingSession)