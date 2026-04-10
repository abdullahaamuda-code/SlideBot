import os
import json
from groq import Groq

groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def generate_slide_content(topic, num_slides=8):
    """Simple, reliable slide generation"""
    
    prompt = f"""Create a {num_slides}-slide presentation about "{topic}".

Return ONLY this JSON format, nothing else:
{{
    "title": "Presentation Title",
    "slides": [
        {{
            "heading": "Slide Title",
            "bullets": ["Point 1", "Point 2", "Point 3"],
            "image_keyword": "business"
        }}
    ]
}}

Make slide 1 an introduction, the last slide a conclusion, and the rest content slides."""
    
    try:
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        
        text = response.choices[0].message.content
        # Clean up
        text = text.replace("```json", "").replace("```", "").strip()
        
        # Find JSON
        start = text.find("{")
        end = text.rfind("}") + 1
        if start != -1 and end != 0:
            text = text[start:end]
        
        data = json.loads(text)
        return data
        
    except Exception as e:
        print(f"Error: {e}")
        # Simple fallback
        return {
            "title": f"About {topic}",
            "slides": [
                {"heading": f"Introduction to {topic}", "bullets": [f"What is {topic}", "Why it matters", "What you'll learn"], "image_keyword": "introduction"},
                {"heading": "Key Benefits", "bullets": ["First major benefit", "Second important benefit", "Third key advantage"], "image_keyword": "success"},
                {"heading": "Conclusion", "bullets": ["Main takeaways", "Action steps", "Next steps"], "image_keyword": "future"}
            ]
        }

def generate_from_text(text, num_slides=8):
    """Simple text-based generation"""
    return generate_slide_content("the provided content", num_slides)
