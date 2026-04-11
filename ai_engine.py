import os
import json
from dotenv import load_dotenv
from google import genai
from groq import Groq
from mistralai import Mistral

load_dotenv()

gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
mistral_client = Mistral(api_key=os.getenv("MISTRAL_API_KEY"))

PROMPT_TEMPLATE = """
You are a world-class presentation designer and storyteller.
Your job is to create engaging, insightful, and creative slide content — NOT generic filler.

User input / document content:
\"\"\"
{user_input}
\"\"\"

Number of slides to generate: {num_slides}

IMPORTANT: Read the ENTIRE content above carefully. The slides MUST be about the actual subject matter of what was provided — not about generic topics like "communication" or "introductions" unless the document is literally about those things.

Respond ONLY with a JSON object exactly like this format, nothing else, no markdown:
{{
    "title": "A Creative, Specific Title About The Actual Topic",
    "slides": [
        {{
            "slide_number": 1,
            "heading": "Introduction to [Actual Topic From Content]",
            "description": "1-2 sentence overview of what this presentation covers and why it matters.",
            "image_keyword": "relevant single English noun",
            "bullets": [
                "Specific insight from the content",
                "Another specific insight",
                "Why this topic is important",
                "What the audience will learn"
            ]
        }}
    ]
}}

Strict Rules:
- READ THE FULL CONTENT — do not just use the first paragraph or heading
- Slides MUST reflect the actual subject matter (food security, research, science, etc.) — never drift into generic topics
- First slide MUST be the introduction with a "description" field (1-2 sentences)
- Last slide MUST be "Conclusion & Key Takeaways" with a "description" field (1-2 sentences)
- Middle slides do NOT need a description field
- Each slide MUST have exactly 4-5 bullet points — specific, punchy, insightful
- Bullet points should feel fresh and intelligent — avoid clichés like "leveraging synergies" or "best practices"
- image_keyword must be a single simple English noun that fits the slide topic visually
- Be creative with headings — make them catchy and specific, not generic
- Do not include any explanations, markdown, comments, or extra text outside the JSON
"""

def clean_json(text: str) -> str:
    """Clean JSON response from AI"""
    if not text:
        return ""

    text = text.strip()

    if "```json" in text:
        parts = text.split("```json")
        if len(parts) > 1:
            text = parts[1]
    if "```" in text:
        text = text.split("```")[0]

    text = text.strip()

    start = text.find("{")
    end = text.rfind("}")

    if start != -1 and end != -1 and end > start:
        text = text[start:end+1]

    return text

def enforce_summary_and_bullets(struct: dict, topic: str = "") -> dict:
    """Ensure each slide has 4-5 bullets, first and last have descriptions"""
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

    # Ensure last slide is conclusion with description
    if slides:
        last_slide = slides[-1]
        last_heading = last_slide.get("heading", "").lower()
        if "conclusion" not in last_heading and "summary" not in last_heading and "takeaway" not in last_heading:
            last_slide["heading"] = "Conclusion & Key Takeaways"
        if not last_slide.get("description"):
            last_slide["description"] = "A summary of the key ideas and actionable insights from this presentation."

    # Ensure first slide has description
    if slides and not slides[0].get("description"):
        slides[0]["description"] = (
            "An overview of what this presentation covers and why it matters."
        )

    struct["slides"] = slides
    return struct

def generate_with_groq(user_input: str, num_slides: int):
    try:
        print(f"📡 Groq: Generating for '{user_input[:80]}...'")
        prompt = PROMPT_TEMPLATE.format(
            user_input=user_input,
            num_slides=num_slides
        )
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.9,   # creative
            max_tokens=4000
        )
        text = clean_json(response.choices[0].message.content)
        if not text:
            print("❌ Groq: Empty response after cleaning")
            return None
        data = json.loads(text)
        print("✅ Groq: Success")
        return enforce_summary_and_bullets(data, user_input[:100])
    except Exception as e:
        print(f"❌ Groq failed: {e}")
        return None

def generate_with_mistral(user_input: str, num_slides: int):
    try:
        print(f"📡 Mistral: Generating for '{user_input[:80]}...'")
        prompt = PROMPT_TEMPLATE.format(
            user_input=user_input,
            num_slides=num_slides
        )
        response = mistral_client.chat.complete(
            model="mistral-large-latest",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.9,
            max_tokens=4000,
        )
        text = clean_json(response.choices[0].message.content)
        if not text:
            print("❌ Mistral: Empty response after cleaning")
            return None
        data = json.loads(text)
        print("✅ Mistral: Success")
        return enforce_summary_and_bullets(data, user_input[:100])
    except Exception as e:
        print(f"❌ Mistral failed: {e}")
        return None

def generate_with_gemini(user_input: str, num_slides: int):
    try:
        print(f"📡 Gemini: Generating for '{user_input[:80]}...'")
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
        return enforce_summary_and_bullets(data, user_input[:100])
    except Exception as e:
        print(f"❌ Gemini failed: {e}")
        return None

def generate_fallback_content(topic: str, num_slides: int) -> dict:
    """Fallback content if all AI calls fail"""
    label = topic[:100].strip() if len(topic) > 100 else topic

    slides = []
    for i in range(num_slides):
        if i == 0:
            slides.append({
                "slide_number": 1,
                "heading": "Introduction",
                "description": "This presentation explores the key themes and insights from the provided content.",
                "image_keyword": "introduction",
                "bullets": [
                    "Overview of the main subject matter",
                    "Key challenges and opportunities discussed",
                    "Why this topic is important today",
                    "What you will learn from this presentation"
                ]
            })
        elif i == num_slides - 1:
            slides.append({
                "slide_number": num_slides,
                "heading": "Conclusion & Key Takeaways",
                "description": "A recap of the most important insights and recommended next steps.",
                "image_keyword": "success",
                "bullets": [
                    "Review of the main concepts discussed",
                    "Key insights to remember and apply",
                    "Actionable steps to take next",
                    "Resources for further learning"
                ]
            })
        else:
            slides.append({
                "slide_number": i + 1,
                "heading": f"Key Theme {i}",
                "image_keyword": "research",
                "bullets": [
                    "Important factor highlighted in the content",
                    "Evidence or data supporting this point",
                    "Real-world implications to consider",
                    "Recommended approach or solution"
                ]
            })

    return {
        "title": "Presentation Summary",
        "slides": slides
    }

def ensure_intro_and_conclusion(slide_data: dict, topic: str, num_slides: int) -> dict:
    """Force intro and conclusion slides to exist with proper descriptions"""
    slides = slide_data.get("slides", [])
    label = topic[:80].strip() if len(topic) > 80 else topic

    # Check if first slide is intro
    if slides:
        first_heading = slides[0].get("heading", "").lower()
        is_intro = any(word in first_heading for word in ["intro", "introduction", "overview", "welcome"])

        if not is_intro:
            intro_slide = {
                "heading": "Introduction",
                "description": "This presentation explores the key themes and insights from the provided content.",
                "bullets": [
                    "Overview of the subject matter",
                    "Key challenges and opportunities",
                    "What you will learn from this presentation",
                    "Real-world applications and examples"
                ],
                "image_keyword": "introduction"
            }
            slides.insert(0, intro_slide)
        else:
            # Make sure existing intro has a description
            if not slides[0].get("description"):
                slides[0]["description"] = "An overview of the key themes and insights this presentation covers."

    # Check if last slide is conclusion
    if slides:
        last_heading = slides[-1].get("heading", "").lower()
        is_conclusion = any(word in last_heading for word in ["conclusion", "summary", "key takeaways", "closing"])

        if not is_conclusion:
            conclusion_slide = {
                "heading": "Conclusion & Key Takeaways",
                "description": "A recap of the most important insights and actionable next steps from this presentation.",
                "bullets": [
                    "Review of main concepts discussed",
                    "Key insights to remember and apply",
                    "Actionable steps to take next",
                    "Resources for further learning"
                ],
                "image_keyword": "success"
            }
            slides.append(conclusion_slide)
        else:
            # Make sure existing conclusion has a description
            if not slides[-1].get("description"):
                slides[-1]["description"] = "A summary of key insights and recommended next steps."

    # Trim or pad to hit exact num_slides
    if len(slides) > num_slides:
        # Always keep first and last, trim from the middle
        middle = slides[1:-1]
        keep = num_slides - 2
        middle = middle[:keep]
        slides = [slides[0]] + middle + [slides[-1]]
    elif len(slides) < num_slides:
        while len(slides) < num_slides:
            slides.insert(-1, {
                "heading": f"Key Insight {len(slides)}",
                "image_keyword": "research",
                "bullets": [
                    "Important factor to consider",
                    "Evidence supporting this point",
                    "Real-world implications",
                    "Recommended approach"
                ]
            })

    slide_data["slides"] = slides
    return slide_data

def generate_slide_content(user_input: str, num_slides: int = 8):
    print(f"\n🎨 Generating {num_slides} slides for: {user_input[:80]}...")

    # 1️⃣ Try Groq first
    result = generate_with_groq(user_input, num_slides)
    if result:
        result = ensure_intro_and_conclusion(result, user_input, num_slides)
        return result

    # 2️⃣ Then Mistral
    result = generate_with_mistral(user_input, num_slides)
    if result:
        result = ensure_intro_and_conclusion(result, user_input, num_slides)
        return result

    # 3️⃣ Then Gemini
    result = generate_with_gemini(user_input, num_slides)
    if result:
        result = ensure_intro_and_conclusion(result, user_input, num_slides)
        return result

    # 4️⃣ Ultimate fallback
    fallback = generate_fallback_content(user_input, num_slides)
    fallback = ensure_intro_and_conclusion(fallback, user_input, num_slides)
    return fallback

def generate_from_text(raw_text: str, num_slides: int = 8):
    """
    Generate from extracted document text.
    Sends up to 12,000 chars so the AI actually understands the full document.
    """
    topic = raw_text[:12000] if len(raw_text) > 12000 else raw_text
    return generate_slide_content(topic, num_slides)
