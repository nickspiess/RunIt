from django.contrib.auth.models import User
from rest_framework import serializers
from .models import Runner, PersonalRecord, TrainingPreference, TrainingPlan, TrainingSession

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['username', 'password', 'email']
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password']
        )
        return user

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with that email already exists.")
        return value

class PersonalRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = PersonalRecord
        fields = '__all__'

class RunnerSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())  # Ensure it expects a primary key
    prs = PersonalRecordSerializer(many=True, required=False)
    id = serializers.IntegerField(read_only=True)  # Add this line to include the ID

    class Meta:
        model = Runner
        fields = [
            'id', 'user', 'first_name', 'last_name', 'email', 'age', 'race_type', 'goal_time', 
            'race_date', 'race_name', 'current_weekly_mileage', 'max_weekly_mileage', 
            'longest_run_last_4_weeks', 'current_running_days_per_week', 
            'willing_running_days_per_week', 'weeks_able_to_train', 'longest_run_day', 
            'distance_unit', 'prs'
        ]

    def validate_email(self, value):
        if Runner.objects.filter(email=value).exists():
            raise serializers.ValidationError("Runner with this email already exists.")
        return value

    def validate(self, data):
        print("Validation data:", data)
        return data

    def create(self, validated_data):
        prs_data = validated_data.pop('prs', [])
        runner = Runner.objects.create(**validated_data)
        for pr_data in prs_data:
            PersonalRecord.objects.create(runner=runner, **pr_data)
        return runner



class TrainingPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrainingPreference
        fields = '__all__'

class TrainingPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrainingPlan
        fields = '__all__'

class TrainingSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrainingSession
        fields = '__all__'
