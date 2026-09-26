# SlideBot

Text prompt in, structured PowerPoint deck out — in seconds.

SlideBot turns a simple prompt into a real presentation: the model plans the slide
flow (titles, bullets, sections), builders render it to `.pptx`, and a small database
keeps your generation history. Built for students, educators, and professionals who
need a finished deck fast.

## How it works

1. You give it a topic or a prompt.
2. The AI engine (`ai_engine.py`, Gemini / Groq — configurable) structures the
   content into a logical slide flow.
3. The builder (`slide_builder.py`) renders the deck to `.pptx` via `python-pptx` —
   standard and magazine-style templates.

## Features

- **One command, one deck** — topic to finished slides, no manual assembly.
- **AI structuring** — titles, bullets, and sections organized by the model.
- **Multiple builders** — standard and magazine-style slide templates.
- **Generation history** — every deck logged (`database.py`) for tracking and reuse.
- **Deployment ready** — ships with a `Procfile` for cloud hosting.

## Use cases

- **Academic** — lectures, projects, seminar decks.
- **Business** — pitch decks and client reports.
- **Content** — course material and talk prep.
- **Prototyping** — visualize an idea in presentation form before building it.

## Status

| Area | Status |
|------|--------|
| Core generation | working |
| AI integration | Gemini / Groq |
| Slide templates | standard & magazine |
| Database logging | done |
| Cloud deployment | configured (Procfile) |
| Web interface | planned |
| Custom templates | planned |

## Setup

```bash
git clone https://github.com/abdullahaamuda-code/SlideBot.git
cd SlideBot
pip install -r requirements.txt
# add your Gemini/Groq keys, then:
python bot.py
```

## Why

Deck assembly is mechanical work models do well — but only when the structure is
decided first. SlideBot decides the structure, then lets the AI fill it. That's the
difference between a deck and a dump.

## License

[MIT](LICENSE)
---

Built by Abdullah A-Amuda.
