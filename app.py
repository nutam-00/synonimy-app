from flask import Flask, render_template, request, redirect, session
from datetime import datetime
import json
import random

app = Flask(__name__)
app.secret_key = "jakis_tajny_klucz_123"

# Wczytaj bazę słów
with open("baza_synonimow.json", "r", encoding="utf-8") as f:
    synonimy = json.load(f)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/start", methods=["POST"])
def start():

    session["imie"] = request.form["imie"]
    session["punkty"] = 0
    session["runda"] = 1
    session["wylosowane"] = random.sample(list(synonimy.keys()), 5)

    return redirect("/gra")



@app.route("/gra", methods=["GET", "POST"])
def gra():

    if session["runda"] > 5:
        return redirect("/koniec")

    slowo = session["wylosowane"][session["runda"] - 1]

    if request.method == "POST":
        odp1 = request.form["synonim1"].lower().strip()
        odp2 = request.form["synonim2"].lower().strip()

        poprawne = synonimy[slowo]

        if odp1 in poprawne and odp2 in poprawne and odp1 != odp2:
            session["punkty"] += 1

        session["runda"] += 1
        return redirect("/gra")

    return render_template("gra.html", slowo=slowo, runda=session["runda"])


@app.route("/koniec")
def koniec():
    wynik = session["punkty"]
    imie = session["imie"]
    return render_template("koniec.html", wynik=wynik, imie=imie)



if __name__ == "__main__":
    app.run()
