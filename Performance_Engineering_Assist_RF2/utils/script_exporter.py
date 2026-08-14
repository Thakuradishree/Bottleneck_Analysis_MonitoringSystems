from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

SCRIPT_PATH = OUTPUT_DIR / "generated_script.js"


def save_script(script: str):

    with open(SCRIPT_PATH, "w", encoding="utf-8") as f:
        f.write(script)

    return SCRIPT_PATH