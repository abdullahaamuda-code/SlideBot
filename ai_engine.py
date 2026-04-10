import os
import json
import re
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

PROMPT_TEMPLATE = """Create a professional PowerPoint presentation about "{topic}" with exactly {num_slides} slides.

IMPORTANT: Each slide MUST have:
- A heading
- An explanation paragraph (2-3 sentences explaining the concept)
- 3-4 bullet points
- An image keyword (one word for Unsplash)

Slide structure:
- Slide 1: INTRODUCTION - Explain the topic and why it matters
- Slides 2 to {num_slides-1}: CONTENT SLIDES - Each with explanation + bullet points
- Slide {num_slides}: CONCLUSION - Summarize key points and give action items

Return ONLY valid JSON. No markdown.

Format:
{{
    "title": "Presentation Title",
    "slides": [
        {{
            "heading": "Introduction to [Topic]",
            "explanation": "2-3 sentences explaining what this slide covers and why it matters...",
            "bullets": ["First key point", "Second key point", "Third key point"],
            "image_keyword": "introduction"
        }}
    ]
}}"""

def clean_json(text):
    text = text.strip()
    text = re.sub(r'```json\s*|\s*```', '', text)
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        text = match.group(0)
    return text

def generate_slide_content(topic, num_slides=8):
    print(f"🎨 Generating {num_slides} slides about: {topic}")
    
    try:
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": PROMPT_TEMPLATE.format(topic=topic, num_slides=num_slides)}],
            temperature=0.7,
            max_tokens=4000
        )
        
        text = clean_json(response.choices[0].message.content)
        data = json.loads(text)
        
        # Ensure correct number of slides
        slides = data.get("slides", [])
        while len(slides) < num_slides:
            slides.append({
                "heading": f"Key Insight {len(slides)+1}",
                "explanation": f"This section explores important aspects of {topic}.",
                "bullets": ["Important point to consider", "Key strategy for success", "Actionable takeaway"],
                "image_keyword": "business"
            })
        
        data["slides"] = slides[:num_slides]
        return data
        
    except Exception as e:
        print(f"Error: {e}")
        return generate_fallback(topic, num_slides)

def generate_from_text(raw_text, num_slides=8):
    return generate_slide_content("the provided content", num_slides)

def generate_fallback(topic, num_slides):
    slides = []
    for i in range(num_slides):
        if i == 0:
            slides.append({"heading": f"Introduction to {topic}", "explanation": f"This presentation explores {topic} and its key concepts.", "bullets": ["What you need to know", "Why this matters", "What you'll learn"], "image_keyword": "introduction"})
        elif i == num_slides - 1:
            slides.append({"heading": "Conclusion", "explanation": "Key takeaways from this presentation.", "bullets": ["Review main points", "Take action", "Continue learning"], "image_keyword": "success"})
        else:
            slides.append({"heading": f"Key Point {i}", "explanation": f"Important aspect of {topic}.", "bullets": ["First insight", "Second insight", "Third insight"], "image_keyword": "business"})
    return {"title": f"About {topic}", "slides": slides}
