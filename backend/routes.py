"""
REST API routes for TaskTraQ
"""

from flask import Blueprint, request, jsonify
from datetime import datetime
from backend.auth import register_user, login_user, require_auth
from backend.habits import (
    create_habit, update_habit_name, delete_user_habit,
    get_habits_with_calculations, toggle_day_completion
)
from backend.analytics import calculate_dashboard_metrics, get_monthly_trend

api_bp = Blueprint('api', __name__)

# ==================== AUTHENTICATION ROUTES ====================

@api_bp.route('/auth/register', methods=['POST'])
def api_register():
    """Register a new user"""
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    
    user, error = register_user(email, password)
    if error:
        return jsonify({'error': error}), 400
    
    return jsonify({
        'message': 'User registered successfully',
        'user_id': user['id'],
        'email': user['email']
    }), 201

@api_bp.route('/auth/login', methods=['POST'])
def api_login():
    """Login a user"""
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    
    result, error = login_user(email, password)
    if error:
        return jsonify({'error': error}), 401
    
    return jsonify(result), 200

# ==================== HABIT ROUTES ====================

@api_bp.route('/habits', methods=['GET'])
@require_auth
def api_get_habits(user):
    """Get all habits for the current month with calculations"""
    year = request.args.get('year', datetime.now().year, type=int)
    month = request.args.get('month', datetime.now().month, type=int)
    
    habits = get_habits_with_calculations(user['id'], year, month)
    return jsonify({
        'habits': habits,
        'year': year,
        'month': month
    }), 200

@api_bp.route('/habits', methods=['POST'])
@require_auth
def api_create_habit(user):
    """Create a new habit"""
    data = request.get_json()
    name = data.get('name', '').strip()
    
    habit, error = create_habit(user['id'], name)
    if error:
        return jsonify({'error': error}), 400
    
    return jsonify({
        'message': 'Habit created successfully',
        'habit': habit
    }), 201

@api_bp.route('/habits/<habit_id>', methods=['PUT'])
@require_auth
def api_update_habit(user, habit_id):
    """Update habit name"""
    data = request.get_json()
    new_name = data.get('name', '').strip()
    
    habit, error = update_habit_name(habit_id, user['id'], new_name)
    if error:
        return jsonify({'error': error}), 400
    
    return jsonify({
        'message': 'Habit updated successfully',
        'habit': habit
    }), 200

@api_bp.route('/habits/<habit_id>', methods=['DELETE'])
@require_auth
def api_delete_habit(user, habit_id):
    """Delete a habit"""
    success, error = delete_user_habit(habit_id, user['id'])
    if error:
        return jsonify({'error': error}), 404
    
    return jsonify({'message': 'Habit deleted successfully'}), 200

@api_bp.route('/habits/<habit_id>/day/<date>', methods=['PUT'])
@require_auth
def api_toggle_day(user, habit_id, date):
    """Toggle day completion (0 or 1)"""
    data = request.get_json()
    completed = data.get('completed')
    
    if completed not in [0, 1]:
        return jsonify({'error': 'Completed must be 0 or 1'}), 400
    
    log, error = toggle_day_completion(user['id'], habit_id, date, completed)
    if error:
        return jsonify({'error': error}), 400
    
    # Return updated habit data with recalculated totals
    year = int(date.split('-')[0])
    month = int(date.split('-')[1])
    habits = get_habits_with_calculations(user['id'], year, month)
    
    return jsonify({
        'message': 'Day updated successfully',
        'habits': habits
    }), 200

# ==================== DASHBOARD ROUTES ====================

@api_bp.route('/dashboard', methods=['GET'])
@require_auth
def api_get_dashboard(user):
    """Get dashboard analytics"""
    year = request.args.get('year', datetime.now().year, type=int)
    month = request.args.get('month', datetime.now().month, type=int)
    
    metrics = calculate_dashboard_metrics(user['id'], year, month)
    return jsonify({
        'metrics': metrics,
        'year': year,
        'month': month
    }), 200

@api_bp.route('/dashboard/trend', methods=['GET'])
@require_auth
def api_get_trend(user):
    """Get monthly trend data"""
    year = request.args.get('year', datetime.now().year, type=int)
    months_str = request.args.get('months', '1,2,3,4,5,6,7,8,9,10,11,12')
    months = [int(m) for m in months_str.split(',')]
    
    trend = get_monthly_trend(user['id'], year, months)
    return jsonify({
        'trend': trend,
        'year': year
    }), 200

# ==================== HEALTH CHECK ====================

@api_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'ok'}), 200