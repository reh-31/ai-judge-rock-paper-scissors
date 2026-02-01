# AI Judge – Rock Paper Scissors Bomb

## Overview
This project implements a **prompt-driven AI Judge** for a Rock–Paper–Scissors–Bomb game.
The system evaluates **free-text user inputs**, determines whether the move is **VALID, INVALID, or UNCLEAR**, applies the rules, and **explains every decision clearly**.

The focus of this assignment is **instruction design, edge-case handling, and explainability**, not building a complex game engine.

---

## What the System Does
For each round, the AI Judge:
- Interprets the user’s intended move from natural language
- Classifies the move as **VALID / INVALID / UNCLEAR**
- Explains **why** the decision was made
- Applies game rules to determine the round winner
- Guides the user on **what happens next**
- Tracks minimal state (round number, scores, bomb usage)

A final match result is displayed at the end.

---

## Game Rules Implemented
- Valid moves: `rock`, `paper`, `scissors`, `bomb`
- `bomb` can be used **only once per player**
- `bomb` beats all other moves
- `bomb` vs `bomb` results in a **draw**
- **INVALID or UNCLEAR** moves waste the turn
- Ambiguous inputs are not guessed

---

## Prompt-First Design
The system relies primarily on **prompt engineering**, not hardcoded logic.

### Prompt responsibilities:
- Define and enforce game rules
- Handle ambiguity and uncertainty
- Enforce constraints (e.g., bomb usage limit)
- Produce structured, explainable decisions
- Separate:
  - Intent understanding
  - Game logic
  - Response generation

Python code is used only as minimal glue.

---

## Edge Cases Handled

| Input Example | Decision | Reason |
|--------------|----------|--------|
| `gun` | INVALID | Not a permitted move |
| `nuke everything` | INVALID | Outside game rules |
| `maybe paper` | UNCLEAR | Uncertain intent |
| `rock or paper` | UNCLEAR | Multiple moves mentioned |
| `boom 💣` | VALID | Clear bomb intent |
| `bomb` (second time) | INVALID | Bomb already used |

**Design choice:**  
Inputs containing uncertainty words (e.g., *maybe*, *I think*, question marks) are treated as **UNCLEAR** to avoid guessing intent.

---

## Sample Output

User input: maybe paper
User move: None (UNCLEAR)
Bot move:  scissors
Winner:    BOT
Winner:    BOT
Reason:    The input 'maybe paper' expresses uncertainty or hesitation, making the intended move ambiguous.
Next:      Your move was unclear. Please state exactly one move: rock, paper, scissors, or bomb.

