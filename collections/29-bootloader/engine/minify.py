import re
def minify_js(s: str) -> str:
    s = re.sub(r"\s+", " ", s)
    return s.strip()
