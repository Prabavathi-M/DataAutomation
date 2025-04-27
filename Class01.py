import sqlite3
import os

print("Running from folder:",os.getcwd())
#connect to database

conn=sqlite3.connect(r"D:\Praba\Automation\Data\mydatabase.db")
cursor=conn.cursor()

def
cursor.execute('select id,name,age from Student')
rows=cursor.fetchall()

def check_age_limit(rows):
for row in rows:
    id,name,age=row
    if age>5:
        print('Name:',name,'Age',age)
    else:
        print('No data for age below 5')

conn.close()