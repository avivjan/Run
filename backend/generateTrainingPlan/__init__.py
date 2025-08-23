import azure.functions as func
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any
import random

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request for training plan generation.')
    
    try:
        # Get request body
        req_body = req.get_json()
        user_id = req_body.get('userId')
        
        if not user_id:
            return func.HttpResponse(
                json.dumps({"error": "userId is required"}),
                status_code=400,
                mimetype="application/json"
            )
        
        # Generate training plan
        training_plan = generate_training_plan(user_id, req_body)
        
        return func.HttpResponse(
            json.dumps(training_plan),
            status_code=200,
            mimetype="application/json"
        )
        
    except Exception as e:
        logging.error(f"Error in generateTrainingPlan: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": "Internal server error"}),
            status_code=500,
            mimetype="application/json"
        )

def generate_training_plan(user_id: str, request_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate a personalized training plan based on user data and goals
    """
    # Extract user data
    user_profile = request_data.get('userProfile', {})
    activities = request_data.get('activities', [])
    goals = request_data.get('goals', {})
    
    # Get user's current fitness level and preferences
    fitness_level = user_profile.get('fitnessLevel', 'beginner')
    max_weekly_runs = user_profile.get('preferences', {}).get('maxWeeklyRuns', 3)
    preferred_distance = goals.get('targetDistance', 5000)  # Default 5k
    
    # Calculate current capabilities
    current_capabilities = calculate_current_capabilities(activities)
    
    # Generate weekly plan
    weekly_plan = generate_weekly_plan(
        fitness_level, 
        current_capabilities, 
        max_weekly_runs, 
        preferred_distance
    )
    
    # Generate 4-week plan
    four_week_plan = generate_four_week_plan(weekly_plan, current_capabilities)
    
    return {
        "userId": user_id,
        "planId": f"plan_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "generatedAt": datetime.now().isoformat(),
        "currentCapabilities": current_capabilities,
        "weeklyPlan": weekly_plan,
        "fourWeekPlan": four_week_plan,
        "recommendations": generate_plan_recommendations(fitness_level, current_capabilities)
    }

def calculate_current_capabilities(activities: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Calculate user's current running capabilities based on recent activities
    """
    if not activities:
        return {
            "maxDistance": 3000,  # 3km default
            "comfortablePace": 7.0,  # 7:00 min/km default
            "weeklyVolume": 15000,  # 15km default
            "recoveryTime": 2  # 2 days default
        }
    
    # Get recent activities (last 4 weeks)
    recent_activities = activities[-10:] if len(activities) > 10 else activities
    
    # Calculate max distance
    max_distance = max(activity.get('distance', 0) for activity in recent_activities)
    
    # Calculate comfortable pace (average of recent runs)
    paces = [activity.get('averagePace', 0) for activity in recent_activities if activity.get('averagePace', 0) > 0]
    comfortable_pace = sum(paces) / len(paces) if paces else 7.0
    
    # Calculate weekly volume
    total_distance = sum(activity.get('distance', 0) for activity in recent_activities)
    weekly_volume = total_distance / 4  # Assume 4 weeks
    
    # Estimate recovery time based on intensity
    recovery_time = estimate_recovery_time(recent_activities)
    
    return {
        "maxDistance": max_distance,
        "comfortablePace": round(comfortable_pace, 2),
        "weeklyVolume": round(weekly_volume, 0),
        "recoveryTime": recovery_time
    }

def estimate_recovery_time(activities: List[Dict[str, Any]]) -> int:
    """
    Estimate recovery time needed based on recent activity intensity
    """
    if not activities:
        return 2
    
    # Calculate average intensity (distance * pace factor)
    intensities = []
    for activity in activities:
        distance = activity.get('distance', 0)
        pace = activity.get('averagePace', 7.0)
        # Higher pace = higher intensity
        intensity = distance * (1 + (7.0 - pace) / 7.0)
        intensities.append(intensity)
    
    avg_intensity = sum(intensities) / len(intensities)
    
    # Estimate recovery time based on intensity
    if avg_intensity > 10000:  # High intensity
        return 3
    elif avg_intensity > 5000:  # Medium intensity
        return 2
    else:  # Low intensity
        return 1

def generate_weekly_plan(fitness_level: str, capabilities: Dict[str, Any], 
                        max_runs: int, target_distance: int) -> Dict[str, Any]:
    """
    Generate a weekly training plan
    """
    max_distance = capabilities.get('maxDistance', 3000)
    comfortable_pace = capabilities.get('comfortablePace', 7.0)
    
    # Determine number of runs based on fitness level and preferences
    if fitness_level == "beginner":
        num_runs = min(3, max_runs)
    elif fitness_level == "intermediate":
        num_runs = min(4, max_runs)
    else:  # advanced
        num_runs = min(5, max_runs)
    
    # Generate run types and distances
    runs = []
    
    # Easy run (recovery)
    if num_runs >= 1:
        runs.append({
            "day": "monday",
            "type": "easy_run",
            "targetDistance": int(max_distance * 0.6),
            "targetPace": comfortable_pace + 1.0,
            "intensity": 0.4,
            "notes": "Recovery run - focus on easy pace and good form"
        })
    
    # Tempo run (if intermediate or advanced)
    if num_runs >= 2 and fitness_level != "beginner":
        runs.append({
            "day": "wednesday",
            "type": "tempo_run",
            "targetDistance": int(max_distance * 0.8),
            "targetPace": comfortable_pace - 0.5,
            "intensity": 0.8,
            "notes": "Tempo run - maintain challenging but sustainable pace"
        })
    
    # Long run
    if num_runs >= 3:
        runs.append({
            "day": "saturday",
            "type": "long_run",
            "targetDistance": int(max_distance * 1.2),
            "targetPace": comfortable_pace + 0.5,
            "intensity": 0.7,
            "notes": "Long run - build endurance, focus on distance not speed"
        })
    
    # Speed work (if advanced)
    if num_runs >= 4 and fitness_level == "advanced":
        runs.append({
            "day": "thursday",
            "type": "interval_run",
            "targetDistance": int(max_distance * 0.5),
            "targetPace": comfortable_pace - 1.0,
            "intensity": 0.9,
            "notes": "Interval training - alternating fast and slow segments"
        })
    
    # Additional easy run
    if num_runs >= 5:
        runs.append({
            "day": "friday",
            "type": "easy_run",
            "targetDistance": int(max_distance * 0.5),
            "targetPace": comfortable_pace + 1.5,
            "intensity": 0.3,
            "notes": "Easy recovery run"
        })
    
    # Calculate weekly totals
    total_distance = sum(run['targetDistance'] for run in runs)
    total_time = sum(run['targetDistance'] * run['targetPace'] / 60 for run in runs)  # Convert to minutes
    avg_intensity = sum(run['intensity'] for run in runs) / len(runs)
    
    return {
        "numberOfRuns": len(runs),
        "runs": runs,
        "metrics": {
            "totalDistance": total_distance,
            "totalTime": round(total_time, 0),
            "averageIntensity": round(avg_intensity, 2)
        }
    }

def generate_four_week_plan(weekly_plan: Dict[str, Any], capabilities: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Generate a progressive 4-week training plan
    """
    four_week_plan = []
    
    for week in range(1, 5):
        # Progressive overload - increase distance by 10% each week
        week_multiplier = 1 + (week - 1) * 0.1
        
        week_runs = []
        for run in weekly_plan['runs']:
            week_run = run.copy()
            week_run['targetDistance'] = int(run['targetDistance'] * week_multiplier)
            week_run['week'] = week
            week_runs.append(week_run)
        
        # Calculate week metrics
        total_distance = sum(run['targetDistance'] for run in week_runs)
        total_time = sum(run['targetDistance'] * run['targetPace'] / 60 for run in week_runs)
        avg_intensity = sum(run['intensity'] for run in week_runs) / len(week_runs)
        
        four_week_plan.append({
            "weekNumber": week,
            "runs": week_runs,
            "metrics": {
                "totalDistance": total_distance,
                "totalTime": round(total_time, 0),
                "averageIntensity": round(avg_intensity, 2)
            },
            "notes": f"Week {week} - Building on previous week's progress"
        })
    
    return four_week_plan

def generate_plan_recommendations(fitness_level: str, capabilities: Dict[str, Any]) -> List[str]:
    """
    Generate recommendations for following the training plan
    """
    recommendations = []
    
    if fitness_level == "beginner":
        recommendations.extend([
            "Start with the easy runs to build your base",
            "Don't worry about speed - focus on completing the distance",
            "Take rest days seriously - they're as important as training days",
            "Listen to your body and adjust if needed"
        ])
    elif fitness_level == "intermediate":
        recommendations.extend([
            "The tempo runs will help improve your pace",
            "Use the long runs to build endurance",
            "Consider cross-training on rest days",
            "Track your progress and adjust the plan as needed"
        ])
    else:  # advanced
        recommendations.extend([
            "The interval training will boost your speed",
            "Focus on quality over quantity",
            "Consider adding strength training",
            "Monitor your recovery and adjust intensity as needed"
        ])
    
    # General recommendations
    recommendations.extend([
        "Stay hydrated and fuel properly",
        "Warm up before each run",
        "Cool down and stretch after",
        "Get adequate sleep for recovery"
    ])
    
    return recommendations
