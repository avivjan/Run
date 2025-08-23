import azure.functions as func
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any
import math

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request for user analysis.')
    
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
        
        # Analyze user data
        analysis_result = analyze_user_data(user_id, req_body)
        
        return func.HttpResponse(
            json.dumps(analysis_result),
            status_code=200,
            mimetype="application/json"
        )
        
    except Exception as e:
        logging.error(f"Error in analyzeUserData: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": "Internal server error"}),
            status_code=500,
            mimetype="application/json"
        )

def analyze_user_data(user_id: str, request_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze user running data and provide insights for coaching
    """
    # Get user activities (this would typically come from a database)
    activities = request_data.get('activities', [])
    
    if not activities:
        return {
            "userId": user_id,
            "analysis": {
                "fitnessLevel": "beginner",
                "consistency": "low",
                "progress": "insufficient_data",
                "recommendations": ["Start with regular short runs to build consistency"]
            }
        }
    
    # Calculate key metrics
    total_distance = sum(activity.get('distance', 0) for activity in activities)
    total_duration = sum(activity.get('duration', 0) for activity in activities)
    total_runs = len(activities)
    
    # Calculate average pace
    paces = [activity.get('averagePace', 0) for activity in activities if activity.get('averagePace', 0) > 0]
    average_pace = sum(paces) / len(paces) if paces else 0
    
    # Analyze consistency (runs per week)
    weekly_runs = analyze_weekly_consistency(activities)
    
    # Analyze progress trends
    progress_trend = analyze_progress_trend(activities)
    
    # Determine fitness level
    fitness_level = determine_fitness_level(total_distance, average_pace, weekly_runs)
    
    # Generate recommendations
    recommendations = generate_recommendations(
        fitness_level, 
        weekly_runs, 
        progress_trend, 
        total_distance,
        average_pace
    )
    
    return {
        "userId": user_id,
        "analysis": {
            "fitnessLevel": fitness_level,
            "consistency": weekly_runs.get('consistency_level', 'low'),
            "progress": progress_trend.get('trend', 'stable'),
            "metrics": {
                "totalDistance": total_distance,
                "totalDuration": total_duration,
                "totalRuns": total_runs,
                "averagePace": round(average_pace, 2) if average_pace > 0 else None,
                "weeklyAverage": weekly_runs.get('average_runs_per_week', 0),
                "bestWeek": weekly_runs.get('best_week', 0)
            },
            "trends": progress_trend,
            "recommendations": recommendations
        }
    }

def analyze_weekly_consistency(activities: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Analyze how consistently the user runs per week
    """
    if not activities:
        return {"consistency_level": "low", "average_runs_per_week": 0}
    
    # Group activities by week
    weekly_counts = {}
    for activity in activities:
        try:
            # Parse date (handle both string and timestamp formats)
            date_str = activity.get('date', '')
            if isinstance(date_str, str) and date_str.isdigit():
                date = datetime.fromtimestamp(int(date_str) / 1000)
            else:
                date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            
            # Get week start (Monday)
            week_start = date - timedelta(days=date.weekday())
            week_key = week_start.strftime('%Y-%m-%d')
            
            weekly_counts[week_key] = weekly_counts.get(week_key, 0) + 1
        except:
            continue
    
    if not weekly_counts:
        return {"consistency_level": "low", "average_runs_per_week": 0}
    
    runs_per_week = list(weekly_counts.values())
    average_runs = sum(runs_per_week) / len(runs_per_week)
    max_runs = max(runs_per_week)
    
    # Determine consistency level
    if average_runs >= 4:
        consistency_level = "high"
    elif average_runs >= 2:
        consistency_level = "medium"
    else:
        consistency_level = "low"
    
    return {
        "consistency_level": consistency_level,
        "average_runs_per_week": round(average_runs, 1),
        "best_week": max_runs,
        "total_weeks": len(weekly_counts)
    }

def analyze_progress_trend(activities: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Analyze progress trends in distance and pace
    """
    if len(activities) < 3:
        return {"trend": "insufficient_data", "message": "Need more runs to analyze trends"}
    
    # Sort activities by date
    sorted_activities = sorted(activities, key=lambda x: x.get('date', ''))
    
    # Analyze last 5 runs for trends
    recent_activities = sorted_activities[-5:]
    
    # Calculate distance trend
    distances = [act.get('distance', 0) for act in recent_activities]
    distance_trend = calculate_trend(distances)
    
    # Calculate pace trend (lower is better)
    paces = [act.get('averagePace', 0) for act in recent_activities if act.get('averagePace', 0) > 0]
    pace_trend = calculate_trend(paces, reverse=True) if paces else "stable"
    
    # Determine overall trend
    if distance_trend == "improving" and pace_trend in ["improving", "stable"]:
        overall_trend = "improving"
    elif distance_trend == "declining" and pace_trend == "declining":
        overall_trend = "declining"
    else:
        overall_trend = "stable"
    
    return {
        "trend": overall_trend,
        "distance_trend": distance_trend,
        "pace_trend": pace_trend,
        "message": f"Distance trend: {distance_trend}, Pace trend: {pace_trend}"
    }

def calculate_trend(values: List[float], reverse: bool = False) -> str:
    """
    Calculate if a series of values is improving, declining, or stable
    """
    if len(values) < 2:
        return "stable"
    
    # Calculate simple linear trend
    first_half = values[:len(values)//2]
    second_half = values[len(values)//2:]
    
    if not first_half or not second_half:
        return "stable"
    
    first_avg = sum(first_half) / len(first_half)
    second_avg = sum(second_half) / len(second_half)
    
    # Calculate percentage change
    if first_avg == 0:
        return "stable"
    
    change_percent = ((second_avg - first_avg) / first_avg) * 100
    
    if reverse:  # For pace, lower is better
        if change_percent < -5:
            return "improving"
        elif change_percent > 5:
            return "declining"
        else:
            return "stable"
    else:  # For distance, higher is better
        if change_percent > 5:
            return "improving"
        elif change_percent < -5:
            return "declining"
        else:
            return "stable"

def determine_fitness_level(total_distance: float, average_pace: float, weekly_runs: Dict[str, Any]) -> str:
    """
    Determine user's fitness level based on metrics
    """
    avg_runs_per_week = weekly_runs.get('average_runs_per_week', 0)
    
    # Convert total distance to km
    total_km = total_distance / 1000
    
    # Determine level based on distance, pace, and consistency
    if total_km > 100 and average_pace < 5.5 and avg_runs_per_week >= 4:
        return "advanced"
    elif total_km > 50 and average_pace < 6.5 and avg_runs_per_week >= 2:
        return "intermediate"
    else:
        return "beginner"

def generate_recommendations(fitness_level: str, weekly_runs: Dict[str, Any], 
                           progress_trend: Dict[str, Any], total_distance: float, 
                           average_pace: float) -> List[str]:
    """
    Generate personalized recommendations based on analysis
    """
    recommendations = []
    
    # Consistency recommendations
    avg_runs = weekly_runs.get('average_runs_per_week', 0)
    if avg_runs < 2:
        recommendations.append("Try to run at least 2-3 times per week to build consistency")
    elif avg_runs < 4:
        recommendations.append("Great consistency! Consider adding one more run per week")
    
    # Progress recommendations
    trend = progress_trend.get('trend', 'stable')
    if trend == "declining":
        recommendations.append("Your performance seems to be declining. Consider taking a rest week")
    elif trend == "improving":
        recommendations.append("Excellent progress! Keep up the great work")
    
    # Distance recommendations
    total_km = total_distance / 1000
    if total_km < 20:
        recommendations.append("Focus on building your base with regular short runs")
    elif total_km < 50:
        recommendations.append("Ready to increase your weekly distance gradually")
    
    # Pace recommendations
    if average_pace > 7.0:
        recommendations.append("Focus on building endurance before working on speed")
    elif average_pace < 5.0:
        recommendations.append("Consider adding some speed work to your routine")
    
    # Fitness level specific recommendations
    if fitness_level == "beginner":
        recommendations.append("Start with run-walk intervals to build endurance safely")
    elif fitness_level == "intermediate":
        recommendations.append("Consider adding tempo runs to improve your pace")
    elif fitness_level == "advanced":
        recommendations.append("You're ready for advanced training techniques like intervals and long runs")
    
    return recommendations[:5]  # Limit to 5 recommendations
