from flask import Flask, render_template, request, redirect, session, url_for, jsonify, send_file
import json
import os
from datetime import date, timedelta, datetime
from collections import defaultdict
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import calendar

app = Flask(__name__)
app.secret_key = "task_tracker_secret_2024"

USERS_FILE = "users.json"
HABITS_FILE = "habits.json"
PROGRESS_FILE = "progress.json"
CHART_DIR = "static/charts"

os.makedirs(CHART_DIR, exist_ok=True)
os.makedirs("templates", exist_ok=True)
os.makedirs("static/css", exist_ok=True)

# ------------------ Helpers ------------------

def load_json(file):
    if not os.path.exists(file):
        return {}
    with open(file, "r") as f:
        return json.load(f)

def save_json(file, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=4)

def login_required():
    return "user" in session

def get_current_month():
    return date.today().strftime("%Y-%m")

def get_month_dates(year_month):
    year, month = map(int, year_month.split("-"))
    num_days = calendar.monthrange(year, month)[1]
    return [f"{year_month}-{str(day).zfill(2)}" for day in range(1, num_days + 1)]

def get_month_name(year_month):
    year, month = map(int, year_month.split("-"))
    return f"{calendar.month_name[month]} {year}"

# ------------------ Auth ------------------

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        users = load_json(USERS_FILE)
        username = request.form["username"]
        password = request.form["password"]

        if username in users and users[username]["password"] == password:
            session["user"] = username
            return redirect("/dashboard")
        return render_template("login.html", error="Invalid credentials")

    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        users = load_json(USERS_FILE)
        username = request.form["username"]
        password = request.form["password"]

        if username in users:
            return render_template("register.html", error="User already exists")

        users[username] = {
            "password": password,
            "created_on": str(date.today())
        }
        save_json(USERS_FILE, users)
        return redirect("/")

    return render_template("register.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# ------------------ Dashboard ------------------

@app.route("/dashboard")
def dashboard():
    if not login_required():
        return redirect("/")
    
    user = session["user"]
    current_month = get_current_month()
    today = str(date.today())
    
    # Get user's habits for current month
    habits_data = load_json(HABITS_FILE)
    user_habits = habits_data.get(user, {}).get(current_month, [])
    
    # Get today's progress
    progress_data = load_json(PROGRESS_FILE)
    today_progress = progress_data.get(user, {}).get(today, {})
    
    completed = sum(today_progress.values())
    total = len(user_habits)
    
    # Calculate streak
    streak = calculate_streak(user)
    
    return render_template(
        "dashboard.html", 
        habits_count=len(user_habits),
        completed_today=completed,
        total_today=total,
        streak=streak,
        month_name=get_month_name(current_month)
    )

def calculate_streak(user):
    progress_data = load_json(PROGRESS_FILE)
    user_progress = progress_data.get(user, {})
    
    current = date.today()
    streak = 0
    
    while True:
        date_str = str(current)
        if date_str in user_progress:
            day_tasks = user_progress[date_str]
            if day_tasks and all(day_tasks.values()):
                streak += 1
                current -= timedelta(days=1)
            else:
                break
        else:
            break
    
    return streak

# ------------------ Habits Management ------------------

@app.route("/habits", methods=["GET", "POST"])
def habits():
    if not login_required():
        return redirect("/")
    
    user = session["user"]
    current_month = get_current_month()
    habits_data = load_json(HABITS_FILE)
    
    habits_data.setdefault(user, {})
    habits_data[user].setdefault(current_month, [])
    
    if request.method == "POST":
        action = request.form.get("action")
        
        if action == "add":
            habit_name = request.form.get("habit_name", "").strip()
            if habit_name and habit_name not in habits_data[user][current_month]:
                habits_data[user][current_month].append(habit_name)
                save_json(HABITS_FILE, habits_data)
        
        elif action == "edit":
            old_habit_name = request.form.get("habit_name")
            new_habit_name = request.form.get("new_habit_name", "").strip()
            if old_habit_name in habits_data[user][current_month] and new_habit_name:
                idx = habits_data[user][current_month].index(old_habit_name)
                habits_data[user][current_month][idx] = new_habit_name
                save_json(HABITS_FILE, habits_data)
        
        elif action == "delete":
            habit_name = request.form.get("habit_name")
            if habit_name in habits_data[user][current_month]:
                habits_data[user][current_month].remove(habit_name)
                save_json(HABITS_FILE, habits_data)
    
    return render_template(
        "habits.html",
        habits=habits_data[user][current_month],
        month_name=get_month_name(current_month)
    )

# ------------------ Daily Tasks ------------------

@app.route("/today", methods=["GET", "POST"])
def today():
    if not login_required():
        return redirect("/")
    
    user = session["user"]
    current_month = get_current_month()
    today_date = str(date.today())
    
    # Get habits for current month
    habits_data = load_json(HABITS_FILE)
    user_habits = habits_data.get(user, {}).get(current_month, [])
    
    # Get progress
    progress_data = load_json(PROGRESS_FILE)
    progress_data.setdefault(user, {})
    progress_data[user].setdefault(today_date, {})
    
    # Initialize today's habits if not present
    for habit in user_habits:
        if habit not in progress_data[user][today_date]:
            progress_data[user][today_date][habit] = False
    
    if request.method == "POST":
        # Check if it's an AJAX request
        if request.is_json or request.headers.get('Content-Type') == 'application/json':
            data = request.get_json()
            habit_name = data.get('habit')
            is_completed = data.get('completed', False)
            
            if habit_name:
                progress_data[user][today_date][habit_name] = is_completed
                save_json(PROGRESS_FILE, progress_data)
                
                # Return updated stats
                completed = sum(progress_data[user][today_date].values())
                total = len(user_habits)
                return jsonify({
                    'success': True,
                    'completed': completed,
                    'total': total
                })
            return jsonify({'success': False, 'error': 'Invalid data'}), 400
        
        # Regular form submission (handle both original name and underscore-replaced name)
        for habit in user_habits:
            habit_key = habit.replace(' ', '_')
            # Check both original name and underscore version
            is_checked = (request.form.get(habit) == "on") or (request.form.get(habit_key) == "on")
            progress_data[user][today_date][habit] = is_checked
        
        save_json(PROGRESS_FILE, progress_data)
        # After manual Save Progress, go back to dashboard
        return redirect("/dashboard")
    
    completed = sum(progress_data[user][today_date].values())
    total = len(user_habits)
    
    return render_template(
        "today.html",
        habits=progress_data[user][today_date],
        completed=completed,
        total=total,
        date_str=date.today().strftime("%A, %B %d, %Y")
    )

# ------------------ Calendar View ------------------

@app.route("/calendar")
def calendar_view():
    if not login_required():
        return redirect("/")
    
    user = session["user"]
    current_month = get_current_month()
    
    # Get habits and progress
    habits_data = load_json(HABITS_FILE)
    progress_data = load_json(PROGRESS_FILE)
    
    user_habits = habits_data.get(user, {}).get(current_month, [])
    user_progress = progress_data.get(user, {})
    
    # Build calendar data
    month_dates = get_month_dates(current_month)
    calendar_data = []
    today = date.today()
    
    for date_str in month_dates:
        day_progress = user_progress.get(date_str, {})
        completed = sum(day_progress.values())
        total = len(user_habits)
        
        # Parse the date string to check if it's in the past
        year, month, day_num = map(int, date_str.split("-"))
        day_date = date(year, month, day_num)
        is_past = day_date < today
        is_missed = is_past and total > 0 and completed == 0
        
        calendar_data.append({
            "date": date_str,
            "day": day_num,
            "completed": completed,
            "total": total,
            "percentage": int((completed / total * 100)) if total > 0 else 0,
            "is_past": is_past,
            "is_missed": is_missed
        })
    
    return render_template(
        "calendar.html",
        calendar_data=calendar_data,
        month_name=get_month_name(current_month)
    )

# ------------------ Analysis ------------------

@app.route("/analysis")
def analysis():
    if not login_required():
        return redirect("/")
    
    user = session["user"]
    current_month = get_current_month()
    
    habits_data = load_json(HABITS_FILE)
    progress_data = load_json(PROGRESS_FILE)
    
    user_habits = habits_data.get(user, {}).get(current_month, [])
    user_progress = progress_data.get(user, {})
    
    # Calculate metrics
    total_tasks = 0
    completed_tasks = 0
    habit_completion = defaultdict(int)
    habit_total = defaultdict(int)
    
    month_dates = get_month_dates(current_month)
    daily_completion = []
    
    for date_str in month_dates:
        day_progress = user_progress.get(date_str, {})
        day_completed = 0
        
        for habit in user_habits:
            habit_total[habit] += 1
            total_tasks += 1
            
            if day_progress.get(habit, False):
                habit_completion[habit] += 1
                completed_tasks += 1
                day_completed += 1
        
        daily_completion.append(day_completed)
    
    consistency = int((completed_tasks / total_tasks * 100)) if total_tasks > 0 else 0
    
    # Generate charts
    generate_charts(user, daily_completion, habit_completion, habit_total, user_habits, user_progress, month_dates)
    
    # Best and worst habits
    best_habit = max(habit_completion, key=habit_completion.get) if habit_completion else "None"
    worst_habit = min(habit_completion, key=habit_completion.get) if habit_completion else "None"
    
    return render_template(
        "analysis.html",
        consistency=consistency,
        best_habit=best_habit,
        worst_habit=worst_habit,
        total_tasks=total_tasks,
        completed_tasks=completed_tasks,
        month_name=get_month_name(current_month)
    )

def generate_charts(user, daily_completion, habit_completion, habit_total, habits, user_progress, month_dates):
    plt.style.use('seaborn-v0_8-darkgrid')
    
    # 1. Daily Completion Trend
    plt.figure(figsize=(12, 4))
    plt.plot(range(1, len(daily_completion) + 1), daily_completion, marker='o', linewidth=2, markersize=4, color='#4CAF50')
    plt.fill_between(range(1, len(daily_completion) + 1), daily_completion, alpha=0.3, color='#4CAF50')
    plt.xlabel('Day of Month')
    plt.ylabel('Tasks Completed')
    plt.title('Daily Task Completion Trend')
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(f"{CHART_DIR}/daily_trend.png", dpi=100, bbox_inches='tight')
    plt.close()
    
    # 2. Habit Completion Rate
    if habits:
        habit_percentages = [(habit_completion[h] / habit_total[h] * 100) if habit_total[h] > 0 else 0 for h in habits]
        colors = ['#4CAF50' if p >= 70 else '#FFC107' if p >= 40 else '#F44336' for p in habit_percentages]
        
        plt.figure(figsize=(10, 6))
        bars = plt.barh(habits, habit_percentages, color=colors)
        plt.xlabel('Completion Rate (%)')
        plt.title('Habit Completion Rates')
        plt.xlim(0, 100)
        
        for i, (bar, pct) in enumerate(zip(bars, habit_percentages)):
            plt.text(pct + 2, bar.get_y() + bar.get_height()/2, f'{pct:.1f}%', 
                    va='center', fontweight='bold')
        
        plt.tight_layout()
        plt.savefig(f"{CHART_DIR}/habit_rates.png", dpi=100, bbox_inches='tight')
        plt.close()
    
    # 3. Weekly Comparison
    weeks = [daily_completion[i:i+7] for i in range(0, len(daily_completion), 7)]
    weekly_totals = [sum(week) for week in weeks]
    week_labels = [f"Week {i+1}" for i in range(len(weekly_totals))]
    
    plt.figure(figsize=(8, 5))
    bars = plt.bar(week_labels, weekly_totals, color=['#2196F3', '#4CAF50', '#FFC107', '#FF5722'][:len(weekly_totals)])
    plt.ylabel('Total Tasks Completed')
    plt.title('Weekly Performance Comparison')
    
    for bar in bars:
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2., height,
                f'{int(height)}', ha='center', va='bottom', fontweight='bold')
    
    plt.tight_layout()
    plt.savefig(f"{CHART_DIR}/weekly_comparison.png", dpi=100, bbox_inches='tight')
    plt.close()
    
    # 4. Today's Status
    today = str(date.today())
    today_progress = user_progress.get(today, {})
    completed = sum(today_progress.values())
    pending = len(habits) - completed
    
    if completed + pending > 0:
        plt.figure(figsize=(6, 6))
        colors = ['#4CAF50', '#E0E0E0']
        explode = (0.1, 0)
        plt.pie([completed, pending], labels=['Completed', 'Pending'], 
                autopct='%1.1f%%', colors=colors, explode=explode, startangle=90)
        plt.title("Today's Progress")
        plt.tight_layout()
        plt.savefig(f"{CHART_DIR}/today_status.png", dpi=100, bbox_inches='tight')
        plt.close()


@app.route("/day_status/<date_str>")
def day_status(date_str):
    """
    Return a pie chart image (PNG) showing completed vs pending tasks
    for a specific day in the current month, for the logged-in user.
    """
    if not login_required():
        return redirect("/")

    user = session["user"]
    current_month = get_current_month()

    # Only allow dates from the current month calendar
    if not date_str.startswith(current_month):
        return redirect("/calendar")

    habits_data = load_json(HABITS_FILE)
    progress_data = load_json(PROGRESS_FILE)

    user_habits = habits_data.get(user, {}).get(current_month, [])
    day_progress = progress_data.get(user, {}).get(date_str, {})

    completed = sum(1 for h in user_habits if day_progress.get(h, False))
    pending = max(len(user_habits) - completed, 0)

    # If there are no habits configured, return a simple empty chart
    plt.figure(figsize=(6, 6))

    if completed + pending > 0:
        sizes = [completed, pending]
        labels = ["Completed", "Pending"]
        colors = ["#4CAF50", "#E0E0E0"]
        explode = (0.1, 0)
        plt.pie(
            sizes,
            labels=labels,
            autopct="%1.1f%%",
            colors=colors,
            explode=explode,
            startangle=90,
        )
        plt.title(f"Progress on {date_str}")
    else:
        # Show a neutral chart when there is no data for the day
        plt.text(0.5, 0.5, "No habits on this day", ha="center", va="center", fontsize=14)
        plt.axis("off")

    plt.tight_layout()
    img_path = os.path.join(CHART_DIR, f"day_status_{user}_{date_str}.png")
    plt.savefig(img_path, dpi=100, bbox_inches="tight")
    plt.close()

    return send_file(img_path, mimetype="image/png")


# ------------------

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)