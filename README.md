# 🚀 SlideBot
### AI-Powered PowerPoint Slides Generator.

**SlideBot** transforms simple text prompts into professional, structured PowerPoint presentations in seconds. Built for students, educators, and professionals who need to create compelling slide decks quickly.

---

## 🧠 Tech Stack

- **Language:** Python
- **AI Integration:** Gemini / GROQ API (configurable)
- **Output:** `.pptx` format via `python-pptx`
- **Deployment Ready:** Includes `Procfile` for cloud hosting

---

## ✨ Key Features

- **Instant Generation:** Go from topic to slide deck in one command.
- **AI-Powered Structuring:** Automatically organizes content into logical slide flows with titles, bullet points, and sections.
- **Multiple Builders:** Supports different slide templates (standard, magazine-style).
- **Database Backend:** Stores generation history (via `database.py`) for tracking and reusability.
- **Modular Design:** Clean separation of AI logic (`ai_engine.py`), slide construction (`slide_builder.py`), and bot interface (`bot.py`).

---

## 🎯 Use Cases

- **Academic:** Students creating presentations for projects and lectures.
- **Business:** Professionals drafting pitch decks and client reports.
- **Content Creation:** Speakers and educators developing course materials.
- **Rapid Prototyping:** Quickly visualize ideas in presentation format.

---

## 🚦 Project Status

**Active Development** — Core generation engine is functional, with ongoing enhancements to templates, AI integration, and user interface.

| Area | Status |
|------|--------|
| Core Generation | ✅ Functional |
| AI Integration | ✅ Gemini/GROQ supported |
| Slide Templates | ✅ Standard & Magazine styles |
| Database Logging | ✅ Implemented |
| Cloud Deployment | ✅ Configured (Procfile) |
| Web Interface | 🔜 Planned |
| Custom Templates | 🔜 Planned |

---

## 👨‍💻 Developer

**Abdullah A-Amuda**  
Computer Engineering Student, ABU Zaria  
Airtel Africa Foundation Fellow  
[GitHub](https://github.com/abdullahaamuda-code)

---

## 🔗 Repository

**[https://github.com/abdullahaamuda-code/SlideBot/](https://github.com/abdullahaamuda-code/SlideBot/)**

---

## 🛠️ Local Setup

```bash
# Clone the repository
git clone https://github.com/abdullahaamuda-code/SlideBot.git
cd SlideBot

# Install dependencies
pip install -r requirements.txt

# Set up your API keys (Gemini/GROQ)
# Run the bot
python bot.py
