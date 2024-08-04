from rest_framework import viewsets
from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate, login
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication
from django.db import IntegrityError
from .models import Runner, PersonalRecord, TrainingPreference, TrainingPlan, TrainingSession
from .serializers import (
    RunnerSerializer, PersonalRecordSerializer, TrainingPreferenceSerializer,
    TrainingPlanSerializer, TrainingSessionSerializer, UserSerializer
)

from runitapp.generator.plan_generator import generate_marathon_plan

import logging
import json
from datetime import timedelta

logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
def generate_training_plan(request):
    print('what is the request', request)
    logger.debug('what is the request', request)
    runner_id = request.data.get('runner_id')
    if not runner_id:
        return Response({'error': 'Runner ID is required'}, status=400)
    
    try:
        generate_marathon_plan(runner_id)
        return Response({'message': 'Training plan generated successfully'}, status=200)
    except Exception as e:
        return Response({'error': str(e)}, status=500)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
def get_training_plan(request):
    runner = Runner.objects.get(user=request.user)
    try:
        plan = TrainingPlan.objects.get(runner=runner)
        sessions = TrainingSession.objects.filter(plan=plan)
        plan_serializer = TrainingPlanSerializer(plan)
        session_serializer = TrainingSessionSerializer(sessions, many=True)
        return Response({
            'plan': plan_serializer.data,
            'sessions': session_serializer.data
        }, status=200)
    except TrainingPlan.DoesNotExist:
        print('got a respone')
        return Response({'error': 'Training plan does not exist for this runner'}, status=404)

class RunnerViewSet(viewsets.ModelViewSet):
    queryset = Runner.objects.all()
    serializer_class = RunnerSerializer

    def create(self, request, *args, **kwargs):
        # Create the runner instance
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        runner = serializer.instance

        # Create the training preference instance with default values
        TrainingPreference.objects.create(
            runner=runner,
            current_weekly_mileage=runner.current_weekly_mileage or 0.0,
            current_weekly_elevation='0',  # Default value
            goal_race_distance=42.195,  # Assuming marathon distance in kilometers
            goal_race_pace='04:00',  # Default value
            training_duration_weeks=runner.weeks_able_to_train or 0,  # Use runner's training duration or default to 0
            available_training_days_per_week=runner.willing_running_days_per_week or 0,
            strength_training=False,  # Default value
            rest_days=1,  # Default value
            injury_prevention='None'  # Default value
        )

        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

@api_view(['POST'])
def sign_up(request):
    logger.debug('Sign-up endpoint hit')
    serializer = UserSerializer(data=request.data)
    if serializer.is_valid():
        try:
            user = serializer.save()  # Save and get the new user instance
            logger.debug('User created successfully')

            # Automatically log in the new user
            login(request, user)
            token, created = Token.objects.get_or_create(user=user)
            return Response({'message': 'User created and logged in successfully', 'token': token.key}, status=status.HTTP_201_CREATED)
        except IntegrityError as e:
            logger.debug('Integrity error: %s', str(e))
            if 'username' in str(e):
                return Response({'username': 'This username is already taken.'}, status=status.HTTP_400_BAD_REQUEST)
            elif 'email' in str(e):
                return Response({'email': 'This email is already taken.'}, status=status.HTTP_400_BAD_REQUEST)
    logger.debug('Errors: %s', serializer.errors)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
def sign_in(request):
    username = request.data.get('username')
    password = request.data.get('password')
    user = authenticate(username=username, password=password)
    if user is not None:
        token, created = Token.objects.get_or_create(user=user)
        try:
            runner = Runner.objects.get(user=user)
            return Response({'token': token.key, 'runner_id': runner.id, 'message': 'Sign-in successful'}, status=status.HTTP_200_OK)
        except Runner.DoesNotExist:
            return Response({'error': 'Runner profile not found.'}, status=status.HTTP_404_NOT_FOUND)
    else:
        return Response({'error': 'Invalid credentials'}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
def save_client_data(request):
    try:
        user = request.user
        print("Request user:", user)
        print("Request data:", request.data)

        # Validate all required fields
        required_fields = [
            'firstName', 'lastName', 'age', 'raceType', 'goalTime', 'raceDate', 'raceName', 
            'longestRunDay', 'currentWeeklyMileage', 'maxWeeklyMileage', 'longestRunLast4Weeks', 
            'currentRunningDaysPerWeek', 'willingRunningDaysPerWeek', 'weeksAbleToTrain', 'distanceUnit', 'email'
        ]
        missing_fields = [field for field in required_fields if not request.data.get(field)]
        
        if missing_fields:
            print('Missing fields:', missing_fields)
            return Response({'error': f'Missing fields: {", ".join(missing_fields)}'}, status=status.HTTP_400_BAD_REQUEST)

        # Convert necessary fields to appropriate types
        try:
            goal_time_str = request.data.get('goalTime')
            hours, minutes = map(int, goal_time_str.split(':'))
            goal_time = timedelta(hours=hours, minutes=minutes)
            
            runner_data = {
                'user': user.id,  # Use user ID instead of User instance
                'first_name': request.data.get('firstName'),
                'last_name': request.data.get('lastName'),
                'email': request.data.get('email'),  # Use email from request data
                'age': int(request.data.get('age')),  # Ensure age is an integer
                'race_type': request.data.get('raceType'),
                'goal_time': goal_time,  # Use the converted timedelta object
                'race_date': request.data.get('raceDate'),
                'race_name': request.data.get('raceName'),
                'current_weekly_mileage': int(request.data.get('currentWeeklyMileage')),  # Ensure mileage is an integer
                'max_weekly_mileage': int(request.data.get('maxWeeklyMileage')),  # Ensure mileage is an integer
                'longest_run_last_4_weeks': int(request.data.get('longestRunLast4Weeks')),  # Ensure mileage is an integer
                'current_running_days_per_week': int(request.data.get('currentRunningDaysPerWeek')),  # Ensure days are an integer
                'willing_running_days_per_week': int(request.data.get('willingRunningDaysPerWeek')),  # Ensure days are an integer
                'weeks_able_to_train': int(request.data.get('weeksAbleToTrain')),  # Ensure weeks are an integer
                'longest_run_day': request.data.get('longestRunDay'),
                'distance_unit': request.data.get('distanceUnit')
            }
        except ValueError as e:
            print("Error converting data types:", e)
            return Response({'error': 'Invalid data type provided.'}, status=status.HTTP_400_BAD_REQUEST)

        print("Runner data:", runner_data)

        # Check if a runner with the same email already exists
        existing_runner = Runner.objects.filter(email=runner_data['email']).first()
        if existing_runner:
            print(f"Existing runner with email found: {existing_runner}")
            if existing_runner.user == user:
                print("Runner already exists for this user, updating information.")
                for attr, value in runner_data.items():
                    print(f"Updating {attr} to {value}")
                    setattr(existing_runner, attr, value)
                existing_runner.save()
                runner = existing_runner
                print("Runner information updated successfully")
            else:
                print("Runner with this email already exists and belongs to a different user.")
                return Response({'error': 'Runner with this email already exists.'}, status=status.HTTP_400_BAD_REQUEST)
        else:
            # Check if the runner already exists for the user
            runner_exists = Runner.objects.filter(user=user).exists()
            if runner_exists:
                print("Runner already exists for this user, updating information.")
                runner = Runner.objects.get(user=user)
                for attr, value in runner_data.items():
                    print(f"Updating {attr} to {value}")
                    setattr(runner, attr, value)
                runner.save()
                print("Runner information updated successfully")
            else:
                print("Creating new runner for this user.")
                runner_serializer = RunnerSerializer(data=runner_data)
                if runner_serializer.is_valid():
                    runner = runner_serializer.save()
                    print("Runner information saved successfully")
                else:
                    print('Runner Serializer Validation errors:', runner_serializer.errors)
                    return Response(runner_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # Create or update training preferences
        TrainingPreference.objects.update_or_create(
            runner=runner,
            defaults={
                'current_weekly_mileage': runner.current_weekly_mileage or 0.0,
                'current_weekly_elevation': '0',  # Default value
                'goal_race_distance': 42.195,  # Assuming marathon distance in kilometers
                'goal_race_pace': '04:00',  # Default value
                'training_duration_weeks': runner.weeks_able_to_train or 0,  # Use runner's training duration or default to 0
                'available_training_days_per_week': runner.willing_running_days_per_week or 0,
                'strength_training': False,  # Default value
                'rest_days': 1,  # Default value
                'injury_prevention': 'None'  # Default value
            }
        )

        prs_data = request.data.get('prs', [])
        for pr in prs_data:
            pr_data = {
                'runner': runner.id,
                'race_type': pr['raceType'],
                'pr_time': pr['time'],
                'date': pr.get('date')
            }
            pr_serializer = PersonalRecordSerializer(data=pr_data)
            if pr_serializer.is_valid():
                pr_serializer.save()
            else:
                print('PR Validation errors:', pr_serializer.errors)
                return Response(pr_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        return Response({'message': 'Runner information saved successfully'}, status=status.HTTP_201_CREATED)
    except Exception as e:
        print('Error saving runner information:', str(e))
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_runner_info(request):
    try:
        runner = Runner.objects.get(user=request.user)
        serializer = RunnerSerializer(runner)
        return Response(serializer.data, status=status.HTTP_200_OK)
    except Runner.DoesNotExist:
        return Response({'error': 'Runner information not found'}, status=status.HTTP_404_NOT_FOUND)


class RunnerViewSet(viewsets.ModelViewSet):
    queryset = Runner.objects.all()
    serializer_class = RunnerSerializer

class PersonalRecordViewSet(viewsets.ModelViewSet):
    queryset = PersonalRecord.objects.all()
    serializer_class = PersonalRecordSerializer

class TrainingPreferenceViewSet(viewsets.ModelViewSet):
    queryset = TrainingPreference.objects.all()
    serializer_class = TrainingPreferenceSerializer

class TrainingPlanViewSet(viewsets.ModelViewSet):
    queryset = TrainingPlan.objects.all()
    serializer_class = TrainingPlanSerializer

class TrainingSessionViewSet(viewsets.ModelViewSet):
    queryset = TrainingSession.objects.all()
    serializer_class = TrainingSessionSerializer
