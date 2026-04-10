import os
import json
import time
from groq import Groq, RateLimitError, APIError

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
client = Groq(api_key=GROQ_API_KEY)

# Use this active model instead
ACTIVE_MODEL = "llama-3.3-70b-versatile"  # or "llama-3.1-8b-instant"

def call_groq_with_retry(messages, max_tokens=4000, retries=3):
    """Call Groq API with automatic retry logic using active model"""
    
    for attempt in range(retries):
        try:
            response = client.chat.completions.create(
                model=ACTIVE_MODEL,  # Changed from mixtral-8x7b-32768
                messages=messages,
                temperature=0.7,
                max_tokens=max_tokens,
                timeout=90
            )
            return response.choices[0].message.content
            
        except RateLimitError as e:
            wait_time = (2 ** attempt) + (attempt * 0.5)
            print(f"⚠️ Rate limit hit (attempt {attempt+1}/{retries}), waiting {wait_time}s...")
            time.sleep(wait_time)
            
        except APIError as e:
            if "timeout" in str(e).lower():
                print(f"⚠️ Timeout, retrying... (attempt {attempt+1}/{retries})")
                time.sleep(2)
            else:
                print(f"❌ API Error: {e}")
                if attempt == retries - 1:
                    raise
                time.sleep(1)
                
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            if attempt == retries - 1:
                raise
            time.sleep(2)
    
    raise Exception("All retries exhausted")

def generate_slide_content(topic: str, num_slides: int) -> dict:
    """Generate slide content using active Groq model"""
    
    content_slides = max(3, num_slides - 2)
    
    prompt = f"""You are a professional presentation designer. Create a PowerPoint presentation about "{topic}".

Generate EXACTLY {num_slides} slides with:
- Slide 1: Title slide with creative title
- Slides 2 to {num_slides - 1}: Content slides ({content_slides} slides)
- Final slide: Conclusion & Key Takeaways

Each content slide should have:
- A clear heading
- 3-4 bullet points (keep each under 15 words)
- An image keyword (e.g., "technology", "teamwork", "growth")

Keep content concise, professional, and actionable.

Return ONLY valid JSON in this exact format:

{{
  "title": "Presentation Title",
  "slides": [
    {{
      "heading": "Section Heading",
      "bullets": ["Point 1", "Point 2", "Point 3"],
      "image_keyword": "relevant_keyword"
    }}
  ]
}}"""

    try:
        result = call_groq_with_retry(
            messages=[
                {"role": "system", "content": "You are an expert presentation designer. Return ONLY valid JSON. No markdown, no extra text."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=4000
        )
        
        # Clean and parse JSON
        result = result.replace("```json", "").replace("```", "").strip()
        
        # Remove any leading/trailing non-JSON text
        import re
        json_match = re.search(r'\{.*\}', result, re.DOTALL)
        if json_match:
            result = json_match.group(0)
        
        slide_data = json.loads(result)
        
        # Ensure we have the right number of slides
        if len(slide_data.get("slides", [])) < num_slides - 1:
            # Add placeholder slides if needed
            current_slides = slide_data["slides"]
            while len(current_slides) < num_slides - 1:
                current_slides.append({
                    "heading": f"Key Insight {len(current_slides)+1}",
                    "bullets": [
                        "Important consideration for success",
                        "Actionable strategy to implement",
                        "Measurable outcome to track"
                    ],
                    "image_keyword": "business"
                })
            slide_data["slides"] = current_slides
        
        return slide_data
        
    except Exception as e:
        print(f"❌ Generation failed after retries: {e}")
        return generate_fallback_content(topic, num_slides)


def generate_from_text(raw_text: str, num_slides: int) -> dict:
    """Generate slide content from extracted text using active model"""
    
    if len(raw_text) > 8000:
        raw_text = raw_text[:8000]
    
    content_slides = max(3, num_slides - 2)
    
    prompt = f"""Create a PowerPoint presentation from this text:

--- TEXT ---
{raw_text}
--- END TEXT ---

Generate EXACTLY {num_slides} slides with:
- Title slide
- {content_slides} content slides extracting key information
- Conclusion slide

Each content slide needs: heading, 3-4 concise bullet points, image keyword.

Return ONLY valid JSON:
{{
  "title": "Presentation Title",
  "slides": [
    {{"heading": "Heading", "bullets": ["point1", "point2", "point3"], "image_keyword": "keyword"}}
  ]
}}"""

    try:
        result = call_groq_with_retry(
            messages=[
                {"role": "system", "content": "You are an expert at summarizing text into presentations. Return ONLY valid JSON."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=4000
        )
        
        result = result.replace("```json", "").replace("```", "").strip()
        
        import re
        json_match = re.search(r'\{.*\}', result, re.DOTALL)
        if json_match:
            result = json_match.group(0)
        
        slide_data = json.loads(result)
        
        if not slide_data.get("title"):
            slide_data["title"] = "Document Summary"
        
        return slide_data
        
    except Exception as e:
        print(f"❌ Text generation failed: {e}")
        return generate_fallback_content("Document Content", num_slides)


def generate_fallback_content(topic: str, num_slides: int) -> dict:
    """Fallback content if AI fails"""
    slides = []
    
    slides.append({
        "heading": f"Introduction to {topic}",
        "bullets": [
            f"Understanding the importance of {topic}",
            "Key challenges and opportunities",
            "What you'll learn from this presentation",
            "Real-world applications and case studies"
        ],
        "image_keyword": "introduction"
    })
    
    middle_slides = max(2, num_slides - 3)
    for i in range(middle_slides):
        slides.append({
            "heading": f"Key Aspect {i+1}",
            "bullets": [
                f"Important factor to consider",
                "How this impacts your strategy",
                "Best practices and proven approaches",
                "Common mistakes to avoid"
            ],
            "image_keyword": "business"
        })
    
    slides.append({
        "heading": "Conclusion & Next Steps",
        "bullets": [
            "Key takeaways from this presentation",
            "Actionable strategies to implement",
            "Resources for further learning",
            "Ready to take the next step"
        ],
        "image_keyword": "success"
    })
    
    return {
        "title": f"Understanding {topic}",
        "slides": slides
    }
