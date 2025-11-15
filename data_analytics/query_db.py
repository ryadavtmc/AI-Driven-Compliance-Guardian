

# DB_PATH = "compliance_guardian.db"  # or your path if different

import os
import sqlite3

DB_PATH = os.getenv("GUARDIAN_DB_PATH", os.path.abspath("./compliance_guardian_v2.db"))

def promote_user_to_admin(user_id: int):
    """Promote a user to admin role based on user_id."""
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        sql = "UPDATE users SET role = 'admin' WHERE id = ?;"
        cur.execute(sql, (user_id,))
        conn.commit()
        print(f"✅ User with ID {user_id} promoted to admin.")
    # No need to call conn.close() — context manager handles it
# cur.execute("UPDATE users SET role = 'admin' WHERE id = ?;", (user_id,))
# conn.commit()

# # Verify the change
# cur.execute("SELECT id, email, name, role FROM users WHERE id = ?;", (user_id,))
# user = cur.fetchone()
# print(user)

# # Close the connection
# cur.close()
# conn.close()

def query_table(table_name: str):
    """Fetch all records from a specified table."""
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        sql = f"SELECT * FROM {table_name};"
        cur.execute(sql)
        rows = cur.fetchall()
        return rows


def delete_table(table_name: str):
    """Delete a table from the database (use with caution!)."""
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        sql = f"DROP TABLE IF EXISTS {table_name};"
        cur.execute(sql)
        conn.commit()
        print(f"✅ Table '{table_name}' deleted successfully.")


if __name__ == "__main__":
    # print(query_table("policy_events"))
    # delete_table("policy_events")
    promote_user_to_admin(1)