"""
Thread-safe JSON file database operations
"""

import json
import os
from threading import Lock
from datetime import datetime

# Thread locks for file safety
users_lock = Lock()
habits_lock = Lock()
logs_lock = Lock()

DATA_DIR = 'data'
USERS_FILE = os.path.join(DATA_DIR, 'users.json')
HABITS_FILE = os.path.join(DATA_DIR, 'habits.json')
LOGS_FILE = os.path.join(DATA_DIR, 'daily_logs.json')

def init_db():
    """Initialize database files if they don't exist"""
    os.makedirs(DATA_DIR, exist_ok=True)
    
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'w') as f:
            json.dump([], f)
    
    if not os.path.exists(HABITS_FILE):
        with open(HABITS_FILE, 'w') as f:
            json.dump([], f)
    
    if not os.path.exists(LOGS_FILE):
        with open(LOGS_FILE, 'w') as f:
            json.dump([], f)

def read_json(filepath, lock):
    """Thread-safe read from JSON file"""
    with lock:
        try:
            with open(filepath, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return []

def write_json(filepath, data, lock):
    """Thread-safe write to JSON file"""
    with lock:
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)

# User operations
def get_users():
    return read_json(USERS_FILE, users_lock)

def save_users(users):
    write_json(USERS_FILE, users, users_lock)

def add_user(user):
    users = get_users()
    users.append(user)
    save_users(users)
    return user

def find_user_by_email(email):
    users = get_users()
    return next((u for u in users if u['email'] == email), None)

def find_user_by_id(user_id):
    users = get_users()
    return next((u for u in users if u['id'] == user_id), None)

# Habit operations
def get_habits():
    return read_json(HABITS_FILE, habits_lock)

def save_habits(habits):
    write_json(HABITS_FILE, habits, habits_lock)

def add_habit(habit):
    habits = get_habits()
    habits.append(habit)
    save_habits(habits)
    return habit

def get_user_habits(user_id):
    habits = get_habits()
    return [h for h in habits if h['user_id'] == user_id]

def find_habit(habit_id):
    habits = get_habits()
    return next((h for h in habits if h['id'] == habit_id), None)

def update_habit(habit_id, updates):
    habits = get_habits()
    for h in habits:
        if h['id'] == habit_id:
            h.update(updates)
            save_habits(habits)
            return h
    return None

def delete_habit(habit_id):
    habits = get_habits()
    habits = [h for h in habits if h['id'] != habit_id]
    save_habits(habits)
    
    # Also delete associated logs
    logs = get_daily_logs()
    logs = [l for l in logs if l['habit_id'] != habit_id]
    save_daily_logs(logs)

# Daily log operations
def get_daily_logs():
    return read_json(LOGS_FILE, logs_lock)

def save_daily_logs(logs):
    write_json(LOGS_FILE, logs, logs_lock)

def get_user_logs(user_id, year, month):
    """Get logs for a specific user and month"""
    logs = get_daily_logs()
    return [
        l for l in logs 
        if l['user_id'] == user_id 
        and l['date'].startswith(f"{year}-{month:02d}")
    ]

def get_habit_logs(habit_id, year, month):
    """Get logs for a specific habit and month"""
    logs = get_daily_logs()
    return [
        l for l in logs 
        if l['habit_id'] == habit_id 
        and l['date'].startswith(f"{year}-{month:02d}")
    ]

def find_log(user_id, habit_id, date):
    """Find a specific log entry"""
    logs = get_daily_logs()
    return next((
        l for l in logs 
        if l['user_id'] == user_id 
        and l['habit_id'] == habit_id 
        and l['date'] == date
    ), None)

def upsert_log(user_id, habit_id, date, completed):
    """Insert or update a daily log entry"""
    logs = get_daily_logs()
    
    # Find existing log
    existing = None
    for i, l in enumerate(logs):
        if (l['user_id'] == user_id and 
            l['habit_id'] == habit_id and 
            l['date'] == date):
            existing = i
            break
    
    log_entry = {
        'user_id': user_id,
        'habit_id': habit_id,
        'date': date,
        'completed': completed,
        'updated_at': datetime.utcnow().isoformat()
    }
    
    if existing is not None:
        logs[existing] = log_entry
    else:
        logs.append(log_entry)
    
    save_daily_logs(logs)
    return log_entry