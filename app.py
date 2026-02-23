
from flask import Flask, render_template, request, redirect, session, make_response

from datetime import datetime, timedelta
import json
import random
import os
import psycopg2


app = Flask(__name__)
app.secret_key = "jakis_tajny_klucz_123"


def get_connection():
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL nie ustawione")

    return psycopg2.connect(
        database_url,
        sslmode="require",
        connect_timeout=10
    )

def get_user_by_id(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, nick, total_points FROM users WHERE id = %s", (user_id,))
    user = cursor.fetchone()
    conn.close()
    return user


def create_user(nick):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO users (nick) VALUES (%s) RETURNING id",
        (nick,)
    )
    user_id = cursor.fetchone()[0]
    conn.commit()
    conn.close()
    return user_id


def add_points(user_id, points):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE users SET total_points = total_points + %s WHERE id = %s",
        (points, user_id)
    )
    conn.commit()
    conn.close()

# ================= TWORZENIE TABELI =================
def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            nick TEXT NOT NULL,
            total_points INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS wyniki (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id),
            punkty INTEGER NOT NULL,
            data TIMESTAMP NOT NULL
        )
    """)


    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tematy (
            id SERIAL PRIMARY KEY,
            temat TEXT NOT NULL,
            wstep TEXT,
            argument1 TEXT,
            argument2 TEXT,
            argument3 TEXT,
            zakonczenie TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS rozprawka_wyniki (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id),
            temat_id INTEGER REFERENCES tematy(id),
            fragment TEXT,
            odpowiedz TEXT,
            data TIMESTAMP DEFAULT NOW(),
            ocenione BOOLEAN DEFAULT FALSE,
            punkty INTEGER
        )
    """)

    conn.commit()
    conn.close()

# ================= WCZYTANIE BAZY SŁÓW =================
with open("baza_synonimow.json", "r", encoding="utf-8") as f:
    synonimy = json.load(f)

def zapisz_wynik(user_id, punkty):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO wyniki (user_id, punkty, data)
        VALUES (%s, %s, %s)
    """, (user_id, punkty, datetime.now()))

    conn.commit()
    conn.close()

def pobierz_ranking():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT 
            u.nick,
            u.total_points,
            MAX(w.data) as last_game
        FROM users u
        LEFT JOIN wyniki w ON u.id = w.user_id
        GROUP BY u.id
        ORDER BY u.total_points DESC, last_game DESC
        LIMIT 5
    """)

    dane = cursor.fetchall()
    conn.close()

    # zwracamy tylko nick i punkty (bez last_game)
    return [(row[0], row[1]) for row in dane]


# ================= STRONA STARTOWA =================
# @app.route("/")
# def index():
#     cookie_user_id = request.cookies.get("user_id")
#     nick = ""

#     if cookie_user_id:
#         user = get_user_by_id(cookie_user_id)
#         if user:
#             nick = user[1]

#     return render_template("index.html", saved_nick=nick)
@app.route("/")
def wybor_gry():
    return render_template("wybor.html")


# ================= SYNONIMY =================
@app.route("/synonimy")
def synonimy_start():
    cookie_user_id = request.cookies.get("user_id")
    nick = ""

    if cookie_user_id:
        user = get_user_by_id(cookie_user_id)
        if user:
            nick = user[1]

    return render_template("index.html", saved_nick=nick)

# ================= ROZPRAWKA =================
@app.route("/rozprawka")
def rozprawka_start():
    return render_template("rozprawka_start.html")

# ================= ROZPOCZĘCIE GRY - ROZPRAWKA =================
@app.route("/start_rozprawka", methods=["POST"])
def start_rozprawka():
    nick = request.form.get("nick").strip()

    session.clear()

    user_id = create_user(nick)

    session["user_id"] = user_id
    session["nick"] = nick
    session["czas_start"] = datetime.now().isoformat()

    return redirect("/gra_rozprawka")

# ================= GRA ROZPRAWKA =================
@app.route("/gra_rozprawka")
def gra_rozprawka():

    if "nick" not in session:
        return redirect("/rozprawka")

    return render_template("gra_rozprawka.html")

# ================= ROZPOCZĘCIE GRY =================
@app.route("/start", methods=["POST"])
def start_post():
    nick = request.form.get("nick").strip()
    remember = request.form.get("remember")

    session.clear()

    cookie_user_id = request.cookies.get("user_id")
    user_id = None

    # Jeśli jest cookie
    if cookie_user_id:
        user = get_user_by_id(cookie_user_id)

        # Jeśli user istnieje w bazie
        if user:
            saved_nick = user[1]

            # Jeśli wpisany nick jest taki sam → używamy tego usera
            if nick == saved_nick:
                user_id = user[0]
            else:
                # Inny nick → tworzymy nowego usera
                user_id = create_user(nick)
        else:
            # Cookie wskazuje nieistniejącego usera
            user_id = create_user(nick)
    else:
        # Brak cookie → tworzymy usera
        user_id = create_user(nick)

    session["user_id"] = user_id
    session["nick"] = nick
    session["punkty"] = 0
    session["runda"] = 1
    session["zapisano"] = False
    session["wylosowane"] = random.sample(list(synonimy.keys()), 5)

    response = make_response(redirect("/gra"))

    # Cookie ustawiamy tylko jeśli checkbox zaznaczony
    if remember:
        response.set_cookie("user_id", str(user_id), max_age=60*60*24*365)

    return response

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
        czy_koniec=ostatnia_runda >= 5
    )


# ================= RANKING =================
@app.route("/ranking")
def ranking():

    if "punkty" in session and not session.get("zapisano", False):
        zapisz_wynik(session["user_id"], session["punkty"])
        add_points(session["user_id"], session["punkty"])
        session["zapisano"] = True

    ranking = pobierz_ranking()
    return render_template("ranking.html", ranking=ranking)




# ================= KONIEC GRY =================
@app.route("/koniec")
def koniec():

    if "nick" not in session:
        return redirect("/")

    wynik = session.get("punkty", 0)
    nick = session.get("nick", "Gracz")

    if not session.get("zapisano", False):
        # zapisz_wynik(nick, wynik)
        zapisz_wynik(session["user_id"], wynik)
        add_points(session["user_id"], wynik)

        session["zapisano"] = True

    return render_template("koniec.html", wynik=wynik, nick=nick)

@app.route("/exit")
def exit_game():
    user_id = session.get("user_id")
    nick = session.get("nick")

    session.clear()

    # przywracamy dane usera do nowej sesji
    if user_id and nick:
        session["user_id"] = user_id
        session["nick"] = nick

    return redirect("/synonimy")

@app.route("/init-db")
def init_database():
    init_db()
    return "Database initialized!"


if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

