#!/usr/bin/env python3
"""
Test direct database access inside container
"""
import sqlite3
import os

db_path = "/app/data/app.db"

if not os.path.exists(db_path):
    print(f"❌ Database not found at {db_path}")
    exit(1)

print(f"✅ Database found at {db_path}")
print(f"📊 File size: {os.path.getsize(db_path) / (1024*1024):.2f} MB")
print()

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# List all tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
tables = cursor.fetchall()
print(f"📋 Tables in database ({len(tables)}):")
for table in tables:
    print(f"   - {table[0]}")
print()

# Check exercicio_orcamentario
if any(t[0] == 'exercicio_orcamentario' for t in tables):
    cursor.execute("SELECT COUNT(*) FROM exercicio_orcamentario")
    count = cursor.fetchone()[0]
    print(f"✅ exercicio_orcamentario: {count} records")
    
    if count > 0:
        cursor.execute("""
            SELECT ano, municipio, tipo_documento, orcamento_total, status, id 
            FROM exercicio_orcamentario 
            WHERE ano >= 2025
            ORDER BY ano DESC, tipo_documento
        """)
        rows = cursor.fetchall()
        print()
        for row in rows:
            print(f"   Exercício {row[0]} - {row[1]} - {row[2]}")
            print(f"      Status: {row[4]}")
            print(f"      Orçamento: R$ {row[3]:,.2f}")
            print(f"      ID: {row[5]}")
            
            # Count regionais
            cursor.execute("SELECT COUNT(*) FROM investimento_regional WHERE exercicio_id = ?", (row[5],))
            reg_count = cursor.fetchone()[0]
            print(f"      Regionais: {reg_count}")
            print()
else:
    print("❌ Table 'exercicio_orcamentario' NOT FOUND!")

conn.close()

