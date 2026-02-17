import json
import nltk
from nltk.corpus import wordnet as wn

def generate_database(limit=200):
    baza = {}

    for synset in wn.all_synsets():
        polskie = synset.lemma_names("pol")

        if len(polskie) >= 2:
            slowo = polskie[0].replace("_", " ")

            if len(slowo) < 5:
                continue

            synonimy = [
                l.replace("_", " ")
                for l in polskie[1:11]
                if l != slowo
            ]

            if len(synonimy) >= 2:
                baza[slowo] = synonimy

        if len(baza) >= limit:
            break

    return baza


if __name__ == "__main__":
    baza = generate_database(300)

    with open("baza_synonimow.json", "w", encoding="utf-8") as f:
        json.dump(baza, f, ensure_ascii=False, indent=2)

    print("Gotowe! Wygenerowano", len(baza), "słów.")
