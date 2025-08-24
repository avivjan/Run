import azure.functions as func
import logging
import json
import os
from openai import AzureOpenAI
from datetime import datetime, timedelta
from typing import Dict, List, Any

# Initialize Azure OpenAI client
def get_openai_client():
    """Get OpenAI client with error handling"""
    try:
        endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")
        api_key = os.environ.get("AZURE_OPENAI_API_KEY")
        
        if not endpoint or not api_key:
            logging.error("Missing OpenAI configuration")
            return None
            
        return AzureOpenAI(
            azure_endpoint=endpoint,
            api_key=api_key,
            api_version="2023-12-01-preview"
        )
    except Exception as e:
        logging.error(f"Error initializing OpenAI client: {str(e)}")
        return None

# Global client variable
client = None

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('AI Coaching Service function processed a request.')
    
    # Initialize OpenAI client
    global client
    if client is None:
        client = get_openai_client()
        if client is None:
            return func.HttpResponse(
                json.dumps({"error": "Failed to initialize OpenAI client"}),
                status_code=500,
                mimetype="application/json"
            )
    
    # Debug: Log environment variables (without exposing sensitive data)
    logging.info(f"AZURE_OPENAI_API_KEY present: {bool(os.environ.get('AZURE_OPENAI_API_KEY'))}")
    logging.info(f"AZURE_OPENAI_ENDPOINT present: {bool(os.environ.get('AZURE_OPENAI_ENDPOINT'))}")
    logging.info(f"AZURE_OPENAI_API_VERSION: {os.environ.get('AZURE_OPENAI_API_VERSION')}")
    
    # Debug: Check if this is a test request
    if req.method == 'GET':
        # Check for specific test type
        test_type = req.params.get('test')
        if test_type == 'basic':
            return test_basic_function()
        elif test_type == 'config':
            return test_openai_configuration()
        else:
            return test_basic_function()
    
    try:
        # Get request body
        req_body = req.get_json()
        user_id = req_body.get('userId')
        request_type = req_body.get('type', 'recommendation')  # 'recommendation' or 'training_plan'
        
        logging.info(f"Request type: {request_type}, User ID: {user_id}")
        
        if not user_id:
            return func.HttpResponse(
                json.dumps({"error": "userId is required"}),
                status_code=400,
                mimetype="application/json"
            )
        
        # Get AI-powered coaching
        if request_type == 'training_plan':
            result = generate_ai_training_plan(user_id, req_body)
        else:
            result = generate_ai_recommendation(user_id, req_body)
        
        logging.info(f"Successfully generated {request_type} for user {user_id}")
        return func.HttpResponse(
            json.dumps(result),
            status_code=200,
            mimetype="application/json"
        )
        
    except Exception as e:
        logging.error(f"Error in aiCoachingService: {str(e)}")
        logging.error(f"Exception type: {type(e).__name__}")
        import traceback
        logging.error(f"Full traceback: {traceback.format_exc()}")
        return func.HttpResponse(
            json.dumps({"error": f"Internal server error: {str(e)}"}),
            status_code=500,
            mimetype="application/json"
        )

def test_basic_function():
    """
    Basic test function to verify the function is working
    """
    try:
        logging.info("Basic function test - function is working")
        return func.HttpResponse(
            json.dumps({
                "status": "success",
                "message": "Basic function test passed",
                "timestamp": datetime.now().isoformat(),
                "environment_vars": {
                    "openai_key_present": bool(os.environ.get("AZURE_OPENAI_API_KEY")),
                    "openai_endpoint_present": bool(os.environ.get("AZURE_OPENAI_ENDPOINT"))
                }
            }),
            status_code=200,
            mimetype="application/json"
        )
    except Exception as e:
        logging.error(f"Basic test failed: {str(e)}")
        return func.HttpResponse(
            json.dumps({
                "status": "error",
                "error": str(e),
                "error_type": type(e).__name__
            }),
            status_code=500,
            mimetype="application/json"
        )

def test_openai_configuration():
    """
    Test function to verify OpenAI configuration
    """
    try:
        logging.info("Testing OpenAI configuration...")
        
        # Check environment variables
        api_key = os.environ.get("AZURE_OPENAI_API_KEY")
        endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")
        api_version = os.environ.get("AZURE_OPENAI_API_VERSION")
        
        if not api_key:
            return func.HttpResponse(
                json.dumps({"error": "AZURE_OPENAI_API_KEY not found in environment variables"}),
                status_code=500,
                mimetype="application/json"
            )
        
        if not endpoint:
            return func.HttpResponse(
                json.dumps({"error": "AZURE_OPENAI_ENDPOINT not found in environment variables"}),
                status_code=500,
                mimetype="application/json"
            )
        
        # Test a simple API call
        logging.info("Attempting test API call...")
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "user", "content": "Say 'Hello, AI is working!' and nothing else."}
            ],
            max_tokens=50,
            temperature=0.1
        )
        
        test_response = response.choices[0].message.content
        logging.info(f"Test API call successful: {test_response}")
        
        return func.HttpResponse(
            json.dumps({
                "status": "success",
                "message": "OpenAI configuration is working",
                "test_response": test_response,
                "config": {
                    "endpoint_present": bool(endpoint),
                    "api_key_present": bool(api_key),
                    "api_version": api_version
                }
            }),
            status_code=200,
            mimetype="application/json"
        )
        
    except Exception as e:
        logging.error(f"Test failed: {str(e)}")
        return func.HttpResponse(
            json.dumps({
                "status": "error",
                "error": str(e),
                "error_type": type(e).__name__
            }),
            status_code=500,
            mimetype="application/json"
        )

def generate_ai_recommendation(user_id: str, request_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate AI-powered personalized coaching recommendations
    """
    activities = request_data.get('activities', [])
    user_profile = request_data.get('userProfile', {})
    
    # Prepare context for AI
    context = prepare_user_context(activities, user_profile)
    
    # Create AI prompt
    prompt = f"""
You are an expert running coach with 20+ years of experience. Analyze the following runner's data and provide personalized, actionable coaching advice.

RUNNER DATA:
{context}

Based on this data, provide:
1. A personalized motivational message (1-2 sentences)
2. 3 specific, actionable recommendations for improvement
3. A tip for their next run
4. Suggested focus area for the week

Format your response as JSON:
{{
    "motivational_message": "personalized message",
    "recommendations": ["rec1", "rec2", "rec3"],
    "next_run_tip": "specific tip",
    "weekly_focus": "focus area"
}}

Keep recommendations practical and specific to this runner's level and patterns.
"""
    
    try:
        logging.info("Attempting to call OpenAI API...")
        logging.info(f"Engine: gpt-4, Max tokens: 500, Temperature: 0.7")
        
        response = client.chat.completions.create(
            model="gpt-4",  # or your deployed model name
            messages=[
                {"role": "system", "content": "You are an expert running coach providing personalized advice."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500,
            temperature=0.7
        )
        
        logging.info("OpenAI API call successful!")
        ai_response = response.choices[0].message.content
        logging.info(f"AI Response length: {len(ai_response)} characters")
        logging.info(f"AI Response preview: {ai_response[:200]}...")
        
        # Parse JSON response
        try:
            coaching_data = json.loads(ai_response)
            logging.info("Successfully parsed JSON response from AI")
        except json.JSONDecodeError:
            # Fallback if AI doesn't return valid JSON
            coaching_data = {
                "motivational_message": "Keep up the great work! Every run makes you stronger.",
                "recommendations": [
                    "Focus on consistency over intensity",
                    "Include rest days in your schedule",
                    "Gradually increase your weekly mileage"
                ],
                "next_run_tip": "Start with a 5-minute warm-up walk",
                "weekly_focus": "Building consistency"
            }
        
        return {
            "userId": user_id,
            "type": "recommendation",
            "generatedAt": datetime.now().isoformat(),
            "coaching": coaching_data
        }
        
    except Exception as e:
        logging.error(f"Error calling OpenAI: {str(e)}")
        logging.error(f"OpenAI Exception type: {type(e).__name__}")
        import traceback
        logging.error(f"OpenAI Full traceback: {traceback.format_exc()}")
        
        # Return fallback recommendation
        return {
            "userId": user_id,
            "type": "recommendation",
            "generatedAt": datetime.now().isoformat(),
            "coaching": {
                "motivational_message": "Your dedication to running is inspiring!",
                "recommendations": [
                    "Focus on consistent weekly runs",
                    "Listen to your body and rest when needed",
                    "Set achievable weekly goals"
                ],
                "next_run_tip": "Start with a comfortable pace",
                "weekly_focus": "Building a sustainable routine"
            }
        }

def generate_ai_training_plan(user_id: str, request_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate AI-powered personalized training plan
    """
    activities = request_data.get('activities', [])
    user_profile = request_data.get('userProfile', {})
    goals = request_data.get('goals', {})
    
    # Prepare context for AI
    context = prepare_user_context(activities, user_profile, goals)
    
    # Create AI prompt for training plan
    prompt = f"""
You are an expert running coach creating a personalized 4-week training plan. Analyze this runner's data and create a progressive plan.

RUNNER DATA:
{context}

Create a 4-week training plan that:
1. Builds gradually and safely
2. Includes variety (easy runs, tempo, long runs)
3. Provides specific distances and paces
4. Includes rest days and cross-training suggestions
5. Adapts to their current fitness level

Format as JSON:
{{
    "plan_overview": "Brief description of the plan",
    "weekly_plans": [
        {{
            "week": 1,
            "focus": "Week focus",
            "runs": [
                {{
                    "day": "Monday",
                    "type": "Easy Run",
                    "distance": "3km",
                    "pace": "comfortable",
                    "notes": "specific instructions"
                }}
            ],
            "rest_days": ["Wednesday", "Sunday"],
            "cross_training": "optional cross-training suggestions"
        }}
    ],
    "progression_notes": "How the plan progresses",
    "safety_tips": ["tip1", "tip2", "tip3"]
}}

Make the plan realistic and achievable for this runner's current level.
"""
    
    try:
        response = client.chat.completions.create(
            model="gpt-4",  # or your deployed model name
            messages=[
                {"role": "system", "content": "You are an expert running coach creating personalized training plans."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1000,
            temperature=0.7
        )
        
        ai_response = response.choices[0].message.content
        
        # Parse JSON response
        try:
            training_plan = json.loads(ai_response)
        except json.JSONDecodeError:
            # Fallback training plan
            training_plan = create_fallback_training_plan(user_profile, goals)
        
        return {
            "userId": user_id,
            "type": "training_plan",
            "generatedAt": datetime.now().isoformat(),
            "plan": training_plan
        }
        
    except Exception as e:
        logging.error(f"Error calling OpenAI for training plan: {str(e)}")
        # Return fallback training plan
        return {
            "userId": user_id,
            "type": "training_plan",
            "generatedAt": datetime.now().isoformat(),
            "plan": create_fallback_training_plan(user_profile, goals)
        }

def prepare_user_context(activities: List[Dict], user_profile: Dict, goals: Dict = None) -> str:
    """
    Prepare user context for AI analysis
    """
    if not activities:
        return "New runner with no previous activities"
    
    # Calculate key metrics
    total_runs = len(activities)
    total_distance = sum(activity.get('distance', 0) for activity in activities)
    total_duration = sum(activity.get('duration', 0) for activity in activities)
    
    # Recent activities (last 4 weeks)
    recent_activities = activities[-10:] if len(activities) > 10 else activities
    recent_distance = sum(activity.get('distance', 0) for activity in recent_activities)
    
    # Calculate paces
    paces = [activity.get('averagePace', 0) for activity in activities if activity.get('averagePace', 0) > 0]
    avg_pace = sum(paces) / len(paces) if paces else 0
    best_pace = min(paces) if paces else 0
    
    # Analyze consistency
    weekly_runs = analyze_weekly_consistency(activities)
    
    # Analyze progress
    progress_trend = analyze_progress_trend(activities)
    
    context = f"""
RUNNING HISTORY:
- Total runs: {total_runs}
- Total distance: {total_distance/1000:.1f}km
- Total time: {total_duration/3600:.1f} hours
- Average pace: {avg_pace:.1f} min/km
- Best pace: {best_pace:.1f} min/km
- Recent 4-week distance: {recent_distance/1000:.1f}km

CONSISTENCY:
- Average runs per week: {weekly_runs.get('average_runs_per_week', 0):.1f}
- Consistency level: {weekly_runs.get('consistency_level', 'low')}
- Best week: {weekly_runs.get('best_week', 0)} runs

PROGRESS:
- Trend: {progress_trend.get('trend', 'stable')}
- Recent improvement: {progress_trend.get('recent_improvement', 'none')}

PROFILE:
- Fitness level: {user_profile.get('fitnessLevel', 'beginner')}
- Max weekly runs: {user_profile.get('preferences', {}).get('maxWeeklyRuns', 3)}
"""
    
    if goals:
        context += f"""
GOALS:
- Target distance: {goals.get('targetDistance', 0)/1000:.1f}km
- Goal type: {goals.get('goalType', 'general fitness')}
"""
    
    return context

def analyze_weekly_consistency(activities: List[Dict]) -> Dict[str, Any]:
    """
    Analyze weekly running consistency
    """
    if not activities:
        return {"average_runs_per_week": 0, "consistency_level": "low", "best_week": 0}
    
    # Group activities by week
    weekly_counts = {}
    for activity in activities:
        if 'timestamp' in activity:
            date = datetime.fromisoformat(activity['timestamp'].replace('Z', '+00:00'))
            week_key = date.strftime('%Y-%W')
            weekly_counts[week_key] = weekly_counts.get(week_key, 0) + 1
    
    if not weekly_counts:
        return {"average_runs_per_week": 0, "consistency_level": "low", "best_week": 0}
    
    avg_runs = sum(weekly_counts.values()) / len(weekly_counts)
    best_week = max(weekly_counts.values())
    
    # Determine consistency level
    if avg_runs >= 4:
        consistency = "high"
    elif avg_runs >= 2:
        consistency = "medium"
    else:
        consistency = "low"
    
    return {
        "average_runs_per_week": avg_runs,
        "consistency_level": consistency,
        "best_week": best_week
    }

def analyze_progress_trend(activities: List[Dict]) -> Dict[str, Any]:
    """
    Analyze progress trends
    """
    if len(activities) < 4:
        return {"trend": "insufficient_data", "recent_improvement": "none"}
    
    # Compare recent vs older activities
    recent = activities[-4:]
    older = activities[-8:-4] if len(activities) >= 8 else activities[:-4]
    
    # Check if we have enough data for comparison
    if len(older) == 0:
        return {"trend": "insufficient_data", "recent_improvement": "none"}
    
    recent_avg_distance = sum(a.get('distance', 0) for a in recent) / len(recent)
    older_avg_distance = sum(a.get('distance', 0) for a in older) / len(older)
    
    if recent_avg_distance > older_avg_distance * 1.1:
        trend = "improving"
        improvement = "distance"
    elif recent_avg_distance < older_avg_distance * 0.9:
        trend = "declining"
        improvement = "none"
    else:
        trend = "stable"
        improvement = "consistent"
    
    return {"trend": trend, "recent_improvement": improvement}

def create_fallback_training_plan(user_profile: Dict, goals: Dict) -> Dict[str, Any]:
    """
    Create a fallback training plan when AI is unavailable
    """
    fitness_level = user_profile.get('fitnessLevel', 'beginner')
    max_runs = user_profile.get('preferences', {}).get('maxWeeklyRuns', 3)
    target_distance = goals.get('targetDistance', 5000) / 1000  # Convert to km
    
    if fitness_level == 'beginner':
        return {
            "plan_overview": "Beginner-friendly 4-week plan focusing on building consistency",
            "weekly_plans": [
                {
                    "week": 1,
                    "focus": "Building a routine",
                    "runs": [
                        {"day": "Monday", "type": "Easy Run", "distance": "2km", "pace": "comfortable", "notes": "Start slow, focus on form"},
                        {"day": "Wednesday", "type": "Easy Run", "distance": "2km", "pace": "comfortable", "notes": "Same as Monday"},
                        {"day": "Saturday", "type": "Easy Run", "distance": "3km", "pace": "comfortable", "notes": "Longer run, take breaks if needed"}
                    ],
                    "rest_days": ["Tuesday", "Thursday", "Friday", "Sunday"],
                    "cross_training": "Light walking on rest days"
                }
            ],
            "progression_notes": "Gradually increase distance by 0.5km each week",
            "safety_tips": ["Listen to your body", "Stay hydrated", "Don't increase distance too quickly"]
        }
    else:
        return {
            "plan_overview": "Intermediate 4-week plan with variety",
            "weekly_plans": [
                {
                    "week": 1,
                    "focus": "Building endurance",
                    "runs": [
                        {"day": "Monday", "type": "Easy Run", "distance": "4km", "pace": "comfortable", "notes": "Recovery run"},
                        {"day": "Wednesday", "type": "Tempo Run", "distance": "3km", "pace": "moderate", "notes": "Middle 1km at faster pace"},
                        {"day": "Friday", "type": "Easy Run", "distance": "3km", "pace": "comfortable", "notes": "Easy pace"},
                        {"day": "Sunday", "type": "Long Run", "distance": "6km", "pace": "comfortable", "notes": "Longest run of the week"}
                    ],
                    "rest_days": ["Tuesday", "Thursday", "Saturday"],
                    "cross_training": "Strength training on Tuesday, yoga on Thursday"
                }
            ],
            "progression_notes": "Increase long run distance weekly, add speed work in week 3",
            "safety_tips": ["Include warm-up and cool-down", "Stay hydrated", "Listen to your body"]
        }
