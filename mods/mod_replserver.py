
from replserver.tcprepl import runReplServer, log

def init():
    log('{} {}'.format('${mod_id}', '${version}'))

    try:
        import threading
        thread = threading.Thread(target=runReplServer, args=())
        thread.setDaemon(True)
        log('thread started..')
        thread.start()
    except:
        import traceback
        traceback.print_exc()
