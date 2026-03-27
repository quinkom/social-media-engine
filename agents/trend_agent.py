"""
TREND INTELLIGENCE AGENT — Monitors what's trending in the clean food,
ancestral health, and functional fitness spaces daily.
"""

import json
import os
from datetime import datetime, date
from pathlib import Path
import anthropic


def run_trend_scan(serper_key="", anthropic_key=""):
    """Scan for trending topics in our niche. Returns structured trend data."""
    
    # Gather raw trend data from web search
    search_results = {}
    if serper_key:
        import requests
        queries = [
            "clean food movement trending 2026",
            "ancestral nutrition news this week",
            "glyphosate food safety latest",
            "seed oil debate trending",
            "pasture raised grass fed trending",
            "fitness mobility trending tiktok",
            "food label awareness viral",
            "paul saladino latest",
            "andrew huberman latest podcast topic",
            "clean eating viral tiktok instagram",
        ]
        
        for query in queries:
            try:
                resp = requests.post(
                    "https://google.serper.dev/search",
                    headers={"X-API-KEY": serper_key, "Content-Type": "application/json"},
                    json={"q": query, "num": 5},
                    timeout=15,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    results = []
                    for item in data.get("organic", [])[:3]:
                        results.append({
                            "title": item.get("title", ""),
                            "snippet": item.get("snippet", ""),
                            "link": item.get("link", ""),
                        })
                    search_results[query] = results
            except:
                continue
    
    # Use Claude to analyze trends and generate actionable brief
    client = anthropic.Anthropic(api_key=anthropic_key)
    
    search_context = json.dumps(search_results, indent=2) if search_results else "No search results available — use your training knowledge of current trends."
    
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2000,
        messages=[{
            "role": "user",
            "content": f"""You are a trend analyst for Quinton Kom's health and fitness brand.
His niche: clean food movement, ancestral nutrition, pasture-raised/grass-fed, 
avoiding glyphosate/additives/seed oils, lifting, and mobility.

Influences: Paul Saladino, Andrew Huberman, Mucci Strength

Today is {date.today().isoformat()}.

WEB SEARCH RESULTS:
{search_context}

Analyze what's trending and generate a daily trend brief. Respond with ONLY valid JSON:
{{
  "trending_topics": [
    {{
      "topic": "Specific topic description",
      "relevance": "high|medium|low",
      "urgency": "post_today|this_week|evergreen",
      "content_angle": "How Quinton should cover this",
      "suggested_format": "carousel|short_video|text_post",
      "pillar": "clean_food|ancestral_nutrition|lifting_mobility",
      "trend_score": 8.5,
      "competitor_coverage": 2
    }}
  ],
  "competitor_activity": [
    {{
      "creator": "Name",
      "recent_topic": "What they posted about",
      "engagement_signal": "high|medium|low",
      "opportunity": "How to differentiate or respond"
    }}
  ],
  "hot_take_opportunity": {{
    "topic": "Something controversial or timely worth commenting on",
    "angle": "Quinton's take",
    "risk_level": "low|medium|high"
  }},
  "weekly_theme_suggestion": "Overarching theme to tie this week's content together",
  "market_summary": "2-3 sentence summary of the landscape"
}}

Focus on topics with high engagement potential. Prioritize things that are 
actively being discussed NOW over evergreen content."""
        }]
    )
    
    # Parse response
    text = response.content[0].text
    try:
        # Extract JSON from response
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(text[start:end])
    except:
        pass
    
    return {"error": "Could not parse trend data", "raw": text[:500]}


def save_trend_brief(trend_data, logs_dir="logs"):
    """Save the daily trend brief."""
    Path(logs_dir).mkdir(exist_ok=True)
    
    filepath = os.path.join(logs_dir, f"trend_brief_{date.today().isoformat()}.json")
    with open(filepath, "w") as f:
        json.dump({
            "date": date.today().isoformat(),
            "generated_at": datetime.now().isoformat(),
            **trend_data,
        }, f, indent=2)
    
    return filepath
