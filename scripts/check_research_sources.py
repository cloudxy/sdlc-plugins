#!/usr/bin/env python3
"""Check dated URL/local-artifact references, not research quality or source quotas."""
import re
import sys
from pathlib import Path

def has_source(path):
    path = Path(path)
    for line in path.read_text(encoding="utf-8").splitlines():
        if not re.search(r"20[0-9]{2}-[0-9]{2}-[0-9]{2}", line):
            continue
        if re.search(r"https?://[^\s|)]+", line):
            return True
        refs = re.findall(r"\[[^]]*\]\(([^)]+)\)|`([^`]+)`", line)
        for link, code in refs:
            raw = (link or code).split("#", 1)[0].strip("<>")
            source = Path(raw)
            if (source if source.is_absolute() else path.parent / source).is_file():
                return True
    return False

if __name__ == "__main__":
    sys.exit(0 if has_source(sys.argv[1]) else 1)
