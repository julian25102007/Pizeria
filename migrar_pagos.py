"""Aplica sql/migracion_pagos.sql en tu MySQL de Aiven (UNA sola vez). No guarda contraseñas."""
import getpass
from pathlib import Path

import pymysql

host = input("Host [pizzeria-pizeria.f.aivencloud.com]: ") or "pizzeria-pizeria.f.aivencloud.com"
puerto = int(input("Puerto [24373]: ") or 24373)
usuario = input("Usuario [avnadmin]: ") or "avnadmin"
base = input("Base de datos [defaultdb]: ") or "defaultdb"
clave = getpass.getpass("Contraseña de Aiven: ")

con = pymysql.connect(host=host, port=puerto, user=usuario, password=clave, database=base,
                      ssl={"fake_flag_to_enable_tls": True})
sql = Path(__file__).parent.joinpath("sql", "migracion_pagos.sql").read_text(encoding="utf-8")
sql = "\n".join(l for l in sql.splitlines() if not l.strip().startswith("--"))
with con.cursor() as cur:
    for sentencia in sql.split(";"):
        if sentencia.strip():
            cur.execute(sentencia)
    cur.execute("SHOW COLUMNS FROM pedidos")
    print([c[0] for c in cur.fetchall()])
con.commit()
print("listo")
