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
            "bullets": [
                "First key point",
                "Second key point",
                "Third key point"
            ]
        }}
    ]
}}

Rules:
- First slide is always the intro/title slide
- Last slide is always Thank You or Conclusion
- Each slide maximum 4 bullet points
- Keep bullet points short and punchy
- image_keyword must be a single simple English word relevant to the slide topic
- Make it professional and engaging
"""

def clean_json(text):
    text = text.strip()
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0].strip()
    elif "```" in text:
        text = text.split("```")[1].split("```")[0].strip()
    start = text.find("{")
    end = text.rfind("}") + 1
    if start != -1 and end != 0:
        text = text[start:end]
    return text

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
        return json.loads(text)
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
        return json.loads(text)
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
