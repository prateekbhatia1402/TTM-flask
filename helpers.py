import os
import urllib.parse

from flask import redirect, render_template, request, session, flash
from functools import wraps
import mysql.connector
from mysql.connector import errorcode
import sys

class SQL:
    
    def __init__(self, host, user, password, database):
        self.host = host
        self.user = user
        self.password = password
        self.database = database
        self.db = None
        self.UNKNOWN_DATABASE_ERROR_MESSAGE = "unknown database {}".format(database)


    def start_transaction(self):
        '''
        STARTS A NEW TRANSACTION, RETURNS FALSE IF ALREADY IN ONE
        '''
        if self.db != None:
            if not self.db.is_connected:
                self.db.connect()
            elif self.db.in_transaction:
                print('already in transaction')
                return False
        else:
            self.db = mysql.connector.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                database=self.database)
        self.db.start_transaction()
        return True


    def execute_trans(self, query, params):
        '''Execute a query in a transaction'''
        if self.db == None or not self.db.in_transaction:
            return None
        mycursor = self.db.cursor()
        rows = self.__execute_command(mycursor, query, params)
        mycursor.close()
        if rows == None:
            raise Exception('error in query execution')
        return rows

    def execute_many_trans(self, query, values):
        if self.db == None or not self.db.in_transaction:
            return None
        mycursor = self.db.cursor()
        rows = self.__execute_command_many(mycursor, query, values)
        mycursor.close()
        if rows == None:
            raise Exception('error in query execution')
        return rows

    def commit(self):
        if self.db == None or not self.db.in_transaction:
            return None
        self.db.commit()
        return True

    def close(self):
        if self.db == None or not self.db.in_transaction:
            return None
        self.db.close()
        self.db = None

    def rollback(self):
        if self.db == None or not self.db.in_transaction:
            return None
        self.db.rollback()
        return True


    def __execute_command(self, cursor, query, params = None):
        try:
            print('inside execute_command function....')
            print('query:', query)
            print('params:', params)
            if params == None:
                cursor.execute(query)
            else:
                cursor.execute(query, params)
            if cursor.with_rows:
                rows = cursor.fetchall()
            else:
                rows = cursor.rowcount
            #print('rows:', rows, type(rows))
            return rows
        except:
            print('in execute_command',sys.exc_info())
            return None
            
    def __execute_command_many(self, mycursor, query, values):
        try:
            print('inside execute_command_many function....')
            print('query:', query)
            print('params:', values)
            mycursor.executemany(query, values)
            if mycursor.with_rows:
                rows = mycursor.fetchall()
            else:
                rows = mycursor.rowcount
            #print('rows:', rows, type(rows))
            return rows
        except:
            print('in execute_command_many',sys.exc_info())
            return None
        

    def execute(self, query, params = None):
        with mysql.connector.connect(
        host=self.host,
        user=self.user,
        password=self.password,
        database=self.database,
        autocommit=True) as db:
            try:
                mycursor = db.cursor()
                rows = self.__execute_command(mycursor, query, params)
                mycursor.close()
                if rows == None:
                    raise Exception('error in query execution')
                return rows
            except:
                db.rollback()


    def execute_many(self, query, params = None):
        with mysql.connector.connect(
        host=self.host,
        user=self.user,
        password=self.password,
        database=self.database,
        autocommit=True) as db:
            try:
                mycursor = db.cursor()
                rows = self.__execute_command_many(mycursor, query, params)
                mycursor.close()
                if rows == None:
                    raise Exception('error in query execution')
                return rows
            except:
                db.rollback()

    def execute_batch(self, batch):
        results = []
        with mysql.connector.connect(
        host=self.host,
        user=self.user,
        password=self.password,
        database=self.database,
        autocommit=False) as db:
            try:
                mycursor = db.cursor()
                for query, params in batch:
                    rows = self.__execute_command(mycursor, query, params)
                    if rows == None:
                        raise Exception('error while executing query')
                    results.append(rows)
                db.commit()
            except:
                db.rollback()
            finally:
                mycursor.close()
        return results
            


class Schedule:

    def __init__(self, sid, dayId, timeslotId, classId,
    subjectId,facultyId, roomId, wef, till = None):
        self.sid = sid
        self.wef = wef
        self.dayId = dayId
        self.timeslotId = timeslotId
        self.classId = classId
        self.subjectId = subjectId
        self.facultyId = facultyId
        self.roomId = roomId


class TimeSlot():
    def __init__(self, id, tfrom, tto):
        self.tid = id
        self.tfrom = tfrom
        self.tto = tto

    def toString(self):
        return self.tfrom[0:2]+":"+self.tfrom[2:4]+" - "+self.tto[0:2]+":"+self.tto[2:4]
    
    def toSimpleString(self):
        hour = int(self.tfrom[0:2])
        if hour > 11:
            aOrP = " PM"
        else:
            aOrP = " AM"

        if hour > 12:
            hour -= 12
        startFrom = str(hour)+":"+self.tfrom[2:4]+ aOrP
        hour = int(self.tto[0:2])
        if hour > 11:
            aOrP = " PM"
        else:
            aOrP = " AM"
        if hour > 12:
            hour -= 12
        endAt = str(hour)+":"+self.tto[2:4] + aOrP
        return startFrom+" - "+endAt


def apology(message, code=400, redirect_to='/'):
    """Render message as an apology to user."""
    if 'user_id' not in session:
        redirect_to = '/login'
    def escape(s):
        """
        Escape special characters.

        https://github.com/jacebrowning/memegen#special-characters
        """
        for old, new in [("-", "--"), (" ", "-"), ("_", "__"), ("?", "~q"),
                         ("%", "~p"), ("#", "~h"), ("/", "~s"), ("\"", "''")]:
            s = s.replace(old, new)
        return s
    flash(escape(message), 'danger')
    print(message, code, redirect_to)
    return redirect(redirect_to)


def login_required(f):
    """
    Decorate routes to require login.

    http://flask.pocoo.org/docs/1.0/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function

def admin_access_required(f):
    """
    Decorate routes to require admin access.

    http://flask.pocoo.org/docs/1.0/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            flash('Login Required','danger')
            return redirect("/login")
        elif session.get('role') != 'admin':
            flash('Permission Denied', 'danger')
            return redirect('/')
        return f(*args, **kwargs)
    return decorated_function

def getallperiods(sql):
    periods = []
    query = r"select * from `time slot`"
    rows = sql.execute(query)
    if rows == None:
        return
    for tid, tfrom, tto in rows:
        periods.append(TimeSlot(tid, tfrom, tto))
    return periods
    

def getalldays(sql):
    days = []
    query = r"select * from `day` order by `day number`"    
    rows = sql.execute(query)
    if rows == None:
        return
    for dayid, dayname, daynum in rows:
        days.append({'id': dayid, 'name': dayname, 'num': daynum})
    return days


def getSubjectDetails(id, sql):
    query = r"select * from subject where `subject id`=%(subjectId)s"
    rows = sql.execute(query, {'subjectId': id})
    if rows == None or len(rows) != 1:
        return None
    return {'id': rows[0], 'name': rows[1], 'lectures': rows[2]}
    
def getCurrentTimeTable(id, sql):
    from datetime import date
    schedule = []
    today = date.today()
    periods = getallperiods(sql)
    days = getalldays(sql)
    query = """select concat(`class id`, '_000') as `ttid`,`WEF` as `from`,NULL as `till`
            from schedule where `wef` <= curdate()
            and `class id`=%(id)s UNION 
            select `time table id`,`from`, `to` 
            from schedule_records where `from` <= curdate()
                and `to` >= curdate() and `class id`=%(id)s"""
    rows = sql.execute(query, {'id': id})
    if rows == None or len(rows) < 1:
        return list()
    tid = rows[0][0]
    if tid.endswith('_000'):
        tid = tid[0:6]
    return getParticularTimeTable(tid, sql)
    

def getLatestTimeTable(id, sql):
    from datetime import date
    schedule = []
    today = date.today()
    periods = getallperiods(sql)
    days = getalldays(sql)
    query = """select `SCHEDULE ID`,`DAY ID`,`TIMESLOT ID`,
sc.`CLASS ID`, c.`NAME` , sc.`SUBJECT ID`, su.`SUBJECT NAME`, f.`FACULTY ID`,
f.`name` , sc.`ROOM ID` ,`WEF` 
from schedule sc, class c, faculty f, subject su 
where sc.`faculty id` = f.`faculty id` and sc.`class id` = c.`id` 
and sc.`subject id` = su.`subject id`  and (sc.`faculty id`=%(id)s or 
sc.`class id`=%(id)s or sc.`room id`=%(id)s)"""
    rows = sql.execute(query, {'id': id})
    if not rows or len(rows) == 0:
        return list()
    for row in rows:
        sid = row[0]
        dayId = row[1]
        timeslotId = row[2]
        classId = row[3]
        className = row[4]
        subjectId = row[5]
        subjectName = row[6]
        facultyId = row[7]
        facultyName = row[8]
        roomId = row[9]
        wef = row[10]
        sced = {
                "id": sid,
                "dayId": dayId,
                "timeslotId": timeslotId,
                "classId": classId,
                "className": className,
                "subjectId": subjectId,
                "subjectName": subjectName,
                "facultyId": facultyId,
                "facultyName": facultyName,
                "roomId":roomId,
                "wef": wef,
                "latest": True
            }   
        schedule.append(sced)
    return schedule
    

def getTimeTable(id, sql):
    periods = getallperiods(sql)
    days = getalldays(sql)
    if id.lower().startswith('c'):
        schedule = getCurrentTimeTable(id, sql)
        if len(schedule) < 1:
            schedule = getLatestTimeTable(id, sql)
    else:
        schedule = getLatestTimeTable(id, sql)
    if len(schedule) < 1:
        return list()
    return parseTT(schedule, periods, days, id)


def parseTT(schedule, periods, days, id ):
    timetable = []
    timetable.append(['DAY\PERIOD'] + [period.toSimpleString() for period in periods])
    for day in days:
        v = ["" for _ in periods]
        v.insert(0, day['name'])
        timetable.append(v)
    for record in schedule:
        dayId = record['dayId']
        periodId = record['timeslotId']
        periodIndex,dayIndex = -1, -1
        for i, period in enumerate(periods):
            if period.tid == periodId:
                periodIndex = i
                break
        for i, day in enumerate(days): 
            if day['id'] == dayId:
                dayIndex = i
                break
        if periodIndex < 0 or dayIndex < 0:
            continue
        subjectName = record['subjectName']
        if id[0] == "C":
            facultyName = record['facultyName']
            roomId = record['roomId']
            val = f"{subjectName} {facultyName} ({roomId})"
        elif id[0] == 'F':
            className = record['className']
            roomId = record['roomId']
            val = f"{subjectName} {className}({roomId})"
        else:
            className = record['className']
            facultyName = record['facultyName']
            val = f"{subjectName} {className}({facultyName})"
        timetable[dayIndex + 1][periodIndex + 1] = val
    return timetable

    
def getParticularTimeTable(tid, sql):
    if len(tid) < 10 or tid.endswith('000'):
        return getLatestTimeTable(tid, sql)
    schedule = []
    rows = sql.execute("""select `SCHEDULE ID`,`DAY ID`,`TIMESLOT ID`,
sc.`CLASS ID`, c.`NAME` , sc.`SUBJECT ID`, su.`SUBJECT NAME`, f.`FACULTY ID`
f.`name` , sc.`ROOM ID` , `FROM`, `TO` 
from schedule_records sc, class c, faculty f, subject su 
where sc.`faculty id` = f.`faculty id` and sc.`class id` = c.`id` 
and sc.`subject id` = su.`subject id`  and `time table id`=%(tid)s""", {'tid':tid})
    for row in rows:
        sid = row[0]
        dayId = row[1]
        timeslotId = row[2]
        classId = row[3]
        className = row[4]
        subjectId = row[5]
        subjectName = row[6]
        facultyId = row[7]
        facultyName = row[8]
        roomId = row[9]
        wef = row[10]
        till = row[11]
        sced = {
                "id": sid,
                "dayId": dayId,
                "timeslotId": timeslotId,
                "classId": classId,
                "className": className,
                "subjectId": subjectId,
                "subjectName": subjectName,
                "facultyId": facultyId,
                "facultyName": facultyName,
                "roomId":roomId,
                "wef": wef,
                "latest": False,
                "till": till
            } 
        schedule.append(sced)
    return schedule

def createTimeTable(schedule, sql):
    print('inside createTimeTable')
    from datetime import datetime
    now = datetime.now()
    try:
        insert_query = r"""insert into schedule(`day id`,`timeslot id`,
`class id`,`subject id`,`faculty id`,`room id`,`wef`, `last updated`) values 
(%(dayId)s,%(tslotId)s,%(classId)s,%(subjectId)s,%(facId)s,%(roomId)s,%(wef)s, %(upd)s)"""
        insert_values = []
        print('starting transaction')
        sql.start_transaction()
        print('getting cursor')
        classes = set()
        print('schedule has', len(schedule), 'items')
        for scheduleItem in schedule:
            classId = scheduleItem['classId']
            print(f'classid : {classId}')
            if classId not in classes:
                query = """select max(substr(`time table id`,8,3)) from schedule_records
 where `class id` = %(id)s"""
                ans = sql.execute(query, {'id': classId})
                print('ans:', ans, type(ans))
                if type(ans) != type(list()):
                    return None
                num = ans[0][0]
                print('num', num)
                if type(num) == type(1):
                    num += 1
                else:
                    num = 0
                print("trying to delete class "+classId)
                query = r"""INSERT INTO `schedule_records`(`time table id`,
        `day id`,`timeslot id`,
        `class id`,`subject id`,`faculty id`,`room id`,`from`,`to`)
         select %(tid)s,`day id`,`timeslot id`,
        `class id`,`subject id`,`faculty id`,`room id`,`wef`,sysdate()
         from schedule where `class id`=%(id)s"""
                # print(query)
                sql.execute_trans(query, {"tid":classId + '_{:03d}'.format(num), "id":classId})
                query = r"delete from schedule where `class id`=%(id)s"
                sql.execute_trans(query,{'id': classId})
                classes.add(classId)
            insert_values.append({
                "dayId":scheduleItem['dayId'],
                "tslotId":scheduleItem['timeslotId'],
                "classId":scheduleItem['classId'],
                "subjectId":scheduleItem['subjectId'],
                "facId":scheduleItem['facultyId'],
                "roomId":int(scheduleItem['roomId']),
                "wef":scheduleItem['wef'],
                "upd":now
            })
        sql.execute_many_trans(insert_query, insert_values)
        sql.commit()
        print("RECORDS ADDED SUCCESSFULLY")
        return True
    except:
        sql.rollback()
        print('in CreateTimeTable',sys.exc_info())
    finally:
        sql.close()
    

def getFacSubDetails(id, sql):
    query = """select f.`faculty id`,f.name,csf.`subject id`,
`subject name`,`LECTURES REQUIRED` from faculty f,class_subject_faculty csf,
subject sub where f.`faculty id`=csf.`faculty id` 
and csf.`subject id`=sub.`subject id` and csf.`class id`=%(classId)s"""
    rows = sql.execute(query, {"classId": id})
    if not rows:
        return
    facsubdetails = []
    for row in rows:
        facsubdetails.append(
            {
                "facId": row[0],
                "facName": row[1],
                "subId": row[2],
                "subName": row[3],
                "lectures": row[4]
            }
        )
    return facsubdetails
    

def getFacSubDetailsAsMap(id, sql):
    data = {}
    res = getFacSubDetails(id, sql)
    for row in res:
        row['allotted'] = 0
        data[row['subId']] = row
    return data
    
def getCreateTimeTable(id, sql):
    timetable = []
    periods = getallperiods(sql)
    days = getalldays(sql)
    dat = sql.execute("select `room id` from class where id=%(id)s",{"id":id})
    if not dat:
        return None
    if len(dat) != 1:
        defaultRoomId = -1
    else:
        defaultRoomId = dat[0][0]
    timetable.append(['DAY\PERIOD'] + [period.toSimpleString() for period in periods])
    for day in days:
        v = ["" for _ in periods]
        timetable.append([day['name'], v])
    query = """select f.`faculty id`,f.name,csf.`subject id`,
`subject name`,`LECTURES REQUIRED` from faculty f,class_subject_faculty csf,
subject sub where f.`faculty id`=csf.`faculty id` 
and csf.`subject id`=sub.`subject id` and csf.`class id`=%(classId)s"""
    rows = sql.execute(query, {"classId": id})
    facsubdetails = []
    for row in rows:
        facsubdetails.append(
            {
                "facId": row[0],
                "facName": row[1],
                "subId": row[2],
                "subName": row[3],
                "lectures": row[4]
            }
        )
    for i, day in enumerate(days):
        for j, period in enumerate(periods):
            possible_faculties = []
            possible_rooms = []
            query = r"""SELECT f.`faculty id`, f.name, csf.`subject id`, `subject name`,
EXISTS(SELECT s2.`subject id` FROM schedule s2 WHERE
s2.`timeslot id`=%(timeslotId)s AND s2.`day id`=%(dayId)s
AND s2.`class id`=%(classId)s AND s2.`subject id`=sub.`subject id`) as exi FROM faculty f,class_subject_faculty csf, 
subject sub WHERE f.`faculty id`=csf.`faculty id` 
AND csf.`subject id`=sub.`subject id` AND csf.`class id`=
%(classId)s AND f.`faculty id` NOT IN 
(SELECT s.`faculty id` FROM schedule s WHERE 
`timeslot id`=%(timeslotId)s AND `day id`=%(dayId)s
AND s.`class id`!=%(classId)s)"""
            rows = sql.execute(query, 
            {"classId": id, "timeslotId":period.tid,"dayId": day['id']})
            for row in rows:
                possible_faculties.append(
                    {
                    "fid": row[0],
                    "fname": row[1],
                    "sid": row[2],
                    "sname": row[3],
                    'selected': bool(row[4])
                    }
                )
            query = r"""SELECT `id`, `sitting capacity`, 
EXISTS(SELECT `room id` FROM schedule WHERE `room id` = `id` 
and`timeslot id`=%(timeslotId)s AND `day id`=%(dayId)s 
AND `class id`=%(classId)s) AS exi FROM room WHERE `id` NOT IN 
(SELECT `room id` FROM schedule WHERE
`timeslot id`=%(timeslotId)s and `day id`=%(dayId)s
AND `class id`!=%(classId)s)"""
            rows = sql.execute(query, 
            {"classId": id, "timeslotId":period.tid, "dayId": day['id']})
            for row in rows:
                if row[0] != defaultRoomId:
                    possible_rooms.append(
                    {
                    "id": row[0],
                    "capacity": row[1],
                    'selected': bool(row[2])
                    }
                )
                else:
                    possible_rooms.insert(0,
                    {
                    "id": row[0],
                    "capacity": row[1],
                    'selected': bool(row[2])
                    }
                    )
            timetable[i + 1][1][j] = {
                'facs': possible_faculties,
                'rooms':possible_rooms,
                'dayId':day['id'],
                'periodId':period.tid
            }
    return timetable


def getCreateTimeTable_suggest(id, sql):
    timetable = []
    periods = getallperiods(sql)
    days = getalldays(sql)
    periods_map = {}
    days_map = {}
    dat = sql.execute("select `room id` from class where id=%(id)s",{"id":id})
    if not dat:
        return None
    if len(dat) != 1:
        defaultRoomId = -1
    else:
        defaultRoomId = dat[0][0]
    timetable.append([period.tid for period in periods])
    for i, day in enumerate(days):
        v = ["" for _ in periods]
        timetable.append(v)
        days_map[day['id']] = i
    
    for i, period in enumerate(periods):
        periods_map[period.tid] = i
    
    for i, day in enumerate(days):
        for j, period in enumerate(periods):
            possible_faculties = []
            possible_rooms = []
            query = r"""SELECT f.`faculty id`, f.name, csf.`subject id`, `subject name`
 FROM faculty f,class_subject_faculty csf, 
subject sub WHERE f.`faculty id`=csf.`faculty id` 
AND csf.`subject id`=sub.`subject id` AND csf.`class id`=
%(classId)s AND f.`faculty id` NOT IN 
(SELECT s.`faculty id` FROM schedule s WHERE 
`timeslot id`=%(timeslotId)s AND `day id`=%(dayId)s
AND s.`class id`!=%(classId)s)"""
            rows = sql.execute(query, 
            {"classId": id, "timeslotId":period.tid,"dayId": day['id']})
            for row in rows:
                possible_faculties.append(
                    {
                    "fid": row[0],
                    "fname": row[1],
                    "sid": row[2],
                    "sname": row[3],
                    }
                )
            query = r"""SELECT `id`, `sitting capacity` FROM room WHERE `id` NOT IN 
(SELECT `room id` FROM schedule WHERE
`timeslot id`=%(timeslotId)s and `day id`=%(dayId)s
AND `class id`!=%(classId)s)"""
            rows = sql.execute(query, 
            {"classId": id, "timeslotId":period.tid, "dayId": day['id']})
            for row in rows:
                if row[0] != defaultRoomId:
                    possible_rooms.append(
                    {
                    "id": row[0],
                    "capacity": row[1]
                    }
                )
                else:
                    possible_rooms.insert(0,
                    {
                    "id": row[0],
                    "capacity": row[1]
                    }
                    )
            timetable[i][j] = {
                'facs': possible_faculties,
                'rooms':possible_rooms,
                'dayId':day['id'],
                'periodId':period.tid
            }
    return (timetable, days, periods)
