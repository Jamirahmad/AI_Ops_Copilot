import time

def sanitize(text: str) -> str:
    # Mask card numbers (simple example)
    return text.replace("1234", "****")

def log_event(query, response, latency):
    with open("logs.txt", "a") as f:
        f.write(f"TIME: {time.time()}\n")
        f.write(f"QUERY: {sanitize(query)}\n")
        f.write(f"RESPONSE: {sanitize(response)}\n")
        f.write(f"LATENCY: {latency}\n\n")
