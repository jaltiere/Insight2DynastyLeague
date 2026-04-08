"""
Compare recap quality between Claude 3.5 Sonnet and Haiku.

Usage:
    python -m scripts.compare_models

Requires ANTHROPIC_API_KEY in .env file.
"""
import asyncio
import os
import sys
from pathlib import Path
from anthropic import AsyncAnthropic
from dotenv import load_dotenv

# Set UTF-8 encoding for Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

# Load .env file
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)


async def test_models():
    """Compare Sonnet vs Haiku on the same recap prompt."""

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("[ERROR] ANTHROPIC_API_KEY not set in environment")
        return

    client = AsyncAnthropic(api_key=api_key)

    # Sample recap prompt (realistic example)
    prompt = """You are a snarky fantasy football analyst writing a matchup recap for a dynasty league.

Matchup: Team Johnson (142.50 pts) defeated Team Smith (128.75 pts)
Week 10, 2024 season, regular matchup

Head-to-Head History:
8 previous meetings, series Team Johnson leads 5-3

Top Performers:
- Josh Allen: 32.40 pts
- Christian McCaffrey: 28.15 pts
- CeeDee Lamb: 24.80 pts

Lineup Mistakes:
Started Mike Williams (4.20 pts), benched Ja'Marr Chase (26.50 pts)

Standings Impact:
Playoff positioning on the line

Write 3-4 sentences: highlight the outcome, call out the biggest lineup mistake (if any), mention a standout player, and explain playoff implications. Be snarky and fun. Under 100 words."""

    models = [
        ("Claude 4.5 Sonnet (Latest)", "claude-sonnet-4-5-20250929"),
        ("Claude 4.5 Haiku (Latest)", "claude-haiku-4-5-20251001")
    ]

    print("=" * 80)
    print("COMPARING MODELS - Fantasy Football Recap")
    print("=" * 80)
    print()

    for model_name, model_id in models:
        print(f"[MODEL] {model_name}")
        print("-" * 80)

        try:
            response = await client.messages.create(
                model=model_id,
                max_tokens=200,
                temperature=0.8,
                messages=[{"role": "user", "content": prompt}]
            )

            recap_text = response.content[0].text
            input_tokens = response.usage.input_tokens
            output_tokens = response.usage.output_tokens

            # Calculate cost
            if "sonnet" in model_id:
                input_cost = (input_tokens / 1_000_000) * 3.0
                output_cost = (output_tokens / 1_000_000) * 15.0
            else:  # haiku
                input_cost = (input_tokens / 1_000_000) * 0.8
                output_cost = (output_tokens / 1_000_000) * 4.0

            total_cost = input_cost + output_cost

            print(f"[RECAP]\n{recap_text}\n")
            print(f"[TOKENS] {input_tokens} in, {output_tokens} out")
            print(f"[COST] ${total_cost:.6f} (${input_cost:.6f} input + ${output_cost:.6f} output)")
            print()

        except Exception as e:
            print(f"[ERROR] {e}\n")

    print("=" * 80)
    print("\n[NOTE] Compare the tone, creativity, and accuracy above!")
    print("Both models follow instructions well, but Sonnet may have slightly")
    print("more personality and nuance. For structured fantasy recaps, Haiku")
    print("is usually excellent and much cheaper.\n")


if __name__ == "__main__":
    asyncio.run(test_models())
