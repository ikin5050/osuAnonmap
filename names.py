"""Random "Adjective Noun" names used to anonymise contest entries."""

from __future__ import annotations

import random
from typing import Iterable

# How many random draws to try before giving up on finding a safe name.
MAX_ATTEMPTS = 10_000

# Neutral or positive words only, so a name can't put judges off an entry.

ADJECTIVES = (
    "happy", "bright", "dark", "loud", "quiet", "calm", "fast", "slow", "big", "small",
    "hot", "cold", "tall", "short", "heavy", "light", "strong", "beautiful", "clean", "healthy",
    "thin", "thick", "rich", "young", "old", "funny", "serious", "kind", "brave", "wise",
    "smart", "simple", "complex", "honest", "generous", "polite", "creative", "loving", "adventurous", "cautious",
    "active", "jolly", "spacious", "mysterious", "delicious", "gentle", "vivid", "pale", "wild", "flexible",
    "tough", "helpful", "peaceful", "exciting", "lively", "confident", "eager", "attractive", "familiar", "caring",
    "daring", "charming", "lucky", "glamorous", "productive", "vibrant", "competent", "shy", "outgoing", "sincere",
    "respectful", "clear", "ambitious", "innocent", "curious", "humble", "determined", "fierce", "elegant", "thoughtful",
    "cooperative", "loyal", "sensible", "experienced", "optimistic", "tolerant", "trustworthy", "rational", "responsible", "passionate",
    "talented", "witty", "grateful", "diligent", "independent", "efficient", "faithful", "resourceful", "exuberant", "accomplished",
    "imaginative", "responsive", "practical", "resilient", "amicable", "graceful", "distinguished", "unique", "assertive", "brilliant",
    "vocal", "prosperous", "celebrated", "mature", "invincible", "persistent", "prudent", "energetic", "humorous", "shrewd",
    "successful", "charismatic", "magnificent", "perceptive",
)

NOUNS = (
    "apple", "banana", "orange", "dog", "cat", "bird", "tree", "flower", "car", "book",
    "house", "table", "chair", "computer", "phone", "pencil", "pen", "river", "mountain", "ocean",
    "sun", "moon", "star", "cloud", "rain", "snow", "wind", "fire", "earth", "sky",
    "friend", "family", "teacher", "student", "doctor", "engineer", "actor", "artist", "singer", "writer",
    "scientist", "chef", "athlete", "baby", "child", "adult", "parent", "grandparent", "neighbor", "city",
    "village", "country", "continent", "island", "lake", "forest", "desert", "jungle", "cave", "school",
    "college", "university", "hospital", "library", "park", "zoo", "market", "store", "restaurant", "airport",
    "train", "bus", "ship", "bicycle", "motorcycle", "helicopter", "rocket", "submarine", "truck", "camera",
    "television", "radio", "music", "movie", "game", "sport", "art", "history", "science", "mathematics",
    "language", "culture", "economy", "society", "nature", "environment", "technology", "space", "time", "love",
    "happiness", "peace", "freedom", "justice", "faith", "hope", "dream", "success", "truth", "wisdom",
    "courage", "strength", "patience", "kindness", "generosity", "humility", "passion", "creativity", "imagination", "curiosity",
    "ambition", "friendship", "loyalty", "laughter", "memory", "idea", "plan", "goal", "challenge", "solution",
    "victory", "adventure", "journey", "experience", "achievement", "discovery", "invention", "celebration", "ceremony", "holiday",
    "tradition", "custom", "legend", "myth", "folklore", "fable", "fairytale", "story", "poem", "song",
    "dance", "painting", "sculpture", "architecture", "design", "recipe", "meal", "drink", "dessert", "snack",
    "clothing", "shoes", "jewelry", "accessory", "gadget", "tool", "instrument", "appliance", "furniture", "artifact",
    "treasure", "coin", "gem", "currency", "ticket", "passport", "certificate", "document", "letter", "message",
    "map", "flag", "symbol", "sign", "code", "number", "word", "sentence", "paragraph", "chapter",
    "verse", "novel", "essay", "article", "report", "speech", "lecture", "presentation", "show", "play",
    "concert", "event", "festival", "wedding", "birthday", "anniversary", "vacation", "trip", "expedition", "exploration",
    "research", "experiment", "theory", "hypothesis", "law", "principle", "formula", "equation", "variable", "constant",
    "quantity", "measurement", "observation", "analysis", "interpretation", "conclusion", "recommendation", "application", "task", "objective",
    "mission", "vision", "aspiration", "desire", "belief", "question", "answer", "query", "inquiry", "investigation",
    "innovation", "creation", "inspiration", "motivation", "enthusiasm",
)


class NameGenerator:
    """Hands out unique anonymous names that cannot be linked to any entrant.

    A name is rejected if it has already been used in this run, or if it
    overlaps with any entrant's username in either direction (e.g. the
    username "Happy" or "HappyMapper" rules out "Happy Cat").
    """

    def __init__(self, usernames: Iterable[str], rng: random.Random | None = None):
        self._usernames = {u.strip().lower() for u in usernames if u.strip()}
        self._used: set[str] = set()
        self._rng = rng or random.Random()

    def is_safe(self, name: str) -> bool:
        lowered = name.lower()
        if lowered in self._used:
            return False
        for username in self._usernames:
            if username in lowered:
                return False
            if any(word in username for word in lowered.split()):
                return False
        return True

    def new_name(self) -> str:
        for _ in range(MAX_ATTEMPTS):
            adjective = self._rng.choice(ADJECTIVES).capitalize()
            noun = self._rng.choice(NOUNS).capitalize()
            name = f"{adjective} {noun}"
            if self.is_safe(name):
                self._used.add(name.lower())
                return name
        raise RuntimeError("Could not generate a unique anonymous name; extend the word lists in names.py")
