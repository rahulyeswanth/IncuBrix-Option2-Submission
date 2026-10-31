"""Read a long input (txt/md/srt/vtt) and extract hooks, key points, keywords.

Deliberately deterministic and dependency-free: no API calls, so a run costs $0 and
gives the same output for the same input. Quality is 'good first draft'; a human
reviews before publishing.
"""
import re
from collections import Counter

STOPWORDS = set("""a about above after again all also am an and any are as at be because been before being below
between both but by can could did do does doing down during each few for from further had has have having he her
here hers him his how i if in into is it its itself just let like me more most my no nor not now of off on once
only or other our out over own same she should so some such than that the their them then there these they this
those through to too under until up very was we were what when where which while who why will with would you your
yours really thing things going got get gonna kind lot stuff yeah okay ok um uh right actually basically""".split())

CUE_WORDS = {"but", "never", "stop", "mistake", "instead", "only", "without", "before", "why", "how",
             "because", "rule", "first", "most", "problem", "fix", "start", "skip", "avoid", "if"}


class InputError(Exception):
    """Raised for unreadable / empty / too-short inputs."""


_TS = re.compile(r"^\s*(\d+\s*)?\d{1,2}:\d{2}(:\d{2})?[.,]?\d*\s*-->\s*\d{1,2}:\d{2}(:\d{2})?[.,]?\d*.*$")


def load_text(path):
    """Return clean prose text from a .txt/.md/.srt/.vtt file."""
    try:
        with open(path, "rb") as fh:
            raw = fh.read()
    except OSError as exc:
        raise InputError(f"cannot read {path}: {exc}") from exc
    for enc in ("utf-8-sig", "utf-16", "latin-1"):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    else:  # pragma: no cover
        raise InputError(f"cannot decode {path}")
    if "\x00" in text:
        raise InputError(f"{path} looks binary, not text")
    lines, title = [], ""
    for ln in text.splitlines():
        s = ln.strip()
        if not s or s.upper() == "WEBVTT" or s.isdigit() or _TS.match(s):
            continue
        if s.startswith("#"):                   # markdown heading: keep as title, not prose
            title = title or re.sub(r"^#+\s*", "", s)
            continue
        s = re.sub(r"^[A-Z][\w .]{0,20}:\s+", "", s)   # "Host: " speaker labels
        s = re.sub(r"<[^>]+>", "", s)          # vtt/html tags
        lines.append(s)
    clean = re.sub(r"\s+", " ", " ".join(lines)).strip()
    if len(clean.split()) < 150:
        raise InputError(f"{path}: input too short ({len(clean.split())} words, need 150+)")
    return clean


def load_title(path, fallback=""):
    """First markdown heading in the file, else fallback."""
    try:
        with open(path, encoding="utf-8-sig", errors="replace") as fh:
            for ln in fh:
                if ln.startswith("#"):
                    return re.sub(r"^#+\s*", "", ln).strip()
    except OSError:
        pass
    return fallback


def split_sentences(text):
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z\"'])", text)
    return [p.strip() for p in parts if len(p.split()) >= 3]


def tokens(text):
    return [w for w in re.findall(r"[a-zA-Z][a-zA-Z'-]+", text.lower())]


def keywords(text, n=12):
    counts = Counter(w for w in tokens(text) if w not in STOPWORDS and len(w) > 3)
    return [w for w, _ in counts.most_common(n)]


def _score(sentence, kw_set, kw_rank):
    toks = tokens(sentence)
    if not toks:
        return 0.0
    overlap = sum(kw_rank.get(w, 0) for w in toks) / (len(toks) ** 0.5)
    cues = sum(1 for w in toks if w in CUE_WORDS)
    n = len(toks)
    length_bonus = 1.0 if 6 <= n <= 22 else 0.2
    q = 0.5 if sentence.endswith("?") else 0
    return (overlap + 1.5 * cues + q) * length_bonus


_BAD_OPEN = re.compile(r"^(because|and|but|so|or|that|this|these|those|it|they|he|she|then|also|which)\b", re.I)


def usable_standalone(sentence, max_words=None):
    """True if the sentence reads fine on its own (no dangling reference, not a fragment)."""
    s = sentence.strip()
    n = len(s.split())
    if _BAD_OPEN.match(s) or n < 4:
        return False
    if max_words and n > max_words:
        return False
    return s.endswith((".", "?", "!"))


def analyse(text, max_hook_words=12):
    sents = split_sentences(text)
    kws = keywords(text)
    rank = {w: (len(kws) - i) / len(kws) for i, w in enumerate(kws)}
    scored = sorted(((_score(s, set(kws), rank), i, s) for i, s in enumerate(sents)), reverse=True)

    hooks, used = [], set()
    for sc, i, s in scored:
        if usable_standalone(s, max_hook_words) and not s.startswith("If ") and s.lower() not in used:
            hooks.append(s)
            used.add(s.lower())
        if len(hooks) >= 30:
            break

    points = []
    for sc, i, s in scored:
        n = len(s.split())
        if 6 <= n <= 24 and usable_standalone(s) and s not in points:
            points.append(s)
        if len(points) >= 36:
            break
    # keep points in the order they appear in the source (reads like an argument)
    order = {s: i for i, s in enumerate(sents)}
    points.sort(key=lambda s: order.get(s, 0))

    topic = " ".join(w.capitalize() for w in kws[:3])
    return {"keywords": kws, "hooks": hooks, "points": points, "topic": topic, "n_sentences": len(sents)}
