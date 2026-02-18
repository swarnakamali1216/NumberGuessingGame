import psycopg2
try:
    conn = psycopg2.connect(
        dbname="number_guessing_db",
        user="gameuser",
        password="swarna",
        host="localhost",
        port="5432"
    )
    print("Success!")
    conn.close()
except Exception as e:
    print(f"Error: {e}")
