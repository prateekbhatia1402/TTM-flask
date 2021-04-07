import os, sys, hashlib, uuid, datetime, random
from flask import Flask, flash, jsonify, redirect, render_template, request, session, Markup
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
import mysql.connector
from mysql.connector import errorcode
from helpers import SQL
from helpers import apology, login_required, admin_access_required
from helpers import getTimeTable, getCreateTimeTable, getCreateTimeTable_suggest, getFacSubDetails, getFacSubDetailsAsMap
from helpers import createTimeTable, getalldays, getallperiods

# Configure application
app = Flask(__name__)

# Get Connection to database
sql = SQL('localhost', os.getenv('TTM_USER'), os.getenv('TTM_PASSWORD'), os.getenv('TTM_DATABASE'))

table_keys = {
    'student': 'sid',
    'faculty': 'fac_id',
    'parent details': 'parent id',
    'account': 'username',
    'qualification': 'fac_id',
    'subject': 'id'
}

fieldmap = {
    'student': {
        'order': 1,
        'other_table_fields':
        {
            'username': 'account',
            'parent id': 'parent details'
        },
        'cols': {
            'sid': ['Student Id', 'registration id'],
            'name': ['Full Name', 'student name'],
            'email': ['email', 'email'],
            'username': ['username', 'username'],
            'mobile': ['Mobile Number', 'mobile number'],
            'paddress': ['Permanent Address', 'permanent address'],
            'caddress': ['Correspondance Address', 'corr. address'],
            'dob': ['Date Of Birth', 'date of birth'],
            'bgrp': ['Blood Group', 'blood group'],
            'gender': ['gender', 'gender'],
            'class': ['class', 'class'],
            'parent id': [None, 'parent id']
        },

    }
    ,
    'faculty':
    {
        'order': 1,
        'other_table_fields':
        {
            'username': 'account',
        },
        'cols': 
        {
            'fac_id': ['Faculty Id', 'faculty id'],
            'name': ['Full Name', 'name'],
            'username': ['username', 'username'],
            'email': ['email', 'email'],
            'mobile': ['Mobile Number', 'mobile number'],
            'paddress': ['Permanent Address', 'permanent address'],
            'caddress': ['Correspondance Address', 'corr. address'],
            'dob': ['Date Of Birth', 'date of birth'],
            'bgrp': ['Blood Group', 'blood group'],
            'gender': ['gender', 'gender'],
            'speciality': ['speciality', 'subject speciality'],
            'experience': ['experience', 'experience']
        }
    },
    'parent details':
    {
        'order': 0,
        'cols':
        {
            'parent id': [None, 'parent id'],
            'fname': ["Father's Name", 'father name'],
            'fdob': ["Father's Date Of Birth", 'father dob'],
            'mname': ["Mother's Name", 'father name'],
            'mdob': ["Mother's Date Of Birth", 'mother dob'],
            'femail': ["Father's Email", 'father email id'],
            'memail': ["Mother's Email", 'mother email'],
            'fmobile': ["Father's Mobile Number", 'father mobile number'],
            'mmobile': ["Mother's Mobile Number", 'mother mobile number'],   
        }
    },
    'account':
    {
        'order': 0,
        'cols':
        {
            'username': ['username', 'username'],
            'password': ['password', 'password'],
            'role': ['role', 'role']
        }
    },
    'qualification':
    {
        'order': 2,
        'cols':
        {
            'fac_id': [None, 'faculty id'],
            'degree': ['degree', 'degree'],
            'institute': ['institute', 'institute'],
            'year': ['year', 'year'],
            'percentage': ['percentage', 'percentage'],
        }

    },
    'subject':
    {
        'order': 0,
        'cols':
        {
            'id': ['Subject Id', 'subject id'],
            'name': ['Subject Name', 'subject name'],
            'nlects': ['Lectures Required', 'lectures required'],
            'tlects': ['Total Lectures Required', 'total lectures required'],
            'credits': ['Credits', 'credits'],
            'syll': ['Syllabus', 'syllabus'],
            'eval_cret': ['Evaluation Creteria', 'evaluation creteria']
        }
    }
}

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# database_requests is a dictionary which maps users requests 
# request :
# format[req_id, userid, type, on (faculty, student,..), row_id (faculty id, ..), current time]

database_requests = {}

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)


@app.route("/")
@login_required
def index():
    return render_template("index.html")

@app.route("/change_password", methods=['GET'])
@login_required
def changePassword():
    """Change Password"""
    if session['user_id'] not in database_requests:
        database_requests[session['user_id']] = {}     
    elif len(database_requests[session['user_id']]) > 0:
        for req in database_requests[session['user_id']].copy():
            del database_requests[session['user_id']][req]
    req_id = str(uuid.uuid4())
    req = [req_id, session['user_id'], 'update', 'account', session['username'], datetime.datetime.now()]
    database_requests[session['user_id']][req_id] = req         
    return render_template("changePassword.html", req_id=req_id)


@app.route("/create_class", methods=['GET', 'POST'])
@admin_access_required
def create_class():
    if request.method == 'GET':
        return render_template('/classDetails.html', mode='create', title='Class Creator')
    else:
        cname = request.form.get('name')
        if not cname:
            return apology('Display Name is a Must',redirect_to=get_referer())
        if not VALIDATION_STATUS[validate_classname(cname)]:
            return apology('Display Name Invalid', redirect_to=get_referer())
        res = sql.execute("select ifnull(max(substring(id, 2, 5)) + 1, 1) as id from class")
        if len(res) != 1:
            flash('Something went wrong', 'danger')
            return redirect(get_referer())
        cid = f'C{res[0][0]:05.0f}'
        res = sql.execute('INSERT INTO class(`id`, `name`) VALUES (%(id)s, %(name)s)',{'id': cid, 'name': cname})
        if res > 0:
            flash(f'Class Created Successfully with ID: {cid}', 'success')
            flash('Now Assign Room, Subjects and Faculties to it', 'info')
            return redirect(f'/class_assignments?class={cid}&mode=update')
        else:
            flash('something went wrong', 'danger')
            return redirect(get_referer())


@app.route("/create_tt", methods = ['GET', 'POST'])
@login_required
def create_tt():
    if session['role'] != 'admin':
        flash('Permission Denied', 'danger')
        return redirect(get_referer())
    if request.method == "POST":
        days = getalldays(sql)
        periods = getallperiods(sql)
        count = 0
        classId = request.form.get('classId')
        schedule = []
        facSubDetails = getFacSubDetails(classId, sql)
        periodAllotedCount = dict()
        for day in days:
            for period in periods:
                timeslotId = period.tid
                dayId = day['id']
                val = request.form.get('fac_'+dayId+"_"+timeslotId)
                if val == None or val == '' or val == 'free':
                   continue
                count += 1
                facultyId = val[0 : val.find("_")]
                subjectId = val[val.find("_") + 1:]
                roomId = request.form.get('room_'+dayId+"_"+timeslotId)
                if subjectId in periodAllotedCount:
                    periodAllotedCount[subjectId] += 1
                else:
                    periodAllotedCount[subjectId] = 1
                schedule.append(
                    {'dayId':dayId,
                    "timeslotId":timeslotId,
                    'classId':classId,
                    'subjectId':subjectId,
                    'facultyId':facultyId,
                    'roomId':roomId,
                    'wef':request.form.get('wef')
                    })
        for facsub in facSubDetails:
            assigned = periodAllotedCount[facsub['subId']]
            if type(assigned) != type(4) or assigned < facsub['lectures']:
                flash('Subject Requirements not met', 'danger')
                return redirect(get_referer())
        createTimeTable(schedule, sql)
        flash('schedule created / updated successfully', 'success')
        return redirect('/search_tt')
    else:
        currentId = request.args.get("value_selector")
        if not currentId:
            return redirect('/search_tt?mode=create')
        timetable = getCreateTimeTable(currentId, sql)
        facSubDetails = getFacSubDetails(currentId, sql)
        theaders = timetable[0].copy()
        timetable = timetable[1:]
        try:
            # Query database for username
            cls_rows  = sql.execute(r"""select id,name,case when 
id in (select distinct `class id` from schedule) then '1'
else '0' end, case when id in 
(select distinct `class id` from class_subject_faculty) then '1'
else '0' end from class""")
            
        except mysql.connector.Error as err:
            if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
                print("Something is wrong with your user name or password")
            elif err.errno == errorcode.ER_BAD_DB_ERROR:
                print("Database does not exist")
            else:
                print(err)
            return
        cls_data = []
        for clsid, clsname, ca, cbe in cls_rows:
            if ca == '1':
                is_assigned = True
            else:
                is_assigned = False
            if cbe == '1':
                can_be_assigned = True
            else:
                can_be_assigned = False
            cls_data.append({'id' :clsid, 'name': clsname, 'assigned': is_assigned,
        'assignable': can_be_assigned})
        return render_template("create_tt2.html", gclasses=cls_data,
        currentId = currentId,theaders=theaders, timetable=timetable)
    

@app.route('/class_assignments', methods=['GET', 'POST'])
@login_required
def class_assignments():
    if request.method == 'GET':
        classId = request.args.get('class', '')
        mode = request.args.get('mode', 'view')
        if mode == 'view':
            data = getAssignmentDetailsWithNames(classId)
        else:
            data = getAssignmentDetails(classId)

        return render_template('ClassAssignments.html', classId=classId, 
            predata=data, mode=mode)
    else:
        if session['role'] != 'admin':
            flash('access denied', 'danger')
            return redirect(get_referer())
        tt_archived = False
        try:
            rid = request.form.get('room_id')
            cid = request.form.get('class_id')
            values = []
            sql.start_transaction()
            res = sql.execute_trans("""select exists(select * from class where `id`=%(cid)s), exists(select * from room where
                        `id`=%(rid)s)""", {'cid': cid, 'rid': rid})
            for c,r in res:
                c, r = bool(c), bool(r)
                if not c or not r:
                    flash('Invalid Entries', 'danger')
                    return redirect('/class_assignments?class='+cid)
            for i in range(8):
                sub, fac = request.form.get('subject_'+str(i)),request.form.get('faculty_'+str(i))
                if sub and fac:
                    validate_q = """select exists(select * from faculty where `faculty id`=%(fid)s), exists(select * from subject where
                        `subject id`=%(sid)s)"""
                    res = sql.execute_trans(validate_q, {'fid': fac, 'sid': sub})
                    for f,s in res:
                        f, s = bool(f), bool(s)
                        if not f or not s:
                            flash('Invalid Entries', 'danger')
                            return redirect('/class_assignments?class='+cid)
                    values.append({'sid': sub, 'fid': fac, 'rid': rid, 'cid': cid})
            
            sql.execute_trans('UPDATE class set `room id` = %(rid)s WHERE id=%(cid)s', {'cid': cid, 'rid': rid})
            ans = sql.execute_trans('delete from class_subject_faculty where `class id`=%(cid)s',{'cid':cid})
            if ans and ans > 0:
                tt_archived = True
            query = """select max(substr(`time table id`,8,3)) from schedule_records
                where `class id` = %(id)s"""
            ans = sql.execute(query, {'id': cid})
            if type(ans) != type(list()):
                return None
            num = ans[0][0]
            if type(num) == type(1):
                num += 1
            else:
                num = 0
                
            query = r"""INSERT INTO `schedule_records`(`time table id`,
        `day id`,`timeslot id`,
        `class id`,`subject id`,`faculty id`,`room id`,`from`,`to`)
         select %(tid)s,`day id`,`timeslot id`,
        `class id`,`subject id`,`faculty id`,`room id`,`wef`,sysdate()
         from schedule where `class id`=%(id)s"""

            sql.execute_trans(query, {"tid":cid + '_{:03d}'.format(num), "id":cid})
            sql.execute_many_trans('''insert into class_subject_faculty 
            (`class id`, `faculty id`, `subject id`,`room id`) values(%(cid)s, %(fid)s,%(sid)s, %(rid)s)''', values)
            query = r"delete from schedule where `class id`=%(id)s"
            sql.execute_trans(query,{'id': cid})
                
            sql.commit()
        except:
            sql.rollback()
            print('in ClassAssignments',sys.exc_info())
            flash('something went wrong','danger')
            return redirect('/class_assignments?class='+cid)    
        finally:
            sql.close()
        flash('Changes saved successfully', 'success')
        if tt_archived:
            flash(Markup(f'''Due to this update current time Table if any has been archived and new one must be created\n
            To do that now <a href="create_tt?value_selector={cid}">Click Me</a>'''), 'Info')
        return redirect('/classes_subjects')


@app.route('/classes_subjects')
@login_required
def classes_subject():
    return render_template('classesAndSubjects.html')


@app.route('/create_room', methods=['GET', 'POST'])
@admin_access_required
def create_room():
    if request.method == 'GET':
        return render_template('roomDetails.html', mode='create')
    else:
        rid = request.form.get('id')
        cap = request.form.get('cap') 
        if not rid.isdigit():
            flash('Invalid ID', 'danger')
            return redirect('/create_room')
        dat = sql.execute('select * from room where id=%(rid)s',{'rid': rid})
        if len(dat) > 0:
            flash('Duplicate ID', 'danger')
            return redirect('/create_room')
        res = sql.execute('insert into room values (%(rid)s, %(cap)s)', {'rid': rid, 'cap': cap})
        if res > 0:
            flash('room successfully created', 'success')    
        else:
            flash('something went wrong', 'danger')
        return redirect('/classes_subjects')


@app.route('/create_subject', methods=['GET', 'POST'])
@admin_access_required
def create_subject():
    if request.method == 'GET':
        return render_template('subjectDetails.html', mode='create')
    else:
        sid = request.form.get('id')
        sname = request.form.get('name') 
        dat = sql.execute('select `subject id` from subject where `subject id`=%(sid)s',{'sid': sid})
        if len(dat) > 0:
            flash('Duplicate ID', 'danger')
            return redirect('/create_subject')
        lects = request.form.get('nlect')
        tlects = request.form.get('tlect')
        cred = request.form.get('credits')
        syll = request.form.get('syllabus')
        eval_cret = request.form.get('eval_cret')
        query = 'insert into subject values (%(sid)s, %(sname)s, %(lw)s, %(tl)s, %(cred)s, %(syl)s, %(ev)s)'
        res = sql.execute(query, {'sid': sid, 'sname': sname, 'lw': lects, 'tl': tlects, 'cred': cred, 'syl': syll, 'ev': eval_cret})
        if res > 0:
            flash('subject successfully created', 'success')    
        else:
            flash('something went wrong', 'danger')
        return redirect('/classes_subjects')


@app.route('/getData')
@login_required
def get_data():
    typeOfSearch = request.args.get('type', None)
    if typeOfSearch == None:
        return None
    elif typeOfSearch == 'get_tt':
        vid = request.args.get('id', 'N')
        if vid[0].lower() == 'f':
            query = 'SELECT name from faculty where `faculty id`=%(id)s'
        elif vid[0].lower() == 'c':
            query = 'SELECT id from class where id=%(id)s'
        else:
            query = 'SELECT id from room where id=%(id)s'
        rows = sql.execute(query, {'id': vid})
        if rows == None:
            return jsonify({'error' : 'internal connection error'})
        if len(rows) < 1:
            return jsonify({'error' : 'invalid id'})
        timetable = getTimeTable(vid, sql)
        if len(timetable) < 1:
            return jsonify({"error":'NOT FOUND'})
        theaders = timetable[0].copy()
        timetable = timetable[1:]
        data = {'header': theaders, 'body': timetable, 'error': ''}
        return jsonify(data)
    
    elif typeOfSearch == 'classes':
        data = getClassValuesForSearchTT()
    elif typeOfSearch == 'faculty':
        data = getFacValuesForSearchTT()
    elif typeOfSearch == 'available_rooms':
        classId = request.args.get('class', None)
        data = getAvailableRooms(classId)
    elif typeOfSearch == 'subjects':
        data = getSubjects()
    elif typeOfSearch == 'facsub_tt':
        clas = request.args.get('class')
        if not clas:
            return None
        data =  getFacSubDetails(clas, sql)
    else:
        return None
    return jsonify(data)


@app.route('/get_schedule_suggestion', methods=['POST'])
@admin_access_required
def get_schedule_suggestion():
    currentId = request.form.get("classId")
    constraint_data, days, periods = getCreateTimeTable_suggest(currentId, sql)
    facSubDetailsMap = getFacSubDetailsAsMap(currentId, sql)
    # theaders = constraint_data[0].copy()
    # constraint_data = constraint_data[1:]
    count = 0
    classId = request.form.get('classId')
    schedule = []
    periodsToAssign = []
    for pi, period in enumerate(periods):
        dayIndices = []
        timeslotId = period.tid
        for di, day in enumerate(days):
            dayId = day['id']
            val = request.form.get('fac_'+dayId+"_"+timeslotId)
            if val == None or val == '' or val == 'free':
                if val != 'free':
                    dayIndices.append(di)
                continue
            count += 1
            facultyId = val[0 : val.find("_")]
            subjectId = val[val.find("_") + 1:]
            roomId = request.form.get('room_'+dayId+"_"+timeslotId)
            facSubDetailsMap[subjectId]['allotted'] += 1
            schedule.append(
                {'dayId':dayId,
                "timeslotId":timeslotId,
                'classId':classId,
                'subjectId':subjectId,
                'facultyId':facultyId,
                'roomId':roomId,
                'wef':request.form.get('wef')
                })
        if len(dayIndices) > 0:
            random.shuffle(dayIndices)
            periodsToAssign.extend([(d, pi) for d in dayIndices])
    
    required_assignments = get_requirement_diff(facSubDetailsMap)
    if required_assignments  < 1:
        return jsonify({'type': 'fail', 'data':'ALREADY DONE'})
    elif len(periodsToAssign) >= required_assignments:
        suggestion = backtrack_suggest({}, periodsToAssign, 0, constraint_data, facSubDetailsMap)
        if not suggestion:
            return jsonify({'type': 'fail', 'data':'Not Possible'})
        data = []
        for period in suggestion:
            data.append([period, suggestion[period][0], suggestion[period][1]])
        return jsonify({'type': 'success', 'data':suggestion})
    else:
        return jsonify({'type':'fail','data':'Assignment Not Possible'})
    

def requirements_met(allotment_data):
    '''
    allotment_data can be a single dict {id, allotted, lectures}
    or a dict of such dicts, eg {sub1: {id, allotted, lectures}}
    '''
    if 'allotted' in allotment_data:
        if allotment_data['allotted'] < allotment_data['lectures']:
            return False
        else:
            return True
    for val in allotment_data:
        if 'allotted' not in allotment_data[val]:
            return False
        if allotment_data[val]['allotted'] < allotment_data[val]['lectures']:
            return False
    return True

def get_requirement_diff(allotment_data):
    '''
        allotment_data can be a single dict {id, allotted, lectures}
        or a dict of such dicts, eg {sub1: {id, allotted, lectures}}
    '''
    if 'allotted' in allotment_data:
        diff = allotment_data['lectures'] - allotment_data['allotted']
        if diff < 0:
            diff = 0
        return diff
    final_diff = 0
    for val in allotment_data:
        if 'allotted' not in allotment_data[val]:
            continue
        diff = allotment_data[val]['lectures'] - allotment_data[val]['allotted']
        if diff > 0:
            final_diff += diff
    return final_diff


def get_unassigned_facs(allotment_data, fac_data):
    available_facs = fac_data
    res = []
    for v in available_facs:
        if not requirements_met(allotment_data[v['sid']]):
            res.append(v)
    return res

def backtrack_suggest(suggested_schedule, periods_to_allot, index, required_data, allocation_data):
    if requirements_met(allocation_data):
        return suggested_schedule
    if index >= len(periods_to_allot):
        return None 
    period_data = periods_to_allot[index]
    related_data = required_data[period_data[0]][period_data[1]]
    room = related_data['rooms'][0]['id']
    dayId, periodId = related_data['dayId'], related_data['periodId']
    if len(related_data['facs']) < 1:
        return backtrack_suggest(suggested_schedule, periods_to_allot, index + 1, required_data, allocation_data)
    available_facs = get_unassigned_facs(allocation_data, related_data['facs'])
    if len(available_facs) < 1:
        return None
    else:
        random.shuffle(available_facs)
    for option in available_facs:
        suggested_schedule[dayId+'_'+periodId] = [option['fid']+'_'+option['sid'], room]
        allocation_data[option['sid']]['allotted'] += 1
        if False: # placeholder for binary checks, currently there are none
            del suggested_schedule[dayId+'_'+periodId]
            allocation_data[option['sid']]['allotted'] -= 1
            continue
        nd = backtrack_suggest(suggested_schedule, periods_to_allot, index + 1, required_data, allocation_data)
        if not nd:
            del suggested_schedule[dayId+'_'+periodId]
            allocation_data[option['sid']]['allotted'] -= 1
            continue
        return nd
    return None

def getAvailableRooms(classId=None):
    rows = sql.execute(r"""select id, `sitting capacity`,
    if(id = (select `room id` from class where id = %(cid)s), true, false) as current_d from room 
     where id not in (select ifnull(`room id`, 0) from class where id != %(cid)s)""", {'cid': classId})
    if rows == None:
        return
    data = []
    for rid, cap, current in rows:
        data.append({'id' :rid, 'cap': cap, 'current': bool(current)})
    return data

def getAssignmentDetails(classId):
    rows = sql.execute(r"""select `subject id`, `faculty id` from 
     class_subject_faculty csf where `class id` = %(cid)s""", {'cid': classId})
    if rows == None:
        return
    data = []
    for sid, fid in rows:
        data.append({'sub' :f'{sid}', 'fac': f'{fid}'})
    return data

def getAssignmentDetailsWithNames(classId):
    rows = sql.execute(r"""select s.`subject id`,s.`subject name`, f.`faculty id`
    , f.`name` from class_subject_faculty csf, faculty f, subject s
      where `class id` = %(cid)s and csf.`subject id` = s.`subject id`
       and f.`faculty id` = csf.`faculty id`""", {'cid': classId})
    if rows == None:
        return
    data = []
    for sid, sname, fid, fname in rows:
        data.append({'sub' :f'{sname} ({sid})', 'fac': f'{fname} ({fid})'})
    return data


def getSubjects():
    rows = sql.execute(r"""select `subject id`, `subject name` from subject""")
    if rows == None:
        return
    data = []
    for sid, sname in rows:
        data.append({'id' :sid, 'name': sname})
    return data

@app.route('/list_faculties')
@login_required
def list_faculties():
    sid = request.args.get('sid')
    sp_view_access = ['admin']
    update_access = ['admin']
    if not sid:
        query = "SELECT `faculty id`,`name`,`email` from faculty"
        rows = sql.execute(query)
        faculties = []
        create_url = None
        if session['role'] == 'admin':
            create_url = '/register?type=faculty'
        for i, row in enumerate(rows):
            faculties.append({"id": row[0], "name": row[1], "email": row[2].lower(), "sno": i + 1})
        return render_template('list_data.html', data=faculties,title="List of Faculties",
          fields=[('sno', False), ('id', True), ('name', True), ('email', True)],
          access_group=sp_view_access, view_access=sp_view_access,
          update_access=update_access, view_url='/list_faculties',
          update_url='/list_faculties', create_url=create_url)

    else:
        if session['role'] not in sp_view_access and session['user_id'] != sid:
            flash('Access Denied', 'danger')
            return redirect(get_referer())
        query = "select * from faculty where `faculty id`=%(sid)s"
        data = sql.execute(query,{"sid":sid})
        if data == None:
            flash('SOMETHING WENT WRONG', 'danger')
            return redirect(get_referer())
        elif len(data) != 1:
            flash('INVALID FACULTY ID', 'danger')
            return redirect(get_referer())
        faculty = {}
        values = data[0]
        faculty['id'] = values[0]
        faculty['name'] = values[1]
        faculty['email'] = values[2]
        faculty['username'] = values[3]
        address = values[4].split("@")
        for _ in range(5 - len(address)):
            address.append('')
        faculty['paddress'] = {'address': address[0], 'city': address[1],
            'state': address[2], 'country': address[3], 'pin': address[4],
            'fulladdress': f"{address[0]}\n{address[1]}\n{address[2]}\n{address[3]}\n{address[4]}\n"}
        address = values[5].split("@")
        for _ in range(5 - len(address)):
            address.append('')
        faculty['caddress'] = {'address': address[0], 'city': address[1],
            'state': address[2], 'country': address[3], 'pin': address[4],
            'fulladdress': f"{address[0]}\n{address[1]}\n{address[2]}\n{address[3]}\n{address[4]}\n"}
        faculty['dob'] = values[6]
        faculty['dor'] = values[7]
        faculty['mobile'] = values[8]
        faculty['gender'] = values[9]
        faculty['bgrp'] = values[10]
        faculty['experience'] = values[11]
        faculty['speciality'] = values[12]
        qualifications = []
        query = "select degree,year,institute,percentage from `qualification` where `faculty id`=%(sid)s"
        data = sql.execute(query,{"sid":sid})
        if data == None:
            flash('something went wrong', 'danger')
            return redirect(get_referer())
        for i, r in enumerate(data):
            qualifications.append([i+1, r[0], r[1], r[2], r[3]])
        faculty['qualifications'] = qualifications
        mode = request.args.get('mode', 'view')
        if mode == 'update':
            if session['role'] not in update_access and session['user_id'] != sid:
                flash('Access Denied', 'danger')
                return redirect(get_referer())
            if session['user_id'] not in database_requests:
                database_requests[session['user_id']] = {}     
            elif len(database_requests[session['user_id']]) > 0:
                for req in database_requests[session['user_id']].copy():
                    del database_requests[session['user_id']][req]
            req_id = str(uuid.uuid4())
            req = [req_id, session['user_id'], 'update', 'faculty', faculty['id'], datetime.datetime.now()]
            database_requests[session['user_id']][req_id] = req
            return render_template("faculty_details.html",faculty=faculty, mode=mode, req_id=req_id)
        else:
            return render_template("faculty_details.html",faculty=faculty, mode=mode)    
    return apology('something went wrong',400)
    
@app.route('/list_students')
@login_required
def list_students():
    sid = request.args.get('sid')
    sp_view_access = ['faculty', 'admin']
    update_access = ['admin']
    if not sid:
        query = "SELECT `registration id`,`student name`,`name` from student s, class c where s.class = c.id"
        rows = sql.execute(query)
        if rows == None:
            return apology('SOMETHING WENT WRONG', 500, get_referer())
        students = []
        for i, row in enumerate(rows):
            students.append({"sno": i + 1, "id": row[0], "name": row[1], "class": row[2]})
        create_url = None
        if session['role'] == 'admin':
            create_url = '/register?type=student'
        return render_template('list_data.html', data=students,title="List of Students",
          fields=[('sno', False), ('id', True), ('name', True), ('class', True)],
          access_group=sp_view_access, view_access=sp_view_access,
          update_access=update_access, view_url='/list_students',
          update_url='/list_students', create_url=create_url)
    else:
        if session['role'] not in sp_view_access and session['user_id'] != sid:
            flash('Access Denied', 'danger')
            return redirect(get_referer())
        query = "select * from student where `registration id`=%(sid)s"
        data = sql.execute(query,{"sid":sid})
        if data == None:
            flash('SOMETHING WENT WRONG', 'danger')
            return redirect(get_referer())
        elif len(data) != 1:
            flash('INVALID STUDENT ID', 'danger')
            return redirect(get_referer())
        student = {}
        values = data[0]
        student['id'] = values[0]
        student['name'] = values[1]
        student['email'] = values[2]
        student['username'] = values[3]
        student['mobile'] = values[4]
        student['class'] = values[5]
        address = values[6].split("@")
        student['paddress'] = {'address': address[0], 'city': address[1],
            'state': address[2], 'country': address[3], 'pin': address[4],
            'fulladdress': f"{address[0]}\n{address[1]}\n{address[2]}\n{address[3]}\n{address[4]}\n"}
        address = values[7].split("@")
        student['caddress'] = {'address': address[0], 'city': address[1],
            'state': address[2], 'country': address[3], 'pin': address[4],
            'fulladdress': f"{address[0]}\n{address[1]}\n{address[2]}\n{address[3]}\n{address[4]}\n"}
        student['rollno'] = values[8]
        student['dob'] = values[9]
        student['dor'] = values[10]
        student['gender'] = values[11]
        student['bgrp'] = values[12]
        pid = values[13]
        query = "select * from `parent details` where `parent id`=%(pid)s"
        data = sql.execute(query,{"pid":pid})
        if data == None:
            flash('SOMETHING WENT WRONG','danger')
            return get_referer()
        elif len(data) != 1:
            student['pdetails'] = False
        else:
            values = data[0]
            student['pdetails'] = True
            student['fname'] = values[1]
            student['femail'] = values[2]
            student['fmobile'] = values[3]
            student['fdob'] = values[4]
            student['mname'] = values[5]
            student['memail'] = values[6]
            student['mmobile'] = values[7]
            student['mdob'] = values[8]

        mode = request.args.get('mode', 'view')
        if mode == 'update':
            if session['role'] not in update_access:
                flash('access denied', 'danger')
                return redirect(get_referer())
            if session['user_id'] not in database_requests:
                database_requests[session['user_id']] = {}     
            elif len(database_requests[session['user_id']]) > 0:
                for req in database_requests[session['user_id']].copy():
                    del database_requests[session['user_id']][req]
            req_id = str(uuid.uuid4())
            req = [req_id, session['user_id'], 'update', 'student', student['id'], datetime.datetime.now()]
            database_requests[session['user_id']][req_id] = req
            return render_template("studentDetails.html",student=student, mode='update', req_id=req_id)
        return render_template("studentDetails.html", student=student, mode="view")
    flash('something went wrong')
    return redirect(get_referer())
    


@app.route('/list_subjects')
@login_required
def list_subjects():
    sid = request.args.get('sid')
    sp_view_access = ['faculty', 'student', 'admin']
    update_access = ['admin']
    if not sid:
        query = "SELECT `subject id`,`subject name`,`credits` from subject"
        rows = sql.execute(query)
        subjects = []
        create_url = None
        if session['role'] == 'admin':
            create_url = '/create_subject'
        for i, row in enumerate(rows):
            subjects.append({"id": row[0], "name": row[1], "credits": row[2], "sno": i + 1})
        return render_template("list_data.html", data=subjects,title="List of Subjects",
         fields=[('sno', False), ('id',True),('name', True), ('credits', False)],
         access_group=['faculty', 'student', 'admin'],
         view_access=sp_view_access, update_access=update_access,
         view_url='/list_subjects', create_url=create_url)
    else:
        if session['role'] not in sp_view_access and session['user_id'] != sid:
            flash('Access Denied', 'danger')
            return redirect(get_referer())
        query = "select * from subject where `subject id`=%(sid)s"
        data = sql.execute(query,{"sid":sid})
        if data == None:
            flash('SOMETHING WENT WRONG', 'danger')
            return redirect(get_referer())
        elif len(data) != 1:
            flash('INVALID SUBJECT ID', 'danger')
            return redirect(get_referer())
        subject = {}
        values = data[0]
        subject['id'] = values[0]
        subject['name'] = values[1]
        subject['rlects'] = values[2]
        subject['tlects'] = values[3]
        subject['credits'] = values[4]
        subject['syll'] = values[5]
        subject['eval_cret'] = values[6]
        mode = request.args.get('mode', 'view')
        if mode == 'update':
            if session['role'] not in update_access and session['user_id'] != sid:
                flash('Access Denied', 'danger')
                return redirect(get_referer())
        
            if session['user_id'] not in database_requests:
                database_requests[session['user_id']] = {}     
            elif len(database_requests[session['user_id']]) > 0:
                for req in database_requests[session['user_id']].copy():
                    del database_requests[session['user_id']][req]
            req_id = str(uuid.uuid4())
            req = [req_id, session['user_id'], 'update', 'subject', subject['id'], datetime.datetime.now()]
            database_requests[session['user_id']][req_id] = req
            return render_template("subjectDetails.html",subject=subject, mode='update', req_id=req_id)
        else:
            return render_template("subjectDetails.html",subject=subject, mode=mode)    
    return apology('something went wrong', 500)

@app.route("/list_rooms")
@login_required
def list_rooms():
    update_access = ['admin']
    sid = request.args.get('sid')
    mode = request.args.get('mode', 'view')
    if sid:
        if mode != 'update':
            flash('Invalid Request')
            return redirect(get_referer())
        elif session['role'] not in update_access:
            flash('Invalid Request')
            return redirect(get_referer())
        res = sql.execute('select * from room where id=%(rid)s', {'rid': sid})
        if len(res) != 1:
            flash('Invalid Request', 'danger')
            return redirect(get_referer())
        data = res[0]
        room = {'id': data[0], 'cap': data[1]}
        if session['user_id'] not in database_requests:
                database_requests[session['user_id']] = {}     
        elif len(database_requests[session['user_id']]) > 0:
            for req in database_requests[session['user_id']].copy():
                del database_requests[session['user_id']][req]
        req_id = str(uuid.uuid4())
        req = [req_id, session['user_id'], 'update', 'room', room['id'], datetime.datetime.now()]
        database_requests[session['user_id']][req_id] = req
        return render_template("roomDetails.html",room=room, mode='update', req_id=req_id)
       
    else:
        query = """SELECT `id`,`sitting capacity`,(select concat(name, ' (', c.id, ')')  
        from class c where c.`room id` = r.id) from room r"""
        rows = sql.execute(query)
        rooms = []
        create_url = None
        if session['role'] == 'admin':
            create_url = '/create_room'
        for i, row in enumerate(rows):
            if not row[2]:
                def_class = ''
            else:
                def_class = row[2]
            rooms.append({"id": row[0], "sitting capacity": row[1], 
            "Default Assigned Class": def_class, "sno": i + 1})
        return render_template("list_data.html", data=rooms,title="List of Rooms",
            fields=[('sno', False), ('id',True),('sitting capacity', True),
            ('Default Assigned Class', True)],
            access_group=['admin'],
            view_access=[], update_access=update_access, update_url="/list_rooms",
            create_url=create_url)


@app.route("/list_classes")
@login_required
def list_classes():
    update_access = ['admin']
    sid = request.args.get('sid')
    mode = request.args.get('mode', 'view')
    if sid:
        if mode != 'update':
            flash('Invalid Request')
            return redirect(get_referer())
        elif session['role'] not in update_access:
            flash('Invalid Request')
            return redirect(get_referer())
        res = sql.execute('select * from class where id=%(id)s', {'id': sid})
        if len(res) != 1:
            flash('Invalid Request', 'danger')
            return redirect(get_referer())
        data = res[0]
        clas = {'id': data[0], 'name': data[1], 'rid': data[2]}
        if session['user_id'] not in database_requests:
                database_requests[session['user_id']] = {}     
        elif len(database_requests[session['user_id']]) > 0:
            for req in database_requests[session['user_id']].copy():
                del database_requests[session['user_id']][req]
        req_id = str(uuid.uuid4())
        req = [req_id, session['user_id'], 'update', 'room', clas['id'], datetime.datetime.now()]
        database_requests[session['user_id']][req_id] = req
        return render_template("classDetails.html",clas=clas, mode='update', req_id=req_id)
       
    else:
        query = """SELECT * from class"""
        rows = sql.execute(query)
        classes = []
        create_url = None
        if session['role'] == 'admin':
            create_url = '/create_class'
        for i, row in enumerate(rows):
            if not row[2]:
                def_room = ''
            else:
                def_room = row[2]
            classes.append({"id": row[0], "name": row[1], 
            "Default Assigned Room": def_room, "sno": i + 1})
        return render_template("list_data.html", data=classes,title="List of Rooms",
            fields=[('sno', False), ('id',True),('name', True),
            ('Default Assigned Room', True)],
            access_group=['admin'],
            view_access=[], update_access=update_access, update_url="/list_classes",
            create_url=create_url)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""
    # Forget any user_id
    session.clear()
    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            flash('INVALID USERNAME', 'danger')
            return render_template('login.html')

        # Ensure password was submitted
        elif not request.form.get("password"):
            flash('INVALID PASSWORD', 'danger')
            return render_template('login.html')
        username = request.form.get("username")
        rows = sql.execute(r"SELECT password, role FROM account WHERE username = %(username)s",
                        {'username': username})
        
        # Ensure username exists and password is correct
        if len(rows) != 1 or hashlib.sha256(request.form.get('password').encode('utf8')).hexdigest() != rows[0][0]:
            flash('INVALID USERNAME OR PASSWORD', 'danger')
            return render_template('login.html')
        role = rows[0][1]
        # Query database for username
        if role == 'admin':
            rows = sql.execute(r"SELECT id, name FROM admin WHERE username = %(username)s",
                        {'username': username})
        elif role == 'faculty':
            rows = sql.execute(r"SELECT `faculty id`, name FROM faculty WHERE username = %(username)s",
                        {'username': username})
        else:
            rows = sql.execute(r"SELECT `REGISTRATION ID`,`student name` FROM student WHERE username = %(username)s",
                        {'username': username})
        if len(rows) != 1:
            flash('Something went wrong', 'danger')
            return redirect('/')
        user_id, name = rows[0]
        if name is None or name == '':
            name = user_id
        # Remember which user has logged in
        session["username"] = request.form.get("username")
        session["role"] = role
        session["user_id"] = user_id
        session["user_name"] = name

        # Redirect user to home page
        flash('Login Successful', 'success')
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""
    clear_session()
    # Redirect user to login form
    return render_template('logout.html')


def parse_address(address):
    paddress = ''
    for _ in ['', '_city', '_state', '_country', '_pin']:
        paddress += request.form.get(address + _)
        if _ == '_pin':
            continue
        paddress += '@'
    return paddress
        


@app.route('/update/<req_id>', methods=['POST'])
@login_required
def update_data(req_id=None):
    if not (req_id and session['user_id'] in database_requests and req_id in database_requests[session['user_id']]):
        flash('Invalid Request', 'danger')
        redirect('/')
    req = database_requests[session['user_id']][req_id]
    req_on = req[3]
    uid = req[4]
    if session['role'] != 'admin' and not (uid == session['user_id'] or uid == session['username']):
        flash('Permission Denied', 'danger')
        return redirect(get_referer())
    else:
        if session['user_id'] == uid or session['username'] == uid:
            req_by = 'self'
            if req_on not in['student', 'faculty', 'account'] and session['role'] != 'admin':
                flash('Permission Denied', 'danger')
                return redirect(get_referer())
        else:
            req_by ='admin'

    if req_on == 'faculty':
        data_correct = True
        res = sql.execute('select * from faculty where `faculty id` = %(fid)s',
        {'fid': uid})
        if len(res) != 1 or res[0][0] != request.form.get('id'):
            flash('Corrupt Request', 'danger')
            redirect('/')
        data = res[0]
        fac_id = data[0]
        tables_to_change = set()
        data_to_update = {
            'faculty':{},
            'qualification': [],
            'keys': {'faculty':  fac_id, 'qualification':  fac_id}
          }
        
        fields = {
            'faculty': ['name', 'email', 'mobile', 'paddress', 'caddress', 'dob', 'bgrp',
             'gender', 'speciality', 'experience']}
        fields_val_rule = {
            # field_name: [parsing rule for input, Empty Check, 
            # Special Checking Rules, old value for update Check]
            'name': [None, True, None, data[1]],
            'email': [None, True, 
             lambda email: VALIDATION_STATUS[validate_email(email, 'faculty', req)], data[2]],
            'mobile': [None, True, 
             lambda mobile: VALIDATION_STATUS[validate_mobile(mobile, 'faculty', req)], data[8]],
            'paddress': [lambda addr: parse_address('paddress'),
             False, lambda address: address.strip('@') != '', data[4]],
            'caddress': [lambda addr: parse_address('caddress'), False, None, data[5]],
            'dob': [lambda dob: str(dob), True, None, data[6]],
            'gender': [None, True, None, data[9]],
            'bgrp': [None, False, None, data[10]],
            'experience': [None, False, None, data[11]],
            'speciality': [None, False, None, data[12]],
        }
        for table_name in fields:
            for field in fields[table_name]:
                if field in fields_val_rule:
                    valid, val = get_form_data(field, fields_val_rule[field][1],
                        fieldmap[table_name]['cols'][field][1], fields_val_rule[field][2],
                         fields_val_rule[field][0], fields_val_rule[field][3])
                else:
                    valid, val = get_form_data(field, key_name=fieldmap[table_name]['cols'][field][1])
                if valid:
                    if len(val) > 0:
                        tables_to_change.add(table_name)
                        data_to_update[table_name].update(val)
                else:
                    data_correct = False
                    flash(f'{fieldmap[table_name]["cols"][field][0]} Value Invalid', 'danger')
        
        qualifications = []
        for i in range(1, 8):
            if not request.form.get('qual_'+str(i)+'_year'):
                continue
            year = request.form.get('qual_'+str(i)+'_year')
            degree = request.form.get('qual_'+str(i)+'_deg')
            institute = request.form.get('qual_'+str(i)+'_ins')
            marks = request.form.get('qual_'+str(i)+'_marks')
            if not year or not degree or not institute or not marks:
                flash('Invalid Qualification Details', 'danger')
                data_correct = False
                break
            qualifications.append({'year': year, 'degree': degree, 'institute': institute, 'percentage': marks})
        if len(qualifications)  == 0:
            data_correct = False
            flash('qualifications must be provided', 'danger')
        else:
            tables_to_change.add('qualification')
            data_to_update['qualification'] = qualifications
        if data_correct:
            result = update_table_data(tables_to_change, data_to_update)
            if result:
                flash('Changes saved successfully', 'success')
            else:
                flash('something went wrong', 'danger')
            del database_requests[session['user_id']][req_id]
            return redirect("/list_faculties")
        else:
            del database_requests[session['user_id']][req_id]
            return redirect(get_referer())
        
    elif req_on == 'student':
        data_correct = True
        res = sql.execute('''select s.*, p.* from student s, `parent details` p 
         where s.`parent id` = p.`parent id` and s.`registration id` = %(sid)s''',
        {'sid': uid})
        if len(res) != 1 or res[0][0] != request.form.get('id'):
            flash('Corrupt Request', 'danger')
            redirect('/')
        data = res[0]
        st_id = data[0]
        tables_to_change = set()
        data_to_update = {'student':{}, 'account':{}, 'parent details': {},
         'keys': {'student': st_id, 'account':data[3],
          'parent details':  data[13]}}
        fields = {
            'student':['name', 'email', 'mobile', 'paddress', 'caddress', 'dob', 'bgrp', 'gender', 'class'],
            'parent details': ['fname', 'fdob', 'mname', 'mdob']
            }
        fields_val_rule = {
            # field_name: [parsing rule for input, Empty Check, 
            # Special Checking Rules, old value for update Check]
            'name': [None, True, None, data[1]],
            'email': [None, True, 
             lambda email: VALIDATION_STATUS[validate_email(email, 'student', req)], data[2]],
            'mobile': [None, True, 
             lambda mobile: VALIDATION_STATUS[validate_mobile(mobile, 'student', req)], data[4]],
            'class': [None, True, None, data[5]],
            'paddress': [lambda addr: parse_address('paddress'), False, 
             lambda address: address.strip('@') != '', data[6]],
            'caddress': [lambda addr: parse_address('caddress'), False, None, data[7]],
            'dob': [lambda dob: str(dob), True, None, data[9]],
            'gender': [None, True, None, data[11]],
            'bgrp': [None, False, None, data[12]],
            'fname': [None, False, None, data[15]],
            'fdob': [lambda fdob: str(fdob), False, None, data[18]],
            'mname': [None, False, None, data[19]],
            'mdob': [lambda mdob: str(mdob), False, None, data[22]],
        }
        for table_name in fields:
            for field in fields[table_name]:
                if field in fields_val_rule:
                    valid, val = get_form_data(field, fields_val_rule[field][1],
                        fieldmap[table_name]['cols'][field][1], fields_val_rule[field][2],
                         fields_val_rule[field][0], fields_val_rule[field][3])
                else:
                    valid, val = get_form_data(field, 
                     key_name=fieldmap[table_name]['cols'][field][1]) 
                if valid:
                    if len(val) > 0:
                        tables_to_change.add(table_name)
                        data_to_update[table_name].update(val)
                else:
                    data_correct = False
                    flash(f'{fieldmap[table_name]["cols"][field][0]} Value Invalid', 'danger')
                    
        femail, memail = request.form.get('femail'), request.form.get('memail')
        if not (femail or memail):
            data_correct = False
            flash('Email of atleast one parent is required', 'danger') 
        else:
            if femail and femail != data[16]:
                tables_to_change.add('parent details')
                data_to_update['parent details'][fieldmap['parent detals']["cols"]['femail']] = femail
            if memail and memail != data[20]:
                tables_to_change.add('parent details')
                data_to_update['parent details'][fieldmap['parent detals']["cols"]['memail'][1]] = memail
        fphone, mphone = request.form.get('fmobile'), request.form.get('mmobile')
        if not (fphone or mphone):
            data_correct = False
            flash('Mobile of atleast one parent is required', 'danger') 
        else:
            if fphone and fphone != data[17]:
                tables_to_change.add('parent details')
                data_to_update['parent details'][fieldmap['parent detals']["cols"]['fmobile'][1]] = fphone
            if mphone and mphone != data[21]:
                tables_to_change.add('parent details')
                data_to_update['parent details'][fieldmap['parent detals']["cols"]['mmobile'][1]] = mphone

        if data_correct:
            if 'class' in data_to_update['student']:
                res = sql.execute('select ifnull(max(`roll number`), 0) + 1 from student where class=%(cls)s',
                {'cls': data_to_update['student']['class']})
                if len(res) > 0:
                    new_rnum = res[0][0]
                else:
                    new_rnum = 1
                data_to_update['student']['roll number'] = new_rnum
                
            result = update_table_data(tables_to_change, data_to_update)
            if result:
                flash('Changes saved successfully', 'success')
            else:
                flash('something went wrong', 'danger')
            del database_requests[session['user_id']][req_id]
            return redirect("/list_students")
        else:
            del database_requests[session['user_id']][req_id]
            return redirect(get_referer())

    elif req_on == 'subject':
        dat = sql.execute('select * from subject where `subject id`=%(sid)s',{'sid': uid})
        if len(dat) != 1:
            flash('Something went wrong', 'danger')
            return redirect(get_referer())
        values = dat[0]
        sid = request.form.get('id')
        if sid != values[0]:
            flash('Corrupt Data', 'danger')
            return redirect(get_referer())
        sname = request.form.get('name')
        if not sname or sname == '':
            flash('Subject Name is required', 'danger')
            return redirect(get_referer())
        lects = request.form.get('nlect')
        if not lects or lects == '':
            flash('Must provide Lectures Required', 'danger')
            return redirect(get_referer())
        tlects = request.form.get('tlect')
        cred = request.form.get('credits')
        syll = request.form.get('syllabus')
        eval_cret = request.form.get('eval_cret')
        query = '''update subject set `subject name`=%(sname)s,
        `lectures required`=%(lw)s,`total lectures required`=%(tl)s,
        `credits`=%(cred)s, `syllabus`=%(syl)s, `evaluation creteria`=%(ev)s 
        WHERE `subject id`=%(sid)s'''
        res = sql.execute(query, {'sid': sid, 'sname': sname, 'lw': lects, 'tl': tlects, 'cred': cred, 'syl': syll, 'ev': eval_cret})
        if res > 0:
            flash('Changes Saved Successfully', 'success')    
        else:
            flash('something went wrong', 'danger')
        return redirect('/list_subjects')


    elif req_on == 'account':
        cuname = request.form.get('change_uname')
        cpass = request.form.get('change_pass')
        msgs = []
        if not(cuname == 'on' or cpass == 'on'):
            flash('Nothing to Change', 'warning')
            return redirect('/')
        old = hashlib.sha256(request.form.get("opassword").encode('utf8')).hexdigest()
        # Ensure password was submitted
        if not old:
            flash('old password must be provided', 'danger')
            return redirect(get_referer())
            
        # Ensure password is correct
        rows = sql.execute("SELECT * FROM account WHERE username = %(id)s",
                            {'id' :session['username']})
        if len(rows) != 1 or old != rows[0][1]:
            flash('Wrong Password', 'danger')
            msgs.append(['wrong password', 'danger'])
            clear_session()
            return render_template('logout.html',msgs=msgs)

        data_to_update = {'account':{},'keys':{'account': session['username']}}
        if request.form.get('change_pass') == 'on':
            # Ensure new password was submitted
            if not request.form.get("password"):
                flash('New Password Must be provided', 'danger')
                return redirect(get_referer())

            password = hashlib.sha256(request.form.get("password").encode('utf8')).hexdigest()
            if password == old:
                msgs.append(['New Password cannot be same as old password', 'warning'])
            else:
                data_to_update['account']['password'] = password
        
        if request.form.get('change_uname') == 'on':
            # Ensure new uername was submitted
            if not request.form.get("username"):
                flash('New username must be provided', 'danger')
                return redirect(get_referer())

            valid, val = get_form_data('username', True, 'username',
              lambda uname: VALIDATION_STATUS[validate_username(uname, req)],None, rows[0][0])
            if valid:
                if len(val) < 1:
                    msgs.append(['new username should not be same as old one', 'warning'])
                else:
                    data_to_update['account'].update(val)
            else:
                flash('Invalid New Username', 'danger')
                return redirect(get_referer())
        
        if len(data_to_update['account']) < 1:
            for msg in msgs:
                flash(msg[0], msg[1])
            flash('Nothing to Change', 'warning')
            return redirect('/')
        # store data in database
        res = update_table_data(['account'], data_to_update)
        if res:
            flash('changes saved successfully', 'success')
            msgs.append(['changes saved successfully', 'success'])
        else:
            flash('something went wrong', 'danger')
        clear_session()
        return render_template('logout.html', msgs=msgs)
    elif req_on == 'room':
        rid = request.form.get('id')
        if str(rid) != str(uid):
            flash('Corrupt Data', 'danger')
            return redirect(get_referer())
        cap = request.form.get('cap')
        try:
            rid, cap = int(rid), int(cap)
        except:
            flash('Invalid Data', 'danger')
            return redirect(get_referer())
        if rid < 1 or cap < 1 or cap > 2000:
            flash('Invalid Data', 'danger')
            return redirect(get_referer())
        res = sql.execute('update room set `sitting capacity`=%(cap)s where id=%(id)s', {'id': uid, 'cap': cap})
        if res > 0:
            flash('Changes Saved Successfully', 'success')
        else:
            flash('Something went wrong', 'danger')
        return redirect('/list_rooms')


@app.route('/my_info')
def my_info():
    if session['role'] == 'admin':
        flash('Feature not yet available', 'danger')
        return redirect(get_referer())
    elif session['role'] == 'student':
        return redirect('/list_students?sid='+session['user_id'])
    elif session['role'] == 'faculty':
        return redirect('/list_faculties?sid='+session['user_id'])
    else:
        flash('Invalid Request', 'danger')
        return redirect(get_referer())


def clear_session():
    if 'user_id' in session and session['user_id'] in database_requests:
        del database_requests[session['user_id']]
    # Forget any user_id
    session.clear()
    

def add_records(tables, data):
    try:
        sql.start_transaction()
        for table in sorted(tables, key=lambda v: fieldmap[v]['order']):
            table_data = data[table]
            if type(table_data) == type(dict()):
                query = f'INSERT INTO `{table}` ('
                query += ','.join([f'`{col}`' for col in table_data])
                query += ') VALUES '
                v_q = '(' + ','.join([f'%({_})s' for _ in table_data]) +')'
                sql.execute_trans(query+v_q, table_data)
            elif type(table_data) == type(list()):
                for row_values in table_data:
                    query = f'INSERT INTO `{table}` ('
                    query += ','.join([f'`{col}`' for col in row_values])
                    query += ') VALUES '
                    v_q = '(' + ','.join([f'%({_})s' for _ in row_values]) +')'
                    sql.execute_trans(query+v_q, row_values)
        sql.commit()
        return True
    except Exception as err:
        print(err)
        sql.rollback()
        return False
    finally:
        sql.close()



def update_table_data(tables, data):
    try:
        sql.start_transaction()
        slist = sorted(tables, key=lambda v:fieldmap[v]['order'])
        for table in slist:
            table_data = data[table]
            key = fieldmap[table]['cols'][table_keys[table]][1], data['keys'][table]
            if type(table_data) == type(dict()):
                query = f'UPDATE `{table}` SET '
                query += ','.join([f"`{col}` = %({col})s " for col in table_data])
                query += f"WHERE `{key[0]}` = %(key_{key[0]})s"
                table_data[f'key_{key[0]}'] = key [1]
                sql.execute_trans(query, table_data)
            elif type(table_data) == type(list()):
                query = f'DELETE FROM `{table}` WHERE `{key[0]}` = %(key_{key[0]})s'
                sql.execute_trans(query, {f'key_{key[0]}': key[1]})
                for v in table_data:
                    v[f'{key[0]}'] = key[1]
                query = parse_insert_query(table, table_data[0])
                sql.execute_many_trans(query, table_data)
        sql.commit()
        return True
    except Exception as err:
        print(err)
        sql.rollback()
        return False
    finally:
        sql.close()

def parse_insert_query(table, data):
    if type(data) == type(dict()):
        query = f'INSERT INTO `{table}` ('
        query += ','.join([f'`{col}`' for col in data])
        query += ') VALUES '
        query += '(' + ','.join([f'%({_})s' for _ in data]) +')'
    elif type(data) == type(list()):
        query = f'INSERT INTO `{table}` ('
        query += ','.join([f'`{col}`' for col in data])
        query += ') VALUES '
        query += ','.join(['(' + ','.join([f'%({_})s' for _ in row_data]) +')' for row_data in data])
    else:
        query = None
    return query



@app.route("/register", methods=["GET", "POST"])
@admin_access_required
def register():
    """Register user"""
    if request.method == "POST":
        data_correct = True
        account_data = {}
        req_type = request.args.get('type')
        if not req_type or req_type not in ['student', 'faculty']:
            flash('INVALID REQUEST', 'danger')
            return redirect(get_referer())

        elif req_type == 'faculty':
            account_data['role'] = 'faculty'
            fac_data = {}
            full_name = request.form.get('name')
            if not full_name:
                flash('must provide name', 'danger')
                data_correct = False
            else:
                fac_data['name'] = full_name
            email = request.form.get('email')
            email_valid = VALIDATION_STATUS[validate_email(email, 'faculty')]
            if not email_valid:
                flash('Invalid email', 'danger')
                data_correct = False
            else:
                fac_data['email'] = email
            mobile = request.form.get('mobile')
            if not mobile:
                flash('Invalid mobile', 'danger')
                data_correct = False
            else:
                fac_data['mobile number'] = mobile
            paddress = parse_address('paddress')
            if paddress.strip('@') == '':
                flash('must provide permanent address', 'danger')
                data_correct = False
            else:
                fac_data['permanent address'] = paddress
            caddress = parse_address('caddress')
            if caddress:
                fac_data['corr. address'] = caddress
            dob = request.form.get('dob')
            if not dob:
                flash('must provide date of birth', 'danger')
                data_correct = False
            else:
                fac_data['date of birth'] = dob
            bgrp = request.form.get('bgrp')
            if bgrp:
                fac_data['blood group'] = bgrp
            gender = request.form.get('gender')
            if gender:
                fac_data['gender'] = gender
            speciality = request.form.get('speciality')
            if speciality:
                fac_data['subject speciality'] = speciality
            experience = request.form.get('experience')
            if experience:
                fac_data['experience'] = experience
            qualifications = []
            for i in range(1, 8):
                if not request.form.get('qual_'+str(i)+'_year'):
                    break
                year = request.form.get('qual_'+str(i)+'_year')
                degree = request.form.get('qual_'+str(i)+'_deg')
                institute = request.form.get('qual_'+str(i)+'_ins')
                marks = request.form.get('qual_'+str(i)+'_marks')
                if not year or not degree or not institute or not marks:
                    flash('Invalid Qualification Details', 'danger')
                    data_correct = False
                    break
                qualifications.append({'year': year, 'degree': degree, 'institute': institute, 'percentage': marks})
            if data_correct:
                try:
                    res = sql.execute('select max(substring(`faculty id`, 2, 5)) + 1 from faculty')
                    if len(res) > 0:
                        fac_id = f'F{res[0][0]:05.0f}'
                    else:
                        fac_id = 'F00001'
                    fac_data['faculty id'] = fac_id
                    fac_data['username'] = fac_id
                    sql.start_transaction()
                    account_data['username'] = fac_id
                    account_data['password'] = hashlib.sha256((fac_id+'_'+fac_data['mobile number']).encode('utf8')).hexdigest()
                    
                    account_query = parse_insert_query('account', account_data)
                    sql.execute_trans(account_query, account_data)
                    fac_query = parse_insert_query('faculty', fac_data)
                    sql.execute_trans(fac_query, fac_data)
                    for qual in qualifications:
                        qual[fieldmap['qualification']['cols'][table_keys['qualification']][1]] = fac_id
                    sql.execute_many_trans(parse_insert_query('qualification', qualifications[0]), qualifications)
                    sql.commit()
                    flash('Added successfully with ID: '+fac_id, 'success')
                    flash(f'Username : {fac_id} ,Password is assigned faculty_mobileNumber eg. F00001_9999999999', 'info')
                except Exception as err:
                    sql.rollback()
                    print(err)
                    flash('something went wrong', 'danger')
                    return redirect(get_referer())
                finally:
                    sql.close()
                return redirect("/list_faculties")
            else:
                return redirect(get_referer())
        elif req_type == 'student':
            fields = {
                'student':['name', 'email', 'mobile', 'paddress', 'caddress', 'dob', 'bgrp',
                    'gender', 'class',],
                    'parent details': ['fname', 'fdob', 'mname', 'mdob']
                }
            fields_val_rule = {
                # field_name: [parsing rule for input, Empty Check, Special Checking Rules]
                'name': [None, True, None],
                'email': [None, True, lambda email: VALIDATION_STATUS[validate_email(email, 'student')]],
                'mobile': [None, False, None],
                'paddress': [lambda addr: parse_address('paddress'), False, lambda address: address.strip('@') != ''],
                'caddress': [lambda addr: parse_address('caddress'), False, None],
                'dob': [lambda dob: str(dob), True, None],
                'gender': [None, True, None],
                'class': [None, True, None]
            }
            data = {'account': {},'student': {}, 'parent details': {}}
            for table_name in fields:
                for field in fields[table_name]:
                    if field in fields_val_rule:
                        valid, val = get_form_data(field, fields_val_rule[field][1],
                        fieldmap[table_name]['cols'][field][1], fields_val_rule[field][2], fields_val_rule[field][0])
                    else:
                        valid, val = get_form_data(field, key_name=fieldmap[table_name]['cols'][field][1])
                    if valid:
                        data[table_name].update(val)
                    else:
                        data_correct = False
                        flash(f'{fieldmap[table_name]["cols"][field][0]} Value Invalid', 'danger')
                        
            femail, memail = request.form.get('femail'), request.form.get('memail')
            if not (femail or memail):
                data_correct = False
                flash('Email of atleast one parent is required', 'danger') 
            else:
                if femail:
                    data['parent details'][fieldmap[table_name]['cols']['femail'][1]] = femail
                if memail:
                    data['parent details'][fieldmap[table_name]['cols']['memail'][1]] = memail
            fphone, mphone = request.form.get('fmobile'), request.form.get('mmobile')
            if not (fphone or mphone):
                data_correct = False
                flash('Mobile of atleast one parent is required', 'danger') 
            else:
                if fphone:
                    data['parent details'][fieldmap[table_name]['cols']['fmobile'][1]] = fphone
                if mphone:
                    data['parent details'][fieldmap[table_name]['cols']['mmobile'][1]] = mphone
            if data_correct:
                res = sql.execute('select max(substring(`registration id`, 2, 5)) + 1 from student')
                if len(res) > 0:
                    sid = f'S{res[0][0]:05.0f}'
                else:
                    sid = 'S00001'
                
                res = sql.execute('select max(substring(`parent id`, 2, 10)) + 1 from `parent details`')
                if len(res) > 0:
                    pid = f'P{res[0][0]:09.0f}'
                else:
                    pid = f'P{1:09.0f}'

                res = sql.execute('select ifnull(max(`roll number`), 0) + 1 from student where class=%(cls)s',
                {'cls': data['student']['class']})
                if len(res) > 0:
                    rnum = res[0][0]
                else:
                    rnum = 1
                data['student']['registration id'] = sid
                data['student']['roll number'] = rnum
                data['student']['parent id'] = pid
                data['parent details']['parent id'] = pid
                data['account']['username'] = sid
                data['account']['password'] = hashlib.sha256((sid+'_'+data['student']['date of birth']).encode('utf8')).hexdigest()
                data['account']['role'] = 'student'
                data['student']['username'] = sid
                try:
                    sql.start_transaction()
                    account_query = parse_insert_query('account', data['account'])
                    sql.execute_trans(account_query, data['account'])
                    parents_query = parse_insert_query('parent details', data['parent details'])
                    sql.execute_trans(parents_query, data['parent details'])
                    
                    student_query = parse_insert_query('student', data['student'])
                    sql.execute_trans(student_query, data['student'])
                    sql.commit()
                    flash(f'Record Added successully with Registration ID: {sid} and assigned roll number {rnum}', 'success')
                    flash(f'Username : {sid} ,Password is assigned reg. Id_date of birth eg. S00000_2020-12-31', 'info')
                    return redirect('/list_students')
                except Exception as err:
                    print(err)
                    sql.rollback()
                    flash('something went wrong', 'danger')
                    return redirect('/list_students')
                finally:
                    sql.close()
            else:
                return redirect(get_referer())
    else:
        reg_type = request.args.get('type')
        if reg_type == 'student':
            return render_template('/studentDetails.html', mode='create')
        elif reg_type == 'faculty':
            return render_template('/faculty_details.html', mode='create')
        else:
            flash('Invalid Registartion Request', 'danger')
            redirect('/')
        return render_template("register.html")


def get_form_data(field, none_check=False, key_name=None, extra_checks=None, preprocess=None,
    old_val=None):
    data, valid = {}, True
    if not key_name:
        key_name = field
    if preprocess:
        val = preprocess(request.form.get(field))
    else:
        val = request.form.get(field)
    
    if none_check and (val is None or val == ''):
        valid = False
    elif extra_checks:
        valid = extra_checks(val)
    if valid and val != '' and str(val) != str(old_val):
        data[key_name] = val
    return valid, data


def get_referer():
    if 'HTTP_REFEFER' in request.headers:
        return request.headers['Referer']
    else:
        return '/'

@app.route("/search_tt", methods=["GET", "POST"])
@login_required
def search_tt():
    """show options to view time table"""
    # User reached route via GET (as by clicking a link or via redirect)
    if request.method == "GET":
        typeOfSearch = request.args.get('type', None)
        mode =request.args.get('mode','view')
        if typeOfSearch == None:
            if session['role'] == 'admin':
                tt_of = None
            elif session['role'] == 'faculty':
                tt_of = (session['user_id'], 'faculty')
            elif session['role'] == 'student':
                q = f'''select `{fieldmap["student"]["cols"]["class"][1]}`
                 from student where `{fieldmap["student"]["cols"][table_keys["student"]][1]}` = %(sid)s'''
                res = sql.execute(q, {'sid': session['user_id']})
                if len(res) > 0:
                    tt_of = (res[0][0],'classes')
                else:
                    tt_of = None
            return render_template("search_tt.html", tt_of=tt_of, start_mode=mode)
        else:
            if typeOfSearch == 'classes':
                data = getClassValuesForSearchTT()
            elif typeOfSearch == 'faculty':
                data = getFacValuesForSearchTT()
            elif typeOfSearch == 'rooms':
                data = getRoomValuesForSearchTT()
            else:
                return None
            return jsonify(data)

        # User reached route via POST (as by submitting a form via POST)
    else:
        timetable = getTimeTable(request.form.get("value_selector"), sql)
        theaders = timetable[0].copy()
        timetable = timetable[1:]
        return render_template("view_tt.html", gfaculties=getFacValuesForSearchTT(),
         gclasses=getClassValuesForSearchTT, theaders=theaders, timetable=timetable)


@app.route('/validate_data', methods = ['POST'])
@login_required
def validate_data():
    check_on = request.form.get('check_on')
    if check_on == None:
        return
    data = {}
    req_id = request.form.get('uid')
    if req_id and session['user_id'] in database_requests and \
        req_id in database_requests[session['user_id']]:
        request_body = database_requests[session['user_id']][req_id] 
    else:
        request_body = None
    
    if 'room' in check_on:
        room = request.form.get('room')
        q = 'select id from room where id = %(rid)s' 
        q_data = {'rid': room}
        res = sql.execute(q, q_data)
        if len(res) > 0:
            data['room'] = 'taken'
        else:
            data['room'] = 'not_taken'
    if 'subid' in check_on:
        subid = request.form.get('subid')
        res = sql.execute('select `subject id` from subject where `subject id` = %(sid)s', {'sid': subid})
        if len(res) > 0:
            data['subid'] = 'taken'
        else:
            data['subid'] = 'not_taken'
    
    if 'username' in check_on:
        username = request.form.get('username')
        data['username'] = validate_username(username, request_body)
    if 'email' in check_on:
        email = request.form.get('email')
        emailof = request.form.get('emailof')
        email_status = validate_email(email, emailof, request_body)    
        data['email'] = email_status

    if 'classname' in check_on:
        cname = request.form.get('classname')
        data['classname'] = validate_classname(cname, request_body)
    data['check_on'] = check_on
    return jsonify(data)

VALIDATION_STATUS = {
    'INVALID REQUEST' : False,
    'TAKEN': False,
    'NOT TAKEN': True
}

def validate_email(email, emailof='student, faculty', req=None):
    if not req:
        res = ''
        if 'faculty' in emailof:
            res = sql.execute('select email from faculty where `email` = %(email)s', {'email': email})
        elif 'student' in emailof:
            res = sql.execute('''select email from student where `email` = %(email)s''', {'email': email})
        elif 'parent' in emailof:
            1
        if type(res) == type(''):    
            return 'INVALID REQUEST'
        elif len(res) > 0:
            return 'TAKEN'
        else:
            return 'NOT TAKEN'
    else:
        req_on = req[3]
        if req_on == 'faculty':
            q = 'select email from faculty where `faculty id` = %(id)s'
            q_data = {'id': req[4]}
        elif req_on == 'student':
            q = 'select email from student where `registration id` = %(id)s'
            q_data = {'id': req[4]}
        else:
            return 'INVALID REQUEST'
        res = sql.execute(q, q_data)
        if len(res) != 1:
            return 'INVALID REQUEST'
        else:
            o_email = res[0][0]
            if o_email != email:
                return validate_email(email, emailof)
            else:
                return 'NOT TAKEN'


def validate_mobile(mobile, mobileof='student, faculty', req=None):
    if not req:
        res = ''
        if 'faculty' in mobileof:
            q = 'select `{0}` from faculty where `{0}` = %(mobile)s'.format(fieldmap['faculty']['cols']['mobile'][1])
            res = sql.execute(q, {'mobile': mobile})
        elif 'student' in mobileof:
            q = 'select `{0}` from student where `{0}` = %(mobile)s'.format(fieldmap['student']['cols']['mobile'][1])
            res = sql.execute(q, {'mobile': mobile})
        if type(res) == type(''):    
            return 'INVALID REQUEST'
        elif len(res) > 0:
            return 'TAKEN'
        else:
            return 'NOT TAKEN'
    else:
        req_on = req[3]
        if req_on == 'faculty':
            q = f"""select `{fieldmap['faculty']['cols']['mobile'][1]}` 
            from faculty where `{fieldmap['faculty']['cols'][table_keys['faculty']][1]}` = %(id)s"""
            q_data = {'id': req[4]}
        elif req_on == 'student':
            q = f"""select `{fieldmap['student']['cols']['mobile'][1]}` from student
             where `{fieldmap['student']['cols'][table_keys['student']][1]}` = %(id)s"""
            q_data = {'id': req[4]}
        else:
            return 'INVALID REQUEST'
        res = sql.execute(q, q_data)
        if len(res) != 1:
            return 'INVALID REQUEST'
        else:
            o_mobile = res[0][0]
            if o_mobile != mobile:
                return validate_email(mobile, mobileof)
            else:
                return 'NOT TAKEN'



def validate_username(username, req=None):
    if req == None:
        q = f"""select `{fieldmap['account']['cols']['username'][1]}` from account 
        where `{fieldmap['account']['cols'][table_keys['account']][1]}`=%(uname)s"""
        res = sql.execute(q, {'uname': username})
        if len(res) > 0:
            return 'TAKEN'
        else:
            return 'NOT TAKEN'
    else:
        req_on = req[3]
        if req_on == 'faculty':
            q = f"""select `{fieldmap['faculty']['cols']['username'][1]}` 
            from faculty where `{fieldmap['faculty']['cols'][table_keys['faculty']][1]}` = %(id)s"""
            q_data = {'id': req[4]}
        elif req_on == 'student':
            q = f"""select `{fieldmap['student']['cols']['username'][1]}` 
            from student where `{fieldmap['student']['cols'][table_keys['student']][1]}` = %(id)s"""
            q_data = {'id': req[4]}
        elif req_on == 'account':
            q = None
        else:
            return 'INVALID REQUEST'
        if q:
            res = sql.execute(q, q_data)
            if len(res) != 1:
                return 'INVALID USERNAME'
            o_username = res[0][0]
        else:
            if session['username'] != req[4]:
                return 'INVALID REQUEST'
            o_username = session['username']
        
        if username != o_username:
            return validate_username(username)
        else:
            return 'NOT TAKEN'


def validate_classname(cname, req=None):
    if req == None:
        q = """select `name` from class where `name`=%(cname)s"""
        res = sql.execute(q, {'cname': cname})
        if len(res) > 0:
            return 'TAKEN'
        else:
            return 'NOT TAKEN'
    else:
        req_on = req[3]
        if req_on == 'class':
            q = f"""select `name` 
            from class where `id` = %(id)s"""
            q_data = {'id': req[4]}
        else:
            return 'INVALID REQUEST'
        res = sql.execute(q, q_data)
        if len(res) != 1:
            return 'INVALID USERNAME'
        else:
            o_name = res[0][0]
            if cname != o_name:
                return validate_classname(cname)
            else:
                return 'NOT TAKEN'


def getRoomValuesForSearchTT():
    # Query database for username
    rows = sql.execute("select `id`, case when "
            + "`id` in (select distinct `room id` from schedule) then '1'"
            + " else '0' end from room")
    if rows == None:
        return 
    room_data = []
    for rid, ca in rows:
        if ca == '1':
            is_assigned = True
            room_data.append({'id' :rid, 'name': ''})
        else:
            is_assigned = False
    return room_data
    

def getFacValuesForSearchTT():
    # Query database for username
    fac_rows = sql.execute("select `faculty id`,name,case when "
            + "`faculty id` in (select distinct `faculty id` from schedule) then '1'"
            + " else '0' end from faculty")
    if fac_rows == None:
        return 
    fac_data = []
    for facid, facname, ca in fac_rows:
        if ca == '1':
            is_assigned = True
            fac_data.append({'id' :facid, 'name': facname})
        else:
            is_assigned = False
    return fac_data
    

def getClassValuesForSearchTT():
    # Query database for username
    cls_rows = sql.execute(r"""select id, name, case when 
id in (select distinct `class id` from schedule) then '1'
else '0' end, case when id in 
(select distinct `class id` from class_subject_faculty) then '1'
else '0' end from class""")
    if cls_rows == None:
        return
    cls_data = []
    for clsid, clsname, ca, cbe in cls_rows:
        if ca == '1':
            is_assigned = True
        else:
            is_assigned = False
        if cbe == '1':
            can_be_assigned = True
        else:
            can_be_assigned = False
        cls_data.append({'id' :clsid, 'name': clsname, 'assigned': is_assigned,
        'assignable': can_be_assigned})
    return cls_data

def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)