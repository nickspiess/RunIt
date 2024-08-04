from django.db import models
from datetime import date, timedelta
from django.contrib.auth.models import User

class Runner(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='runner_profile')
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)
    age = models.IntegerField(default=18)
    email = models.EmailField(unique=True)
    race_type = models.CharField(max_length=100, default='Marathon')
    goal_time = models.DurationField()
    race_date = models.DateField()
    race_name = models.CharField(max_length=100)
    current_weekly_mileage = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    max_weekly_mileage = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    longest_run_last_4_weeks = models.IntegerField(blank=True, null=True)
    current_running_days_per_week = models.IntegerField(blank=True, null=True)
    willing_running_days_per_week = models.IntegerField(blank=True, null=True)
    weeks_able_to_train = models.IntegerField(blank=True, null=True)
    longest_run_day = models.CharField(max_length=10, blank=True, null=True)
    distance_unit = models.CharField(max_length=10, choices=[('miles', 'Miles'), ('kilometers', 'Kilometers')], default='miles')

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class PersonalRecord(models.Model):
    runner = models.ForeignKey(Runner, on_delete=models.CASCADE, related_name='prs')
    race_type = models.CharField(max_length=100, default='Marathon')
    pr_time = models.DurationField(default=timedelta(hours=1))
    date = models.DateField(blank=True, null=True)

    def __str__(self):
        return f"{self.race_type} - {self.pr_time}"



class TrainingPreference(models.Model):
    runner = models.OneToOneField(Runner, on_delete=models.CASCADE)
    current_weekly_mileage = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)  # Default value provided
    current_weekly_elevation = models.CharField(max_length=100, default='0')  # Default value provided
    goal_race_distance = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)  # Default value provided
    goal_race_pace = models.CharField(max_length=100, default='00:00')  # Default value provided
    training_duration_weeks = models.IntegerField(default=0)  # Default value provided
    available_training_days_per_week = models.IntegerField(default=0)  # Default value provided
    strength_training = models.BooleanField(default=False)
    rest_days = models.IntegerField(default=0)  # Default value provided
    injury_prevention = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Preferences for {self.runner}"

class TrainingPlan(models.Model):
    runner = models.ForeignKey(Runner, on_delete=models.CASCADE)
    start_date = models.DateField(default=date.today)  # Default value as date
    end_date = models.DateField(default=date.today)  # Default value as date
    distance = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)  # Default value provided
    race_name = models.CharField(max_length=100, default='Unknown Race')  # Default value provided

    def __str__(self):
        return f"{self.race_name} training plan for {self.runner}"

class TrainingSession(models.Model):
    plan = models.ForeignKey(TrainingPlan, on_delete=models.CASCADE)
    date = models.DateField(default=date.today)  # Default value as date
    distance = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)  # Default value provided
    duration = models.DurationField(default=timedelta(hours=1))  # Default value as timedelta
    description = models.TextField(blank=True, null=True)
    type = models.CharField(max_length=20, default='Unknown')  # Default value provided

    def __str__(self):
        return f"{self.type} run on {self.date} for {self.distance} miles"
