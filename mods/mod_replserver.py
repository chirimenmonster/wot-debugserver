
import datetime
from replserver import tcprepl

def log(text):
    ds = datetime.time.strftime(datetime.datetime.now().time(), '%H:%M')
    print 'replserver %s: %s' % (ds, text)

def run_server():
    log('run server...')
    try:
        while True:
            tcprepl.run_repl()
            log('REPL stopped, restarting...')
    except:
        log('* Crashed *')
        import traceback
        traceback.print_exc()
    log('Server stopped!')

def init():
    log('starting..')

    try:
        import threading
        thread = threading.Thread(target=run_server, args=())
        thread.setDaemon(True)
        thread.start()

        log('thread started..')
    except:
        import traceback
        traceback.print_exc()
