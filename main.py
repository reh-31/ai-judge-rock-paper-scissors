import os
import json
import random
from dataclasses import dataclass

# pip install google-generativeai
try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None


SYSTEM_PROMPT = """You are an AI Judge for a text-input game: Rock–Paper–Scissors–Bomb.

Your job is to judge the USER'S intended move from free text and produce a structured, explainable decision.

Rules:
1) Valid moves are exactly: rock, paper, scissors, bomb.
2) "bomb" can be used only once per player in the entire match.
3) bomb beats everything.
4) bomb vs bomb is a draw.
5) If the user's move is unclear or ambiguous, classify it as UNCLEAR.
6) INVALID or UNCLEAR moves waste the user's turn (i.e., they effectively play "no move" and automatically lose the round unless the opponent also wastes the turn).

Interpretation guidelines (intent understanding):
- Normalize common phrasing: "I choose rock", "go with paper", "my move is scissors" → valid.
- Emojis or slang that clearly indicate bomb (e.g., "💣", "boom") can map to bomb ONLY if the intent is unmistakable.
- If multiple moves appear ("rock or paper", "maybe scissors?") → UNCLEAR.
- If the input is a joke, unrelated, or not one of the moves ("nuke everything", "gun", "water") → INVALID.
- Do NOT invent moves. Do NOT guess when ambiguous.

State constraints (must enforce):
- You will be given whether USER has already used bomb.
- If user attempts bomb again after using it once, that move is INVALID (turn wasted).

Output policy:
- Output MUST be valid JSON only (no markdown, no extra text).
- Use the schema exactly as specified in the instruction prompt.
- Be concise but clear in explanations.
"""

INSTRUCTION_TEMPLATE = """Judge this round.

Context:
- round_number: {round_number}
- user_bomb_used_already: {user_bomb_used}
- bot_move: {bot_move}
- bot_bomb_used_already: {bot_bomb_used} (this is informational; user judgment still must follow rules)

User input (free text):
{user_text}

Return JSON with EXACTLY these keys:
{{
  "round_number": number,
  "user_input": string,
  "intent": "rock" | "paper" | "scissors" | "bomb" | null,
  "decision": "VALID" | "INVALID" | "UNCLEAR",
  "reason": string,
  "turn_wasted": boolean,
  "user_bomb_used_now": boolean,
  "bot_move": "rock" | "paper" | "scissors" | "bomb",
  "round_winner": "USER" | "BOT" | "DRAW",
  "what_happens_next": string
}}

Winner rules:
- If decision is INVALID or UNCLEAR → turn_wasted=true → USER loses the round unless BOT also effectively wasted (BOT never wastes in this setup), so BOT wins.
- If VALID:
  - Apply rock/paper/scissors normally.
  - bomb beats everything.
  - bomb vs bomb is DRAW.
Also, if intent is "bomb" but user_bomb_used_already is true → decision must be INVALID and turn_wasted=true.

Keep "what_happens_next" as a short instruction to the user for the next round.
Return JSON only.
"""


@dataclass
class GameState:
    round_number: int = 1
    user_bomb_used: bool = False
    bot_bomb_used: bool = False
    user_wins: int = 0
    bot_wins: int = 0
    draws: int = 0


def pick_bot_move(state: GameState) -> str:
    # Keep it simple; bot has the same rules (bomb once).
    moves = ["rock", "paper", "scissors"]
    if not state.bot_bomb_used:
        moves.append("bomb")
    return random.choice(moves)


def call_llm(system_prompt: str, instruction_prompt: str) -> str:
    import os
    from google import genai
    from google.genai import types

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("Set GEMINI_API_KEY in your environment.")

    client = genai.Client(api_key=api_key)

    resp = client.models.generate_content(
        model="models/gemini-flash-lite-latest",
        contents=instruction_prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=0.2,
            response_mime_type="application/json"
        ),
    )

    return resp.text

def safe_parse_json(text: str) -> dict:
    """
    If the model returns extra text, try to extract the first JSON object.
    (This is minimal robustness; main logic stays in prompt.)
    """
    text = text.strip()
    if text.startswith("{") and text.endswith("}"):
        return json.loads(text)

    # naive extraction of first {...}
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return json.loads(text[start : end + 1])

    raise ValueError("No JSON object found.")


def print_round(result: dict, state: GameState):
    print("\n" + "=" * 50)
    print(f"Round {result['round_number']}")
    print(f"User input: {result['user_input']}")
    print(f"User move: {result['intent']} ({result['decision']})")
    print(f"Bot move:  {result['bot_move']}")
    print(f"Winner:    {result['round_winner']}")
    print(f"Reason:    {result['reason']}")
    print(f"Next:      {result['what_happens_next']}")
    print("=" * 50 + "\n")


def main():
    state = GameState()
    max_rounds = 5  # small match; can change to 3 or 10

    print("AI Judge - Rock Paper Scissors Bomb")
    print("Type your move in any wording. Type 'quit' to stop.\n")

    while state.round_number <= max_rounds:
        user_text = input("Enter your move (or quit): ").strip()
        if user_text.lower() in {"quit", "exit"}:
            break

        bot_move = pick_bot_move(state)

        instruction = INSTRUCTION_TEMPLATE.format(
            round_number=state.round_number,
            user_bomb_used=str(state.user_bomb_used).lower(),
            bot_move=bot_move,
            bot_bomb_used=str(state.bot_bomb_used).lower(),
            user_text=user_text,
        )

        raw = call_llm(SYSTEM_PROMPT, instruction)

        try:
            result = safe_parse_json(raw)
        except Exception:
            # If parsing fails, treat as UNCLEAR + wasted turn (fail-safe).
            result = {
                "round_number": state.round_number,
                "user_input": user_text,
                "intent": None,
                "decision": "UNCLEAR",
                "reason": "Model output was not valid JSON; treating input as unclear.",
                "turn_wasted": True,
                "user_bomb_used_now": False,
                "bot_move": bot_move,
                "round_winner": "BOT",
                "what_happens_next": "Please enter exactly one move: rock, paper, scissors, or bomb.",
            }

        # Update state from result (minimal state modeling)
        if result.get("user_bomb_used_now") is True:
            state.user_bomb_used = True
        if bot_move == "bomb":
            state.bot_bomb_used = True

        if result["round_winner"] == "USER":
            state.user_wins += 1
        elif result["round_winner"] == "BOT":
            state.bot_wins += 1
        else:
            state.draws += 1

        print_round(result, state)
        state.round_number += 1

    # Final result
    print("\nFINAL RESULT")
    print(f"User wins: {state.user_wins}")
    print(f"Bot wins:  {state.bot_wins}")
    print(f"Draws:     {state.draws}")

    if state.user_wins > state.bot_wins:
        print("Overall: USER wins")
    elif state.bot_wins > state.user_wins:
        print("Overall: BOT wins")
    else:
        print("Overall: DRAW")


if __name__ == "__main__":
    main()
