"""Fix package.json and directory names in existing skills by removing 'skill-' prefix."""

import json
import sys
from pathlib import Path
import shutil

# Default skills directories
SKILLS_DIRS = [
    Path("skills"),  # Current workspace skills directory
    Path(r"C:\Users\Administrator\.claude\skills"),
    Path(r"C:\Users\Administrator\.codex\skills"),
    Path(r"C:\Users\Administrator\.gemini\skills"),
]


def fix_package_json(package_json_path: Path) -> bool:
    """Fix package.json by removing 'skill-' prefix from name."""
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

            return True
    except Exception as e:
        print(f"  [ERROR] Error fixing package.json: {e}")
        return False

    return False


def fix_skill_directory(skill_dir: Path) -> bool:
    """Fix a skill directory: rename directory and fix package.json."""
    dir_name = skill_dir.name
    
    # if directory name has 'skill-' prefix
    if not dir_name.startswith("skill-"):
        print(f"- Skipped {dir_name}: no 'skill-' prefix in directory name")
        return False

    new_dir_name = dir_name[6:]  # Remove 'skill-'
    new_skill_dir = skill_dir.parent / new_dir_name

    # Check if target directory already exists
    if new_skill_dir.exists():
        print(f"  [WARN] Skipped {dir_name}: target directory '{new_dir_name}' already exists")
        return False

    try:
        # Fix package.json first (in the old directory)
        package_json_path = skill_dir / "package.json"
        package_fixed = fix_package_json(package_json_path)

        # Rename directory
        skill_dir.rename(new_skill_dir)
        
        status = "[OK]"
        details = []
        if package_fixed:
            details.append("package.json fixed")
        details.append(f"directory renamed")
        
        print(f"{status} {dir_name} -> {new_dir_name} ({', '.join(details)})")
        return True

    except Exception as e:
        print(f"  [ERROR] Error fixing {dir_name}: {e}")
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
        # Get all subdirectories first (to avoid issues during renaming)
        skill_dirs = [d for d in skills_dir.iterdir() if d.is_dir()]
        
        for skill_dir in skill_dirs:
            if fix_skill_directory(skill_dir):
                fixed_count += 1

        print(f"\nFixed {fixed_count} skills in {skills_dir}\n")
        total_fixed += fixed_count

    print(f"=" * 50)
    print(f"Total fixed: {total_fixed} skills")


if __name__ == "__main__":
    main()
