import re

# =========================
# UNWANTED TAGS
# =========================

TAGS = [
    # ഇവിടെ നിങ്ങൾ മുമ്പ് നൽകിയ മുഴുവൻ TAGS ലിസ്റ്റ് Paste ചെയ്യുക
]


# =========================
# CLEAN FILE NAME
# =========================

def clean_file_name(file_name):

    if not file_name:
        return "Unknown File"

    cleaned = str(file_name)

    for tag in sorted(TAGS, key=len, reverse=True):

        tag = tag.strip()

        if not tag:
            continue

        pattern = (
            r"(?<![A-Za-z0-9])"
            + re.escape(tag)
            + r"(?![A-Za-z0-9])"
        )

        cleaned = re.sub(
            pattern,
            " ",
            cleaned,
            flags=re.IGNORECASE
        )

    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    cleaned = re.sub(
        r"^[\W_]+|[\W_]+$",
        "",
        cleaned
    ).strip()

    return cleaned or "Unknown File"
