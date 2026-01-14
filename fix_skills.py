"""Fix package.json in existing skills by removing 'skill-' prefix."""

import json
import sys
from pathlib import Path

# Default skills directories
SKILLS_DIRS = [
    Path(r"C:\Users\Administrator\.claude\skills"),
    Path(r"C:\Users\Administrator\.codex\skills"),
    Path(r"C:\Users\Administrator\.gemini\skills"),
]


def fix_package_json(skill_dir: Path) -> bool:
    """Fix package.json in a skill directory."""
    package_json_path = skill_dir / "package.json"

    if not package_json_path.exists():
        return False

    try:
        # Read package.json
        with open(package_json_path, "r", encoding="utf-8") as f:
            package = json.load(f)

        # Check if name has 'skill-' prefix
        name = package.get("name", "")
        if name.startswith("skill-"):
            # Remove prefix
            new_name = name[6:]  # Remove 'skill-'
            package["name"] = new_name

            # Write back
            with open(package_json_path, "w", encoding="utf-8") as f:
                json.dump(package, f, indent=2, ensure_ascii=False)

            print(f"[OK] Fixed {skill_dir.name}: {name} -> {new_name}")
            return True
        else:
            print(f"- Skipped {skill_dir.name}: no 'skill-' prefix")
            return False
    except Exception as e:
        print(f"[ERROR] Error fixing {skill_dir.name}: {e}")
        return False


def main():
    """Fix all skills in the skills directories."""
    # Allow custom directory from command line
    if len(sys.argv) > 1:
        dirs_to_process = [Path(sys.argv[1])]
    else:
        dirs_to_process = SKILLS_DIRS

    total_fixed = 0
    for skills_dir in dirs_to_process:
        if not skills_dir.exists():
            print(f"Skipping (not found): {skills_dir}\n")
            continue

        print(f"Scanning skills in: {skills_dir}\n")

        fixed_count = 0
        for skill_dir in skills_dir.iterdir():
            if skill_dir.is_dir():
                if fix_package_json(skill_dir):
                    fixed_count += 1

        print(f"\nFixed {fixed_count} skills in {skills_dir}\n")
        total_fixed += fixed_count

    print(f"Total fixed: {total_fixed} skills")


if __name__ == "__main__":
    main()
