
from flask import Flask, render_template, request, redirect, session
from datetime import datetime, timedelta
import json
import random
import os



BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PLIK_WYNIKOW = os.path.join(BASE_DIR, "wyniki.json")

print("PLIK WYNIKOW:", PLIK_WYNIKOW)

app = Flask(__name__)
app.secret_key = "jakis_tajny_klucz_123"

# Wczytaj bazę słów
with open("baza_synonimow.json", "r", encoding="utf-8") as f:
    synonimy = json.load(f)

def zapisz_wynik(nick, punkty):

    try:
        with open(PLIK_WYNIKOW, "r", encoding="utf-8") as f:
            wyniki = json.load(f)
    except:
        wyniki = []

    wyniki.append({
        "nick": nick,
        "punkty": punkty,
        "data": datetime.now().strftime("%Y-%m-%d")

    })

    with open(PLIK_WYNIKOW, "w", encoding="utf-8") as f:
        json.dump(wyniki, f, ensure_ascii=False, indent=2)



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

# ================= RANKING =================


@app.route("/ranking")
def ranking():

    print("CZYTAM Z:", PLIK_WYNIKOW)

    # zapis jeśli ktoś ominął /koniec
    if "punkty" in session and not session.get("zapisano", False):
        zapisz_wynik(session.get("nick", "Gracz"), session["punkty"])
        session["zapisano"] = True

    try:
        with open(PLIK_WYNIKOW, "r", encoding="utf-8") as f:

            wyniki = json.load(f)
    except:
        wyniki = []

    # ostatnie 7 dni
    siedem_dni_temu = (datetime.now() - timedelta(days=7)).date()

    ostatnie = []
    for w in wyniki:
        data_txt = w.get("data", "")

        data_gry = None

        # obsługa wszystkich wersji jakie miałaś
        for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S"):
            try:
                data_gry = datetime.strptime(data_txt, fmt)
                break
            except:
                pass

        if not data_gry:
            continue

        if data_gry.date() >= siedem_dni_temu:
            w["data_obj"] = data_gry
            ostatnie.append(w)




    # sortowanie: punkty ↓, data ↓
    ostatnie.sort(key=lambda x: (x["punkty"], x["data_obj"]), reverse=True)
    top5 = ostatnie[:5]


    # usuń godzinę (tylko do wyświetlenia)
    for w in top5:
        w["data"] = w["data"][:10]

    return render_template("ranking.html", ranking=top5)



# ================= KONIEC GRY =================
@app.route("/koniec")
def koniec():

    if "nick" not in session:
        return redirect("/")

    wynik = session.get("punkty", 0)
    nick = session.get("nick", "Gracz")

    # zapis tylko raz
    if not session.get("zapisano", False):
        zapisz_wynik(nick, wynik)
        session["zapisano"] = True

    return render_template("koniec.html", wynik=wynik, nick=nick)




if __name__ == "__main__":
    app.run()
