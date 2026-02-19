
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

    conn.commit()
    conn.close()


# def init_db():
#     conn = get_connection()
#     cursor = conn.cursor()

#     cursor.execute("""
#         CREATE TABLE IF NOT EXISTS wyniki (
#             id SERIAL PRIMARY KEY,
#             nick TEXT NOT NULL,
#             punkty INTEGER NOT NULL,
#             data TIMESTAMP NOT NULL
#         )
#     """)

#     conn.commit()
#     conn.close()



# ================= WCZYTANIE BAZY SŁÓW =================
with open("baza_synonimow.json", "r", encoding="utf-8") as f:
    synonimy = json.load(f)


# ================= ZAPIS WYNIKU =================
# def zapisz_wynik(nick, punkty):
#     conn = get_connection()
#     cursor = conn.cursor()

#     cursor.execute("""
#         INSERT INTO wyniki (nick, punkty, data)
#         VALUES (%s, %s, %s)
#     """, (nick, punkty, datetime.now()))

#     conn.commit()
#     conn.close()

def zapisz_wynik(user_id, punkty):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO wyniki (user_id, punkty, data)
        VALUES (%s, %s, %s)
    """, (user_id, punkty, datetime.now()))

    conn.commit()
    conn.close()



# ================= POBIERANIE RANKINGU =================
def pobierz_ranking():
    conn = get_connection()
    cursor = conn.cursor()

    # cursor.execute("""
    #     SELECT nick, punkty
    #     FROM wyniki
    #     WHERE data >= NOW() - INTERVAL '7 days'
    #     ORDER BY punkty DESC, data DESC
    #     LIMIT 5
    # """)
    cursor.execute("""
        SELECT users.nick, wyniki.punkty
        FROM wyniki
        JOIN users ON wyniki.user_id = users.id
        WHERE wyniki.data >= NOW() - INTERVAL '7 days'
        ORDER BY wyniki.punkty DESC, wyniki.data DESC
        LIMIT 5
    """)


    dane = cursor.fetchall()
    conn.close()

    return dane


# ================= STRONA STARTOWA =================
@app.route("/")
def index():
    return render_template("index.html")


# ================= ROZPOCZĘCIE GRY =================
# @app.route("/start", methods=["POST"])
# def start_post():
#     nick = request.form.get("nick")

#     session.clear()
#     session["nick"] = nick
#     session["punkty"] = 0
#     session["runda"] = 1
#     session["zapisano"] = False

#     session["wylosowane"] = random.sample(list(synonimy.keys()), 5)

#     return redirect("/gra")

@app.route("/start", methods=["POST"])
def start_post():
    nick = request.form.get("nick")
    remember = request.form.get("remember")

    session.clear()

    # jeśli user ma cookie
    user_id = request.cookies.get("user_id")

    if user_id:
        user = get_user_by_id(user_id)
        if user:
            session["user_id"] = user[0]
            session["nick"] = user[1]
        else:
            user_id = create_user(nick)
            session["user_id"] = user_id
            session["nick"] = nick
    else:
        user_id = create_user(nick)
        session["user_id"] = user_id
        session["nick"] = nick

    session["punkty"] = 0
    session["runda"] = 1
    session["zapisano"] = False
    session["wylosowane"] = random.sample(list(synonimy.keys()), 5)

    response = make_response(redirect("/gra"))

    if remember:
        response.set_cookie("user_id", str(session["user_id"]), max_age=60*60*24*365)

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
# @app.route("/ranking")
# def ranking():

#     if "punkty" in session and not session.get("zapisano", False):
#         zapisz_wynik(session.get("nick", "Gracz"), session["punkty"])
#         session["zapisano"] = True

#     ranking = pobierz_ranking()
#     return render_template("ranking.html", ranking=ranking)
# @app.route("/ranking")
# def ranking():

#     if "punkty" in session and not session.get("zapisano", False):
#         zapisz_wynik(session["user_id"], session["punkty"])
#         add_points(session["user_id"], session["punkty"])
#         session["zapisano"] = True

#     ranking = pobierz_ranking()
#     return render_template("ranking.html", ranking=ranking)

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

@app.route("/init-db")
def init_database():
    init_db()
    return "Database initialized!"

# @app.route("/debug-users")
# def debug_users():
#     conn = get_connection()
#     cursor = conn.cursor()
#     cursor.execute("SELECT id, nick, total_points FROM users")
#     users = cursor.fetchall()
#     conn.close()
#     return str(users)

# @app.route("/reset-db")
# def reset_db():
#     conn = get_connection()
#     cursor = conn.cursor()

#     cursor.execute("DROP TABLE IF EXISTS wyniki")
#     cursor.execute("DROP TABLE IF EXISTS users")

#     conn.commit()
#     conn.close()

#     return "Tables dropped!"





if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

