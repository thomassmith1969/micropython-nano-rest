# Nanorest

Nanorest is an is a full asynchronous web server for micropython created in order to benefit from minimal implementation of powerful features.

It is thus able to run on an most Micropython platforms, including the ESP8266.

(*heavily based upon the Nanoweb micro webserver implementation by https://github.com/hugokernel)
## Features fron nanoweb

* Completely asynchronous
* Callbacks functions when a new query or an error occurs
* Extraction of HTML headers
* User code dense and concise
* output helper methods (e.g. send_file,send_json)


## NEW Features
* Rest mapping to include automatic JSON parsing and sending
* Parameterized Routes ( i.e. '/api/v1/servo/<pin>/move' or '/api/v2/rigging/
* _WEB SOCKETS_  Special thanks go out to https://github.com/marcidy .   Thanks to a minor fork to his asyncio websocket example, we now have websocket support

<puppet_number>/<subsystem>' )
* JSON element in requests that send json (i.e.  request.json )

## Design considerations
* async processing sometimes collides with irq functions such as PWM



## Use

```Python

import uasyncio
from nanorest import Nanorest,send_headers,send_file,send_json,write
import machine
from machine import PWM,Pin
import time
import _thread


request_queue=[]
websockets=[]

#servo range 18-115
def set_servo2(zero_to_hundred):
    request_queue.append({"method":"_internal_set_servo","params":[zero_to_hundred]})
    print("queued")
##    _internal_set_servo(zero_to_hundred)

#def _internal_set_servo(zero_to_hundred):
def set_servo(zero_to_hundred):
    print("setting value to:{}".format(zero_to_hundred))
    if int(zero_to_hundred) <0 or int(zero_to_hundred)>100:
        yield
    else:
        duty=38+int(97*int(zero_to_hundred)/100)
        print("duty:{}".format(duty))
        servo1= PWM(Pin(15,Pin.OUT),freq=50,duty=duty)
        uasyncio.sleep_ms(100);
        servo1.deinit()
        uasyncio.sleep_ms(100);
    return
#    time.sleep(0.1)
#    servo1.deinit()

naw = Nanorest()
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
known_sockets=[]
@naw.socket("/socket")
async def socket(ws,path):
    known_sockets.append(ws)
    print("Connection on {}".format(path))
    try:
        async for msg in ws:
            print(msg)
            for sender in known_sockets:
                await sender.send(msg)
    finally:
        print("Disconnected")

    
gimbal_data={"x":90,"y":90}

@naw.route("/gimbal/<x>/<y>")
def gimbal_route(request,x,y):
    gimbal_data["x"]=x
    gimbal_data["y"]=y
    await set_servo(x)
    await send_json(request,gimbal_data)
@naw.route("/gimbal")
def gimbal(request):
    print("Setting gimbal")
    print("json data:{}".format(request.json))
    if request.json: #only sent on post requests
        if 'x' in request.json:
            gimbal_data["x"]=request.json['x']
            await set_servo(request.json['x'])
        if 'y' in request.json:
            gimbal_data["y"]=request.json['y']   
    await send_json(request,gimbal_data)
    await request.close();
# Declare route from a dict
# Declare route directly with decorator
@naw.route("/ping")
def ping(request):
    await request.write("HTTP/1.1 200 OK\r\n\r\n")
    await request.write("pong")


loop = uasyncio.get_event_loop()
loop.create_task(naw.run())
loop.run_forever()


```
