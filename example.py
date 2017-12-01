from flask import Flask
import client
from contextlib import contextmanager
import time

app = Flask(__name__)

def fib(n):
    if n < 1:
        return 0
    if n == 1:
        return 1
    return fib(n - 1) + fib(n - 2)

class Profiler:
    def __enter__(self):
        self.t1 = time.time()
        return self

    def __exit__(self, a, b, c):
        pass

    def get_duration(self):
        t2 = time.time()
        return "%.3f s" % (t2 - self.t1)

@app.route('/fib/nocache/<int:num>')
def fib_nocache(num):
    with Profiler() as p:
        return "%s %s" % (str(fib(num)), p.get_duration())

@app.route('/fib/cache/<int:num>')
def fib_cache(num):
    with Profiler() as p:
        with client.connection('localhost', 1234) as cache:
            try:
                result = cache.get(str(num))
            except:
                result = str(fib(num))
                cache.set(str(num), result)
            return "%s %s" % (result, p.get_duration())
