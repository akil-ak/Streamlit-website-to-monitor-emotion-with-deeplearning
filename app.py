import sqlite3
from flask import Flask, render_template,url_for,Response
import os
import requests
import json
import datetime
from flask import Flask, jsonify, render_template, request, flash,session,redirect
from flask_session import Session
from flask_socketio import SocketIO, emit, join_room, leave_room, send
import cv2
from fer import FER
from rake_nltk import Rake
rake_nltk_var = Rake()
question=["How long you have been under stress?","Have you shared your problem to anyone else?","can you say further more...","have you taken any steps to solve the problem","did anyone help you to solve this problem"]
Answers=[]
all_states=[]
neutral=0.0
angry=0.0
sad=0.0
happy=0.0
suprise=0.0
i=-1
neu_no=0
ang_no=0
sup_no=0
sad_no=0
hap_no=0

emotion2=""
face_cascade_name = cv2.data.haarcascades + 'haarcascade_frontalface_alt.xml'  #getting a haarcascade xml file
face_cascade = cv2.CascadeClassifier()  #processing it for our project
if not face_cascade.load(cv2.samples.findFile(face_cascade_name)):  #adding a fallback event
    print("Error loading xml file")

camera=cv2.VideoCapture(0)

def generate_frames():
    global emotion
    while True:
            
        ## read the camera frame
        success,frame=camera.read()
        if not success:
            break
        else:
            gray=cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY)  #changing the video to grayscale to make the face analisis work properly
            face=face_cascade.detectMultiScale(gray,scaleFactor=1.1,minNeighbors=5)

            for x,y,w,h in face:
                img=cv2.rectangle(frame,(x,y),(x+w,y+h),(0,0,255),1)  #making a recentangle to show up and detect the face and setting it position and colour
          
            ret,buffer=cv2.imencode('.jpg',frame)
            emotion_detector = FER()
            emotion=emotion_detector.top_emotion(frame)
            global emotion2,neu_no,ang_no,sad_no,hap_no,sup_no,neutral,angry,suprise,sad,happy
            
            emotion2=emotion[0]
            print(emotion)
            if(emotion[0]=="neutral"):
                neu_no+=1
                neutral+=emotion[1]
            elif(emotion[0]=="angry"):
                ang_no+=1
                angry=angry+emotion[1]
            elif(emotion[0]=="surprise"):
                sup_no+=1
                suprise+=emotion[1]
            elif(emotion[0]=="happy"):
                happy+=emotion[1]
                hap_no+=1
            elif(emotion[0]=="sad"):
                sad+=emotion[1]
                sad_no+=1
            frame=buffer.tobytes()


        yield(b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')


#with open('schema.sql') as f:
  #connection.executescript(f.read())
app = Flask(__name__) 
app.debug = True
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")
app.config["SESSION_PERMANENET"]=False
app.config["SESSION_TYPE"]="filesystem"
Session(app)
socketio = SocketIO(app, manage_session=False)
connection = sqlite3.connect('database.db',check_same_thread=False)

flag=0

@app.route("/", methods=['GET','POST']) 

def home():
  return render_template("home.html")
def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn
@app.route("/Admin_main",methods=['POST'])
def Admin_main():
    q=[request.form['name1'],request.form['name2'],request.form['name3'],request.form['name4'],request.form['name5']]
    for i in range(0,len(question)):
        if(q[i]!=''):
            question[i]=q[i]
    return render_template('admin.html')

@app.route("/login",methods=['POST', 'GET'])
def login_pg():
    
    
    if request.method=="POST":
        session["name"]=request.form.get("uname")
        session["password"]=request.form.get("upswd")
        print("hi",flush=True)
        conn = get_db_connection()
        users = conn.execute('SELECT * FROM registers').fetchall()
        print("users")
        for user in users:
            if(user["name"]==session["name"]):
                global flag
                flag=1
                if(user["password"]==session["password"]):
                    flag=1
                else:
                    flag=0
        print(flag)
        if(flag==0):
            session["name"]=None
            session["password"]=None
            message="username or password is wrong"
            return render_template("login.html",message=message)
        conn.close()
        
        return redirect("/")
    return render_template("login.html")

@app.route('/signup1',methods=["GET","POST"])
def signup1():
    return render_template("signup.html")

@app.route('/sign',methods=["GET","POST"])
def sign():
    

    name=(request.form.get("uname1"))
    email=(request.form.get("email1"))
    passwd1=request.form.get("upswd1")
    passwd2=request.form.get("upswd2")
    if not name :
        return render_template("error.html",message="Missing Name")   
    if (passwd1!=passwd2):
        return render_template("error.html",message="passwords not matching")
    cur = connection.cursor()   
    cur.execute("INSERT INTO registers (name,password) VALUES (?, ?)",(name,passwd1)
            )
    
    connection.commit()           
   
    
    return render_template("login.html")

@app.route('/admin_ques')
def admin_ques():
    return render_template("admin_ques.html",questions=question)
@app.route('/index',methods=["GET","POST"])
def index():
        if not session.get("name"):
            return redirect("/login")
        
        return render_template("index.html")
@app.route('/connect')
def connect():
   

    if not session.get("name"):
            return redirect("/login")
    
    cur=connection.cursor()
    post=cur.execute('SELECT id FROM registers WHERE name =?',(session["name"],)).fetchone()
    print(post[0])
    
    connection.commit()
    
    return render_template("connect.html")

@app.route("/logout")
def logout():
    session["name"]=None
    global flag
    flag=0
    print ("hi")
    return redirect("/")
@app.route('/chat', methods=['GET', 'POST'])
def chat():
    if(request.method=='POST'):
        username = request.form['username']
        room = request.form['room']
        #Store the data in session
        session['username'] = username
        session['room'] = room
        return render_template('chat.html', session = session)
    else:
        if(session.get('username') is not None):
            return render_template('chat.html', session = session)
        else:
            return redirect(url_for('index'))
@app.route('/admin')
def admin():
     conn = get_db_connection()
     users = conn.execute('SELECT * FROM registers').fetchall()
     conn.close()
     return render_template('admin.html',users=users)
@app.route('/details')
def details():
    connection = sqlite3.connect('database.db',check_same_thread=False)

    detail=request.args.get("details")
    conn = get_db_connection()
    users = conn.execute('SELECT * FROM questions WHERE id =?',(detail)).fetchall()
    for user in users:
        print(user["text"])
    conn.close()
    return render_template('details.html',users=users)

@socketio.on('join', namespace='/chat')
def join(message):
    room = session.get('room')
    join_room(room)
    emit('status', {'msg':  session.get('username') + ' has entered the room.'}, room=room)


@socketio.on('text', namespace='/chat')
def text(message):
    room = session.get('room')
    emit('message', {'msg': session.get('username') + ' : ' + message['msg']}, room=room)


@socketio.on('left', namespace='/chat')
def left(message):
    room = session.get('room')
    username = session.get('username')
    leave_room(room)
    session.clear()
    emit('status', {'msg': username + ' has left the room.'}, room=room)

@app.route('/thread')
def thread():
    connection = sqlite3.connect('database.db',check_same_thread=False)

    
    if not session.get("name"):
            return redirect("/login")
    try:
        cur=connection.cursor()
    except:
        return redirect("/") 
        
    post=cur.execute('SELECT id FROM registers WHERE name =?',(session["name"],)).fetchone()
    global i,neu_no,ang_no,sad_no,hap_no,neutral,angry,suprise,sad,happy,sup_no
    
    answer=request.args.get("name")
    
    


    
    
    i=i+1
    if(neu_no!=0):
        neu_val=(neutral*100)/neu_no
    else:
        neu_val=0
    if(hap_no!=0):
        hap_val=happy*100/hap_no
    else:
        hap_val=0
    if(sad_no!=0):
        sad_val=sad*100/sad_no
    else:
        sad_val=0
    if(sup_no!=0):
        suprise_val=suprise*100/sup_no
    else:
        suprise_val=0
    if(ang_no!=0):
        ang_val=angry*100/ang_no
    else:
        ang_val=0
    neutral=0.0
    angry=0.0
    sad=0.0
    happy=0.0
    suprise=0.0
    neu_no=0
    ang_no=0
    sup_no=0
    sad_no=0
    hap_no=0
    print(all_states)
    cur = connection.cursor()   
    cur.execute("INSERT INTO questions (id,ques_no,angry,sad,neutral,happy,suprise,text) VALUES (?,?,?,?,?,?,?,?)",(post[0],i+1,ang_val,sad_val,neu_val,hap_val,suprise_val,answer)
            )
    connection.commit()
    if(i>=len(question)):
     
        connection.close()
        return "thank you"
   
    return render_template('voice.html',message=question[i],emotion1=emotion2)


@app.route('/video')
def video():
    return Response(generate_frames(),mimetype='multipart/x-mixed-replace; boundary=frame')
