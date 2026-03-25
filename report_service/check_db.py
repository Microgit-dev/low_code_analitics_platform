import psycopg

conn = psycopg.connect(
    "host=host.docker.internal port=5432 dbname=low_code user=postgres password=postgres"
)
cur = conn.cursor()

cur.execute("show server_encoding")
print("server_encoding =", cur.fetchone())

cur.execute("show client_encoding")
print("client_encoding =", cur.fetchone())

cur.execute("select id, road_name, region from roads order by id limit 10")
print("roads =", cur.fetchall())
