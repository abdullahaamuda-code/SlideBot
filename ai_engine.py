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
You are a professional presentation designer. Generate structured slide content.

User input: {user_input}
Number of slides: {num_slides}

IMPORTANT RULES:
1. Each slide MUST have:
   - A clear heading
   - 1-2 sentences of explanation (NOT just bullets!)
   - 3-5 bullet points for key details
   - An image_keyword (single word for Unsplash)

2. Slide structure:
   - Slide 1: Introduction to the topic (explain what it is, why it matters)
   - Slides 2 to {num_slides-1}: Content slides (each with explanation + bullets)
   - Slide {num_slides}: Conclusion & Key Takeaways (summary + action items)

3. For the Conclusion slide:
   - Heading: "Conclusion & Key Takeaways"
   - Explanation paragraph summarizing main points
   - 3-4 bullet points as action items
   - Image keyword: "success" or "future"

4. Keep bullet points concise (under 15 words each)
5. Make explanations informative (2-3 sentences)
6. Be professional and engaging

Respond ONLY with a JSON object exactly like this, nothing else, no markdown:

{{
    "title": "Professional Presentation Title",
    "slides": [
        {{
            "slide_number": 1,
            "heading": "Introduction to [Topic]",
            "explanation": "This slide provides an overview of the key concepts and why this topic matters in today's context. Understanding these fundamentals will help you make better decisions.",
            "image_keyword": "introduction",
            "bullets": [
                "First key point with clear insight",
                "Second key point with actionable takeaway",
                "Third key point that adds value"
            ]
        }},
        {{
            "slide_number": 2,
            "heading": "Main Topic Area",
            "explanation": "This section explores the core aspects of the topic, providing context and real-world applications that demonstrate its importance.",
            "image_keyword": "business",
            "bullets": [
                "Important insight with supporting detail",
                "Key strategy that drives results",
                "Critical factor for success",
                "Measurable outcome to track"
            ]
        }}
    ]
}}

Now generate for: {user_input}
Number of slides: {num_slides}
"""

def clean_json(text: str) -> str:
    """Clean JSON-like response from an LLM into best-effort JSON string."""
    if not text:
        return ""

    text = text.strip()

    # Remove markdown code fences if present
    if "```json" in text:
        text = text.split("```json", 1)[1]
        if "```" in text:
            text = text.split("```", 1)[0]
    elif "```" in text:
        text = text.split("```", 1)[1]
        if "```" in text:
            text = text.split("```", 1)[0]

    text = text.strip()

    # Extract first {...} block
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        text = text[start : end + 1]

    # Remove some common trailing-comma issues
    text = re.sub(r",\s*}", "}", text)
    text = re.sub(r",\s*]", "]", text)

    return text


def validate_and_fix_slides(result: dict, expected_slides: int) -> dict | None:
    """Normalize slides: count, numbering, intro + conclusion, required fields."""
    if not result or "slides" not in result or not isinstance(result["slides"], list):
        return None

    slides = result["slides"]
    topic = result.get("title", "the topic")

    # Trim or pad to expected_slides
    if len(slides) > expected_slides:
        slides = slides[:expected_slides]
    elif len(slides) < expected_slides:
        for i in range(len(slides), expected_slides):
            slides.append({
                "slide_number": i + 1,
                "heading": f"Extra Insight {i+1}",
                "explanation": (
                    f"This slide adds additional context about {topic}, "
                    "helping you deepen your understanding."
                ),
                "image_keyword": "business",
                "bullets": [
                    "Additional point for better understanding",
                    "Another practical implication",
                    "Key reminder about this concept",
                ],
            })

    # Re‑enforce numbering 1..expected_slides and required fields
    for idx, slide in enumerate(slides):
        slide["slide_number"] = idx + 1

        if not slide.get("heading"):
            slide["heading"] = f"Slide {idx+1}"

        if not slide.get("explanation"):
            slide["explanation"] = (
                f"This slide covers important aspects of {slide['heading']}. "
                "Understanding these points will help you apply the concepts effectively."
            )

        if not slide.get("image_keyword"):
            slide["image_keyword"] = "business"

        bullets = slide.get("bullets") or []
        if not isinstance(bullets, list) or len(bullets) == 0:
            bullets = [
                "Key insight about this topic",
                "Important factor to consider",
                "Actionable takeaway for you",
            ]
        # max 5 bullets
        bullets = bullets[:5]
        slide["bullets"] = bullets

    # Enforce INTRO slide (slide 1)
    first = slides[0]
    if not first.get("heading") or "intro" not in first["heading"].lower():
        first["heading"] = f"Introduction to {topic}"

    first["explanation"] = (
        f"This slide introduces {topic} and explains why it matters in today's context. "
        "It sets the stage for the rest of the presentation."
    )
    first["image_keyword"] = first.get("image_keyword") or "introduction"

    # Enforce CONCLUSION slide (last slide)
    last = slides[-1]
    last["slide_number"] = expected_slides
    last["heading"] = "Conclusion & Key Takeaways"
    last["explanation"] = (
        f"In conclusion, {topic} presents key opportunities and challenges. "
        "By applying these insights, you can achieve better outcomes and drive meaningful results."
    )
    last["image_keyword"] = last.get("image_keyword") or "success"
    last["bullets"] = [
        "Review the main concepts and examples discussed",
        "Identify 1–2 ideas to implement immediately",
        "Share these insights with your team or stakeholders",
        "Continue learning and refining your approach",
    ][:4]

    result["slides"] = slides
    return result


def generate_with_gemini(user_input: str, num_slides: int) -> dict | None:
    """Generate content using Gemini 2.0 Flash."""
    try:
        prompt = PROMPT_TEMPLATE.format(
            user_input=user_input,
            num_slides=num_slides,
        )
        print(f"📡 Calling Gemini API for: {user_input[:50]}...")

        response = gemini_client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
        )

        text = clean_json(response.text)
        result = json.loads(text)

        result = validate_and_fix_slides(result, num_slides)

        if result:
            print(f"✅ Gemini succeeded! Generated {len(result.get('slides', []))} slides")
        return result

    except Exception as e:
        print(f"❌ Gemini failed: {e}")
        return None


def generate_with_groq(user_input: str, num_slides: int) -> dict | None:
    """Generate content using Groq Llama 3.3 with JSON mode."""
    try:
        prompt = PROMPT_TEMPLATE.format(
            user_input=user_input,
            num_slides=num_slides,
        )
        print(f"📡 Calling Groq API for: {user_input[:50]}...")

        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": "You are a professional presentation designer.",
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            temperature=0.7,
            max_tokens=4000,
            # JSON mode – forces pure JSON string in message.content
            response_format={"type": "json_object"},  # supported for this model[web:6][web:12]
        )

        text = response.choices[0].message.content
        result = json.loads(text)

        result = validate_and_fix_slides(result, num_slides)

        if result:
            print(f"✅ Groq succeeded! Generated {len(result.get('slides', []))} slides")
        return result

    except Exception as e:
        print(f"❌ Groq failed: {e}")
        return None


def generate_from_text(raw_text: str, num_slides: int) -> dict:
    """Generate slide content from extracted text (URL, PDF, DOCX)."""

    if len(raw_text) > 8000:
        raw_text = raw_text[:8000]

    prompt = f"""You are a professional presentation designer. Create a presentation from this text:

--- START OF TEXT ---
{raw_text}
--- END OF TEXT ---

Generate EXACTLY {num_slides} slides with:
1. Title slide (extract or create a compelling title)
2. Introduction slide (explain what the text is about)
3. {num_slides-2} content slides extracting key information
4. Conclusion slide with key takeaways

IMPORTANT: Each slide MUST have:
- A clear heading
- 1-2 sentences of explanation (NOT just bullets!)
- 3-5 bullet points for key details
- An image_keyword (single word for Unsplash)

For the Conclusion slide:
- Heading: "Conclusion & Key Takeaways"
- Explanation paragraph summarizing main points
- 3-4 bullet points as action items

Return ONLY valid JSON in this format:
{{
    "title": "Presentation Title",
    "slides": [
        {{
            "slide_number": 1,
            "heading": "Section Heading",
            "explanation": "This section provides context and explains why this matters...",
            "image_keyword": "keyword",
            "bullets": ["Point 1", "Point 2", "Point 3"]
        }}
    ]
}}"""

    # Try Gemini first
    try:
        print("📡 Generating from text with Gemini...")
        response = gemini_client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
        )

        text = clean_json(response.text)
        result = json.loads(text)
        result = validate_and_fix_slides(result, num_slides)

        if result:
            print("✅ Text generation with Gemini succeeded!")
            return result

    except Exception as e:
        print(f"❌ Gemini text generation failed: {e}")

    # Try Groq as fallback
    try:
        print("📡 Trying Groq for text generation...")
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": "You are a professional presentation designer.",
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            temperature=0.7,
            max_tokens=4000,
            response_format={"type": "json_object"},
        )

        text = response.choices[0].message.content
        result = json.loads(text)
        result = validate_and_fix_slides(result, num_slides)

        if result:
            print("✅ Groq text generation succeeded!")
            return result

    except Exception as e2:
        print(f"❌ Groq text generation failed: {e2}")

    # Fallback content if all fails
    return generate_fallback_content("Document Content", num_slides)


def generate_fallback_content(topic: str, num_slides: int) -> dict:
    """Fallback content if all AI calls fail."""

    slides = []

    # Introduction slide
    slides.append({
        "slide_number": 1,
        "heading": f"Introduction to {topic}",
        "explanation": (
            f"This presentation explores the key aspects of {topic}, providing valuable "
            "insights and actionable strategies. Understanding this topic is essential "
            "for success in today's environment."
        ),
        "image_keyword": "introduction",
        "bullets": [
            f"What you need to know about {topic}",
            "Key challenges and opportunities",
            "Real-world applications and examples",
            "Benefits of mastering this topic",
        ],
    })

    # Middle content slides
    middle_count = max(2, num_slides - 2)
    for i in range(middle_count):
        slides.append({
            "slide_number": i + 2,
            "heading": f"Key Insight {i+1}",
            "explanation": (
                f"This section covers critical aspects of {topic} that will help you "
                "understand and apply the concepts effectively in real situations."
            ),
            "image_keyword": "business",
            "bullets": [
                "Important factor to consider for success",
                "Strategy that drives measurable results",
                "Common pitfall to avoid",
                "Best practice from industry leaders",
            ],
        })

    # Conclusion slide
    slides.append({
        "slide_number": num_slides,
        "heading": "Conclusion & Key Takeaways",
        "explanation": (
            f"In conclusion, {topic} offers significant opportunities for growth and "
            "innovation. By applying these insights, you can achieve better outcomes."
        ),
        "image_keyword": "success",
        "bullets": [
            "Take action on these key insights",
            "Implement strategies incrementally",
            "Measure results and iterate",
            "Continue learning and adapting",
        ],
    })

    return {
        "title": f"Understanding {topic}",
        "slides": slides,
    }


def generate_slide_content(user_input: str, num_slides: int = 8) -> dict:
    """
    Main function to generate slide content.
    Tries Gemini first, then Groq as fallback, then static fallback.
    """
    print(f"\n🎨 Generating {num_slides} slides for: {user_input[:50]}...")

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
