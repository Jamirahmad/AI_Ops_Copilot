feedback_store = []

def store_feedback(query, rating):
    feedback_store.append({
        "query": query,
        "rating": rating
    })

def adjust_prompt(base_prompt):
    low_ratings = [f for f in feedback_store if f["rating"] < 3]
    
    if len(low_ratings) > 2:
        return base_prompt + "\nBe more structured and explicit."
    
    return base_prompt
