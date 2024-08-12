import math
import os
import sys
import random
import django
from datetime import date, timedelta
from django.utils import timezone

# Setup Django environment
sys.path.append('/Users/nickspiess/Desktop/RunItApp/runit/backend')
print('what is sys path', sys.path)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'runitapp.settings')
django.setup()

from run_it.models import Runner, TrainingPreference, TrainingPlan, TrainingSession


def clear_training_plans():
    TrainingPlan.objects.all().delete()
    print("All training plans have been deleted.")
    
def clear_all_sessions():
    TrainingSession.objects.all().delete()
    print("All training sessions have been deleted.")

# Debug: Print all runner IDs
def print_all_runner_ids():
    runners = Runner.objects.all()
    print("All Runner IDs:")
    for runner in runners:
        print(runner.id, runner.first_name, runner.last_name)

print_all_runner_ids()

def calculate_weekly_mileage(starting_mileage, goal_mileage, weeks):
    """
    Calculate weekly mileage incrementally from starting mileage to goal mileage,
    including a taper for the last 3 weeks. The increment is limited to 5-7% of the previous week's mileage.
    """
    
    mileage = []
    taper_weeks = 3
    build_up_weeks = weeks - taper_weeks
    
    # Initial mileage is the starting mileage
    current_mileage = starting_mileage
    mileage.append(int(current_mileage))
    
    # Calculate build-up phase
    for week in range(1, build_up_weeks):
        if current_mileage >= goal_mileage:
            break
        
        # Increase mileage by 5-7% of the previous week's mileage
        increment = float(current_mileage) * 0.065  # Using 6.5% as an average of 5-7%
        next_week_mileage = float(current_mileage) + increment
        
        # Ensure we do not exceed the goal mileage too soon
        if next_week_mileage >= goal_mileage:
            next_week_mileage = goal_mileage
        
        current_mileage = next_week_mileage
        mileage.append(int(current_mileage))
    
    # Tapering phase
    mileage[-1] = int(goal_mileage)  # Ensure the last build-up week reaches the goal mileage exactly
    mileage.append(int(float(goal_mileage) * 0.75))
    mileage.append(int(float(goal_mileage) * 0.5))
    mileage.append(int(float(goal_mileage) * 0.25))

    return mileage

# get total workouts by difficulty
def calculate_total_workouts(total_weeks, difficulty):
    if difficulty == 'easy':
        total_workouts = 0  # No speed workouts
    elif difficulty == 'moderate':
        total_workouts = ((total_weeks - 1) // 2)  # 1 speed workout every other week
    elif difficulty == 'challenging':
        total_workouts = total_weeks - 1  # 1 speed workout every week
    elif difficulty == 'difficult':
        total_workouts = (total_weeks - 1) + ((total_weeks - 1) // 2) - 1  # 1 speed workout every week, plus 2 every other week
    elif difficulty == 'intense':
        total_workouts = (total_weeks - 1) * 2  # 2 speed workouts every week
    else:
        raise ValueError("Invalid difficulty level provided.")
    
    return total_workouts

# Function to generate the speed workout order
def generate_speed_workout_order(available_workouts, total_weeks, difficulty):
    speed_workout_order = []  # List to store the final workout order
    tempo_run_interval = 3  # Insert a tempo run every 3 workouts

    total_workouts = calculate_total_workouts(total_weeks, difficulty)

    # Define thresholds for starting mile repeats and 2-mile repeats
    mile_repeat_start = int(total_workouts * 0.25)  # Mile repeats start at 25% into the plan
    two_mile_repeat_start = int(total_workouts * 0.60)  # 2-mile repeats start at 60% into the plan

    last_mile_repeat = -float('inf')  # Track the last mile repeat placement
    last_two_mile_repeat = -float('inf')  # Track the last 2-mile repeat placement
    last_interval_type = None  # Track the last interval type (400m or 800m)

    remaining_workouts = {k: len(v) for k, v in available_workouts.items()}

    def can_place_workout(workout_type, last_workout):
        """Determine if a workout can be placed based on the previous workout."""
        if not speed_workout_order:  # Always allow the first workout
            return True
        if workout_type == last_workout:  # Prevent back-to-back identical workouts
            return False
        if workout_type in ['400m_repeats', '800m_repeats'] and last_workout in ['400m_repeats', '800m_repeats']:
            return False  # Prevent back-to-back interval workouts
        if 'tempo_runs' in speed_workout_order[-2:] and workout_type in ['mile_repeats', '2_mile_repeats']:
            return False  # Prevent placing mile repeats or 2-mile repeats right after a tempo run
        if workout_type == 'tempo_runs' and any(x in speed_workout_order[-2:] for x in ['mile_repeats', '2_mile_repeats']):
            return False  # Prevent placing a tempo run after mile or 2-mile repeats
        return True

    def get_next_interval():
        """Alternate between 400m and 800m repeats, ensuring they don't occur back-to-back."""
        nonlocal last_interval_type
        print('what are our remaining workouts in next interval', remaining_workouts)
        if last_interval_type == '400m_repeats' and remaining_workouts.get('800m_repeats', 0) > 0:
            remaining_workouts['800m_repeats'] -= 1
            last_interval_type = '800m_repeats'
            return '800m_repeats'
        elif last_interval_type == '800m_repeats' and remaining_workouts.get('400m_repeats', 0) > 0:
            remaining_workouts['400m_repeats'] -= 1
            last_interval_type = '400m_repeats'
            return '400m_repeats'
        elif remaining_workouts.get('400m_repeats', 0) > 0:
            remaining_workouts['400m_repeats'] -= 1
            last_interval_type = '400m_repeats'
            return '400m_repeats'
        elif remaining_workouts.get('800m_repeats', 0) > 0:
            remaining_workouts['800m_repeats'] -= 1
            last_interval_type = '800m_repeats'
            return '800m_repeats'
        return None

    def get_next_workout():
        """Select the next available workout type other than 400m or 800m repeats."""
        possible_workouts = ['hill_repeats', '2min_fartleks']
        random.shuffle(possible_workouts)
        for workout in possible_workouts:
            if remaining_workouts.get(workout, 0) > 0:
                remaining_workouts[workout] -= 1
                return workout
        return None

    def place_tempo_run():
        """Place a tempo run, ensuring it's not overloaded at the end."""
        # if we haven't placed a workout yet
        # base case
        if len(speed_workout_order) == 0:
            speed_workout_order.append('tempo_runs')
            remaining_workouts['tempo_runs'] -= 1
            return True
        # at least 3 workouts
        elif len(speed_workout_order) > 2:
            # if previous 2 workouts weren't a tempo, place a tempo
            if (speed_workout_order[-1] != 'tempo_runs' and speed_workout_order[-2] != 'tempo_runs' and speed_workout_order[-1] not in ['2_mile_repeats', '1_mile_repeats']):
                print('placing tempo run')
                if (len(speed_workout_order) > 1):
                    print('lenght of speed workout order', len(speed_workout_order))
                    sample = speed_workout_order[-1]
                    print('speed workout order -1', sample)
                speed_workout_order.append('tempo_runs')
                remaining_workouts['tempo_runs'] -= 1
                return True

        return False

    while len(speed_workout_order) < total_workouts:
        current_position = len(speed_workout_order)
        last_workout = speed_workout_order[-1] if speed_workout_order else None
        print()
        print(f"Current position: {current_position}, Last workout: {last_workout}")
        print()
        # fulfilling tempo every 3 times
        if current_position % tempo_run_interval == 0 and remaining_workouts.get('tempo_runs', 0) > 0:
            if place_tempo_run():
                print("Placed tempo run.")
                continue
        # 2 mile repeat check
        elif current_position >= two_mile_repeat_start and remaining_workouts.get('2_mile_repeats', 0) > 0:
            print('greater than 2 mile repeat start')
            if current_position - last_two_mile_repeat >= 3 and last_workout not in ['mile_repeats', 'tempo_runs', '2_mile_repeats']:
                speed_workout_order.append('2_mile_repeats')
                last_two_mile_repeat = current_position
                remaining_workouts['2_mile_repeats'] -= 1
                print("Placed 2-mile repeat.")
                continue
        # 1 mile repeat check
        elif current_position >= mile_repeat_start and remaining_workouts.get('mile_repeats', 0) > 0:
            print('greater than 1 mile repeat start')
            if current_position - last_mile_repeat >= 3 and last_workout not in ['2_mile_repeats', 'tempo_runs']:
                speed_workout_order.append('mile_repeats')
                last_mile_repeat = current_position
                remaining_workouts['mile_repeats'] -= 1
                print("Placed mile repeat.")
                continue

        # if we had an interval last, grab a workout
        if last_workout in ['400m_repeats', '800m_repeats']:
            next_workout = get_next_workout()
        # else, grab an interval
        else:
            next_workout = get_next_interval()

        print('what is the next workout', next_workout)
        if next_workout and can_place_workout(next_workout, last_workout):
            speed_workout_order.append(next_workout)
            print(f"Placed workout: {next_workout}")
        else:
            # If we can't place a valid workout, try to relax the constraints slightly
            if not place_tempo_run():
                print("No valid workout found, breaking loop.")
                print()
                print('current order', speed_workout_order)
                print()
                print('remaining workouts', remaining_workouts)
                print()
                break

    # Place any remaining tempo runs
    while len(speed_workout_order) < total_workouts and remaining_workouts.get('tempo_runs', 0) > 0:
        if place_tempo_run():
            print("Placed remaining tempo run.")

    return speed_workout_order

###Easy: 0 speed workouts
#Moderate: 1 speed workout every other week
#Challenging: 1 speed workout every week
#Difficult: 1 speed workout every week, 2 speed workouts every other week
#Intense: 2 speed workouts a week

def generate_speed_work_schedule(total_weeks, difficulty):
    ### TO DO:
    ### Implement check to be sure that 800m repeats, or no workout, is getting stacked at the end
    ### Implement tiered-difficult -  1, 2, 3, 4, 5 - (easy, moderate, challenging, difficult, intense)
    difficulty = "intense"
    total_weeks = 18 
    speed_work_plans = {
        'easy': {},
        'moderate': {
            '400m_repeats': [6, 8, 10, 12],
            'hill_repeats': [6, 8, 10],
            '800m_repeats': [4, 6, 8, 10],
            '2min_fartleks': [6, 8, 10],
            'mile_repeats': [4],
            'tempo_runs': [4, 5, 6, 7]
        },
        'challenging': {
            '400m_repeats': [6, 8, 10, 12],
            'hill_repeats': [6, 8, 10],
            '800m_repeats': [4, 6, 8, 10],
            '2min_fartleks': [6, 8, 10],
            'mile_repeats': [4],
            'tempo_runs': [4, 5, 6, 7],
            '2_mile_repeats': [3]
        },
        'difficult': {
            '400m_repeats': [6, 8, 10, 12, 14, 16, 18, 20],
            'hill_repeats': [6, 8, 10],
            '800m_repeats': [4, 6, 8, 10],
            '2min_fartleks': [6, 8, 10, 12, 14],
            'mile_repeats': [4],
            'tempo_runs': [4, 5, 6, 7, 8, 9, 10],
            '2_mile_repeats': [3, 3]
        },
        'intense': {
            '400m_repeats': [6, 8, 10, 12, 14, 16, 18, 20],
            'hill_repeats': [6, 8, 10],
            '800m_repeats': [4, 6, 8, 10, 12],
            '2min_fartleks': [6, 8, 10, 12],
            'mile_repeats': [4, 4],
            'tempo_runs': [4, 5, 6, 7, 8, 9, 10, 11, 12, 13],
            '2_mile_repeats': [3, 3]
        }
    }

    if difficulty not in speed_work_plans:
        raise ValueError("Invalid difficulty level")

    # Get the available workouts for the given difficulty
    available_workouts = speed_work_plans[difficulty]

    # Generate the speed workout order
    speed_workout_order = generate_speed_workout_order(available_workouts, total_weeks, difficulty)
    print(f"Generated speed workout order: {speed_workout_order}")

    # Initialize the final speed work schedule list
    speed_work_schedule = []


    # Iterate over the workout order and pop the interval/distance from available_workouts
    for workout_type in speed_workout_order:
        if workout_type in available_workouts and available_workouts[workout_type]:
            repeats = available_workouts[workout_type].pop(0)
            speed_work_schedule.append((workout_type, repeats))

    return speed_work_schedule


def schedule_long_runs(starting_long_run, max_long_run, taper_weeks, total_weeks, race_type):
    """
    Schedule long runs backwards from the taper point to the starting week.
    """
    if race_type.lower() == 'marathon':
        taper_distances = [0, 10, 14]  # Last 3 weeks: 14, 10, race day (0 represents race day)
        taper_weeks = 3  # Adjust taper weeks to fit the custom taper distances
    else:
        taper_distances = [int(max_long_run - (i * (max_long_run - starting_long_run) / taper_weeks)) for i in range(taper_weeks)]

    long_runs = taper_distances[::-1]

    # Calculate the number of build-up weeks (excluding taper weeks)
    build_up_weeks = total_weeks - len(taper_distances)

    # Calculate the increment for each week during the build-up phase
    increment = (max_long_run - starting_long_run) / build_up_weeks

    # Fill in the long runs for the build-up phase
    for i in range(build_up_weeks - 1, -1, -1):
        long_runs.insert(0, int(starting_long_run + i * increment))

    print('what is long runs at end of schedule function', long_runs)
    return long_runs


def plan_weekly_sessions(runner, weekly_mileage, long_runs, long_run_day_str, speed_work_days, available_days, difficulty='medium'):
    """
    Plan weekly training sessions including long runs, speed work, easy runs, and rest days.
    """
    day_name_to_int = {
        'Monday': 0,
        'Tuesday': 1,
        'Wednesday': 2,
        'Thursday': 3,
        'Friday': 4,
        'Saturday': 5,
        'Sunday': 6,
    }

    long_run_day = day_name_to_int[long_run_day_str]
    sessions = []
    total_weeks = len(weekly_mileage)

    speed_workout_schedule = []
    if difficulty == 'medium':
        speed_workout_schedule = ['400m_repeats', '800m_repeats', 'tempo_runs', 'mile_repeats']
        speed_workout_schedule = speed_workout_schedule * ((total_weeks // 4) + 1)
        speed_workout_schedule = speed_workout_schedule[:total_weeks - 1]
    elif difficulty == 'hard':
        speed_workout_schedule = ['400m_repeats', '800m_repeats', 'tempo_runs', 'mile_repeats', '400m_repeats']
        speed_workout_schedule = speed_workout_schedule * (((total_weeks * 2) // 6) + 1)
        speed_workout_schedule = speed_workout_schedule[:(total_weeks - 1) * 2]

    max_speed_work_week = total_weeks - 2
    last_speed_workout_date = runner.race_date - timedelta(days=10)
    max_speed_work_week = min(max_speed_work_week, (last_speed_workout_date - date.today()).days // 7)


    schedule = generate_speed_work_schedule(total_weeks, difficulty)
    for week, (workout, repeats) in enumerate(schedule):
        print(f"Workout {week + 1}: {repeats}x {workout.replace('_', ' ')}")

    exit()

    speed_workout_index = 0
    workout_count = {
        '400m_repeats': 0,
        '800m_repeats': 0,
        'tempo_runs': 0,
        'mile_repeats': 0
    }

    for week in range(total_weeks):
        week_sessions = []

        if week > max_speed_work_week:
            remaining_days = available_days - 2 if available_days > 3 else available_days - 1
            long_run_miles = long_runs[week]
            remaining_miles = weekly_mileage[week] - long_run_miles - 4
            easy_run_distance = remaining_miles / remaining_days if remaining_days > 0 else 0
            easy_run_distance = round_to_nearest_half_or_whole(easy_run_distance)
            for day in range(7):
                if day == long_run_day:
                    week_sessions.append({
                        'type': 'Long Run',
                        'distance': long_run_miles,
                        'day': day
                    })
                elif day == (long_run_day + 1) % 7:
                    week_sessions.append({
                        'type': 'Recovery Run',
                        'distance': 4,
                        'day': day
                    })
                else:
                    week_sessions.append({
                        'type': 'Easy Run',
                        'distance': easy_run_distance,
                        'day': day
                    })
            sessions.append(week_sessions)
            continue

        weekly_miles = weekly_mileage[week]
        long_run_miles = long_runs[week]
        remaining_miles = weekly_miles - long_run_miles - 4  # 4 miles for recovery run
        remaining_days = available_days - 2 if available_days > 3 else available_days - 1

        if difficulty == 'easy':
            easy_run_days = max(1, remaining_days - 1)
            speed_work_day_count = min(len(speed_work_days), remaining_days - easy_run_days)
        elif difficulty == 'medium':
            if available_days == 3:
                easy_run_days = 1
                remaining_days = remaining_days - 1
            elif available_days > 4:
                easy_run_days = 3
                remaining_days = remaining_days - 3
            speed_work_day_count = remaining_days
        elif difficulty == 'hard':
            easy_run_days = max(1, remaining_days - 3)
            speed_work_day_count = min(len(speed_work_days), remaining_days - easy_run_days)
        else:
            raise ValueError("Invalid difficulty level. Choose 'easy', 'medium', or 'hard'.")

        if available_days == 3:
            if difficulty == 'hard':
                easy_run_days = 1
                speed_work_day_count = 2
            elif difficulty == 'medium':
                easy_run_days = 1
                speed_work_day_count = 1
            elif difficulty == 'easy':
                easy_run_days = 2
                speed_work_day_count = 0
        elif available_days == 4:
            if difficulty == 'hard':
                easy_run_days = 1
                speed_work_day_count = 2
            elif difficulty == 'medium':
                easy_run_days = 1
                speed_work_day_count = 1
            elif difficulty == 'easy':
                easy_run_days = 3
                speed_work_day_count = 0
        elif available_days == 5:
            if difficulty == 'hard':
                easy_run_days = 1
                speed_work_day_count = 2
            elif difficulty == 'medium':
                easy_run_days = 2
                speed_work_day_count = 1
            elif difficulty == 'easy':
                easy_run_days = 3
                speed_work_day_count = 0
        elif available_days == 6:
            if difficulty == 'hard':
                easy_run_days = 2
                speed_work_day_count = 2
            elif difficulty == 'medium':
                easy_run_days = 3
                speed_work_day_count = 1
            elif difficulty == 'easy':
                easy_run_days = 4
                speed_work_day_count = 0
        elif available_days == 7:
            if difficulty == 'hard':
                easy_run_days = 3
                speed_work_day_count = 2
            elif difficulty == 'medium':
                easy_run_days = 3
                speed_work_day_count = 1
            elif difficulty == 'easy':
                easy_run_days = 5
                speed_work_day_count = 0

        if difficulty == 'hard':
            speed_work_miles = remaining_miles * 0.45
            easy_run_miles = remaining_miles - speed_work_miles
        elif difficulty == 'medium':
            speed_work_miles = (remaining_miles * 0.45) / 2
            easy_run_miles = remaining_miles - speed_work_miles
        else:
            speed_work_miles = 0
            easy_run_miles = remaining_miles

        speed_work_distance = speed_work_miles / speed_work_day_count if speed_work_day_count > 0 else 0
        speed_work_distance = round_to_nearest_half_or_whole(speed_work_distance)

        easy_run_distance = easy_run_miles / easy_run_days if easy_run_days > 0 else 0
        easy_run_distance = round_to_nearest_half_or_whole(easy_run_distance)

        recovery_miles = weekly_mileage[week] - long_run_miles - speed_work_miles - easy_run_miles

        rest_days = []
        if available_days < 6:
            rest_days.append((long_run_day - 1) % 7)
            if available_days < 5:
                rest_days.append((rest_days[0] - 3) % 7)
        day_schedule = ['Rest Day' if i in rest_days else None for i in range(7)]
        if available_days > 3:
            if difficulty == "medium" or difficulty == "easy":
                day_schedule[long_run_day] = 'Long Run'
                day_schedule[(long_run_day + 1) % 7] = "Recovery Run"
            else:
                day_schedule[long_run_day] = 'Long Run'
        else:
            day_schedule[long_run_day] = 'Long Run'
            if available_days == 7:
                if difficulty == "hard":
                    day_schedule[long_run_day - 1] = 'Easy Run'
                else:
                    day_schedule[long_run_day - 1] = 'Recovery Run'
            if difficulty == "hard" and available_days == 7:
                day_schedule[long_run_day - 1] = 'Easy Run'

        for day in range(7):
            if day_schedule[day] is None:
                if available_days < 6 and difficulty == 'hard':
                    if day_schedule[day - 1] == 'Recovery Run':
                        day_schedule[day] = 'Rest Day'
                    elif speed_work_day_count > 0 and day_schedule[day - 1] == 'Rest Day':
                        day_schedule[day] = 'Speed Work'
                        speed_work_day_count -= 1
                    elif easy_run_days > 0:
                        day_schedule[day] = 'Easy Run'
                        easy_run_days -= 1
                    else:
                        day_schedule[day] = 'Speed Work'
                        speed_work_day_count -= 1
                elif available_days < 6:
                    if day_schedule[day - 1] == 'Recovery Run':
                        day_schedule[day] = 'Rest Day'
                    elif speed_work_day_count > 0 and day_schedule[day - 1] == 'Easy Run':
                        day_schedule[day] = 'Speed Work'
                        speed_work_day_count -= 1
                    elif easy_run_days > 0:
                        day_schedule[day] = 'Easy Run'
                        easy_run_days -= 1
                    else:
                        day_schedule[day] = 'Speed Work'
                        speed_work_day_count -= 1
                else:
                    if day_schedule[day - 1] == 'Recovery Run':
                        day_schedule[day] = 'Easy Run'
                        easy_run_days -= 1
                    elif day_schedule[day - 1] == 'Easy Run' and speed_work_day_count > 0 and difficulty == 'hard':
                        day_schedule[day] = 'Speed Work'
                        speed_work_day_count -= 1
                    elif day_schedule[day - 1] == 'Speed Work' and easy_run_days > 0:
                        day_schedule[day] = 'Easy Run'
                        easy_run_days -= 1
                    elif day_schedule[day - 1] == 'Easy Run' and day_schedule[day - 2] == 'Easy Run' and speed_work_day_count > 0 and difficulty == 'medium':
                        day_schedule[day] = 'Speed Work'
                        speed_work_day_count -= 1
                    elif day_schedule[day - 1] == "Long Run" and available_days == 6:
                        day_schedule[day] = 'Recovery Run'
                    elif day_schedule[day + 1] == "Long Run" and available_days == 6:
                        day_schedule[day] = 'Rest Day'
                    else:
                        day_schedule[day] = 'Easy Run'
                        easy_run_days -= 1

        for day in range(7):
            if day_schedule[day] == 'Rest Day':
                session_type = 'Rest Day'
                session_distance = 0
            elif day_schedule[day] == 'Long Run':
                session_type = 'Long Run'
                session_distance = long_run_miles
            elif day_schedule[day] == 'Recovery Run':
                session_type = 'Recovery Run'
                session_distance = recovery_miles
            elif day_schedule[day] == 'Speed Work':
                speed_workout = speed_workout_schedule[speed_workout_index]
                repeats = speed_work_plans[speed_workout][min(week // (total_weeks // len(speed_work_plans[speed_workout])), len(speed_work_plans[speed_workout]) - 1)]
                workout_details, warm_up_cool_down_distance = get_speed_workout_details(speed_workout, repeats, speed_work_distance, difficulty)
                session_type = f'Speed Work: {workout_details}'
                session_distance = speed_work_distance
                remaining_miles -= session_distance
                easy_run_miles = remaining_miles
                easy_run_distance = easy_run_miles / easy_run_days if easy_run_days > 0 else 0
                easy_run_distance = round_to_nearest_half_or_whole(easy_run_distance)
                speed_workout_index += 1
                if speed_workout_index >= len(speed_workout_schedule):
                    speed_workout_index = 0  # Reset index if it goes out of range
            elif day_schedule[day] == 'Easy Run':
                session_type = 'Easy Run'
                session_distance = easy_run_distance
            else:
                continue
            week_sessions.append({
                'type': session_type,
                'distance': session_distance,
                'day': day
            })
        sessions.append(week_sessions)
    return sessions

def get_speed_workout_details(workout_type, repeats, speed_work_distance, difficulty):
    """
    Generate detailed speed workout description including warm-up, repeats, recovery, and cool-down.
    """
    if workout_type == '400m_repeats':
        recovery_distance = 0.25 if difficulty == "medium" else 0.125  # 400m for medium, 200m for hard
        repeat_distance = 0.25  # 400m
    elif workout_type == '800m_repeats':
        recovery_distance = 0.25  # 400m
        repeat_distance = 0.5  # 800m
    elif workout_type == 'mile_repeats':
        repeat_distance = 1  # 1 mile
        warm_up_cool_down_distance = (speed_work_distance - (repeats * repeat_distance)) / 2
        return f"{repeats}x1 mile Repeats with 3-4 minute standing recovery, {round(warm_up_cool_down_distance, 2)} mile Warm-up and Cool-down", warm_up_cool_down_distance
    elif workout_type == 'tempo_runs':
        total_distance = repeats  # In miles
        warm_up_cool_down_distance = (speed_work_distance - total_distance) / 2
        return f"{repeats} mile Tempo Run with {round(warm_up_cool_down_distance, 2)} mile Warm-up and Cool-down", warm_up_cool_down_distance
    elif workout_type == '3x2_mile_repeats':
        return "3x2 Mile Repeats with 1 mile Recovery", 0

    total_repeats_distance = repeats * repeat_distance
    total_recovery_distance = repeats * recovery_distance
    warm_up_cool_down_distance = (speed_work_distance - total_repeats_distance - total_recovery_distance) / 2

    return f"{repeats}x{int(repeat_distance * 1600)}m Repeats with {int(recovery_distance * 1600)}m Recovery, " \
           f"{round(warm_up_cool_down_distance, 2)} mile Warm-up and Cool-down", warm_up_cool_down_distance

def round_to_nearest_half_or_whole(number):
    rounded = round(number * 2) / 2
    if rounded.is_integer():
        return int(rounded)
    return rounded




def generate_marathon_plan(id):
    """
    Generate a marathon training plan for a specific runner.
    """
    try:
        runner = Runner.objects.get(id=id)
        print(f"Runner found: {runner.first_name} {runner.last_name}")
    except Runner.DoesNotExist:
        print(f"Runner with ID {id} does not exist.")
        return
    try:
        preferences = TrainingPreference.objects.get(runner=runner)
        print(f"Training preferences found for runner {runner.first_name} {runner.last_name}")
    except TrainingPreference.DoesNotExist:
        print(f"Training preferences for runner {runner.first_name} {runner.last_name} do not exist.")
        return
    
    start_date = date.today()
    end_date = runner.race_date
    total_weeks = (end_date - start_date).days // 7
    # print('OUR TOTAL WEEKS', total_weeks)
    # print('RUNNER EMAIL', runner.email)
    # print('WHAT IS MAX WEEKLY MILEAGE', runner.max_weekly_mileage)

    weekly_mileage = calculate_weekly_mileage(
        starting_mileage=runner.current_weekly_mileage,
        goal_mileage=runner.max_weekly_mileage,
        weeks=total_weeks
    )
    # print('what is our weekly mileage in generator', weekly_mileage)
    # print('length:', len(weekly_mileage))

    long_runs = schedule_long_runs(
        starting_long_run=runner.longest_run_last_4_weeks,
        max_long_run=22,
        taper_weeks=3,
        total_weeks=total_weeks,
        race_type=runner.race_type
    )
    print('what are our long runs in generator', long_runs)

    sessions = plan_weekly_sessions(
        runner=runner,
        weekly_mileage=weekly_mileage,
        long_runs=long_runs,
        long_run_day_str=runner.longest_run_day,  # Pass the string day name
        speed_work_days=[1, 3],  # Assume speed work days are Tuesday and Thursday
        available_days=runner.willing_running_days_per_week
    )

    training_plan = TrainingPlan.objects.create(
        runner=runner,
        start_date=start_date,
        end_date=end_date,
        distance=runner.max_weekly_mileage,
        race_name=runner.race_name
    )

    for week in range(total_weeks):
        print('WEEK', week)
        print()
        for session in sessions[week]:
            print('session:', session)
            session_date = start_date + timedelta(days=(week * 7) + session['day'])
            TrainingSession.objects.create(
                plan=training_plan,
                date=session_date,
                distance=session['distance'],
                duration=timedelta(hours=session['distance'] / 6),  # Assume average pace of 6 mph
                description=f"{session['type']} run",
                type=session['type']
            )

if __name__ == "__main__":
    ### KEEP UNCOMMENTED UNLESS YOU WANT TO REMOVE ALL TRAINING PLANS - SHOULD NOT EXIST UPON DEPLOYMENT
    ######clear_training_plans()
    ######clear_all_sessions()
    id = 3  # Replace with the actual runner ID you want to generate the plan for
    generate_marathon_plan(id)
