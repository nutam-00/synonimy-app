
from flask import Flask, render_template, request, redirect, session
from datetime import datetime
import json
import random
import os

app = Flask(__name__)
app.secret_key = "jakis_tajny_klucz_123"

# Wczytaj bazę słów
with open("baza_synonimow.json", "r", encoding="utf-8") as f:
    synonimy = json.load(f)

def zapisz_wynik(nick, punkty):
    plik = "wyniki.json"

    # jeśli plik nie istnieje – utwórz
    if not os.path.exists(plik):
        with open(plik, "w", encoding="utf-8") as f:
            json.dump([], f)

    # wczytaj stare wyniki
    with open(plik, "r", encoding="utf-8") as f:
        dane = json.load(f)

    # dodaj nowy wynik
    dane.append({
        "nick": nick,
        "punkty": punkty,
        "max": 5,
        "data": datetime.now().strftime("%Y-%m-%d %H:%M")
    })

    # zapisz
    with open(plik, "w", encoding="utf-8") as f:
        json.dump(dane, f, ensure_ascii=False, indent=2)


# ================= STRONA STARTOWA =================
@app.route("/")
def index():
    return render_template("index.html")


# ================= ROZPOCZĘCIE GRY =================
@app.route("/start", methods=["POST"])
def start_post():
    nick = request.form.get("nick")

    session.clear()
    session["nick"] = nick
    session["punkty"] = 0
    session["runda"] = 1
    session["zapisano"] = False

    session["wylosowane"] = random.sample(list(synonimy.keys()), 5)

    return redirect("/gra")


# ================= GRA =================
@app.route("/gra", methods=["GET", "POST"])
def gra():

    if "wylosowane" not in session:
        return redirect("/")

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

        # zapisz wynik rundy
        session["ostatnie_slowo"] = slowo
        session["ostatnie_trafione"] = trafione
        session["ostatnie_poprawne"] = poprawne[:6]

        session["runda"] += 1
        return redirect("/wynik")

    return render_template("gra.html", slowo=slowo, runda=session["runda"], punkty=session["punkty"])


# ================= WYNIK RUNDY =================
@app.route("/wynik")
def wynik():

    if "ostatnie_slowo" not in session:
        return redirect("/gra")

    ostatnia_runda = session["runda"] - 1

    return render_template(
        "wynik.html",
        slowo=session["ostatnie_slowo"],
        trafione=session["ostatnie_trafione"],
        poprawne=session["ostatnie_poprawne"],
        runda=ostatnia_runda,
        punkty=session["punkty"],
        czy_koniec = ostatnia_runda >= 5
    )


# ================= KONIEC GRY =================
@app.route("/koniec")
def koniec():
    wynik = session["punkty"]
    nick = session.get("nick", "Gracz")

    # zapisz tylko raz (żeby nie zapisywało po odświeżeniu)
    if not session.get("zapisano"):
        zapisz_wynik(nick, wynik)
        session["zapisano"] = True

    return render_template("koniec.html", wynik=wynik, imie=nick)



if __name__ == "__main__":
    app.run()
