from streaming_roleplay import stream_ai_roleplay
import json
import threading
import os
import traceback
import random
import tkinter as tk
from tkinter import ttk
from dotenv import load_dotenv

load_dotenv()

# Constants
BG_COLOR = "#1e1e1e"
FG_COLOR = "#ffffff"
USER_BUBBLE_COLOR = "#4FC3F7"
AI_BUBBLE_COLOR = "#A5D6A7"
SARAH_BUBBLE_COLOR = "#A5D6A7"
LILY_BUBBLE_COLOR = "#FFF59D"
SCENE_COLOR = "#cccccc"
FONT_FAMILY = ("Segoe UI", "Arial", "Helvetica")
FONT_SIZE = 11

# Memory and state
memory_data = {
    "summary": "Sarah and Lily are staying at the user's home.",
    "events": []
}
world_state = {
    "time": "evening",
    "weather": "clear",
    "location": "user_home"
}

if os.path.exists("memory.json"):
    with open("memory.json", "r") as f:
        memory_data = json.load(f)

def save_memory():
    with open("memory.json", "w") as f:
        json.dump(memory_data, f, indent=2)

def detect_world_changes(text):
    """Detect weather and time changes in AI response text."""
    import re
    text_lower = text.lower()
    changes = {}
    
    # Weather keywords with priority (broader matches last)
    weather_keywords = {
        'rain': ['rain', 'raining', 'rainy', 'storm', 'stormy', 'downpour', 'drizzle'],
        'clear': ['clear', 'sunny', 'bright', 'cloudless', 'clear skies', 'beautiful weather'],
        'fog': ['fog', 'foggy', 'mist', 'misty', 'haze', 'hazy'],
        'snow': ['snow', 'snowing', 'snowy', 'blizzard', 'snowfall', 'snowed'],
    }
    
    # Time keywords with priority (more specific matches first)
    time_keywords = {
        'morning': ['morning', 'dawn', 'sunrise', 'early light', 'daybreak'],
        'afternoon': ['afternoon', 'midday', 'noon', 'midday sun'],
        'evening': ['evening', 'dusk', 'sunset', 'twilight', 'late afternoon'],
        'night': ['night', 'midnight', 'dark', 'darkness', 'nightfall', 'nocturnal'],
    }
    
    # Check for weather changes - use word boundary matching for better accuracy
    for weather, keywords in weather_keywords.items():
        for keyword in keywords:
            # Use word boundaries to avoid partial matches
            if re.search(r'\b' + re.escape(keyword) + r'\b', text_lower):
                changes['weather'] = weather
                break
        if 'weather' in changes:
            break
    
    # Check for time changes - use word boundary matching for better accuracy
    for time_period, keywords in time_keywords.items():
        for keyword in keywords:
            # Use word boundaries to avoid partial matches
            if re.search(r'\b' + re.escape(keyword) + r'\b', text_lower):
                changes['time'] = time_period
                break
        if 'time' in changes:
            break
    
    return changes

def parse_user_input(text):
    """Parse user input for mixed actions and speech."""
    parts = []
    i = 0
    while i < len(text):
        # Look for asterisks (action)
        if text[i] == '*':
            end = text.find('*', i + 1)
            if end != -1:
                action_text = text[i+1:end].strip()
                if action_text:
                    parts.append(('action', action_text))
                i = end + 1
            else:
                i += 1
        # Look for quotes (speech)
        elif text[i] == '"':
            end = text.find('"', i + 1)
            if end != -1:
                speech_text = text[i+1:end].strip()
                if speech_text:
                    parts.append(('speech', speech_text))
                i = end + 1
            else:
                i += 1
        else:
            # Regular text - accumulate until we hit a marker
            end = i
            while end < len(text) and text[end] not in ('*', '"'):
                end += 1
            regular_text = text[i:end].strip()
            if regular_text:
                parts.append(('narration', regular_text))
            i = end
    return parts

def parse_response(text):
    """Parse AI response into parts: action, sarah_action, sarah_speech, lily_action, lily_speech."""
    lines = text.split('\n')
    parts = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if line.startswith('*') and line.endswith('*'):
            # Action wrapped in asterisks (generic narration)
            action_text = line[1:-1].strip()
            if action_text:
                parts.append(('action', action_text))
        elif line.startswith('[Scene:'):
            # Scene description
            scene_text = line[7:].rstrip(']').strip()
            if scene_text:
                parts.append(('action', scene_text))
        elif line.startswith('Sarah:'):
            # Sarah dialogue or mixed actions/speech
            dialogue = line[6:].strip()
            if dialogue:
                # Check if it starts with a quote - if so, it's speech
                if dialogue.startswith('"'):
                    # Extract quoted speech
                    quote_end = dialogue.find('"', 1)
                    if quote_end != -1:
                        speech_text = dialogue[1:quote_end].strip()
                        if speech_text:
                            parts.append(('sarah_speech', speech_text))
                        # Check if there's more after the quote
                        remainder = dialogue[quote_end+1:].strip()
                        if remainder:
                            sub_parts = parse_user_input(remainder)
                            for sub_type, sub_text in sub_parts:
                                if sub_type == 'action':
                                    parts.append(('sarah_action', sub_text))
                                elif sub_type == 'speech':
                                    parts.append(('sarah_speech', sub_text))
                    else:
                        # Unclosed quote - treat whole thing as speech
                        parts.append(('sarah_speech', dialogue))
                elif dialogue.startswith('*'):
                    # Starts with action
                    sub_parts = parse_user_input(dialogue)
                    for sub_type, sub_text in sub_parts:
                        if sub_type == 'action':
                            parts.append(('sarah_action', sub_text))
                        elif sub_type == 'speech':
                            parts.append(('sarah_speech', sub_text))
                else:
                    # Plain text without markers - treat as action/narration
                    parts.append(('sarah_action', dialogue))
        elif line.startswith('Lily:'):
            # Lily dialogue or mixed actions/speech
            dialogue = line[5:].strip()
            if dialogue:
                # Check if it starts with a quote - if so, it's speech
                if dialogue.startswith('"'):
                    # Extract quoted speech
                    quote_end = dialogue.find('"', 1)
                    if quote_end != -1:
                        speech_text = dialogue[1:quote_end].strip()
                        if speech_text:
                            parts.append(('lily_speech', speech_text))
                        # Check if there's more after the quote
                        remainder = dialogue[quote_end+1:].strip()
                        if remainder:
                            sub_parts = parse_user_input(remainder)
                            for sub_type, sub_text in sub_parts:
                                if sub_type == 'action':
                                    parts.append(('lily_action', sub_text))
                                elif sub_type == 'speech':
                                    parts.append(('lily_speech', sub_text))
                    else:
                        # Unclosed quote - treat whole thing as speech
                        parts.append(('lily_speech', dialogue))
                elif dialogue.startswith('*'):
                    # Starts with action
                    sub_parts = parse_user_input(dialogue)
                    for sub_type, sub_text in sub_parts:
                        if sub_type == 'action':
                            parts.append(('lily_action', sub_text))
                        elif sub_type == 'speech':
                            parts.append(('lily_speech', sub_text))
                else:
                    # Plain text without markers - treat as action/narration
                    parts.append(('lily_action', dialogue))
    return parts

class ChatApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AI RP Chat")
        self.root.geometry("1000x700")
        self.root.configure(bg=BG_COLOR)
        self.root.resizable(True, True)

        # Time progression tracking
        self.interaction_count = 0
        self.next_time_change = random.randint(2, 5)
        self.time_progression = ["morning", "afternoon", "evening", "night"]

        # Main frame with grid
        self.main_frame = tk.Frame(root, bg=BG_COLOR)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Configure grid: 2 columns, 2 rows
        self.main_frame.columnconfigure(0, weight=3)  # Chat area
        self.main_frame.columnconfigure(1, weight=1)  # Side panel
        self.main_frame.rowconfigure(0, weight=1)     # Chat + side
        self.main_frame.rowconfigure(1, weight=0)     # Input

        # Chat area (Canvas + Frame)
        self.chat_canvas = tk.Canvas(self.main_frame, bg=BG_COLOR, highlightthickness=0)
        self.chat_scrollbar = ttk.Scrollbar(self.main_frame, orient="vertical", command=self.chat_canvas.yview)
        self.chat_canvas.configure(yscrollcommand=self.chat_scrollbar.set)

        self.chat_frame = tk.Frame(self.chat_canvas, bg=BG_COLOR)
        self.chat_window = self.chat_canvas.create_window((0, 0), window=self.chat_frame, anchor="nw", tags="chat_window")

        self.chat_frame.bind("<Configure>", lambda e: self.chat_canvas.configure(scrollregion=self.chat_canvas.bbox("all")))
        self.chat_canvas.bind("<Configure>", self._on_canvas_configure)

        self.chat_canvas.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        self.chat_scrollbar.grid(row=0, column=0, sticky="nse", padx=(0, 10))

        # Side panel
        self.side_frame = tk.Frame(self.main_frame, bg=BG_COLOR)
        self.side_frame.grid(row=0, column=1, sticky="nsew")

        tk.Label(self.side_frame, text="World Controls", bg=BG_COLOR, fg=FG_COLOR, font=(FONT_FAMILY, FONT_SIZE, "bold")).pack(pady=10)

        # Weather dropdown
        weather_frame = tk.Frame(self.side_frame, bg=BG_COLOR)
        weather_frame.pack(pady=5, fill=tk.X)
        tk.Label(weather_frame, text="Weather:", bg=BG_COLOR, fg=FG_COLOR, font=(FONT_FAMILY, FONT_SIZE)).pack(anchor="w")
        self.weather_combo = ttk.Combobox(weather_frame, values=["Clear", "Rain", "Storm", "Fog", "Snow"], state="readonly", font=(FONT_FAMILY, FONT_SIZE))
        self.weather_combo.pack(fill=tk.X, pady=2)
        self.weather_combo.set(world_state["weather"].capitalize())

        # Time dropdown
        time_frame = tk.Frame(self.side_frame, bg=BG_COLOR)
        time_frame.pack(pady=5, fill=tk.X)
        tk.Label(time_frame, text="Time:", bg=BG_COLOR, fg=FG_COLOR, font=(FONT_FAMILY, FONT_SIZE)).pack(anchor="w")
        self.time_combo = ttk.Combobox(time_frame, values=["Morning", "Afternoon", "Evening", "Night"], state="readonly", font=(FONT_FAMILY, FONT_SIZE))
        self.time_combo.pack(fill=tk.X, pady=2)
        self.time_combo.set(world_state["time"].capitalize())

        # Generate Scene button
        tk.Button(self.side_frame, text="Generate Scene", command=self.generate_scene, bg="#4FC3F7", fg="black", font=(FONT_FAMILY, FONT_SIZE)).pack(pady=10, fill=tk.X)

        # Input area
        self.input_frame = tk.Frame(self.main_frame, bg=BG_COLOR)
        self.input_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(10, 0))

        self.entry = tk.Entry(self.input_frame, bg="#2c2c2c", fg=FG_COLOR, insertbackground=FG_COLOR, font=(FONT_FAMILY, FONT_SIZE))
        self.entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        self.entry.bind("<Return>", lambda e: self.send_message())

        self.send_btn = tk.Button(self.input_frame, text="Send", command=self.send_message, bg="#4FC3F7", fg="black", font=(FONT_FAMILY, FONT_SIZE, "bold"))
        self.send_btn.pack(side=tk.RIGHT)

        # Initial messages - immersive opener
        self.add_scene_text("*The alley stretches between two old brick buildings, narrow and cramped. A single flickering streetlight casts long shadows across wet pavement, the aftermath of recent rain. The air is thick with humidity and the faint smell of wet garbage. Distant traffic hums from the main street, punctuated by occasional car horns. Closer, there's only the sound of cardboard being shifted, the clink of something metal.*", sender=None)
        self.add_scene_text("*Sarah crouches near an overturned dumpster, one ear flicked back, ears alert despite her careful movements. Her fingers work through a torn garbage bag, methodical but tense. Behind her, Lily sits hunched on her heels, trembling slightly as she clutches a half-eaten takeout container, her ears pressed flat against her head.*", sender=None)
        self.add_scene_text("*The scrape of a shoe on concrete echoes in the narrow space. Sarah's head snaps up instantly, her entire body going rigid. Her eyes reflect the light for just a moment before she shifts, moving between Lily and the sound of you.*", sender=None)
        self.add_message_bubble("...Don't move.", "sarah")
        self.add_message_bubble("S-Sarah...?", "lily")

    def _on_canvas_configure(self, event):
        self.chat_canvas.itemconfig(self.chat_window, width=event.width)

    def add_message_bubble(self, text, sender):
        # Create bubble frame
        bubble_frame = tk.Frame(self.chat_frame, bg=BG_COLOR)
        
        if sender == "user":
            bubble_frame.pack(anchor="e", pady=5, padx=10, fill=tk.X)
            bubble_color = USER_BUBBLE_COLOR
            text_color = "black"
            justify = "right"
            anchor_pos = "e"
        elif sender == "sarah":
            bubble_frame.pack(anchor="w", pady=5, padx=10, fill=tk.X)
            bubble_color = SARAH_BUBBLE_COLOR
            text_color = "black"
            justify = "left"
            anchor_pos = "w"
        elif sender == "lily":
            bubble_frame.pack(anchor="w", pady=5, padx=10, fill=tk.X)
            bubble_color = LILY_BUBBLE_COLOR
            text_color = "black"
            justify = "left"
            anchor_pos = "w"
        else:
            bubble_frame.pack(anchor="w", pady=5, padx=10, fill=tk.X)
            bubble_color = AI_BUBBLE_COLOR
            text_color = "black"
            justify = "left"
            anchor_pos = "w"

        # Bubble label with name prefix
        if sender == "user":
            display_text = f"You: {text}"
        elif sender == "sarah":
            display_text = f"Sarah: {text}"
        elif sender == "lily":
            display_text = f"Lily: {text}"
        else:
            display_text = text
            
        bubble_label = tk.Label(bubble_frame, text=display_text, bg=bubble_color, fg=text_color, font=(FONT_FAMILY, FONT_SIZE), wraplength=400, justify=justify, padx=10, pady=5)
        bubble_label.pack(anchor=anchor_pos)

        # Auto-scroll
        self.chat_canvas.update_idletasks()
        self.chat_canvas.yview_moveto(1.0)

    def add_scene_text(self, text, sender=None):
        # Scene narration: full width, italic, center, gray
        # Remove asterisks if present
        if text.startswith('*') and text.endswith('*'):
            text = text[1:-1]
        
        # Add sender label if provided
        if sender == "user":
            display_text = f"You: {text}"
        elif sender == "sarah":
            display_text = f"Sarah: {text}"
        elif sender == "lily":
            display_text = f"Lily: {text}"
        else:
            display_text = text
        
        scene_label = tk.Label(self.chat_frame, text=display_text, bg=BG_COLOR, fg=SCENE_COLOR, font=(FONT_FAMILY, FONT_SIZE, "italic"), justify="center", wraplength=600)
        scene_label.pack(pady=(10, 5), fill=tk.X, padx=10)

        # Auto-scroll
        self.chat_canvas.update_idletasks()
        self.chat_canvas.yview_moveto(1.0)

    def type_message(self, label, full_text):
        """Type text character by character into the label."""
        label.config(text="")
        i = 0
        def add_char():
            nonlocal i
            if i < len(full_text):
                label.config(text=full_text[:i+1])
                self.chat_canvas.update_idletasks()
                self.chat_canvas.yview_moveto(1.0)
                i += 1
                self.root.after(30, add_char)  # 30ms per char
            else:
                self.entry.config(state="normal")
        add_char()

    def send_message(self):
        prompt = self.entry.get().strip()
        if not prompt:
            return
        
        # Parse user input for mixed actions and speech
        parts = parse_user_input(prompt)
        
        if not parts:
            # If no specific markers, treat as narration
            self.add_scene_text(prompt, sender="user")
        else:
            # Render each part
            for part_type, part_text in parts:
                if part_type == 'action':
                    self.add_scene_text(part_text, sender="user")
                elif part_type == 'speech':
                    self.add_message_bubble(part_text, "user")
                elif part_type == 'narration':
                    self.add_scene_text(part_text, sender="user")
        
        self.entry.delete(0, tk.END)
        self.entry.config(state="disabled")

        # Track interactions and advance time randomly
        self.interaction_count += 1
        if self.interaction_count >= self.next_time_change:
            # Time to advance
            current_time = world_state["time"].lower()
            current_idx = self.time_progression.index(current_time) if current_time in self.time_progression else 0
            next_idx = (current_idx + 1) % len(self.time_progression)
            new_time = self.time_progression[next_idx]
            world_state["time"] = new_time
            self.time_combo.set(new_time.capitalize())
            
            # Add atmospheric transition
            time_transitions = {
                "morning": "*The first light of dawn begins to creep across the alley, the night slowly retreating.*",
                "afternoon": "*The sun climbs higher, harsh light cutting through the alley, casting sharp shadows.*",
                "evening": "*The sun dips lower on the horizon, painting the alley in shades of orange and purple. Shadows grow longer.*",
                "night": "*The streetlight flickers to life as darkness settles in. The alley grows colder, quieter.*"
            }
            self.add_scene_text(time_transitions.get(new_time, "*Time passes.*"))
            
            # Reset counter
            self.interaction_count = 0
            self.next_time_change = random.randint(2, 5)

        self.current_ai_text = ""

        def add_chunk(chunk):
            self.current_ai_text += chunk

        def on_done():
            parts = parse_response(self.current_ai_text)
            for part_type, part_text in parts:
                if part_type == 'action':
                    # Generic narration without sender label
                    self.add_scene_text(part_text)
                elif part_type == 'sarah_action':
                    # Sarah action renders as narration with label
                    self.add_scene_text(part_text, sender="sarah")
                elif part_type == 'lily_action':
                    # Lily action renders as narration with label
                    self.add_scene_text(part_text, sender="lily")
                elif part_type == 'sarah_speech':
                    # Sarah speech renders as bubble
                    self.add_message_bubble(part_text, 'sarah')
                elif part_type == 'lily_speech':
                    # Lily speech renders as bubble
                    self.add_message_bubble(part_text, 'lily')
            
            # Detect and update world state changes
            changes = detect_world_changes(self.current_ai_text)
            if 'weather' in changes:
                world_state['weather'] = changes['weather']
                self.weather_combo.set(changes['weather'].capitalize())
            if 'time' in changes:
                world_state['time'] = changes['time']
                self.time_combo.set(changes['time'].capitalize())
            
            self.entry.config(state="normal")

        stream_ai_roleplay(prompt, add_chunk, on_done, model="gpt-4o-mini")

    def generate_scene(self):
        # Update world state from combos
        world_state["weather"] = self.weather_combo.get().lower()
        world_state["time"] = self.time_combo.get().lower()

        # Generate scene prompt
        scene_prompt = f"Generate a short, immersive scene description based on the current time: {world_state['time']}, weather: {world_state['weather']}. Make it cinematic and atmospheric, like a narration in a story. Keep it under 100 words."

        # Call AI for scene
        def add_scene_chunk(chunk):
            self.scene_text += chunk

        def on_scene_done():
            self.add_scene_text(self.scene_text)

        self.scene_text = ""
        stream_ai_roleplay(scene_prompt, add_scene_chunk, on_scene_done, model="gpt-4o-mini")

if __name__ == "__main__":
    root = tk.Tk()
    app = ChatApp(root)
    root.mainloop()