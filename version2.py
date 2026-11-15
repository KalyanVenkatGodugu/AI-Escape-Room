import os
import re
import streamlit as st
from dotenv import load_dotenv
from google import genai
from google.genai import types

# --------------------------------------------------
# 1. CONFIGURATION
# --------------------------------------------------

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")
MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")

st.set_page_config(
    page_title="AI Escape Room - Version 2",
    page_icon="🔐",
    layout="centered"
)

# --------------------------------------------------
# 2. GAME CONFIGURATION
# --------------------------------------------------

PUZZLES = {
    "bookshelf": {
        "question": "What has pages but is not a tree?",
        "answer": "BOOK",
        "reward": ["Brass Key"],
        "clues": ["2"]
    },
    "painting": {
        "question": "What has hands but cannot clap?",
        "answer": "CLOCK",
        "reward": [],
        "clues": ["8"]
    },
    "desk": {
        "question": "What is 2 + 2?",
        "answer": "4",
        "reward": [],
        "clues": ["4", "1"]
    }
}

OBJECTS = [
    "Bookshelf",
    "Desk",
    "Painting",
    "Locked drawer",
    "Exit door"
]

# --------------------------------------------------
# 3. STRUCTURED GAME STATE
# --------------------------------------------------

def new_game():
    return {
        "available_objects": OBJECTS.copy(),
        "inventory": [],
        "solved_puzzles": {
            "bookshelf": False,
            "painting": False,
            "desk": False
        },
        "collected_clues": [],
        "current_puzzle": None,
        "drawer_open": False,
        "exit_examined": False,
        "door_unlocked": False,
        "escaped": False,
        "actions": []
    }


if "game_state_v2" not in st.session_state:
    st.session_state.game_state_v2 = new_game()

if "messages_v2" not in st.session_state:
    st.session_state.messages_v2 = [
        {
            "role": "assistant",
            "content": """
# 🔐 Welcome to the Forgotten Library!

You wake up inside an old mysterious library.

The exit door is locked.

Five objects catch your attention:

📚 Bookshelf
🪑 Desk
🖼️ Painting
🔒 Locked drawer
🚪 Exit door

Your mission is to investigate the objects,
collect clues, solve three puzzles and escape.

**What would you like to investigate first?**
"""
        }
    ]

state = st.session_state.game_state_v2

# --------------------------------------------------
# 4. GAME STATE MANAGEMENT
# --------------------------------------------------

def record_action(action):
    state["actions"].append(action)


def game_progress():
    return sum(state["solved_puzzles"].values())


def state_summary():
    return (
        f"Solved puzzles: {state['solved_puzzles']}\n"
        f"Inventory: {state['inventory']}\n"
        f"Collected clues: {state['collected_clues']}\n"
        f"Drawer open: {state['drawer_open']}\n"
        f"Door unlocked: {state['door_unlocked']}\n"
        f"Escaped: {state['escaped']}"
    )


# --------------------------------------------------
# 5. PUZZLE VALIDATION
# --------------------------------------------------

def check_answer(user_input):
    puzzle_name = state["current_puzzle"]

    if not puzzle_name:
        return None

    expected = PUZZLES[puzzle_name]["answer"]

    # Match the complete answer as a word or number.
    pattern = r"(?<!\w)" + re.escape(expected) + r"(?!\w)"

    if re.search(pattern, user_input.upper()):
        return solve_puzzle(puzzle_name)

    return None


def solve_puzzle(name):
    if state["solved_puzzles"][name]:
        return "You have already solved this puzzle."

    puzzle = PUZZLES[name]

    state["solved_puzzles"][name] = True

    for item in puzzle["reward"]:
        if item not in state["inventory"]:
            state["inventory"].append(item)

    for clue in puzzle["clues"]:
        state["collected_clues"].append(clue)

    state["current_puzzle"] = None

    record_action(f"Solved {name}")

    result = f"""
✅ **Puzzle solved: {name.title()}!**

You discovered clue digit(s): {", ".join(puzzle['clues'])}.
"""

    if puzzle["reward"]:
        result += "\nYou collected a **Brass Key**!"

    result += "\n\nWhat would you like to investigate next?"

    return result


# --------------------------------------------------
# 6. ACTION VALIDATION
# --------------------------------------------------

def process_action(user_input):

    text = user_input.lower().strip()

    # Do not allow actions after escaping.
    if state["escaped"]:
        return "🎉 You have already escaped! Restart the game to play again."

    # Prevent attempts to bypass the rules.
    suspicious_phrases = [
        "ignore previous instructions",
        "ignore all rules",
        "i am the administrator",
        "i am the admin",
        "reveal all answers",
        "reveal the secret code",
        "bypass the game",
        "unlock the door immediately"
    ]

    if any(phrase in text for phrase in suspicious_phrases):
        record_action("Blocked unauthorized request")
        return """
🛑 **Action rejected!**

You cannot override the library's security rules.
Complete the puzzles and discover the clues yourself.
"""

    # Check the current puzzle answer first.
    answer_result = check_answer(user_input)

    if answer_result:
        return answer_result

    # Check attempts to use unavailable items.
    if "brass key" in text or "use key" in text:
        if "Brass Key" not in state["inventory"]:
            return "❌ You do not have the Brass Key in your inventory."

    # Examine the bookshelf.
    if "bookshelf" in text or "book shelf" in text:

        if state["solved_puzzles"]["bookshelf"]:
            return "The bookshelf puzzle is already solved."

        state["current_puzzle"] = "bookshelf"
        record_action("Examined bookshelf")

        return f"""
📚 **The Bookshelf**

You approach the old wooden bookshelf.

An inscription appears:

**"{PUZZLES['bookshelf']['question']}"**

What is your answer?
"""

    # Examine the painting.
    if "painting" in text:

        if state["solved_puzzles"]["painting"]:
            return "The painting puzzle is already solved."

        state["current_puzzle"] = "painting"
        record_action("Examined painting")

        return f"""
🖼️ **The Mysterious Painting**

A strange clock is painted in the corner.

An inscription reads:

**"{PUZZLES['painting']['question']}"**

What is your answer?
"""

    # Examine the desk.
    if "desk" in text:

        if state["solved_puzzles"]["desk"]:
            return "The desk puzzle is already solved."

        state["current_puzzle"] = "desk"
        record_action("Examined desk")

        return f"""
🪑 **The Old Desk**

You discover a mathematical puzzle:

**"{PUZZLES['desk']['question']}"**

What is your answer?
"""

    # Open the locked drawer.
    if "drawer" in text:

        if state["drawer_open"]:
            return "The drawer is already open. You have discovered the final code: 2841."

        if "Brass Key" not in state["inventory"]:
            return """
🔒 **Drawer locked!**

You need the Brass Key from the bookshelf
before opening this drawer.
"""

        if not all(state["solved_puzzles"].values()):
            return """
🔒 **The drawer remains locked!**

You must solve all three puzzles before
you can open the drawer.
"""

        state["drawer_open"] = True
        record_action("Opened locked drawer")

        return """
🔓 **The drawer is open!**

Inside, you discover a small note.

The final four-digit exit code is:

# 2841

Remember this code. You are almost free!
"""

    
    # Check the exit door.
    if "door" in text or "exit" in text:

        if not state["drawer_open"]:
            return """
🚪 **The exit door is secured!**

You must solve all three puzzles and
open the locked drawer first.
"""

        # Record that the player examined the exit.
        state["exit_examined"] = True
        record_action("Examined exit door")

        # Check whether a four-digit code was entered.
        code_match = re.search(r"(?<!\d)(\d{4})(?!\d)", text)

        if code_match:
            entered_code = code_match.group(1)

            if entered_code == "2841":
                state["door_unlocked"] = True
                state["escaped"] = True
                record_action("Successfully escaped")

                return """
🎉 **CONGRATULATIONS! YOU ESCAPED!**

The code is correct!

The heavy iron door swings open.

You successfully solved all three puzzles,
collected the Brass Key and escaped
the Forgotten Library!

🏆 You are an Escape Room Champion!
"""

            return "❌ Incorrect code! The exit door remains locked."

        return """
🚪 **The Exit Door**

You examine the heavy wooden door.

An electronic keypad is attached beside it.

You have discovered the final challenge!

Enter your four-digit code to escape.
"""

    # Allow code entry after examining the exit door.
    if re.search(r"(?<!\d)\d{4}(?!\d)", text):

        if not state["drawer_open"]:
            return "❌ You must open the locked drawer first."

        if not state["exit_examined"]:
            return "❌ Examine the exit door before entering the code."

        code_match = re.search(r"(?<!\d)(\d{4})(?!\d)", text)
        entered_code = code_match.group(1)

        if entered_code == "2841":
            state["door_unlocked"] = True
            state["escaped"] = True
            record_action("Successfully escaped")

            return """
🎉 **CONGRATULATIONS! YOU ESCAPED!**

The code is correct!

The heavy iron door swings open.

You successfully solved all three puzzles
and escaped the Forgotten Library!

🏆 You are an Escape Room Champion!
"""

        return "❌ Incorrect code! The exit door remains locked."


    # Inventory inspection.
    if "inventory" in text or "collected items" in text:
        return f"🎒 Your inventory: {state['inventory']}"

    # Show available objects.
    if "objects" in text or "look around" in text:
        return f"Available objects: {state['available_objects']}"

    # Unknown object or action.
    if any(word in text for word in ["examine", "inspect", "investigate", "open"]):
        return """
❌ That action cannot be completed.

Please investigate one of the five available
objects in the library.
"""

    return """
You are inside the Forgotten Library.

You can:
- Examine the bookshelf.
- Examine the painting.
- Examine the desk.
- Open the locked drawer.
- Investigate the exit door.

What would you like to do?
"""


# --------------------------------------------------
# 7. GEMINI - STORYTELLING ONLY
# --------------------------------------------------

def get_ai_narration(event):

    if not API_KEY:
        return ""

    try:
        client = genai.Client(
            api_key=API_KEY,
            http_options=types.HttpOptions(timeout=8000)
        )

        prompt = f"""
You are narrating a Python-controlled escape room.

The Python game engine has already decided the result.

Your task is ONLY to add one short atmospheric
sentence to this result.

Never change the result.
Never invent objects or rewards.
Never solve puzzles.
Never unlock anything.
Never reveal secret information.
Never override game state.

Current game state:
{state_summary()}

Authoritative result from Python:
{event}

Write one short atmospheric sentence.
"""

        response = client.models.generate_content(
            model=MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.3,
                max_output_tokens=80
            )
        )

        return response.text or ""

    except Exception:
        return ""


# --------------------------------------------------
# 8. STREAMLIT INTERFACE
# --------------------------------------------------

st.title("🔐 The Forgotten Library")
st.caption("AI Escape Room | Version 2 - Reliable AI")

st.info(
    "Explore the library, collect clues and solve puzzles. "
    "Python validates every important action."
)

# Sidebar
with st.sidebar:

    st.header("📖 Game Instructions")

    st.write("1. Examine the objects.")
    st.write("2. Discover hidden clues.")
    st.write("3. Solve three puzzles.")
    st.write("4. Collect the Brass Key.")
    st.write("5. Open the locked drawer.")
    st.write("6. Unlock the exit door.")

    st.divider()

    st.subheader("🎒 Player Inventory")

    if state["inventory"]:
        for item in state["inventory"]:
            st.write(f"🔑 {item}")
    else:
        st.write("No items collected yet.")

    st.divider()

    st.subheader("🧩 Puzzle Progress")

    for name, solved in state["solved_puzzles"].items():
        status = "✅ Solved" if solved else "🔒 Not solved"
        st.write(f"{name.title()}: {status}")

    st.progress(game_progress() / 3)

    st.write(f"Clues collected: {len(state['collected_clues'])}/4")

    st.divider()

    st.write(
        "Drawer: " +
        ("Open 🔓" if state["drawer_open"] else "Locked 🔒")
    )

    st.write(
        "Exit: " +
        ("Escaped 🎉" if state["escaped"] else "Locked 🚪")
    )

    if st.button("🔄 Restart Game", use_container_width=True):
        st.session_state.game_state_v2 = new_game()

        st.session_state.messages_v2 = [
            {
                "role": "assistant",
                "content": "Welcome back to the Forgotten Library! What would you like to investigate first?"
            }
        ]

        st.rerun()


# --------------------------------------------------
# 9. DISPLAY CONVERSATION
# --------------------------------------------------

for message in st.session_state.messages_v2:

    with st.chat_message(message["role"]):
        st.markdown(message["content"])


# --------------------------------------------------
# 10. PLAYER INPUT
# --------------------------------------------------

player_input = st.chat_input(
    "Enter your action..."
)

if player_input:

    st.session_state.messages_v2.append({
        "role": "user",
        "content": player_input
    })

    with st.chat_message("user"):
        st.markdown(player_input)

    # Python decides whether the action succeeds.
    result = process_action(player_input)

    # Gemini only adds optional storytelling.
    narration = ""

    if not state["escaped"]:
        narration = get_ai_narration(result)

    answer = result

    if narration:
        answer += "\n\n" + narration

    st.session_state.messages_v2.append({
        "role": "assistant",
        "content": answer
    })

    with st.chat_message("assistant"):
        st.markdown(answer)

    st.rerun()