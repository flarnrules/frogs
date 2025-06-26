import os

REPLACEMENTS = {
    "from emojifier.emojify_image": "from core.emojify_image",
    "from emojifier.emojify_gif": "from core.emojify_gif",
    "from emojifier.batch_runner": "from core.batch_runner",
    "from emojifier.config": "from config.config",
}

TARGET_DIRS = ["core", "cli"]

def fix_imports():
    for folder in TARGET_DIRS:
        for root, _, files in os.walk(folder):
            for file in files:
                if file.endswith(".py"):
                    file_path = os.path.join(root, file)
                    with open(file_path, "r", encoding="utf-8") as f:
                        lines = f.readlines()

                    changed = False
                    new_lines = []
                    for line in lines:
                        new_line = line
                        for old, new in REPLACEMENTS.items():
                            if old in new_line:
                                new_line = new_line.replace(old, new)
                                changed = True
                        new_lines.append(new_line)

                    if changed:
                        with open(file_path, "w", encoding="utf-8") as f:
                            f.writelines(new_lines)
                        print(f"✅ Updated: {file_path}")

if __name__ == "__main__":
    fix_imports()
