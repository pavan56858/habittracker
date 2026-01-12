"""
Habit management and Excel-style calculations
"""

import uuid
from datetime import datetime
from calendar import monthrange
from backend.database import (
    add_habit, get_user_habits, find_habit, update_habit, 
    delete_habit, get_habit_logs, upsert_log
)

def create_habit(user_id, habit_name):
    """Create a new habit"""
    # Validate name length (max 25 characters)
    if not habit_name or len(habit_name) > 25:
        return None, 'Habit name must be 1-25 characters'
    
    # Check for duplicate names
    existing_habits = get_user_habits(user_id)
    if any(h['name'].lower() == habit_name.lower() for h in existing_habits):
        return None, 'Habit name already exists'
    
    habit = {
        'id': str(uuid.uuid4()),
        'user_id': user_id,
        'name': habit_name.strip(),
        'created_at': datetime.utcnow().isoformat()
    }
    
    return add_habit(habit), None

def update_habit_name(habit_id, user_id, new_name):
    """Update habit name"""
    if not new_name or len(new_name) > 25:
        return None, 'Habit name must be 1-25 characters'
    
    habit = find_habit(habit_id)
    if not habit or habit['user_id'] != user_id:
        return None, 'Habit not found'
    
    # Check for duplicate names
    existing_habits = get_user_habits(user_id)
    if any(h['name'].lower() == new_name.lower() and h['id'] != habit_id 
           for h in existing_habits):
        return None, 'Habit name already exists'
    
    updated = update_habit(habit_id, {'name': new_name.strip()})
    return updated, None

def delete_user_habit(habit_id, user_id):
    """Delete a habit and its logs"""
    habit = find_habit(habit_id)
    if not habit or habit['user_id'] != user_id:
        return False, 'Habit not found'
    
    delete_habit(habit_id)
    return True, None

def get_habits_with_calculations(user_id, year, month):
    """
    Get all habits with calculated Total and % Complete
    This replicates the Excel sheet behavior
    """
    habits = get_user_habits(user_id)
    days_in_month = monthrange(year, month)[1]
    
    result = []
    for habit in habits:
        logs = get_habit_logs(habit['id'], year, month)
        
        # Create a day-by-day completion map
        completion_map = {}
        for log in logs:
            day = int(log['date'].split('-')[2])
            completion_map[day] = log['completed']
        
        # Build days array (1-31, with 0 or 1 values)
        days = []
        for day in range(1, 32):
            if day <= days_in_month:
                days.append(completion_map.get(day, 0))
            else:
                days.append(None)  # Days that don't exist in this month
        
        # Calculate Total (sum of completed days)
        total = sum(completion_map.values())
        
        # Calculate % Complete
        percent_complete = (total / days_in_month * 100) if days_in_month > 0 else 0
        
        result.append({
            'id': habit['id'],
            'name': habit['name'],
            'days': days,  # Array of 31 elements
            'total': total,  # Calculated, not stored
            'percent_complete': round(percent_complete, 1)  # Calculated, not stored
        })
    
    return result

def toggle_day_completion(user_id, habit_id, date, completed):
    """
    Toggle completion status for a specific day
    This is the core auto-update logic
    """
    habit = find_habit(habit_id)
    if not habit or habit['user_id'] != user_id:
        return None, 'Habit not found'
    
    # Validate completed value (must be 0 or 1)
    if completed not in [0, 1]:
        return None, 'Completed value must be 0 or 1'
    
    # Update log
    log = upsert_log(user_id, habit_id, date, completed)
    return log, None