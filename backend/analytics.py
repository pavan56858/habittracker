"""
Dashboard analytics - Excel Dashboard sheet replication
All metrics are calculated dynamically, NEVER stored
"""

from calendar import monthrange
from backend.habits import get_habits_with_calculations
from backend.database import get_user_habits

def calculate_dashboard_metrics(user_id, year, month):
    """
    Calculate all Dashboard metrics
    Replicates the Excel "Dashboard" sheet behavior
    """
    habits_data = get_habits_with_calculations(user_id, year, month)
    days_in_month = monthrange(year, month)[1]
    
    if not habits_data:
        return {
            'total_habits': 0,
            'overall_completion_percent': 0,
            'best_habit': None,
            'worst_habit': None,
            'habit_summaries': []
        }
    
    # 1. Total Number of Habits
    total_habits = len(habits_data)
    
    # 2. Overall Completion Percentage
    total_completed_days = sum(h['total'] for h in habits_data)
    total_possible_days = total_habits * days_in_month
    overall_completion = (total_completed_days / total_possible_days * 100) if total_possible_days > 0 else 0
    
    # 3. Best Performing Habit
    best_habit = max(habits_data, key=lambda h: h['percent_complete'])
    
    # 4. Worst Performing Habit
    worst_habit = min(habits_data, key=lambda h: h['percent_complete'])
    
    # 5. Habit-wise Progress Summary
    habit_summaries = [
        {
            'name': h['name'],
            'total': h['total'],
            'percent_complete': h['percent_complete']
        }
        for h in sorted(habits_data, key=lambda h: h['percent_complete'], reverse=True)
    ]
    
    return {
        'total_habits': total_habits,
        'overall_completion_percent': round(overall_completion, 1),
        'best_habit': {
            'name': best_habit['name'],
            'percent_complete': best_habit['percent_complete']
        },
        'worst_habit': {
            'name': worst_habit['name'],
            'percent_complete': worst_habit['percent_complete']
        },
        'habit_summaries': habit_summaries,
        'days_in_month': days_in_month,
        'total_completed_days': total_completed_days,
        'total_possible_days': total_possible_days
    }

def get_monthly_trend(user_id, year, months):
    """Get completion trends over multiple months"""
    trends = []
    for month in months:
        habits_data = get_habits_with_calculations(user_id, year, month)
        days_in_month = monthrange(year, month)[1]
        
        if habits_data:
            total_completed = sum(h['total'] for h in habits_data)
            total_possible = len(habits_data) * days_in_month
            completion = (total_completed / total_possible * 100) if total_possible > 0 else 0
        else:
            completion = 0
        
        trends.append({
            'month': month,
            'completion_percent': round(completion, 1)
        })
    
    return trends