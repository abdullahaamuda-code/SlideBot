import os
from dotenv import load_dotenv
from google import genai
from groq import Groq
import json

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
            "image_keyword": "relevant single word for unsplash image",
            "intro_description": "1 short sentence summarizing the presentation focus.",
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
- Intro slide MUST include: a very short 1-sentence description of the whole presentation in "intro_description"
- Last slide is always a real summary: concise recap of the most important ideas, not generic advice
- Last slide MUST summarize the key ideas from the whole presentation in the bullets
- Each slide MUST have between 4 and 5 bullet points, never fewer than 4
- Bullet points must be short and punchy
- image_keyword must be a single simple English noun relevant to the slide topic (e.g. "teamwork", "growth", "innovation")
- Make it professional and engaging
- Do not include any explanations, markdown, comments, or extra text outside the JSON object
"""

def clean_json(text):
    text = text.strip()
    if "```json" in text:
        text = text.split("```json").split("```").strip()[1]
    elif "```" in text:
        text = text.split("```")[1].split("```")[0].strip()
    start = text.find("{")
    end = text.rfind("}") + 1
    if start != -1 and end != 0:
        text = text[start:end]
    return text

def enforce_summary_and_bullets(struct):
    """
    Safety net:
    - Ensure last slide is a proper summary (not 'review the main concepts...')
    - Ensure 4–5 bullets per slide by trimming or padding if necessary
    """
    slides = struct.get("slides", [])

    for i, slide in enumerate(slides):
        bullets = slide.get("bullets", []) or []

        # Ensure between 4 and 5 bullets
        if len(bullets) < 4:
            last_text = bullets[-1] if bullets else "Key idea"
            while len(bullets) < 4:
                bullets.append(last_text)
        elif len(bullets) > 5:
            bullets = bullets[:5]
        slide["bullets"] = bullets

    if slides:
        last_slide = slides[-1]
        # If last slide is too generic, overwrite bullets with a clearer summary
        generic_phrases = [
            "review the main concepts",
            "review key ideas",
            "reflect on the concepts discussed",
            "you have learned",
        ]
        joined = " ".join(last_slide.get("bullets", [])).lower()
        if any(p in joined for p in generic_phrases):
            # Replace with a generic but proper summary scaffold
            last_slide["bullets"] = [
                "Recap the core topic and its importance",
                "Highlight the main ideas covered in the slides",
                "Emphasize the most practical takeaways",
                "Encourage applying these concepts in real situations",
            ]

    struct["slides"] = slides
    return struct

def generate_with_gemini(user_input, num_slides):
    try:
        prompt = PROMPT_TEMPLATE.format(
            user_input=user_input,
            num_slides=num_slides
        )
        response = gemini_client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt
        )
        text = clean_json(response.text)
        data = json.loads(text)
        return enforce_summary_and_bullets(data)
    except Exception as e:
        print(f"Gemini failed: {e}")
        return None

def generate_with_groq(user_input, num_slides):
    try:
        prompt = PROMPT_TEMPLATE.format(
            user_input=user_input,
            num_slides=num_slides
        )
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        text = clean_json(response.choices[0].message.content)
        data = json.loads(text)
        return enforce_summary_and_bullets(data)
    except Exception as e:
        print(f"Groq failed: {e}")
        return None

def generate_slide_content(user_input, num_slides=8):
    print("Trying Gemini...")
    result = generate_with_gemini(user_input, num_slides)
    if result:
        print("Gemini succeeded ✅")
        return result

    print("Trying Groq...")
    result = generate_with_groq(user_input, num_slides)
    if result:
        print("Groq succeeded ✅")
        return result

    print("All AIs failed ❌")
    return None
