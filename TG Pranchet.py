python -m pip install --upgrade pip wheel setuptools virtualenv

python -m pip install docutils pygments pypiwin32 kivy_deps.sdl2==0.1.22 kivy_deps.glew==0.1.12
python -m pip install kivy_deps.gstreamer==0.1.17

python -m pip install kivy==1.11.1

# -*- coding: utf-8 -*-

import kivy
from kivy.app import App
from kivy.uix.label import Label
from kivy.uix.boxlayout import BoxLayout

from kivy.uix.button import Button

kivy.require('1.9.1')

var = 0
def soma_um(instance):
    global var
    var += 1
    instance.text = str(var)    
    
class MeuApp(App):
    def build(self):
        layout = BoxLayout(orientation='vertical',
                padding=[40, 20, 40, 20])
        
        layout.add_widget(Label(text='Olá do Lopes!'))
        btn = Button(text='Continuar', size=(100,50))
        
        btn.bind(on_press=soma_um)
        layout.add_widget(btn)
        return layout 
    
if __name__ == '__main__':
    TGPrancheta().run()

title=TG Prancheta
author=Lopes
orientation=portrait

#Arquivo de configuração do aplicativo
################################
#Chave secreta que será usada pelo Flask para assinar com segurança o cookie da sessão
#e pode ser usado para outras necessidades relacionadas à segurança
SECRET_KEY = 'SECRET_KEY'
#######################################
#Número mínimo de tarefas para gerar
MIN_NBR_TASKS = 1
#Número máximo de tarefas para gerar
MAX_NBR_TASKS = 100
#Tempo de espera ao produzir tarefas
WAIT_TIME = 1
#Mapeamento de endpoint de webhook para quem verifica
WEBHOOK_RECEIVER_URL = 'http://localhost:5001/consumetasks'
#######################################
#Mapa para a porta do servidor REDIS
BROKER_URL = 'redis://localhost:6379'
#######################################

# init_producer.py
from flask import Flask

#Cria uma instância do Flask
app = Flask(__name__)

#Carrega configurações do Flask pelo config.py
app.secret_key = app.config['SECRET_KEY']
app.config.from_object("config")

# tasks_producer.py
import random
from faker.providers import BaseProvider
from faker import Faker
import config
import time
import requests
import json
import uuid

# Define a TaskProvider
class TaskProvider(BaseProvider):
    def task_priority(self):
        severity_levels = [
            'Low', 'Moderate', 'Major', 'Critical'
        ]
        return severity_levels[random.randint(0, len(severity_levels)-1)]


# Cria uma instância do Faker e semeia para ter os mesmos resultados toda vez que executarmos o script
# Retorna dados em Portugues
fakeTasks = Faker('pt_BR')
# Semeia a instância do Faker para ter os mesmos resultados toda vez que executamos o programa
fakeTasks.seed_instance(0)
# Atribue o TaskProvider à instância do Faker
fakeTasks.add_provider(TaskProvider)

# Gera uma tarefa falsa
def produce_task(batchid, taskid):
    # Message composition
    message = {
        'batchid': batchid, 'id': taskid, 'owner': fakeTasks.unique.name(), 'priority': fakeTasks.task_priority()
        # ,'raised_date':fakeTasks.date_time_this_year()
        # ,'description':fakeTasks.text()
    }
    return message


def send_webhook(msg):
    """
    Send a webhook to a specified URL
    :param msg: task details
    :return:
    """
    try:
        # Postar uma mensagem de webhook
        # padrão é uma função aplicada a objetos que não são serializáveis ​​= converte-os em str
        resp = requests.post(config.WEBHOOK_RECEIVER_URL, data=json.dumps(
            msg, sort_keys=True, default=str), headers={'Content-Type': 'application/json'}, timeout=1.0)
        # Retorna um HTTPError se um erro ocorreu durante o processo (usado para depuração).
        resp.raise_for_status()
    except requests.exceptions.HTTPError as err:
        #print("An HTTP Error occurred",repr(err))
        pass
    except requests.exceptions.ConnectionError as err:
        #print("An Error Connecting to the API occurred", repr(err))
        pass
    except requests.exceptions.Timeout as err:
        #print("A Timeout Error occurred", repr(err))
        pass
    except requests.exceptions.RequestException as err:
        #print("An Unknown Error occurred", repr(err))
        pass
    except:
        pass
    else:
        return resp.status_code

# Gera um monte de tarefas falsas
def produce_bunch_tasks():
    """
    Gera um monte de tarefas falsas
    """
    n = random.randint(config.MIN_NBR_TASKS, config.MAX_NBR_TASKS)
    batchid = str(uuid.uuid4())
    for i in range(n):
        msg = produce_task(batchid, i)
        resp = send_webhook(msg)
        time.sleep(config.WAIT_TIME)
        print(i, "out of ", n, " -- Status", resp, " -- Message = ", msg)
        yield resp, n, msg


if __name__ == "__main__":
    for resp, total, msg in produce_bunch_tasks():
        pass

#app_producer.py
from flask import Response, render_template
from init_producer import app
import tasks_producer

def stream_template(template_name, **context):
    app.update_template_context(context)
    t = app.jinja_env.get_template(template_name)
    rv = t.stream(context)
    rv.enable_buffering(5)
    return rv

@app.route("/", methods=['GET'])
def index():
    return render_template('producer.html')

@app.route('/producetasks', methods=['POST'])
def producetasks():
    print("producetasks")
    return Response(stream_template('producer.html', data= tasks_producer.produce_bunch_tasks() ))

if __name__ == "__main__":
   app.run(host="localhost",port=5000, debug=True)

<!doctype html>
<html>
  <head>
    <title>Tasks Producer</title>
    <style>
      .content {
        width: 100%;
      }
      .container{
        max-width: none;
      }
    </style>
    <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  </head>
<body class="container">
    <div class="content">
      <form method='post' id="produceTasksForm" action = "/producetasks">
        <button style="height:20%x;width:100%" type="submit" id="produceTasks">Produce Tasks</button>
      </form>
    </div>
    <div class="content">
        <div id="Messages" class="content" style="height:400px;width:100%; border:2px solid gray; overflow-y:scroll;"></div>
        {% for rsp,total, msg in data: %}
         <script>
            var rsp   = "{{ rsp }}";
            var total = "{{ total }}";
            var msg   = "{{ msg }}";
            var lineidx = "{{ loop.index }}";
            //If the webhook request succeeds color it in blue else in red.
            if (rsp == '200') {
                rsp = rsp.fontcolor("blue");
            }
            else {
                rsp = rsp.fontcolor("red");
            }
            //Add the details of the generated task to the Messages section.
            document.getElementById('Messages').innerHTML += "<br>" + lineidx  + " out of " + total + " -- "+ rsp + " -- " + msg;
        </script>
        {% endfor %}
    </div>
</body>
</html>

# init_consumer.py
from flask import Flask

#Cria uma instância do Flask
app = Flask(__name__)

#Carrega configurações do Flask pelo config.py
app.secret_key = app.config['SECRET_KEY']
app.config.from_object("config")

#Configura a integração do Flask SocketIO ao mapear o servidor Redis.
from flask_socketio import SocketIO
socketio = SocketIO(app,logger=True,engineio_logger=True,message_queue=app.config['BROKER_URL'])

#app_consumer.py
from flask import render_template, request,session
from flask_socketio import join_room
from init_consumer import app, socketio
import json
import uuid

#Renderiza o arquivo de modelo atribuído
@app.route("/", methods=['GET'])
def index():
    return render_template('consumer.html')

# Enviando mensagem pelo websocket
def send_message(event, namespace, room, message):
    # print("Message = ", message)
    socketio.emit(event, message, namespace=namespace, room=room)

# Registra uma função a ser executada antes da primeira solicitação para esta instância do aplicativo
# Cria um ID de sessão exclusivo e armazena-o no arquivo de configuração do aplicativo
@app.before_first_request
def initialize_params():
    if not hasattr(app.config,'uid'):
        sid = str(uuid.uuid4())
        app.config['uid'] = sid
        print("initialize_params - Session ID stored =", sid)

# Recebe os webhooks e emite eventos de websocket
@app.route('/consumetasks', methods=['POST'])
def consumetasks():
    if request.method == 'POST':
        data = request.json
        if data:
           print("Received Data = ", data)
           roomid =  app.config['uid']
           var = json.dumps(data)
           send_message(event='msg', namespace='/collectHooks', room=roomid, message=var)
    return 'OK'

#Executar ao conectar
@socketio.on('connect', namespace='/collectHooks')
def socket_connect():
    # Exibir mensagem ao se conectar do namespace
    print('Client Connected To NameSpace /collectHooks - ', request.sid)

#Executar ao desconectar
@socketio.on('disconnect', namespace='/collectHooks')
def socket_connect():
    # Exibir mensagem ao se desconectar do namespace
    print('Client disconnected From NameSpace /collectHooks - ', request.sid)

#Executar ao entrar em uma sala específica
@socketio.on('join_room', namespace='/collectHooks')
def on_room():
    if app.config['uid']:
        room = str(app.config['uid'])
        # Exibir mensagem ao entrar em uma sala específica para a sessão armazenada anteriormente.
        print(f"Socket joining room {room}")
        join_room(room)

#Executar ao encontrar qualquer erro relacionado ao websocket
@socketio.on_error_default
def error_handler(e):
    # Display message on error.
    print(f"socket error: {e}, {str(request.event)}")

#Rodar port 5001
if __name__ == "__main__":
    socketio.run(app,host='localhost', port=5001,debug=True)

<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Tasks Consumer</title>
    <link rel="stylesheet" href="{{url_for('static',filename='css/bootstrap.min.css')}}">
    <link rel="stylesheet" href="{{url_for('static',filename='css/Chart.min.css')}}">
</head>
<body>
    <div class="content">
        <div id="Messages" class="content" style="height:200px;width:100%; border:1px solid gray; overflow-y:scroll;"></div>
    </div>
    <div class="container">
        <div class="row">
            <div class="col-12">
                <div class="card">
                    <div class="card-body">
                        <canvas id="canvas"></canvas>
                    </div>
                </div>
            </div>
        </div>
    </div>
    <!-- import the jquery library -->
    <script src="{{ url_for('static',filename='js/jquery.min.js') }}"></script>
    <!-- import the socket.io library -->
    <script src="{{ url_for('static',filename='js/socket.io.js') }}"></script>
    <!-- import the bootstrap library -->
    <script src="{{ url_for('static',filename='js/bootstrap.min.js') }}"></script>
    <!-- import the Chart library -->
    <script src="{{ url_for('static',filename='js/Chart.min.js') }}"></script>
<script>
      $(document).ready(function(){
        const config = {
            //Type of the chart - Bar Chart
            type: 'bar',
            //Data for our chart
            data: {
                labels: ['Low','Moderate','Major','Critical'],
                datasets: [{
                    label: "Count Of Tasks",
                    //Setting a color for each bar
                    backgroundColor: ['green','blue','yellow','red'],
                    borderColor: 'rgb(255, 99, 132)',
                    data: [0,0,0,0],
                    fill: false,
                }],
            },
            //Configuration options
            options: {
                responsive: true,
                title: {
                    display: true,
                    text: 'Tasks Priority Matrix'
                },
                tooltips: {
                    mode: 'index',
                    intersect: false,
                },
                hover: {
                    mode: 'nearest',
                    intersect: true
                },
                scales: {
                    xAxes: [{
                        display: true,
                        scaleLabel: {
                            display: true,
                            labelString: 'Priority'
                        }
                    }],
                    yAxes: [{
                        display: true
                     ,ticks: {
                            beginAtZero: true
                        }
                       ,scaleLabel: {
                            display: true,
                            labelString: 'Total'
                        }
                    }]
                }
            }
        };
        const context = document.getElementById('canvas').getContext('2d');
        //Creating the bar chart
        const lineChart = new Chart(context, config);
        //Reserved for websocket manipulation
        var namespace='/collectHooks';
        var url = 'http://' + document.domain + ':' + location.port + namespace;
        var socket = io.connect(url);
        //When connecting to the socket join the room
        socket.on('connect', function() {
                              socket.emit('join_room');
                            });
        //When receiving a message
        socket.on('msg' , function(data) {
                            var msg = JSON.parse(data);
                            var newLine = $('<li>'+ 'Batch ID. = ' + msg.batchid + ' -- Task ID. = ' + msg.id + ' -- Owner = ' + msg.owner + ' -- Priority = ' + msg.priority +'</li>');
                            newLine.css("color","blue");
                            $("#Messages").append(newLine);
                            //Retrieve the index of the priority of the received message
                            var lindex = config.data.labels.indexOf(msg.priority);
                            //Increment the value of the priority of the received message
                            config.data.datasets[0].data[lindex] += 1;
                            //Update the chart
                            lineChart.update();
                          });
      });
</script>
</body>
</html>

import mysql.connector as mysql
from tabulate import tabulate

# insere as informações do banco de dados MySQL
HOST = "localhost"
DATABASE = ""
USER = "root"
PASSWORD = ""

# conecta ao banco de dados
db_connection = mysql.connect(host=HOST, database=DATABASE, user=USER, password=PASSWORD)
# get server information
print(db_connection.get_server_info())

5.5.5-10.1.32-EtamusDB

# usa o cursor db
cursor = db_connection.cursor()
# usa informações do banco de dados
cursor.execute("select database();")
database_name = cursor.fetchone()
print("[+] You are connected to the database:", database_name)

# cria um novo banco de dados chamado biblioteca
cursor.execute("create database if not exists library")

# usa aquele banco de dados
cursor.execute("use library")
print("[+] Changed to `library` database")# create a table
cursor.execute("""create table if not exists book (
    `id` integer primary key auto_increment not null,
    `name` varchar(255) not null,
    `author` varchar(255) not null,
    `price` float not null,
    `url` varchar(255)
    )""")
print("[+] Table `book` created")

5.5.5-10.1.32-MariaDB

# usa o cursor db
cursor = db_connection.cursor()
# usa informações do banco de dados
cursor.execute("select database();")
database_name = cursor.fetchone()
print("[+] You are connected to the database:", database_name)

[+] You are connected to the database: (None,)

# usa informações do banco de dados
cursor.execute("create database if not exists library")

# usa aquele banco de dados
cursor.execute("use library")
print("[+] Changed to `library` database")

# cria uma table
cursor.execute("""create table if not exists book (
    `id` integer primary key auto_increment not null,
    `name` varchar(255) not null,
    `author` varchar(255) not null,
    `price` float not null,
    `url` varchar(255)
    )""")
print("[+] Table `book` created")

# interage com a lista de books
for book in books:
    id = book.get("id")
    name = book.get("name")
    author = book.get("author")
    price = book.get("price")
    url = book.get("url")
    # insert each book as a row in MySQL
    cursor.execute("""insert into book (id, name, author, price, url) values (
        %s, %s, %s, %s, %s
    )
    """, params=(id, name, author, price, url))
    print(f"[+] Inserted the book: {name}")
[+] Inserted the book: Automate the Boring Stuff with Python: Practical Programming for Total Beginners
[+] Inserted the book: Python Crash Course: A Hands-On, Project-Based Introduction to Programming
[+] Inserted the book: MySQL for Python

# inserção de commit
db_connection.commit()

# busca o banco de dados
cursor.execute("select * from book")
# get all selected rows
rows = cursor.fetchall()
# print all rows in a tabular format
print(tabulate(rows, headers=cursor.column_names))

# fecha o cursor
cursor.close()
# close the DB connection
db_connection.close()

creation_date: [datetime.datetime(2012, 9, 15, 0, 0), '15 Sep 2012 20:41:00']
domain_name: ['GLIDEAPP.COM', 'glideapp.com']
...
...
updated_date: 2013-08-20 00:00:00
whois_server: whois.enom.com

>>> w.expiration_date 

import whois

data = raw_input("Enter a domain: ")
w = whois.whois(data)

print w

[bug_tracker]
url = http://localhost:8080/bugs/
username = dhellmann
password = SECRET

#Importa os modulos
import os
import ConfigParser
import time

# /etc/mysql/debian.cnf contains 'root' como um login e senha
config = ConfigParser.ConfigParser()
config.read("/etc/mysql/debian.cnf")
username = config.get('client', 'user')
password = config.get('client', 'password')
hostname = config.get('client', 'host')
filestamp = time.strftime('%Y-%m-%d')

# Obtem uma lista de bancos de dados com :
database_list_command="mysql -u %s -p%s -h %s --silent -N -e 'show databases'" % (username, password, hostname)
for database in os.popen(database_list_command).readlines():
    database = database.strip()
    if database == 'information_schema':
        continue
    if database == 'performance_schema':
        continue
    filename = "/backups/mysql/%s-%s.sql" % (database, filestamp)
    os.popen("mysqldump --single-transaction -u %s -p%s -h %s -d %s | gzip -c > %s.gz" % (username, password, hostname, database, filename))

#!/usr/bin/env python

#obtem o nome de usuário em um prompt
username = raw_input("Login: >> ")

#lista de usuários permitidos
user1 = "Jack"
user2 = "Jill"

#controla se o usuário pertence à lista de usuários permitidos
if username == user1:
    print "Access granted"
elif username == user2:
    print "Welcome to the system"
else:
    print "Access denied"
In this example, I will use the /var/log/syslog file. 

The for loop will go through each line of the log file and the line_split variablewill split it by lines. 

If you just print the line_split, you will see an output similar to this:

>> ['Sep', '27', '15:22:15', 'Virtualbox', 'NetworkManager[710]:', '', 'DNS:'..']

If you want to print each element just add the line_split[element_to_show]

You are here: Home / Code Snippets / Log Checker in Python
Log Checker in Python
Author: PFB Staff Writer
Last Updated: June 04, 2021

Show all entries in a logfile

>> ['Sep', '27', '15:22:15', 'Virtualbox', 'NetworkManager[710]:', '', 'DNS:'..']

If you want to print each element just add the line_split[element_to_show]
#!/usr/bin/env python
logfile = open("/var/log/syslog", "r")
for line in logfile:
    line_split = line.split()
    print line_split
    list = line_split[0], line_split[1], line_split[2], line_split[4]
    print list

import urllib2
import re

#connect to a URL
website = urllib2.urlopen(url)

#read html code
html = website.read()

#use re.findall to get all the links
links = re.findall('"((http|ftp)s?://.*?)"', html)

print links

# Python Program to Calculate Sum of Even Numbers from 1 to 100

minimum = int(input(" Please Enter the Minimum Value : "))
maximum = int(input(" Please Enter the Maximum Value : "))
total = 0

for number in range(minimum, maximum+1):
    if(number % 2 == 0):
        print("{0}".format(number))
        total = total + number

print("The Sum of Even Numbers from {0} to {1} = {2}".format(minimum, number, total))]

# Python Program to check character is Alphabet Digit or Special Character
ch = input("Please Enter Your Own Character : ")

if((ch >= 'a' and ch <= 'z') or (ch >= 'A' and ch <= 'Z')): 
    print("The Given Character ", ch, "is an Alphabet") 
elif(ch >= '0' and ch <= '9'):
    print("The Given Character ", ch, "is a Digit")
else:
    print("The Given Character ", ch, "is a Special Character")

# Python Program to Reverse String
string = input("Please enter your own String : ")

string2 = ''
i = len(string) - 1

while(i >= 0):
    string2 = string2 + string[i]
    i = i - 1
    
print("\nThe Original String = ", string)
print("The Reversed String = ", string2))
print("The Given String in Lowercase =  ", string1)

# Python Program to find a String Length

str1 = input("Please enter your own String : ")

print("Total Length of a Given String = ", len(str1))

# Create a Set

s1 = {2, 4, 6, 8, 10}
print(s1)
print(type(s1))

s2 = set(['USA', 'China', 'UK', 'Russia', 'India', 'France'])
print(s2)
print(type(s2))

s3 = set("Tutorial Gateway")
print(s3)
print(type(s3))

# Set Min Item

smtSet = set()

number = int(input("Enter the Total Set Items = "))
for i in range(1, number + 1):
    value = int(input("Enter the %d Set Item = " %i))
    smtSet.add(value)

print("Set Items = ", smtSet)

sortVals = sorted(smtSet)
print("Smallest Item in smtSet Set = ", sortVals[0])
print("Data Type of sortVals = ", type(sortVals))

# Set Negative Numbers

negativeSet = set()

number = int(input("Enter the Total Negative Set Items = "))
for i in range(1, number + 1):
    value = int(input("Enter the %d Set Item = " %i))
    negativeSet.add(value)

print("Negative Set Items = ", negativeSet)

print("\nThe Negative Numbers in this negativeSet Set are:")
for negaVal in negativeSet:
    if(negaVal < 0):
        print(negaVal, end = "  ")

# Python Program to calculate Sum of Series 1³+2³+3³+….+n³
import math 

number = int(input("Please Enter any Positive Number  : "))
total = 0

total = math.pow((number * (number + 1)) /2, 2)

for i in range(1, number + 1):
    if(i != number):
        print("%d^3 + " %i, end = ' ')
    else:
        print("{0}^3 = {1}".format(i, total))

