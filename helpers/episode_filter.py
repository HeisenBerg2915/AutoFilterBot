import re


EPISODE_PATTERNS = [
    r"\bS\d{1,2}\s*E\d{1,3}\b",
    r"\b\d{1,2}x\d{1,3}\b",
    r"\bSeason\s*\d+\s*Episode\s*\d+\b",
    r"\bS\d{1,2}\s*EP\d{1,3}\b",
    r"\bSeason\s*\d+\s*Ep\s*\d+\b",
]


def is_tv_episode(file_name):
    if not file_name:
        return False

    for pattern in EPISODE_PATTERNS:
        if re.search(pattern, file_name, re.IGNORECASE):
            return True

    return False
