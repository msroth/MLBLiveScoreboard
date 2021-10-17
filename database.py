import sqlite3


class Database:
    db_file = None
    db_conn = None

    def __init__(self, db_file):
        self.db_file = db_file
        self.db_conn = self.get_connection()

    def get_connection(self):
        if self.db_conn is None:
            self.db_conn = sqlite3.connect(self.db_file)
        return self.db_conn

    def db_query(self, sql):
        results = None
        conn = None

        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(sql)
            results = cursor.fetchall()
        except sqlite3.Error as err:
            print('Query error: {}'.format(err))
        finally:
            if results is None or len(results) == 0:
                return None
            else:
                return results

    def db_count(self, table, column='*', cond=''):
        sql = 'SELECT COUNT({}) FROM {}'.format(column, table)
        if len(cond) > 0:
            sql += ' WHERE {}'.format(cond)
        results = self.db_query(sql)
        if results is None or len(results) == 0:
            return 0
        else:
            return results[0][0]

    def db_insert(self, table, items: dict):
        conn = None
        rows = 0

        columns = ','.join(items.keys())            # string of column names
        placeholders = ','.join(['?'] * len(items))   # string of '?,?,?' etc.
        values = list(items.values())

        sql = 'INSERT INTO {} ({}) VALUES ({})'.format(table, columns, placeholders)

        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            rows = cursor.execute(sql, values)
            conn.commit()
        except sqlite3.Error as err:
            print('Insert error: {}'.format(err))

        return rows

    def db_delete(self, table, cond=''):
        sql = 'DELETE from {}'.format(table)
        if len(cond) > 0:
            sql += ' WHERE {}'.format(cond)
        results = self.db_query(sql)
        if results is None or len(results) == 0:
            return 0
        else:
            return results[0][0]

    def db_update(self, table, update_str, cond=''):
        sql = 'UPDATE {} SET {}'.format(table, update_str)
        if len(cond) > 0:
            sql += ' WHERE {}'.format(cond)
        results = self.db_query(sql)
        conn = self.db_conn.commit()
        if results is None or len(results) == 0:
            return 0
        else:
            return results[0][0]

#<SDG><