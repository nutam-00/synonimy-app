from flask import Flask, render_template, request
from datetime import datetime
import json
import random

app = Flask(__name__)

# Wczytaj bazę słów
with open("baza_synonimow.json", "r", encoding="utf-8") as f:
    baza = json.load(f)

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        imie = request.form.get("imie")
        data_start = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        slowo, synonimy = random.choice(list(baza.items()))

        return f"""
        <h1>Witaj {imie}!</h1>
        <p>Data rozpoczęcia: {data_start}</p>
        <h2>Słowo: {slowo}</h2>
        """

    return render_template("index.html")

if __name__ == "__main__":
    app.run()
