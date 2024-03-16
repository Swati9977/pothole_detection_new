import datetime
import time
from pathlib import Path
from static.prediction import detect 
import re
from flask import Flask, flash, request, redirect, url_for, render_template, send_from_directory,jsonify
from werkzeug.utils import secure_filename
import os
import pymysql

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['ALLOWED_EXTENSIONS'] = {'jpg', 'jpeg', 'png', 'gif'}
app.secret_key = 'mysecretkey'



def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def connect_db():
    print("swati")
    return pymysql.connect(
        host='localhost',
        user='root',
        password='',
        database='visipol'
    )

@app.route('/')
def home():
    return render_template('home.html')

def predict(image):
    sum_last_item = 0
    count = 0
    BASE_DIR = Path(__file__).resolve().parent
    STATIC_DIR = os.path.join(BASE_DIR,"static")

    wt_name = "./static/prediction/visipol.pt"
    imgsrc = "./uploads/"+image

    resp = detect.run(weights=wt_name,source=imgsrc,save_txt=True,save_conf=True)
    x = re.findall("exp(.*)", str(resp))
    lableFolder = x[0]
    imgx = image.split('.')
    fname = str(imgx[0])
    with open(STATIC_DIR+"/prediction/runs/detect/exp"+lableFolder+"/labels/"+fname+".txt") as f:
        for line in f:
            items = line.strip().split()
            last_item = float(items[-1])
            sum_last_item += last_item
            count += 1
    average_last_item = sum_last_item / count
    resp=average_last_item
    cropped_img_path="static/prediction/runs/detect/exp"+lableFolder+"/"+image
    if resp > 0.7:
        severity='Severe'
    elif resp > 0.5 and resp <0.7:
        severity='Major'
    else:
        severity='Minor'

    #insert_pred = Prediction(conf=resp,severity=severity,fname=cropped_img_path)
    #db.session.add(insert_pred)
    #db.session.commit()

    return [resp,severity,cropped_img_path]

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            location = request.form.get('location').split(',')
            ts = time.time()
            print("ddddddddddddddddddddddddddddddddddddddddddddddddd")
            timestamp = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
            print("ddd1")
            image = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            predictVal=predict(filename)
            print(predictVal) 
            db = connect_db()
            cursor = db.cursor()
            sql = "INSERT INTO images (filename, lat, lng,created_at,conf,severity,predictfname) VALUES (%s, %s, %s,%s,%s,%s,%s)"
            values = (filename, location[0], location[1],timestamp,predictVal[0],predictVal[1],predictVal[2])
            cursor.execute(sql, values)
            db.commit()
            cursor.close()
            db.close()
            flash('File uploaded successfully')

            # Classify the image
            # image = Image.open(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            # predicted_class, probabilities = classify_image(image)
            # print(predicted_class, probabilities)
            # # Render the result page with the predicted class and probability distribution
            # classes = ['class1', 'class2', 'class3', 'class4', 'class5']
            # redicted_class_name = classes[predicted_class]

            return render_template('upload.html')
        else:
            flash('Invalid file type. Only JPG, JPEG, PNG, and GIF files are allowed.')
            return redirect(request.url)
    return render_template('upload.html')

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


# Route to display image locations in a Leaflet map
@app.route('/map')
def map():
    # Connect to the database
    connection = connect_db()
    try:
        with connection.cursor() as cursor:
            # Query the images table for location data
            sql = 'SELECT lat,lng,created_at FROM images'
            cursor.execute(sql)
            rows = cursor.fetchall()               

    finally:
        connection.close()

    # Render the map HTML file and pass the location data as a list of rows
    return render_template('maps.html', rows=rows)


# Route to display image locations in a Leaflet map
@app.route('/getLocations')
def getLocations():
    # Connect to the database
    connection = connect_db()
    try:
        with connection.cursor() as cursor:
            # Query the images table for location data
            sql = 'SELECT lat,lng,id,created_at,severity FROM images'
            cursor.execute(sql)
            rows = cursor.fetchall()      

    finally:
        connection.close()

    # Render the map HTML file and pass the location data as a list of rows
    return jsonify(rows)

@app.route('/dashboard', methods=['GET'])
def dashboard():
    # Connect to the database
    connection = connect_db()
    try:
        with connection.cursor() as cursor:
            # Query the images table for location data
            sql = 'SELECT lat,lng,created_at FROM images'
            cursor.execute(sql)
            rows = cursor.fetchall()               

    finally:
        connection.close()
    '''
    Render the main page
    '''
    return render_template('dashboard.html',rows=rows)

# Route to display image locations in a Leaflet map
@app.route('/getLatestLocations')
def getLatestLocations():
    # Connect to the database
    connection = connect_db()
    try:
        with connection.cursor() as cursor:
            # Query the images table for location data
            sql = 'SELECT lat,lng,filename FROM images where created_at >= DATE_SUB(NOW(), INTERVAL 5 MINUTE);'
            cursor.execute(sql)
            rows = cursor.fetchall()      

    finally:
        connection.close()

    # Render the map HTML file and pass the location data as a list of rows
    return jsonify(rows)

if __name__ == '__main__':
    app.run(debug=True)
