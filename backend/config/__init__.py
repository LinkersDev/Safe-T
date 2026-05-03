"""
Install PyMySQL as a drop-in MySQLdb replacement.

Spoofs the version to satisfy Django 6's mysqlclient >= 2.2.1 check.
This must run before Django initialises any database connections.
"""
import pymysql

pymysql.version_info = (2, 2, 8, "final", 0)
pymysql.__version__ = "2.2.8"
pymysql.install_as_MySQLdb()
