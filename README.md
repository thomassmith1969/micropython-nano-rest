# Nanorest

Nanorest is an is a full asynchronous web server for micropython created in order to benefit from minimal implementation of powerful features.

It is thus able to run on an most Micropython platforms, including the ESP8266.

(*heavily based upon the Nanoweb micro webserver implementation)
## Features fron nanoweb

* Completely asynchronous
* Callbacks functions when a new query or an error occurs
* Extraction of HTML headers
* User code dense and concise
* output helper methods (e.g. send_file,send_json)


## NEW Features
* Rest mapping to include automatic JSON parsing and stringification
* Parameterized Routes ( i.e. '/api/v1/servo/<pin>/move' )
* JSON element in requests that send json




## Use

```Python

import uasyncio
from nanoweb import Nanoweb,send_file,send_json

async def api_status(request):
    """API status endpoint"""
    await request.write("HTTP/1.1 200 OK\r\n")
    await request.write("Content-Type: application/json\r\n\r\n")
    await request.write('{"status": "running"}')

naw = Nanoweb()
@naw.route("/")
@naw.route("/index.html")
def get_index(request):
    await send_file(request,"a/index.html")
@naw.route("/main.28.js")
def get_main(request):
    await send_file(request,"a/main.28.js")
@naw.route("/polyfills.28.js")
def get_poly(request):
    await send_file(request,"a/polyfills.28.js")
@naw.route("/runtime.28.js")
def get_runtime(request):
    await send_file(request,"a/runtime.28.js")
@naw.route("/styles.28.css")
def get_style(request):
    await send_file(request,"a/styles.28.css")
@naw.route("/favicon.ico")
def get_favico(request):
    await send_file(request,"a/favicon.ico")
    
gimbal_data={"x":90,"y":90}

@naw.route("/gimbal/<x>/<y>")
def gimbal_route(request,x,y):
    gimbal_data["x"]=x
    gimbal_data["y"]=y
    await send_json(request,gimbal_data)
@naw.route("/gimbal")
def gimbal(request):
    print("json data:{}".format(request.json))
    if request.json: #only sent on post requests
        if 'x' in request.json:
            gimbal_data["x"]=request.json['x']
        if 'y' in request.json:
            gimbal_data["y"]=request.json['y']   
    await send_json(request,gimbal_data)
# Declare route from a dict
naw.routes = {
    '/api/status': api_status,
}

# Declare route directly with decorator
@naw.route("/ping")
def ping(request):
    await request.write("HTTP/1.1 200 OK\r\n\r\n")
    await request.write("pong")

loop = uasyncio.get_event_loop()
loop.create_task(naw.run())
loop.run_forever()
```
