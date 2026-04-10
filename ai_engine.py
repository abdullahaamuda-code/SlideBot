import os
import json
import re
from dotenv import load_dotenv
from google import genai
from groq import Groq

load_dotenv()

gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

PROMPT_TEMPLATE = """
You are a professional presentation designer.
Generate structured slide content based on the user's input.

User input: {user_input}
Number of slides: {num_slides}

Respond ONLY with a JSON object exactly like this, nothing else, no markdown:
{{
    "title": "Presentation Title",
    "slides": [
        {{
            "slide_number": 1,
            "heading": "Slide Title Here",
            "image_keyword": "relevant single word for image",
            "bullets": [
                "First key point",
                "Second key point",
                "Third key point",
                "Fourth key point"
            ]
        }}
    ]
}}

Rules:
- First slide is always the intro/title slide
- Last slide is always a real summary: concise recap of the most important ideas
- Each slide MUST have between 4 and 5 bullet points, never fewer than 4
- Bullet points must be short and punchy
- image_keyword must be a single simple English noun relevant to the slide topic
- Make it professional and engaging
- Do not include any explanations, markdown, comments, or extra text outside the JSON object
"""

def clean_json(text: str) -> str:
    """Clean JSON response from AI"""
    if not text:
        return ""
    
    text = text.strip()
    
    # Remove markdown code blocks
    if "```json" in text:
        parts = text.split("```json")
        if len(parts) > 1:
            text = parts[1]
    if "```" in text:
        text = text.split("```")[0]
    
    text = text.strip()
    
    # Find first { and last }
    start = text.find("{")
    end = text.rfind("}")
    
    if start != -1 and end != -1 and end > start:
        text = text[start:end+1]
    
    return text

def enforce_summary_and_bullets(struct: dict) -> dict:
    """Ensure each slide has 4-5 bullets and last slide is a proper summary"""
    if not struct or "slides" not in struct:
        return struct
    
    slides = struct.get("slides", [])
    
    for slide in slides:
        bullets = slide.get("bullets", [])
        
        # Ensure between 4 and 5 bullets
        if len(bullets) < 4:
            # Add placeholder bullets if needed
            while len(bullets) < 4:
                bullets.append("Important key point to remember")
        elif len(bullets) > 5:
            bullets = bullets[:5]
        
        slide["bullets"] = bullets
    
    # Ensure last slide is a proper summary
    if slides:
        last_slide = slides[-1]
        # Make sure last slide has summary-like heading
        if "conclusion" not in last_slide.get("heading", "").lower() and "summary" not in last_slide.get("heading", "").lower():
            last_slide["heading"] = "Conclusion & Key Takeaways"
    
    struct["slides"] = slides
    return struct

def generate_with_gemini(user_input: str, num_slides: int):
    try:
        print(f"📡 Gemini: Generating for '{user_input[:50]}...'")
        prompt = PROMPT_TEMPLATE.format(
            user_input=user_input,
            num_slides=num_slides
        )
        response = gemini_client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt
        )
        text = clean_json(response.text)
        if not text:
            print("❌ Gemini: Empty response after cleaning")
            return None
        data = json.loads(text)
        print("✅ Gemini: Success")
        return enforce_summary_and_bullets(data)
    except Exception as e:
        print(f"❌ Gemini failed: {e}")
        return None

def generate_with_groq(user_input: str, num_slides: int):
    try:
        print(f"📡 Groq: Generating for '{user_input[:50]}...'")
        prompt = PROMPT_TEMPLATE.format(
            user_input=user_input,
            num_slides=num_slides
        )
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=4000
        )
        text = clean_json(response.choices[0].message.content)
        if not text:
            print("❌ Groq: Empty response after cleaning")
            return None
        data = json.loads(text)
        print("✅ Groq: Success")
        return enforce_summary_and_bullets(data)
    except Exception as e:
        print(f"❌ Groq failed: {e}")
        return None

def generate_slide_content(user_input: str, num_slides: int = 8):
    """Main function - clears old context, generates fresh content"""
    print(f"\n🎨 Generating {num_slides} slides for: {user_input[:100]}...")
    
    # Try Gemini first
    result = generate_with_gemini(user_input, num_slides)
    if result:
        return result
    
    # Try Groq as fallback
    result = generate_with_groq(user_input, num_slides)
    if result:
        return result
    
    # Ultimate fallback
    print("⚠️ All AIs failed, using fallback content")
    return generate_fallback_content(user_input, num_slides)

def generate_from_text(raw_text: str, num_slides: int = 8):
    """Generate from extracted text"""
    # Take first 200 chars as topic for generation
    topic = raw_text[:200] if len(raw_text) > 200 else raw_text
    return generate_slide_content(topic, num_slides)

def generate_fallback_content(topic: str, num_slides: int) -> dict:
    """Fallback content if all AI calls fail"""
    slides = []
    for i in range(num_slides):
        if i == 0:
            slides.append({
                "slide_number": 1,
                "heading": f"Introduction to {topic[:50]}",
                "image_keyword": "introduction",
                "bullets": [
                    f"What you need to know about {topic[:30]}",
                    "Key challenges and opportunities",
                    "Why this matters today",
                    "What you'll learn from this presentation"
                ]
            })
        elif i == num_slides - 1:
            slides.append({
                "slide_number": num_slides,
                "heading": "Conclusion & Key Takeaways",
                "image_keyword": "success",
                "bullets": [
                    "Review of the main concepts discussed",
                    "Key insights to remember",
                    "Actionable steps to take",
                    "Resources for further learning"
                ]
            })
        else:
            slides.append({
                "slide_number": i + 1,
                "heading": f"Key Insight {i}",
                "image_keyword": "business",
                "bullets": [
                    "Important factor to consider",
                    "Strategy that drives results",
                    "Common pitfall to avoid",
                    "Best practice to follow"
                ]
            })
    
    return {
        "title": f"Understanding {topic[:50]}",
        "slides": slides
    }
