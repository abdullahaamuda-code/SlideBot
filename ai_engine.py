import os
import json
from groq import Groq

# Initialize Groq client
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
client = Groq(api_key=GROQ_API_KEY)

def generate_slide_content(topic: str, num_slides: int) -> dict:
    """
    Generate structured slide content using Groq AI
    Returns a dict with title, slides (heading, bullets, notes)
    """
    
    # Adjust slide count (include intro and conclusion)
    content_slides = max(3, num_slides - 2)  # Subtract intro and conclusion
    
    prompt = f"""You are a professional presentation designer. Create a complete PowerPoint presentation about "{topic}".

Generate EXACTLY {num_slides} slides with this structure:
- Slide 1: Title slide with creative title and subtitle
- Slides 2 to {num_slides - 1}: Content slides (total of {content_slides} content slides)
- Final slide: Conclusion & Call to Action

IMPORTANT RULES:
1. Each content slide MUST have:
   - A clear heading
   - 2-3 sentences of explanation/context (NOT just bullets!)
   - 3-4 bullet points for key takeaways
   - An image keyword (e.g., "technology", "teamwork", "growth")

2. The Conclusion slide MUST have:
   - Heading: "Conclusion & Key Takeaways" or similar
   - Summary paragraph (3-4 sentences summarizing main points)
   - 3-4 action items or next steps as bullets
   - Image keyword related to "success" or "future"

3. Do NOT make every slide only bullets. Mix paragraphs and bullets.

4. Make the content professional, insightful, and actionable.

Return ONLY valid JSON in this exact format:

{{
  "title": "Main Presentation Title",
  "slides": [
    {{
      "heading": "Introduction to [Topic]",
      "bullets": [
        "Key point 1 with explanation",
        "Key point 2 with explanation",
        "Key point 3 with explanation"
      ],
      "image_keyword": "abstract"
    }},
    {{
      "heading": "Slide Heading",
      "bullets": [
        "First bullet point with context",
        "Second bullet point with context",
        "Third bullet point with context"
      ],
      "image_keyword": "relevant_keyword"
    }}
  ]
}}

Generate {num_slides} slides total (title slide will be handled separately, so provide {num_slides - 1} content slides including conclusion)."""

    try:
        response = client.chat.completions.create(
            model="mixtral-8x7b-32768",
            messages=[
                {"role": "system", "content": "You are an expert presentation designer. Create engaging, well-structured PowerPoint content with a mix of explanatory text and bullet points. Always include proper conclusions."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=4000
        )
        
        result = response.choices[0].message.content
        # Clean up JSON (remove markdown code blocks if present)
        result = result.replace("```json", "").replace("```", "").strip()
        
        slide_data = json.loads(result)
        
        # Ensure we have the right number of slides
        if len(slide_data.get("slides", [])) < num_slides - 1:
            # Add more slides if needed
            current_slides = slide_data["slides"]
            while len(current_slides) < num_slides - 1:
                current_slides.append({
                    "heading": f"More About {topic}",
                    "bullets": [
                        "Additional insight about this topic",
                        "Another important perspective to consider",
                        "Key takeaway for your audience"
                    ],
                    "image_keyword": "business"
                })
            slide_data["slides"] = current_slides
        
        return slide_data
        
    except Exception as e:
        print(f"AI generation error: {e}")
        # Return fallback content
        return generate_fallback_content(topic, num_slides)


def generate_from_text(raw_text: str, num_slides: int) -> dict:
    """
    Generate slide content from extracted text (URL, PDF, DOCX)
    """
    
    # Truncate text if too long
    if len(raw_text) > 8000:
        raw_text = raw_text[:8000]
    
    content_slides = max(3, num_slides - 2)
    
    prompt = f"""You are a professional presentation designer. Create a PowerPoint presentation based on this text:

--- START OF TEXT ---
{raw_text}
--- END OF TEXT ---

Generate EXACTLY {num_slides} slides with this structure:
- Slide 1: Title slide (extract or create a compelling title)
- Slides 2 to {num_slides - 1}: Content slides ({content_slides} slides)
- Final slide: Conclusion & Key Takeaways

IMPORTANT RULES:
1. Extract the most important information from the text
2. Each content slide MUST have:
   - A clear heading
   - 2-3 sentences of explanation (summarizing the text)
   - 3-4 bullet points for key details
   - An image keyword related to the content

3. The Conclusion slide MUST have:
   - Heading: "Key Takeaways" or "Summary"
   - A paragraph summarizing the main points
   - 3-4 action items or recommendations as bullets

4. Do NOT make every slide only bullets. Include explanatory paragraphs.

Return ONLY valid JSON in this format:

{{
  "title": "Presentation Title",
  "slides": [
    {{
      "heading": "Section Heading",
      "bullets": [
        "Important point from the text",
        "Another key insight",
        "Supporting detail"
      ],
      "image_keyword": "relevant_keyword"
    }}
  ]
}}

Generate {num_slides - 1} content slides (including conclusion)."""

    try:
        response = client.chat.completions.create(
            model="mixtral-8x7b-32768",
            messages=[
                {"role": "system", "content": "You are an expert at summarizing text into professional presentations. Create engaging slides with a mix of paragraphs and bullet points."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=4000
        )
        
        result = response.choices[0].message.content
        result = result.replace("```json", "").replace("```", "").strip()
        
        slide_data = json.loads(result)
        
        # Add title if missing
        if not slide_data.get("title"):
            slide_data["title"] = "Presentation from Document"
        
        return slide_data
        
    except Exception as e:
        print(f"Text generation error: {e}")
        # Extract a title from the text
        title = raw_text[:50].strip() + "..."
        return generate_fallback_content(title, num_slides)


def generate_fallback_content(topic: str, num_slides: int) -> dict:
    """
    Fallback content if AI fails
    """
    slides = []
    
    # Introduction slide
    slides.append({
        "heading": f"Introduction to {topic}",
        "bullets": [
            f"Understanding the importance of {topic} in today's world",
            f"Key challenges and opportunities in this space",
            f"What you'll learn from this presentation",
            f"Real-world applications and case studies"
        ],
        "image_keyword": "introduction"
    })
    
    # Middle content slides
    middle_slides = max(2, num_slides - 3)
    for i in range(middle_slides):
        slides.append({
            "heading": f"Key Aspect {i+1} of {topic}",
            "bullets": [
                f"Important factor to consider about {topic}",
                f"How this impacts your strategy and decisions",
                f"Best practices and proven approaches",
                f"Common mistakes to avoid"
            ],
            "image_keyword": "business"
        })
    
    # Conclusion slide
    slides.append({
        "heading": "Conclusion & Key Takeaways",
        "bullets": [
            f"{topic} offers significant opportunities for growth",
            "Implement these strategies for better results",
            "Stay updated with latest trends and developments",
            "Take action today to leverage these insights"
        ],
        "image_keyword": "success"
    })
    
    return {
        "title": f"Understanding {topic}",
        "slides": slides
    }


# Optional: Function to add explanatory paragraphs to slides
def enhance_slide_with_paragraph(slide_data: dict) -> dict:
    """
    Add explanatory paragraphs to slides that only have bullets
    """
    for slide in slide_data.get("slides", []):
        if "paragraph" not in slide:
            # Generate a paragraph from the heading and first bullet
            heading = slide.get("heading", "")
            bullets = slide.get("bullets", [])
            if bullets:
                slide["paragraph"] = f"{heading}. {bullets[0]} This section explores key insights and actionable strategies to help you succeed."
            else:
                slide["paragraph"] = f"This section covers important aspects of {heading.lower()} with practical examples and expert recommendations."
    
    return slide_data
