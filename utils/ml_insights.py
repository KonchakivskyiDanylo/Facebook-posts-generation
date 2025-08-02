import random

def generate_ml_insights():
    return {
        "topic": {
            "high": [("Electric Vehicles", random.randint(80, 100))],
            "medium": [("Charging Infrastructure", random.randint(60, 79))],
            "low": [("Diesel Engines", random.randint(30, 59))]
        },
        "language": {
            "high": [("English", random.randint(70, 100))],
            "low": [("Arabic", random.randint(30, 69))]
        }
    }
