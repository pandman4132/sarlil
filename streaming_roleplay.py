"""Streaming roleplay helper for Tkinter + modern OpenAI client.

Usage:
    from streaming_roleplay import stream_ai_roleplay
    # call `stream_ai_roleplay(prompt, chat_box, entry_widget, model="gpt-4o-mini")`

Set your `OPENAI_API_KEY` in the environment before running the GUI.
"""
import os
import re
import threading
import traceback
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Do not hardcode API keys in source. Create the client lazily using the
# `OPENAI_API_KEY` environment variable. `client` is set to `None` here and
# will be initialized inside the worker on first use.
client = None

SYSTEM_ROLEPLAY = (
    "You are two demi-human cat-like sisters in a modern city alley at night. "
    "CHARACTERS:\n"
    "Sarah (16): Older sister, protective and defensive. Distrustful of humans. She stands between Lily and danger. "
    "Speaks cautiously, sometimes sharply. Her tone is guarded, her body language tense. She leads decisions.\n"
    "Lily (14): Younger sister, timid and anxious. Emotionally dependent on Sarah. Curious but afraid. "
    "Speaks softly, hesitates, may stutter. She looks to Sarah for safety.\n"
    "SCENARIO:\n"
    "You are both in a dim, cramped alley searching for food in garbage. The air is thick with humidity and the smell of refuse. "
    "Distant traffic echoes from the main street. A flickering streetlight casts long shadows. You've just been discovered by the user. "
    "Sarah is immediately protective and cautious. Lily trembles and hides behind her sister.\n"
    "FORMATTING RULES:\n"
    "For speech (dialogue): Sarah: \"your dialogue here\" or Lily: \"your dialogue here\"\n"
    "For actions/narration: Use *asterisks* like *Sarah steps protectively in front of Lily* or *the alley is quiet except for distant traffic*\n"
    "For mixed content: Sarah: \"speech\" or Sarah: *action* or Sarah: *action* \"speech\"\n"
    "TONE & BEHAVIOR:\n"
    "Keep everything grounded and realistic. Show subtle vulnerability beneath the fear and defensiveness. "
    "Sarah reacts first with caution and protectiveness. Lily stays behind her or reacts quietly. "
    "Dialogue is natural and short, never over-the-top. Maintain immersion. Do not introduce yourselves or explain the situation. "
    "Show physical reactions: ears flattening, tails curling, trembling. React to the user's presence and actions realistically. "
    "The sisters are NOT safe, NOT comfortable, and NOT trusting."
)


def _insert_with_tag(chat_box, text, tag=None):
    """Insert text into `chat_box` on the Tk main thread with optional tag."""
    def do_insert():
        if tag:
            chat_box.insert("end", text, tag)
        else:
            chat_box.insert("end", text)
        chat_box.see("end")
    chat_box.after(0, do_insert)


def _insert_chunk_by_label(chat_box, chunk):
    """Heuristic: if chunk begins with `Sarah:` or `Lily:` tag that label.
    If it begins with [Scene: ], or is wrapped in *, tag as scene and strip markers.
    Falls back to `ai` tag for unlabelled text.
    """
    s = chunk
    # Check for Sarah/Lily dialogue
    m = re.match(r"^(\s*(Sarah:|Lily:))", s, flags=re.IGNORECASE)
    if m:
        label = m.group(2).capitalize()
        rest = s[m.end():]
        # Strip surrounding quotes from speech
        rest = rest.strip()
        if rest.startswith('"') and rest.endswith('"'):
            rest = rest[1:-1]
        tag = "sarah" if label == "Sarah" else "lily"
        _insert_with_tag(chat_box, m.group(1), tag)
        if rest:
            _insert_with_tag(chat_box, rest, "ai")  # Speech in bold white
    else:
        # Check for scene description [Scene: ] or *text*
        scene_m = re.match(r"^(\s*\[Scene:\s*)", s, flags=re.IGNORECASE)
        if scene_m:
            rest = s[scene_m.end():]
            _insert_with_tag(chat_box, scene_m.group(1), "scene")
            if rest:
                _insert_with_tag(chat_box, rest, "scene")
        elif s.strip().startswith('*') and s.strip().endswith('*'):
            # Strip * and tag as scene
            cleaned = s.strip()[1:-1] if len(s.strip()) > 1 else s
            _insert_with_tag(chat_box, cleaned, "scene")
        else:
            _insert_with_tag(chat_box, s, "ai")


def stream_ai_roleplay(prompt, callback, on_done=None, model="gpt-4o-mini"):
    """Stream a roleplayed AI response and call callback with each text chunk.

    - `callback` is a function that takes a string chunk and processes it.
    """
    def worker():
        global client
        messages = [{"role": "system", "content": SYSTEM_ROLEPLAY}]
        messages.append({"role": "user", "content": prompt})
        try:
            if client is None:
                client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

            # Use generator-style streaming (more reliable)
            resp = client.chat.completions.create(model=model, messages=messages, stream=True)
            for chunk in resp:
                try:
                    if hasattr(chunk, 'choices') and chunk.choices:
                        c0 = chunk.choices[0]
                        if hasattr(c0, 'delta') and c0.delta and hasattr(c0.delta, 'content'):
                            text = c0.delta.content or ""
                            if text:
                                callback(text)
                except Exception:
                    pass
        except Exception as exc:
            callback(f"\n[stream error: {exc}]\n")
            traceback.print_exc()
        finally:
            if on_done:
                on_done()

    threading.Thread(target=worker, daemon=True).start()


if __name__ == "__main__":
    # quick smoke test when run directly
    print("streaming_roleplay module loaded")
    print("OPENAI_API_KEY present:", bool(os.getenv("OPENAI_API_KEY")))
