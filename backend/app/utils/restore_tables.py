"""
@File       : restore_tables.py
@Author     : ChiLei Tai JOU
@Date       : 2025-03-01
@Description: 在不连接数据库的情况下，从 SQLAlchemy 模型导出 SQL建表语句
@Version    : 1.1.1
"""

from sqlalchemy.dialects.mysql import dialect as mysql_dialect
from sqlalchemy.schema import CreateTable

from app import create_app
from app.utils.db import db

# 创建 Flask 应用（不连接数据库）
app = create_app()


# 只用 metadata，不需要实际连接 MySQL
def export_sql(filename='../../data/init_tables.sql'):
    """Export SQL create table statements to a .sql file without connecting DB."""
    with app.app_context():
        with open(filename, 'w', encoding='utf-8') as f:
            for table in db.metadata.sorted_tables:
                create_stmt = str(CreateTable(table).compile(dialect=mysql_dialect(),
                                                             compile_kwargs={
                                                                 "literal_binds": True}))
                f.write(f"{create_stmt};\n\n")

    print(f"✅ SQL建表语句已导出到: {filename}")


if __name__ == "__main__":
    export_sql()
