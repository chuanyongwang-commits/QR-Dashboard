import mysql.connector

def update_db():
    try:
        conn = mysql.connector.connect(
            host="10.246.97.159",
            user="root",
            password="root",
            database="QREP"
        )
        cursor = conn.cursor()
        
        table_hist = """
        CREATE TABLE IF NOT EXISTS qr_history (
            id INT AUTO_INCREMENT PRIMARY KEY,
            qr_number VARCHAR(50),
            field_name VARCHAR(100),
            old_value TEXT,
            new_value TEXT,
            changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
        cursor.execute(table_hist)
        print("History table created or already exists.")
        conn.commit()
    except Exception as e:
        print("Error creating table:", e)
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()

if __name__ == "__main__":
    update_db()
