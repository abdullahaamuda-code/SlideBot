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

def clean_json(text):
    """Clean JSON response from AI"""
    text = text.strip()
    # Remove markdown code blocks
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0].strip()
    elif "```" in text:
        text = text.split("```")[1].split("```")[0].strip()
    
    # Extract JSON object
    start = text.find("{")
    end = text.rfind("}") + 1
    if start != -1 and end != 0:
        text = text[start:end]
    
    # Fix common JSON issues
    text = re.sub(r',\s*}', '}', text)  # Remove trailing commas
    text = re.sub(r',\s*]', ']', text)  # Remove trailing commas in arrays
    
    return text

def generate_with_gemini(user_input, num_slides):
    """Generate content using Gemini 2.0 Flash"""
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
        
        text = clean_json(response.text)
        result = json.loads(text)
        
        # Validate and fix structure
        result = validate_and_fix_slides(result, num_slides)
        
        print(f"✅ Gemini succeeded! Generated {len(result.get('slides', []))} slides")
        return result
        
    except Exception as e:
        print(f"❌ Gemini failed: {e}")
        return None

def generate_with_groq(user_input, num_slides):
    """Generate content using Groq Llama 3.3"""
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
        
        text = clean_json(response.choices[0].message.content)
        result = json.loads(text)
        
        # Validate and fix structure
        result = validate_and_fix_slides(result, num_slides)
        
        print(f"✅ Groq succeeded! Generated {len(result.get('slides', []))} slides")
        return result
        
    except Exception as e:
        print(f"❌ Groq failed: {e}")
        return None

def validate_and_fix_slides(result, expected_slides):
    """Ensure slides have all required fields"""
    if not result or "slides" not in result:
        return None
    
    fixed_slides = []
    for i, slide in enumerate(result["slides"]):
        # Ensure explanation field exists
        if "explanation" not in slide or not slide["explanation"]:
            slide["explanation"] = f"This slide covers important aspects of {slide.get('heading', 'the topic')}. Understanding these key points will help you apply these concepts effectively."
        
        # Ensure image_keyword exists
        if "image_keyword" not in slide or not slide["image_keyword"]:
            slide["image_keyword"] = "business"
        
        # Ensure bullets exist and have proper count
        if "bullets" not in slide or not slide["bullets"]:
            slide["bullets"] = [
                "Key insight about this topic",
                "Important factor to consider",
                "Actionable takeaway for you"
            ]
        
        # Limit bullets to 5 max
        if len(slide["bullets"]) > 5:
            slide["bullets"] = slide["bullets"][:5]
        
        fixed_slides.append(slide)
    
    result["slides"] = fixed_slides
    return result

def generate_from_text(raw_text, num_slides):
    """Generate slide content from extracted text (URL, PDF, DOCX)"""
    
    # Truncate if too long
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

    try:
        print("📡 Generating from text with Gemini...")
        response = gemini_client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt
        )
        
        text = clean_json(response.text)
        result = json.loads(text)
        result = validate_and_fix_slides(result, num_slides)
        
        if result:
            print(f"✅ Text generation succeeded!")
            return result
            
    except Exception as e:
        print(f"❌ Gemini text generation failed: {e}")
        
        # Try Groq as fallback
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
            
            text = clean_json(response.choices[0].message.content)
            result = json.loads(text)
            result = validate_and_fix_slides(result, num_slides)
            
            if result:
                print(f"✅ Groq text generation succeeded!")
                return result
                
        except Exception as e2:
            print(f"❌ Groq text generation failed: {e2}")
    
    # Fallback content if all fails
    return generate_fallback_content("Document Content", num_slides)

def generate_fallback_content(topic, num_slides):
    """Fallback content if AI fails"""
    slides = []
    
    # Introduction slide
    slides.append({
        "slide_number": 1,
        "heading": f"Introduction to {topic}",
        "explanation": f"This presentation explores the key aspects of {topic}, providing valuable insights and actionable strategies. Understanding this topic is essential for success in today's environment.",
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
            "explanation": f"This section covers critical aspects of {topic} that will help you understand and apply the concepts effectively in real situations.",
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
    
    return {
        "title": f"Understanding {topic}",
        "slides": slides
    }

def generate_slide_content(user_input, num_slides=8):
    """
    Main function to generate slide content
    Tries Gemini first, then Groq as fallback
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
