"""
Test script for TypeSafe AI Jev integration.
"""

from typesafe_router import classify_intent_with_jev, is_jev_enabled, JEV_INTENT_CRITERIA

def test_router():
    print("=== Testing TypeSafe AI Jev Router ===")
    print(f"Total defined intent criteria: {len(JEV_INTENT_CRITERIA)}")
    print(f"Jev Enabled: {is_jev_enabled()}")
    
    test_queries = [
        "open google chrome for me",
        "turn down the volume a bit",
        "what is currently displayed on my screen?",
        "remind me to call mom tomorrow at noon",
        "how does photosynthesis work in plants?"
    ]
    
    for q in test_queries:
        intent, conf = classify_intent_with_jev(q)
        print(f"Query: '{q}' -> Jev Intent: {intent} (conf: {conf})")

    print("\nRouter test executed cleanly.")

if __name__ == "__main__":
    test_router()
