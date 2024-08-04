import math
import os
import sys
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

###Easy: 0 speed workouts
#Moderate: 1 speed workout every other week
#Challenging: 1 speed workout every week
#Difficult: 1 speed workout every week, 2 speed workouts every other week
#Intense: 2 speed workouts a week

def generate_speed_work_schedule(total_weeks, difficulty):
    ### TO DO:
    ### Implement check to be sure that 800m repeats, or no workout, is getting stacked at the end
    ### Implement tiered-difficult -  1, 2, 3, 4, 5 - (easy, moderate, challenging, difficult, intense)
    difficulty = "hard"
    total_weeks = 18
    speed_work_plans = {
        'medium': {
            '400m_repeats': [6, 8, 10, 12, 14, 16],
            '800m_repeats': [4, 6, 8, 10],
            'mile_repeats': [4],
            'tempo_runs': [4, 5, 6, 7],
            '200m_-_300m_hill_repeats': [4, 6, 8],
            '2min_fartleks': [6, 8, 10]
        },
        'hard': {
            '400m_repeats': [8, 10, 12, 14, 16, 18, 20],
            '800m_repeats': [4, 6, 8, 10, 12],
            'mile_repeats': [4, 4],
            'tempo_runs': [3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13],
            '2_mile_repeats': [3, 3],
            '300m_-_400m_hill_repeats': [6, 8, 10],
            '2min_fartleks': [6, 8, 10, 12]
        }
    }

    speed_work_schedule = []
    if difficulty == 'medium':
        num_speed_workouts = total_weeks - 1
        speed_workout_order = ['400m_repeats', '200m_-_300m_hill_repeats', 'tempo_runs', '800m_repeats', '2min_fartleks']
        speed_workout_plans = speed_work_plans['medium']
        max_mile_repeats = 1
    elif difficulty == 'hard':
        print('hard difficulty')
        num_speed_workouts = (total_weeks - 1) * 2
        speed_workout_order = ['400m_repeats', '300m_-_400m_hill_repeats', 'tempo_runs', '800m_repeats', '2min_fartleks']
        speed_workout_plans = speed_work_plans['hard']
        max_mile_repeats = 2
    
    # Ensuring at least one mile repeats for medium and two for hard
    mile_repeat_count = 0
    two_mile_repeat_count = 0
    last_3x2_mile_index = -5

    i = 0

    while i < num_speed_workouts:
        workout_type = None
        # if we are over 60% of the way through the plan, with hard difficulty, and already have max'd out mile repeats allowed
        if difficulty == 'hard' and two_mile_repeat_count < 2 and i - last_3x2_mile_index >= 5 and i > (num_speed_workouts * 0.6) and mile_repeat_count == max_mile_repeats:
            # get distance from last 3x2 mile repeat - need to make sure distance is at least 5 workouts from last 3x2 mile
            # if the previous run wasn't mile repeats or tempo or 3x2, schedule a 3x2 workout
            if speed_work_schedule[len(speed_work_schedule) - 1][0] != 'mile_repeats' and speed_work_schedule[len(speed_work_schedule) - 1][0] != 'tempo_runs':
                workout_type = '2_mile_repeats'
                two_mile_repeat_count += 1
                last_3x2_mile_index = i
        # if we have mile repeats left and are over 25% of the way through the plan and haven't chosen 2x3 mile repeats in previous if block
        if mile_repeat_count < max_mile_repeats and (i % 4 == 3) and workout_type == None:
            workout_type = 'mile_repeats'
            mile_repeat_count += 1
            print('week', i)
            print('mile repeats')
        # else, we will grab the order of speed workouts, 400m, 800m, tempo, hill repeats, fartlek
        elif workout_type == None:
            if (len(speed_work_schedule) > 2):
                # if the previous run wasn't a tempo run, assign tempo
                if speed_work_schedule[i - 1][0] != "tempo_runs" and speed_work_schedule[i - 2][0] != "tempo_runs":
                    workout_type = "tempo_runs"
                # else, check the value if it's tempo, if it is, add one
                elif (speed_workout_order[i % len(speed_workout_order)] == "tempo_runs"):
                    # list indexing check over and underflow
                    sample = i % len(speed_workout_order)
                    if (i % len(speed_workout_order) == 0):
                        workout_type = speed_workout_order[(i % len(speed_workout_order)) + 1]
                    else:
                        workout_type = speed_workout_order[(i % len(speed_workout_order)) - 1]
                # default to whatever order is
                else:
                    # check for previous workout being the same , avoid repeats
                    workout_type = speed_workout_order[i % len(speed_workout_order)]
            else:
                workout_type = speed_workout_order[i % len(speed_workout_order)]

        # get amount of repeats and append it to the schedule
        print('what is the workout type', workout_type)
        print('speed workout plans', speed_workout_plans)
        repeats = speed_workout_plans[workout_type].pop(0)
        speed_work_schedule.append((workout_type, repeats))

        # check if no workouts left for type to remove empty workouts so we don't query again in the future
        if speed_workout_plans[workout_type] == []:
            del speed_work_plans[difficulty][workout_type]
            if workout_type in speed_workout_order:
                speed_workout_order.remove(workout_type)
        
        i += 1

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

    if (difficulty == "medium"):
        speed_work_plans = {
            '400m_repeats': [6, 8, 10, 12, 14, 16],
            '800m_repeats': [4, 6, 8, 10],
            'mile_repeats': [4],
            'tempo_runs': [4, 5, 6, 7],
        }
    elif (difficulty == "hard"):
        speed_work_plans = {
            '400m_repeats': [8, 10, 12, 14, 16, 18],
            '800m_repeats': [4, 6, 8, 10, 12],
            'mile_repeats': [4],
            'tempo_runs': [4, 5, 6, 7, 8, 9, 10, 11, 12, 13],
            '3x2_mile_repeats': [6]
        }

    schedule = generate_speed_work_schedule(total_weeks, difficulty)
    for week, (workout, repeats) in enumerate(schedule):
        print(f"Week {week + 1}: {repeats}x {workout.replace('_', ' ')}")

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
