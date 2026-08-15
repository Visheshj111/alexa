"""
Memory system for the voice assistant.

Architecture:
    Conversations → LLM proposes changes → Python validates → Merge engine → memory.json
    
Each memory entry carries metadata:
    - source: initial_profile | explicit | inferred | correction
    - confidence: 0.0-1.0
    - first_seen / last_confirmed: timestamps
    - status: active | stale

The LLM never directly rewrites memory.json. It proposes add/update/remove
operations, which Python validates against a schema before applying.
"""

import json
import os
import shutil
from datetime import datetime

HISTORY_FILE = "conversation_history.json"
MEMORY_FILE = "memory.json"
MEMORY_BACKUP = "memory.json.bak"
CHANGELOG_FILE = "memory_changelog.json"
CONSOLIDATION_INTERVAL = 10

SESSION_START_INDEX = 0

NOW = lambda: datetime.now().strftime("%Y-%m-%d %H:%M")
TODAY = lambda: datetime.now().strftime("%Y-%m-%d")

# ── Memory entry schema ────────────────────────────────────────────────
VALID_CATEGORIES = [
    "identity", "response_preferences", "standing_corrections",
    "technical_profile", "active_context", "explicit_memories"
]
VALID_SOURCES = ["initial_profile", "explicit", "inferred", "correction"]
VALID_STATUSES = ["active", "stale"]

REQUIRED_ENTRY_KEYS = {"fact", "category"}


def _make_entry(fact, category, source="inferred", confidence=0.7):
    """Create a properly structured memory entry."""
    return {
        "fact": fact,
        "category": category,
        "source": source,
        "confidence": min(1.0, max(0.0, confidence)),
        "first_seen": TODAY(),
        "last_confirmed": TODAY(),
        "status": "active"
    }


# ── Default memory structure ────────────────────────────────────────────
DEFAULT_MEMORY = {
    "entries": [],
    "do_not_infer": [
        "Do not assume a temporary project is still active.",
        "Do not assume a technology is still preferred because it was used previously.",
        "Do not treat a single complaint as a permanent preference.",
        "Do not store secrets, credentials, API keys or authentication tokens.",
        "Do not infer personality traits from isolated conversations.",
        "Do not treat plans as completed actions."
    ]
}


# ── File I/O ────────────────────────────────────────────────────────────
def _load_memory():
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                # Migration: if old format (no "entries" key), convert
                if "entries" not in data:
                    return _migrate_old_format(data)
                return data
        except (json.JSONDecodeError, Exception):
            return dict(DEFAULT_MEMORY)
    return dict(DEFAULT_MEMORY)


def _migrate_old_format(old):
    """Convert the old flat-dict format to the new entries-based format."""
    entries = []
    
    identity = old.get("identity", {})
    for k, v in identity.items():
        if v:
            entries.append(_make_entry(f"{k}: {v}", "identity", "initial_profile", 0.95))

    for pref in old.get("response_preferences", []):
        entries.append(_make_entry(pref, "response_preferences", "initial_profile", 0.95))

    for corr in old.get("standing_corrections", []):
        entries.append(_make_entry(corr, "standing_corrections", "correction", 1.0))

    for tech in old.get("technical_profile", []):
        entries.append(_make_entry(tech, "technical_profile", "initial_profile", 0.9))

    for ctx in old.get("active_context", []):
        entries.append(_make_entry(ctx, "active_context", "initial_profile", 0.8))

    for mem in old.get("explicit_memories", []):
        fact = mem["fact"] if isinstance(mem, dict) else mem
        entries.append(_make_entry(fact, "explicit_memories", "explicit", 1.0))

    return {
        "entries": entries,
        "do_not_infer": old.get("do_not_infer", DEFAULT_MEMORY["do_not_infer"])
    }


def _save_memory(memory_data):
    if os.path.exists(MEMORY_FILE):
        shutil.copy(MEMORY_FILE, MEMORY_BACKUP)
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(memory_data, f, indent=2, ensure_ascii=False)


def _log_change(action, field, old_value, new_value, reason, source="consolidation"):
    """Append a detailed changelog entry."""
    log = []
    if os.path.exists(CHANGELOG_FILE):
        try:
            with open(CHANGELOG_FILE, "r", encoding="utf-8") as f:
                log = json.load(f)
        except (json.JSONDecodeError, Exception):
            log = []

    log.append({
        "timestamp": NOW(),
        "action": action,
        "field": field,
        "old": old_value,
        "new": new_value,
        "reason": reason,
        "source": source
    })
    log = log[-300:]
    with open(CHANGELOG_FILE, "w", encoding="utf-8") as f:
        json.dump(log, f, indent=2, ensure_ascii=False)


# ── Conversation history ────────────────────────────────────────────────
def _load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, Exception):
            return []
    return []


def _save_history(history):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)


def save_turn(user_text, assistant_response):
    """Save a raw conversation turn. Returns True if consolidation is due."""
    history = _load_history()
    history.append({
        "user": user_text,
        "assistant": assistant_response,
        "time": NOW()
    })
    _save_history(history)
    return len(history) % CONSOLIDATION_INTERVAL == 0 and len(history) >= CONSOLIDATION_INTERVAL


# ── Explicit user commands ──────────────────────────────────────────────
def add_explicit_memory(fact):
    """User said 'remember that...' — stored with source=explicit, confidence=1.0"""
    memory = _load_memory()
    entry = _make_entry(fact, "explicit_memories", "explicit", 1.0)
    memory["entries"].append(entry)
    _save_memory(memory)
    _log_change("add", "explicit_memories", None, fact, "User explicitly asked to remember", "user_command")
    return "I'll remember that."


def forget_memory(fact_fragment):
    """User said 'forget that...' — marks matching entries as stale."""
    memory = _load_memory()
    fact_lower = fact_fragment.lower()
    removed = []

    for entry in memory["entries"]:
        if fact_lower in entry["fact"].lower() and entry["status"] == "active":
            entry["status"] = "stale"
            removed.append(entry["fact"])
            _log_change("remove", entry["category"], entry["fact"], None,
                        f"User explicitly asked to forget", "user_command")

    if removed:
        _save_memory(memory)
        return f"Forgot {len(removed)} thing{'s' if len(removed) > 1 else ''}."
    return "I couldn't find anything matching that in my memory."


# ── Validation layer ────────────────────────────────────────────────────
def _validate_proposal(proposal):
    """Validate a proposed memory change from the LLM.
    Returns (valid_adds, valid_updates, valid_removes)."""
    valid_adds = []
    valid_updates = []
    valid_removes = []

    for item in proposal.get("add", []):
        if not isinstance(item, dict):
            continue
        if "fact" not in item or "category" not in item:
            continue
        if item["category"] not in VALID_CATEGORIES:
            continue
        if item.get("source") and item["source"] not in VALID_SOURCES:
            item["source"] = "inferred"
        # Don't allow LLM to add explicit_memories — only user commands can
        if item["category"] == "explicit_memories":
            continue
        valid_adds.append(item)

    for item in proposal.get("update", []):
        if not isinstance(item, dict):
            continue
        if "old_fact" not in item or "new_fact" not in item:
            continue
        valid_updates.append(item)

    for item in proposal.get("remove", []):
        if isinstance(item, str):
            valid_removes.append(item)
        elif isinstance(item, dict) and "fact" in item:
            valid_removes.append(item["fact"])

    return valid_adds, valid_updates, valid_removes


# ── Merge engine ────────────────────────────────────────────────────────
def apply_proposed_changes(proposal):
    """Validate and apply proposed memory changes. Returns summary of what changed."""
    valid_adds, valid_updates, valid_removes = _validate_proposal(proposal)
    memory = _load_memory()
    changes_made = []

    # Apply removes (mark as stale)
    for remove_fact in valid_removes:
        remove_lower = remove_fact.lower()
        for entry in memory["entries"]:
            if remove_lower in entry["fact"].lower() and entry["status"] == "active":
                # Don't let LLM remove explicit user memories
                if entry["source"] == "explicit":
                    continue
                entry["status"] = "stale"
                changes_made.append(f"Removed: {entry['fact']}")
                _log_change("remove", entry["category"], entry["fact"], None,
                            proposal.get("remove_reason", "consolidation pruning"), "consolidation")

    # Apply updates
    for update in valid_updates:
        old_lower = update["old_fact"].lower()
        found = False
        for entry in memory["entries"]:
            if old_lower in entry["fact"].lower() and entry["status"] == "active":
                # Don't let LLM update explicit user memories
                if entry["source"] == "explicit":
                    continue
                old_fact = entry["fact"]
                entry["fact"] = update["new_fact"]
                entry["last_confirmed"] = TODAY()
                # Boost confidence slightly when updated
                entry["confidence"] = min(1.0, entry.get("confidence", 0.7) + 0.05)
                changes_made.append(f"Updated: '{old_fact}' → '{update['new_fact']}'")
                _log_change("update", entry["category"], old_fact, update["new_fact"],
                            update.get("reason", "consolidation update"), "consolidation")
                found = True
                break
        if not found:
            # Treat as an add if old fact wasn't found
            valid_adds.append({
                "fact": update["new_fact"],
                "category": update.get("category", "active_context"),
                "source": "inferred"
            })

    # Apply adds (check for duplicates)
    existing_facts = {e["fact"].lower() for e in memory["entries"] if e["status"] == "active"}
    for add_item in valid_adds:
        if add_item["fact"].lower() in existing_facts:
            # Just bump last_confirmed on the existing entry
            for entry in memory["entries"]:
                if entry["fact"].lower() == add_item["fact"].lower():
                    entry["last_confirmed"] = TODAY()
                    break
            continue

        entry = _make_entry(
            add_item["fact"],
            add_item["category"],
            add_item.get("source", "inferred"),
            add_item.get("confidence", 0.7)
        )
        memory["entries"].append(entry)
        changes_made.append(f"Added: {add_item['fact']}")
        _log_change("add", add_item["category"], None, add_item["fact"],
                     add_item.get("reason", "consolidation add"), "consolidation")

    if changes_made:
        _save_memory(memory)

    return changes_made


# ── Consolidation prompt ────────────────────────────────────────────────
def get_consolidation_prompt():
    """Build the prompt asking the LLM to PROPOSE changes, not rewrite memory."""
    history = _load_history()
    recent = history[-CONSOLIDATION_INTERVAL:]
    memory = _load_memory()

    # Show only active entries to the LLM
    active_entries = [e for e in memory.get("entries", []) if e.get("status") == "active"]
    active_summary = json.dumps(active_entries, indent=2, ensure_ascii=False)

    conversation_block = ""
    for turn in recent:
        conversation_block += f"[{turn['time']}] User: {turn['user']}\n"
        conversation_block += f"[{turn['time']}] Assistant: {turn['assistant']}\n\n"

    prompt = (
        "You are a memory manager. Read the recent conversations and PROPOSE changes "
        "to the user's memory. Do NOT rewrite the entire memory. Only propose specific changes.\n\n"

        "Output ONLY valid JSON with this exact structure:\n"
        "{\n"
        '  "add": [\n'
        '    {"fact": "...", "category": "...", "confidence": 0.0-1.0, "reason": "..."}\n'
        "  ],\n"
        '  "update": [\n'
        '    {"old_fact": "...", "new_fact": "...", "reason": "..."}\n'
        "  ],\n"
        '  "remove": [\n'
        '    {"fact": "...", "reason": "..."}\n'
        "  ]\n"
        "}\n\n"

        f"Valid categories: {', '.join(VALID_CATEGORIES)}\n\n"

        "RULES:\n"
        "1. Only ADD facts that reveal something lasting about the user.\n"
        "2. Only UPDATE facts that are now outdated or were corrected by the user.\n"
        "3. Only REMOVE facts that are clearly stale or contradicted.\n"
        "4. NEVER add emotional state, casual venting, or one-off moods.\n"
        "5. Corrections from the user get category='standing_corrections' and confidence=1.0.\n"
        "6. If nothing meaningful changed, return: {\"add\": [], \"update\": [], \"remove\": []}\n"
        "7. Do NOT touch entries with source='explicit' — those are user-controlled.\n\n"

        f"CURRENT ACTIVE MEMORY:\n{active_summary}\n\n"
        f"RECENT CONVERSATIONS:\n{conversation_block}\n\n"

        "Propose changes now (JSON only, no commentary):"
    )
    return prompt


# ── Error guards for consolidation output ────────────────────────────────
ERROR_SIGNALS = [
    "error connecting", "isn't running", "took too long",
    "error talking to", "connection refused", "timed out",
    "traceback", "exception"
]


def parse_consolidation_output(raw_output):
    """Parse and validate LLM consolidation output.
    Returns the proposal dict or None if invalid."""
    raw_output = raw_output.strip()

    if not raw_output:
        print("[MEMORY] Empty consolidation output.")
        return None

    if any(sig in raw_output.lower() for sig in ERROR_SIGNALS):
        print("[MEMORY] Consolidation output looks like an error, rejecting.")
        return None

    # Strip markdown code fences if present
    if raw_output.startswith("```"):
        lines = raw_output.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        raw_output = "\n".join(lines)

    try:
        proposal = json.loads(raw_output)
    except json.JSONDecodeError:
        print(f"[MEMORY] Output is not valid JSON: {raw_output[:200]}")
        return None

    if not isinstance(proposal, dict):
        print("[MEMORY] Output is not a dict.")
        return None

    # Must have at least one of the expected keys
    if not any(k in proposal for k in ["add", "update", "remove"]):
        print("[MEMORY] Output missing add/update/remove keys.")
        return None

    return proposal


# ── Context builder for prompt injection ─────────────────────────────────
def start_new_session():
    """Start a new conversation session, resetting short-term context."""
    global SESSION_START_INDEX
    SESSION_START_INDEX = len(_load_history())
    print(f"[MEMORY] Started new session at turn {SESSION_START_INDEX}")

def get_recent_turns(n=3):
    history = _load_history()[SESSION_START_INDEX:]
    return history[-n:] if history else []


def build_memory_context():
    """Build concise memory string for prompt injection.
    Only injects active entries, grouped by category."""
    memory = _load_memory()
    active = [e for e in memory.get("entries", []) if e.get("status") == "active"]

    if not active:
        return ""

    parts = []

    # Group by category
    by_cat = {}
    for entry in active:
        cat = entry.get("category", "other")
        by_cat.setdefault(cat, []).append(entry["fact"])

    cat_labels = {
        "identity": "User",
        "response_preferences": "Response preferences",
        "standing_corrections": "Standing corrections (never re-litigate)",
        "technical_profile": "Technical profile",
        "active_context": "Currently working on",
        "explicit_memories": "User explicitly asked to remember",
    }

    for cat, facts in by_cat.items():
        label = cat_labels.get(cat, cat)
        if cat == "identity":
            parts.append(f"{label}: {'; '.join(facts)}")
        else:
            parts.append(f"{label}: {'; '.join(facts)}")

    # Recent raw turns for immediate context
    recent = get_recent_turns(3)
    if recent:
        recent_lines = []
        for turn in recent:
            recent_lines.append(f"User: {turn['user']}")
            recent_lines.append(f"You: {turn['assistant']}")
        parts.append("Recent conversation:\n" + "\n".join(recent_lines))

    return "\n".join(parts)
