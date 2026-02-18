import psycopg2

def try_connect(user, password, dbname="postgres"):
    try:
        conn = psycopg2.connect(
            dbname=dbname,
            user=user,
            password=password,
            host="localhost"
        )
        msg = f"SUCCESS: {user} / {password} - Databases: "
        cur = conn.cursor()
        cur.execute("SELECT datname FROM pg_database;")
        dbs = cur.fetchall()
        msg += str([db[0] for db in dbs])
        cur.close()
        conn.close()
        return msg + "\n"
    except Exception as e:
        return f"FAILED: {user} / {password} -> {str(e)}\n"

results = []
results.append(try_connect("gameuser", "swarna"))
results.append(try_connect("gameuser", "swarna_00_"))
results.append(try_connect("postgres", "swarna"))
results.append(try_connect("postgres", "swarna_00_"))

with open("db_results.txt", "w", encoding="utf-8") as f:
    f.writelines(results)
