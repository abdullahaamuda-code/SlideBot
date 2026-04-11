import os
import json
import time
import random
from dotenv import load_dotenv

load_dotenv()

# Initialize clients
groq_client = None
mistral_client = None

try:
    from groq import Groq
    groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
except Exception as e:
    print(f"Warning: Groq client failed to init: {e}")

try:
    from mistralai.client import Mistral
    mistral_client = Mistral(api_key=os.getenv("MISTRAL_API_KEY"))
except Exception as e:
    print(f"Warning: Mistral client failed to init: {e}")

PROMPT_TEMPLATE = """
You are a world-class presentation designer and storyteller.
Your job is to create engaging, insightful, and creative slide content — NOT generic filler.

User input / document content:
\"\"\"
{user_input}
\"\"\"

Number of slides to generate: {num_slides}

IMPORTANT: Read the ENTIRE content above carefully. The slides MUST be about the actual subject matter.

Respond ONLY with a JSON object exactly like this format, nothing else:

{
    "title": "A Creative, Specific Title About The Actual Topic",
    "slides": [
        {
            "slide_number": 1,
            "heading": "Introduction to [Actual Topic]",
            "description": "1-2 sentence overview",
            "image_keyword": "relevant single English noun",
            "bullets": ["Specific insight", "Another insight", "Why important", "What audience learns"]
        }
    ]
}

Strict Rules:
- First slide must have description (Introduction)
- Last slide must be "Conclusion & Key Takeaways" with description
- Each slide should have 4-5 strong bullets
- Use actual content — do not make generic slides
- Make headings catchy and relevant
"""

def clean_json(text: str) -> str:
    if not text:
        return ""
    text = text.strip()
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0]
    elif "```" in text:
        text = text.split("```")[1]
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        text = text[start:end+1]
    return text.strip()


def enforce_summary_and_bullets(struct: dict, topic: str = "") -> dict:
    if not struct or "slides" not in struct:
        return struct
    slides = struct.get("slides", [])
    for slide in slides:
        bullets = slide.get("bullets", [])
        if len(bullets) < 4:
            while len(bullets) < 4:
                bullets.append("Key insight from the content")
        elif len(bullets) > 5:
            bullets = bullets[:5]
        slide["bullets"] = bullets
    # Ensure last slide is conclusion
    if slides:
        last_slide = slides[-1]
        last_heading = last_slide.get("heading", "").lower()
        if "conclusion" not in last_heading and "summary" not in last_heading and "takeaway" not in last_heading:
            last_slide["heading"] = "Conclusion & Key Takeaways"
        if not last_slide.get("description"):
            last_slide["description"] = "A summary of the key ideas and actionable insights from this presentation."
    # Ensure first slide has description
    if slides and not slides[0].get("description"):
        slides[0]["description"] = "An overview of the key themes and insights this presentation covers."
    struct["slides"] = slides
    return struct


def ensure_intro_and_conclusion(slide_data: dict, topic: str, num_slides: int) -> dict:
    slides = slide_data.get("slides", [])
    # Ensure first slide is introduction
    if slides:
        first_heading = slides[0].get("heading", "").lower()
        is_intro = any(word in first_heading for word in ["intro", "introduction", "overview"])
        if not is_intro:
            intro_slide = {
                "heading": "Introduction",
                "description": "An overview of the key themes and insights this presentation covers.",
                "bullets": ["Overview of the main subject", "Key challenges", "Why it matters", "What you will learn"],
                "image_keyword": "introduction"
            }
            slides.insert(0, intro_slide)
        elif not slides[0].get("description"):
            slides[0]["description"] = "An overview of the key themes and insights this presentation covers."
    # Ensure last slide is conclusion
    if slides:
        last_heading = slides[-1].get("heading", "").lower()
        is_conclusion = any(word in last_heading for word in ["conclusion", "summary", "takeaway", "closing"])
        if not is_conclusion:
            conclusion_slide = {
                "heading": "Conclusion & Key Takeaways",
                "description": "A recap of the most important insights and actionable next steps.",
                "bullets": ["Review of main concepts", "Key insights", "Actionable steps", "Final thoughts"],
                "image_keyword": "success"
            }
            slides.append(conclusion_slide)
        elif not slides[-1].get("description"):
            slides[-1]["description"] = "A summary of key insights and recommended next steps."
    # Adjust number of slides
    if len(slides) > num_slides:
        middle = slides[1:-1]
        keep = num_slides - 2
        middle = middle[:keep]
        slides = [slides[0]] + middle + [slides[-1]]
    elif len(slides) < num_slides:
        while len(slides) < num_slides:
            slides.insert(-1, {
                "heading": f"Key Insight {len(slides)}",
                "image_keyword": "research",
                "bullets": ["Important factor", "Evidence", "Implications", "Recommended approach"]
            })
    slide_data["slides"] = slides
    return slide_data


def generate_slide_content(user_input: str, num_slides: int = 8):
    print(f"\n🎨 Generating {num_slides} slides for: {user_input[:80]}...")

    prompt = PROMPT_TEMPLATE.format(user_input=user_input[:12000], num_slides=num_slides)

    # Try Groq first, then Mistral as fallback
    for attempt in range(3):
        # Try Groq
        if groq_client:
            try:
                print("📡 Trying Groq...")
                response = groq_client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.8,
                    max_tokens=4000
                )
                text = clean_json(response.choices[0].message.content)
                if text:
                    data = json.loads(text)
                    print("✅ Groq succeeded")
                    result = enforce_summary_and_bullets(data)
                    return ensure_intro_and_conclusion(result, user_input, num_slides)
            except Exception as e:
                print(f"Groq failed: {e}")
                if "429" in str(e):
                    time.sleep(2 ** attempt + random.uniform(0, 1))

        # Try Mistral
        if mistral_client:
            try:
                print("📡 Trying Mistral...")
                response = mistral_client.chat.complete(
                    model="mistral-large-latest",
                    messages=[{"role": "user", "content": prompt}]
                )
                text = clean_json(response.choices[0].message.content)
                if text:
                    data = json.loads(text)
                    print("✅ Mistral succeeded")
                    result = enforce_summary_and_bullets(data)
                    return ensure_intro_and_conclusion(result, user_input, num_slides)
            except Exception as e:
                print(f"Mistral failed: {e}")
                if "429" in str(e):
                    time.sleep(2 ** attempt + random.uniform(0, 1))

    # Fallback
    print("⚠️ All APIs failed - using fallback")
    fallback = generate_fallback_content(user_input, num_slides)
    return ensure_intro_and_conclusion(fallback, user_input, num_slides)


def generate_from_text(raw_text: str, num_slides: int = 8):
    text = raw_text[:12000] if len(raw_text) > 12000 else raw_text
    return generate_slide_content(text, num_slides)


def generate_fallback_content(topic: str, num_slides: int):
    slides = []
    for i in range(num_slides):
        if i == 0:
            slides.append({
                "slide_number": 1,
                "heading": "Introduction",
                "description": "An overview of the key themes and insights from the provided content.",
                "image_keyword": "introduction",
                "bullets": ["Main subject", "Background", "Why it matters", "What you will learn"]
            })
        elif i == num_slides - 1:
            slides.append({
                "slide_number": num_slides,
                "heading": "Conclusion & Key Takeaways",
                "description": "Summary of the most important insights and next steps.",
                "image_keyword": "success",
                "bullets": ["Key insights", "Main takeaways", "Actionable recommendations", "Final thoughts"]
            })
        else:
            slides.append({
                "slide_number": i + 1,
                "heading": f"Key Insight {i+1}",
                "image_keyword": "research",
                "bullets": ["Important point from content", "Supporting evidence", "Real-world implication", "Recommended approach"]
            })
    return {"title": "Presentation Summary", "slides": slides}
