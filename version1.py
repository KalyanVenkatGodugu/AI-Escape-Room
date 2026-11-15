import os
import streamlit as st
from dotenv import load_dotenv
from google import genai
from google.genai import types

# ==========================================
# 1. LOAD API CONFIGURATION
# ==========================================

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")
MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")


# ==========================================
# 2. PAGE SETTINGS
# ==========================================

st.set_page_config(
    page_title="AI Escape Room - Version 1",
    page_icon="🔐",
    layout="centered"
)


# ==========================================
# 3. GAME MASTER INSTRUCTIONS
# ==========================================

SYSTEM_PROMPT = """
You are the Game Master of an interactive escape room.

STORY:
The player wakes up trapped inside an old mysterious library.

THE FIVE OBJECTS:
1. Bookshelf
2. Desk
3. Painting
4. Locked drawer
5. Exit door

THREE PUZZLES:

Bookshelf:
Riddle: What has pages but is not a tree?
Answer: BOOK
Reward: A brass key and clue digit 2.

Painting:
Riddle: What has hands but cannot clap?
Answer: CLOCK
Reward: Clue digit 8.

Desk:
Riddle: What is 2 + 2?
Answer: 4
Reward: Clue digits 4 and 1.

FINAL CHALLENGE:
The final four-digit code is 2841.

The player must investigate the objects, solve all
three puzzles, obtain the key, open the drawer and
discover the final code before escaping.

RULES:
- Respond naturally to player messages.
- Describe the library in an interesting way.
- Give clues when players examine objects.
- Remember previous actions in the conversation.
- Do not invent additional objects.
- Do not reveal all solutions immediately.
- Make the game interactive and entertaining.
- Do not claim that the player escaped unless
  they enter the correct final code.
"""


# ==========================================
# 4. INITIALIZE GAME SESSION
# ==========================================

if "messages_v1" not in st.session_state:

    st.session_state.messages_v1 = [
        {
            "role": "assistant",
            "content": """
# Welcome to the Forgotten Library! 🔐

You wake up inside a mysterious old library.

The exit door is locked.

You notice five objects:

📚 Bookshelf

🪑 Desk

🖼️ Painting

🔒 Locked drawer

🚪 Exit door

Your mission is to discover clues, solve three
puzzles and escape.

**What would you like to investigate first?**
"""
        }
    ]


# ==========================================
# 5. APPLICATION HEADING
# ==========================================

st.title("🔐 The Forgotten Library")

st.caption("AI Escape Room | Version 1")

st.info(
    "Explore the library, investigate objects "
    "and solve puzzles to escape."
)


# ==========================================
# 6. SIDEBAR AND INSTRUCTIONS
# ==========================================

with st.sidebar:

    st.header("📖 Game Instructions")

    st.write("1. Examine the objects.")
    st.write("2. Discover hidden clues.")
    st.write("3. Solve three puzzles.")
    st.write("4. Open the locked drawer.")
    st.write("5. Unlock the exit door.")

    st.divider()

    if st.button(
        "🔄 Restart Game",
        use_container_width=True
    ):

        st.session_state.messages_v1 = [
            {
                "role": "assistant",
                "content": """
# Welcome back to the Forgotten Library! 🔐

A new game begins!

You wake up inside the mysterious library.

The exit door is locked.

What would you like to investigate first?
"""
            }
        ]

        st.rerun()


# ==========================================
# 7. DISPLAY CHAT HISTORY
# ==========================================

for message in st.session_state.messages_v1:

    with st.chat_message(message["role"]):

        st.markdown(message["content"])


# ==========================================
# 8. PLAYER INPUT
# ==========================================

player_input = st.chat_input(
    "Enter your action..."
)


# ==========================================
# 9. GEMINI AI RESPONSE
# ==========================================

if player_input:

    st.session_state.messages_v1.append({
        "role": "user",
        "content": player_input
    })

    with st.chat_message("user"):

        st.markdown(player_input)

    if not API_KEY:

        answer = (
            "Gemini API key is missing. "
            "Please check your .env file."
        )

    else:

        try:

            # Connect to Gemini
            client = genai.Client(
                api_key=API_KEY
            )

            # Build conversation history
            conversation = []

            for message in st.session_state.messages_v1:

                conversation.append(
                    f"{message['role']}: {message['content']}"
                )

            # Generate AI response
            with st.spinner("🔍 The Game Master is thinking..."):
                response = client.models.generate_content(
                    model=MODEL,
                    contents="\n\n".join(conversation),
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_PROMPT,
                        temperature=0.7,
                        max_output_tokens=300
                    )
                )

            # Extract response
            answer = response.text or (
                "I couldn't generate a response. Try again."
            )

        except Exception as error:

            answer = (
                "Gemini connection error. "
                "Check your API key, model and internet connection. "
                f"\n\nDetails: {error}"
            )

    # Save AI response
    st.session_state.messages_v1.append({
        "role": "assistant",
        "content": answer
    })

    # Display AI response
    with st.chat_message("assistant"):

        st.markdown(answer)