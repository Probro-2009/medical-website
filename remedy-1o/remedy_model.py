# remedy_model.py
class RemedyPredictor:
    def __init__(self):
        self.symptom_map = {
            "headache": "Belladonna",
            "acne": "Sulphur",
            "cold": "Arsenicum Album",
            "insomnia": "Coffea Cruda",
            "fever": "Aconite"   # <-- make sure this exists!
        }

    def predict(self, symptoms: list[str]) -> list[str]:
        remedies = []
        for sym in symptoms:
            remedy = self.symptom_map.get(sym.lower())
            if remedy and remedy not in remedies:
                remedies.append(remedy)
        return remedies or ["No remedy found"]
