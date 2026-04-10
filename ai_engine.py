import os
import json
import re
import traceback
from dotenv import load_dotenv
from google import genai
from groq import Groq

load_dotenv()

# ─── DEBUG: Check environment variables ──────────────────────────
print("🔧 AI Engine Loading...")
print(f"✅ GEMINI_API_KEY present: {'YES' if os.getenv('GEMINI_API_KEY') else 'NO'}")
print(f"✅ GROQ_API_KEY present: {'YES' if os.getenv('GROQ_API_KEY') else 'NO'}")

# Initialize clients
try:
    gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    print("✅ Gemini client initialized")
except Exception as e:
    print(f"❌ Gemini init failed: {e}")
    gemini_client = None

try:
    groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    print("✅ Groq client initialized")
except Exception as e:
    print(f"❌ Groq init failed: {e}")
    groq_client = None

# ─── SIMPLIFIED PROMPT TEMPLATE ──────────────────────────────────
PROMPT_TEMPLATE = """
Create a professional PowerPoint presentation about "{user_input}" with exactly {num_slides} slides.

IMPORTANT: Return ONLY valid JSON. No markdown, no explanations, no extra text.

JSON Format:
{{
    "title": "Presentation Title",
    "slides": [
        {{
            "slide_number": 1,
            "heading": "Introduction to [Topic]",
            "explanation": "2-3 sentences explaining what this slide covers.",
            "image_keyword": "introduction",
            "bullets": ["First key point", "Second key point", "Third key point"]
        }}
    ]
}}

Requirements:
- Slide 1: Introduction with explanation (2-3 sentences) and 3-4 bullets
- Slides 2 to {num_slides-1}: Content slides with explanation and 3-4 bullets each
- Slide {num_slides}: Conclusion with summary explanation and 3-4 action items as bullets

Keep bullets short (under 15 words). Make it professional.
"""

# ─── SIMPLIFIED TEXT PROMPT ──────────────────────────────────────
TEXT_PROMPT_TEMPLATE = """
Create a PowerPoint presentation from this text:

--- TEXT ---
{raw_text}
--- END TEXT ---

Generate exactly {num_slides} slides.

Return ONLY valid JSON in this format:
{{
    "title": "Presentation Title",
    "slides": [
        {{
            "slide_number": 1,
            "heading": "Introduction",
            "explanation": "2-3 sentence summary of what this text covers.",
            "image_keyword": "introduction",
            "bullets": ["Key point 1", "Key point 2", "Key point 3"]
        }}
    ]
}}

Requirements:
- Slide 1: Introduction explaining what the text is about
- Slides 2 to {num_slides-1}: Key points from the text with explanation
- Slide {num_slides}: Conclusion with key takeaways

Keep bullets short and professional.
"""


# ─── JSON CLEANING FUNCTION ──────────────────────────────────────
def clean_json(text: str) -> str:
    """Clean JSON response from AI - handles markdown and common issues"""
    if not text:
        print("⚠️ clean_json received empty text")
        return ""
    
    print(f"📝 Raw response preview: {text[:200]}...")
    text = text.strip()
    
    # Remove markdown code blocks
    if "```json" in text:
        text = text.split("```json", 1)[1]
        if "```" in text:
            text = text.split("```", 1)[0]
    elif "```" in text:
        text = text.split("```", 1)[1]
        if "```" in text:
            text = text.split("```", 1)[0]
    
    text = text.strip()
    
    # Extract JSON object
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        text = text[start:end + 1]
    else:
        print("⚠️ Could not find JSON braces in response")
        return ""
    
    # Fix common JSON issues
    text = re.sub(r',\s*}', '}', text)
    text = re.sub(r',\s*]', ']', text)
    text = re.sub(r'([{,])\s*([a-zA-Z0-9_]+)\s*:', r'\1"\2":', text)
    
    print(f"✅ Cleaned JSON preview: {text[:150]}...")
    return text


# ─── VALIDATE AND FIX SLIDES ─────────────────────────────────────
def validate_and_fix_slides(result: dict, expected_slides: int) -> dict | None:
    """Validate and fix slide structure"""
    print(f"🔍 Validating result with expected {expected_slides} slides...")
    
    if not result:
        print("❌ Result is None")
        return None
    
    if "slides" not in result:
        print(f"❌ Result missing 'slides' key. Keys: {result.keys()}")
        return None
    
    slides = result.get("slides", [])
    if not slides:
        print("❌ Slides list is empty")
        return None
    
    print(f"✅ Found {len(slides)} slides in result")
    
    # Get title
    title = result.get("title", "Presentation")
    
    # Ensure correct number of slides
    if len(slides) > expected_slides:
        slides = slides[:expected_slides]
        print(f"✂️ Trimmed to {len(slides)} slides")
    elif len(slides) < expected_slides:
        print(f"⚠️ Need {expected_slides - len(slides)} more slides, adding placeholders")
        for i in range(len(slides), expected_slides):
            slides.append({
                "slide_number": i + 1,
                "heading": f"Key Insight {i+1}",
                "explanation": f"This section explores important aspects related to {title}.",
                "image_keyword": "business",
                "bullets": [
                    "Important factor to consider",
                    "Strategy that drives results",
                    "Actionable takeaway"
                ]
            })
    
    # Fix each slide
    for idx, slide in enumerate(slides):
        slide["slide_number"] = idx + 1
        
        if not slide.get("heading"):
            slide["heading"] = f"Slide {idx + 1}"
        
        if not slide.get("explanation"):
            slide["explanation"] = f"This slide covers key points about {slide['heading']}."
        
        if not slide.get("image_keyword"):
            slide["image_keyword"] = "business"
        
        bullets = slide.get("bullets", [])
        if not bullets or len(bullets) == 0:
            bullets = ["Key point about this topic", "Important insight", "Actionable takeaway"]
        bullets = bullets[:5]
        slide["bullets"] = bullets
    
    # Ensure first slide is intro
    slides[0]["heading"] = f"Introduction to {title}"
    slides[0]["image_keyword"] = slides[0].get("image_keyword") or "introduction"
    
    # Ensure last slide is conclusion
    slides[-1]["heading"] = "Conclusion & Key Takeaways"
    slides[-1]["image_keyword"] = slides[-1].get("image_keyword") or "success"
    
    result["slides"] = slides
    result["title"] = title
    
    print(f"✅ Validation complete. Final slides: {len(slides)}")
    return result


# ─── GENERATE WITH GEMINI ────────────────────────────────────────
def generate_with_gemini(user_input: str, num_slides: int) -> dict | None:
    """Generate content using Gemini 2.0 Flash"""
    if not gemini_client:
        print("❌ Gemini client not available")
        return None
    
    try:
        prompt = PROMPT_TEMPLATE.format(
            user_input=user_input,
            num_slides=num_slides
        )
        print(f"📡 Calling Gemini API for: {user_input[:50]}...")
        
        response = gemini_client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt
        )
        
        print(f"📥 Gemini response received")
        raw_text = response.text
        print(f"📝 Response length: {len(raw_text)} chars")
        
        cleaned = clean_json(raw_text)
        if not cleaned:
            print("❌ Failed to clean JSON from Gemini")
            return None
        
        result = json.loads(cleaned)
        print("✅ Gemini JSON parsed successfully")
        
        validated = validate_and_fix_slides(result, num_slides)
        return validated
        
    except json.JSONDecodeError as e:
        print(f"❌ Gemini JSON decode error: {e}")
        print(f"Problematic text: {cleaned[:200] if 'cleaned' in locals() else 'N/A'}")
        return None
    except Exception as e:
        print(f"❌ Gemini failed: {e}")
        traceback.print_exc()
        return None


# ─── GENERATE WITH GROQ ──────────────────────────────────────────
def generate_with_groq(user_input: str, num_slides: int) -> dict | None:
    """Generate content using Groq Llama 3.3"""
    if not groq_client:
        print("❌ Groq client not available")
        return None
    
    try:
        prompt = PROMPT_TEMPLATE.format(
            user_input=user_input,
            num_slides=num_slides
        )
        print(f"📡 Calling Groq API for: {user_input[:50]}...")
        
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You are a professional presentation designer. Return ONLY valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=4000
        )
        
        print(f"📥 Groq response received")
        raw_text = response.choices[0].message.content
        print(f"📝 Response length: {len(raw_text)} chars")
        
        cleaned = clean_json(raw_text)
        if not cleaned:
            print("❌ Failed to clean JSON from Groq")
            return None
        
        result = json.loads(cleaned)
        print("✅ Groq JSON parsed successfully")
        
        validated = validate_and_fix_slides(result, num_slides)
        return validated
        
    except json.JSONDecodeError as e:
        print(f"❌ Groq JSON decode error: {e}")
        print(f"Problematic text: {cleaned[:200] if 'cleaned' in locals() else 'N/A'}")
        return None
    except Exception as e:
        print(f"❌ Groq failed: {e}")
        traceback.print_exc()
        return None


# ─── GENERATE FROM TEXT ──────────────────────────────────────────
def generate_from_text(raw_text: str, num_slides: int) -> dict:
    """Generate slide content from extracted text"""
    print(f"\n📄 Generating {num_slides} slides from text ({len(raw_text)} chars)...")
    
    if len(raw_text) > 8000:
        raw_text = raw_text[:8000]
        print(f"✂️ Text truncated to 8000 chars")
    
    prompt = TEXT_PROMPT_TEMPLATE.format(
        raw_text=raw_text,
        num_slides=num_slides
    )
    
    # Try Gemini first
    if gemini_client:
        try:
            print("📡 Trying Gemini for text generation...")
            response = gemini_client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt
            )
            
            cleaned = clean_json(response.text)
            if cleaned:
                result = json.loads(cleaned)
                validated = validate_and_fix_slides(result, num_slides)
                if validated:
                    print("✅ Text generation with Gemini succeeded!")
                    return validated
        except Exception as e:
            print(f"❌ Gemini text generation failed: {e}")
    
    # Try Groq as fallback
    if groq_client:
        try:
            print("📡 Trying Groq for text generation...")
            response = groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": "You are a professional presentation designer. Return ONLY valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=4000
            )
            
            cleaned = clean_json(response.choices[0].message.content)
            if cleaned:
                result = json.loads(cleaned)
                validated = validate_and_fix_slides(result, num_slides)
                if validated:
                    print("✅ Text generation with Groq succeeded!")
                    return validated
        except Exception as e:
            print(f"❌ Groq text generation failed: {e}")
    
    # Fallback
    print("⚠️ All text generation failed, using fallback")
    return generate_fallback_content("Document Content", num_slides)


# ─── FALLBACK CONTENT ────────────────────────────────────────────
def generate_fallback_content(topic: str, num_slides: int) -> dict:
    """Fallback content if all AI calls fail"""
    print(f"📋 Generating fallback content for: {topic[:50]}...")
    
    slides = []
    
    # Introduction slide
    slides.append({
        "slide_number": 1,
        "heading": f"Introduction to {topic}",
        "explanation": f"This presentation explores the key aspects of {topic}, providing valuable insights and actionable strategies for success.",
        "image_keyword": "introduction",
        "bullets": [
            f"What you need to know about {topic}",
            "Key challenges and opportunities",
            "Real-world applications and examples",
            "Benefits of mastering this topic"
        ]
    })
    
    # Middle content slides
    middle_count = max(2, num_slides - 2)
    for i in range(middle_count):
        slides.append({
            "slide_number": i + 2,
            "heading": f"Key Insight {i+1}",
            "explanation": f"This section covers critical aspects of {topic} that will help you understand and apply the concepts effectively.",
            "image_keyword": "business",
            "bullets": [
                "Important factor to consider for success",
                "Strategy that drives measurable results",
                "Common pitfall to avoid",
                "Best practice from industry leaders"
            ]
        })
    
    # Conclusion slide
    slides.append({
        "slide_number": num_slides,
        "heading": "Conclusion & Key Takeaways",
        "explanation": f"In conclusion, {topic} offers significant opportunities for growth and innovation. By applying these insights, you can achieve better outcomes.",
        "image_keyword": "success",
        "bullets": [
            "Take action on these key insights",
            "Implement strategies incrementally",
            "Measure results and iterate",
            "Continue learning and adapting"
        ]
    })
    
    result = {
        "title": f"Understanding {topic}",
        "slides": slides
    }
    
    print(f"✅ Fallback created with {len(slides)} slides")
    return result


# ─── MAIN FUNCTION ───────────────────────────────────────────────
def generate_slide_content(user_input: str, num_slides: int = 8) -> dict:
    """
    Main function to generate slide content.
    Tries Gemini first, then Groq as fallback, then static fallback.
    """
    print(f"\n{'='*50}")
    print(f"🎨 GENERATING {num_slides} SLIDES")
    print(f"📝 Topic: {user_input[:100]}")
    print(f"{'='*50}")
    
    # Try Gemini first
    if gemini_client:
        print("\n🟢 Attempting Gemini...")
        result = generate_with_gemini(user_input, num_slides)
        if result:
            print("✅ Gemini succeeded!")
            print(f"📊 Generated {len(result.get('slides', []))} slides")
            return result
        else:
            print("❌ Gemini failed")
    else:
        print("⚠️ Gemini client not available")
    
    # Try Groq as fallback
    if groq_client:
        print("\n🟢 Attempting Groq...")
        result = generate_with_groq(user_input, num_slides)
        if result:
            print("✅ Groq succeeded!")
            print(f"📊 Generated {len(result.get('slides', []))} slides")
            return result
        else:
            print("❌ Groq failed")
    else:
        print("⚠️ Groq client not available")
    
    # Ultimate fallback
    print("\n⚠️ All AIs failed, using fallback content")
    fallback = generate_fallback_content(user_input, num_slides)
    print(f"✅ Fallback created with {len(fallback.get('slides', []))} slides")
    
    return fallback


# ─── TEST FUNCTION ───────────────────────────────────────────────
if __name__ == "__main__":
    # Test the AI engine
    print("\n🧪 TESTING AI ENGINE...")
    result = generate_slide_content("Artificial Intelligence", 5)
    
    if result:
        print(f"\n✅ SUCCESS!")
        print(f"Title: {result.get('title')}")
        print(f"Slides: {len(result.get('slides', []))}")
        
        # Print first slide preview
        if result.get('slides'):
            first = result['slides'][0]
            print(f"\n📄 First slide:")
            print(f"  Heading: {first.get('heading')}")
            print(f"  Explanation: {first.get('explanation', '')[:100]}...")
            print(f"  Bullets: {len(first.get('bullets', []))}")
    else:
        print("\n❌ FAILED to generate content")
