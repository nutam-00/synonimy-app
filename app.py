from flask import Flask, render_template, request, redirect, session
from datetime import datetime
import json
import random

app = Flask(__name__)
app.secret_key = "jakis_tajny_klucz_123"

# Wczytaj bazę słów
with open("baza_synonimow.json", "r", encoding="utf-8") as f:
    synonimy = json.load(f)


# ================= START GRY =================
@app.route("/")
def index():
    return render_template("index.html")

# @app.route("/")
# def start():
#     session.clear()
#     session["punkty"] = 0
#     session["runda"] = 1
#     session["wylosowane"] = random.sample(list(synonimy.keys()), 5)
#     return redirect("/gra")

@app.route("/start", methods=["POST"])
def start():
    imie = request.form["imie"]

    session.clear()
    session["imie"] = imie
    session["punkty"] = 0
    session["runda"] = 1
    session["wylosowane"] = random.sample(list(synonimy.keys()), 5)

    return redirect("/gra")



# ================= GRA =================
@app.route("/gra", methods=["GET", "POST"])
def gra():

    if session["runda"] > 5:
        return redirect("/koniec")

    slowo = session["wylosowane"][session["runda"] - 1]

    if request.method == "POST":
        odp1 = request.form["synonim1"].lower().strip()
        odp2 = request.form["synonim2"].lower().strip()

        poprawne = synonimy[slowo]

        trafione = 0
        if odp1 in poprawne:
            trafione += 1
        if odp2 in poprawne and odp2 != odp1:
            trafione += 1

        if trafione == 2:
            session["punkty"] += 1

        # zapisz wynik rundy do sesji
        session["ostatnie_slowo"] = slowo
        session["ostatnie_trafione"] = trafione
        session["ostatnie_poprawne"] = poprawne[:6]

        session["runda"] += 1
        return redirect("/wynik")

    return render_template("gra.html", slowo=slowo, runda=session["runda"])



# ================= WYNIK RUNDY =================
@app.route("/wynik")
def wynik():

    if "ostatnie_slowo" not in session:
        return redirect("/gra")

    return render_template(
        "wynik.html",
        slowo=session["ostatnie_slowo"],
        trafione=session["ostatnie_trafione"],
        poprawne=session["ostatnie_poprawne"],
        runda=session["runda"] - 1,
        punkty=session["punkty"]
    )



# ================= NASTĘPNA RUNDA =================
# @app.route("/nastepna")
# def nastepna():
#     session["runda"] += 1
#     return redirect("/gra")


# ================= KONIEC =================
@app.route("/koniec")
def koniec():
    wynik = session["punkty"]
    return render_template("koniec.html", wynik=wynik, imie=session.get("imie"))


if __name__ == "__main__":
    app.run()
