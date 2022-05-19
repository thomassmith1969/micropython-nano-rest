import uasyncio as asyncio
import uerrno
import json
import os
import gc
import _thread

_MIME_TYPES = {
        ".txt"   : "text/plain",
        ".htm"   : "text/html",
        ".html"  : "text/html",
        ".css"   : "text/css",
        ".csv"   : "text/csv",
        ".js"    : "application/javascript",
        ".xml"   : "application/xml",
        ".xhtml" : "application/xhtml+xml",
        ".json"  : "application/json",
        ".zip"   : "application/zip",
        ".pdf"   : "application/pdf",
        ".ts"    : "application/typescript",
        ".woff"  : "font/woff",
        ".woff2" : "font/woff2",
        ".ttf"   : "font/ttf",
        ".otf"   : "font/otf",
        ".jpg"   : "image/jpeg",
        ".jpeg"  : "image/jpeg",
        ".png"   : "image/png",
        ".gif"   : "image/gif",
        ".svg"   : "image/svg+xml",
        ".ico"   : "image/x-icon"
    }

class ParameterizedPath:
    def __init__(self,pathSpec,func=None):
        self.func=func
        if '<' in pathSpec:
            if pathSpec.index('<')<1 or '>' not in pathSpec:
                raise Exception("Illegal parameterization")
        _lastSeg=pathSpec.endswith('>')
        segs = pathSpec.split("<");
        self._segments = []
        self._end_param=False
        self._parameter_names =[]
        self._segments.append(segs[0]);
        segs.remove(segs[0])
        for seg in segs:
            pair=seg.split('>')
            self._parameter_names.append(pair[0])
            if '/' in pair[0]:
                raise Exception("Illegal paramter specification")
            if len(pair) == 2:
                if pair[1] != "":
                    self._segments.append(pair[1])
            else:
                self._end_param=True
               
    def map_parameters(self,url):
        #print("searching for:{}".format(url))
        param_map={}
        if url.startswith(self._segments[0]):
            index = 0
            line=url[len(self._segments[0]):]
            param_size=len(self._parameter_names)    
            while index < param_size:
                if len(self._segments) > (index+1):
                    segment=self._segments[index+1];
                    if segment not in line:
                        return None
                    nexSegPos=line.index(segment);
                    param_map[self._parameter_names[index]]=line[:nexSegPos]
                    line=line[nexSegPos+len(segment):]
                else:
                    param_map[self._parameter_names[index]]=line
                    line=""
                index=index+1
                    
                
            if len(line)>0:
                return None
            return param_map
        else:
            return None
        

        

class HttpError(Exception):
    pass


class Request:
    url = ""
    method = ""
    headers = {}
    route = ""
    read = None
    write = None
    close = None
    version = "1.0"
    _current_params=None
    _response_code = "200"
    _response_headers = {}
    def __init__(self):
        self._response_headers ={}
        self._response_code: "200"
    def add_header(self,key,value):
        self._response_headers[key]=value
    def get_headers(self):
        return self._response_headers
    def set_return_code(self,code):
        self._response_code=code
    def get_return_code(self):
        return self._response_code
    def send_json(self,obj):
        send_json(self,obj)
    def send_file(self,filename, content_type=None, segment=4096, binary=False):
        send_file(self,filename, content_type=content_type, segment=segment, binary=binary)


async def write(request, data):
    await request.write(
        data.encode('ISO-8859-1') if type(data) == str else data
    )


async def error(request, code, reason):
    await request.write("HTTP/1.1 %s %s\r\n\r\n" % (code, reason))
    await request.write("<h1>%s</h1>" % (reason))

async def send_headers(request):
    #print("sending headers")
    """Compose and send:
    - HTTP request line
    - HTTP headers following by \r\n.
    This function is generator.

    P.S.
    Because of usually we have only a few HTTP headers (2-5) it doesn't make sense
    to send them separately - sometimes it could increase latency.
    So combining headers together and send them as single "packet".
    """
    # Request line
    hdrs = 'HTTP/{} {} MSG\r\n'.format(request.version, request.get_return_code())
    # Headers
    for k, v in request._response_headers.items():
        hdrs += '{}: {}\r\n'.format(k, v)
    hdrs += '\r\n'
    # Collect garbage after small mallocs
    gc.collect()
    #print("sending headers as:{}".format(hdrs))
    await request.write(hdrs)

async def send_json(request, val):
    filename="tmp-{}.json".format(_thread.get_ident())
    with open(filename, 'w') as jsonfile:
        json.dump(val, jsonfile)
    await send_file(request, filename)


async def send_file(request, filename, content_type=None, segment=4096, binary=False):
    try:
        stat = os.stat(filename)
        slen = str(stat[6])
        request.add_header('Content-Length', slen)
        # Find content type
        if content_type:
            add_header('Content-Type', content_type)
        elif "." in filename:
            ending=filename[filename.rfind("."):]
            if ending in _MIME_TYPES:
                request.add_header('Content-Type', _MIME_TYPES[ending])
        #print("send file is about to send header")
        await send_headers(request)
        with open(filename, 'rb' if binary else 'r') as f:
            while True:
                data = f.read(segment)
                if not data:
                    break
                await request.write(data)
    except OSError as e:
        if e.args[0] != uerrno.ENOENT:
            raise
        raise HttpError(request, 404, "File Not Found")


class Nanoweb:

    extract_headers = ('Authorization', 'Content-Length', 'Content-Type')
    headers = {}

    parameterized_routes = []
    assets_extensions = ('html', 'css', 'js')

    callback_request = None
    callback_error = staticmethod(error)

    STATIC_DIR = './'
    INDEX_FILE = STATIC_DIR + 'index.html'

    def __init__(self, port=80, address='0.0.0.0'):
        self.port = port
        self.address = address

    def route(self, route):
        """Route decorator"""
        def decorator(func):
            self.parameterized_routes.append(ParameterizedPath(route,func))
            return func
        return decorator

    async def generate_output(self, request, handler,params=None):
        #print("generating output")
        request._current_params = params
        """Generate output from handler

        `handler` can be :
         * dict representing the template context
         * string, considered as a path to a file
         * tuple where the first item is filename and the second
           is the template context
         * callable, the output of which is sent to the client
        """
        while True:
            if isinstance(handler, dict):
                handler = (request.url, handler)

            if isinstance(handler, str):
                await write(request, "HTTP/1.1 200 OK\r\n\r\n")
                await send_file(request, handler)
            elif isinstance(handler, tuple):
                await write(request, "HTTP/1.1 200 OK\r\n\r\n")
                filename, context = handler
                context = context() if callable(context) else context
                try:
                    with open(filename, "r") as f:
                        for l in f:
                            await write(request, l.format(**context))
                except OSError as e:
                    print("caught:{}".format(e))
                    if e.args[0] != uerrno.ENOENT:
                        raise
                    raise HttpError(request, 404, "File Not Found")
            else:
                #print("handling else current params:{}".format(request._current_params))
                if params != None:
                    #print("using params:{}".format(json.dumps(params)))
                    handler = await handler(request,**params)
                else:
                    handler = await handler(request)
                if handler:
                    # handler can returns data that can be fed back
                    # to the input of the function
                    continue
            break

    async def handle(self, reader, writer):
        items = await reader.readline()
        items = items.decode('ascii').split()
        if len(items) != 3:
            return

        request = Request()
        request.read = reader.read
        request.write = writer.awrite
        request.close = writer.aclose

        request.method, request.url, version = items

        try:
            try:
                if version not in ("HTTP/1.0", "HTTP/1.1"):
                    raise HttpError(request, 505, "Version Not Supported")

                while True:
                    items = await reader.readline()
                    items = items.decode('ascii').split(":", 1)

                    if len(items) == 2:
                        header, value = items
                        value = value.strip()

                        if header in self.extract_headers:
                            request.headers[header] = value
                    elif len(items) == 1:
                        break

                if self.callback_request:
                    self.callback_request(request)
                params=None
                index=0
                handler=None
                while handler == None and index<len(self.parameterized_routes):
                    route=self.parameterized_routes[index]
                    index=index+1
                    #print("checking route:{}".format(json.dumps(route)))
                    params=route.map_parameters(request.url)
                    if params != None:
                        handler=route.func
                        #print("got handler:{}".format(handler))
                        break

                if handler != None:
                    #print("handler:{}".format(handler))
                    await self.generate_output(request,
                                               handler,params)
                else:
                    raise HttpError(request, 404, "File Not Found")
            except HttpError as e:
                print("caught error:{}".format(e))
                request, code, message = e.args
                await self.callback_error(request, code, message)
        except OSError as e:
            # Skip ECONNRESET error (client abort request)
            if e.args[0] != uerrno.ECONNRESET:
                raise
        finally:
            await writer.aclose()

    async def run(self):
        return await asyncio.start_server(self.handle, self.address, self.port)

