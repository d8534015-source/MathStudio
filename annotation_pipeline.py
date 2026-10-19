"""Bounded optimistic board operations; worker code never owns a Tk object."""
from collections import deque
import queue
import threading


def apply(board, operation):
    shapes=[] if operation['clear'] else [s for s in board.get('shapes',[]) if s['id'] not in operation['remove']]
    present={s['id'] for s in shapes}
    shapes.extend(s for s in operation['add'] if s['id'] not in present)
    return {**board,'shapes':shapes,**operation['properties']}


class BoardQueue:
    LIMIT=128

    def __init__(self,board,version,send,fetch):
        self.board=board;self.version=version;self.send=send;self.fetch=fetch
        self.pending=deque();self.results=queue.Queue(maxsize=1)
        self.busy=False;self.paused=False;self.error='';self.inflight=0

    def projected(self):
        board=self.board
        for operation in self.pending:board=apply(board,operation)
        return board

    def enqueue(self,before,after,clear=False):
        if clear:
            while len(self.pending)>self.inflight:self.pending.pop()
        elif len(self.pending)>=self.LIMIT:raise RuntimeError('Annotation queue full. Reconnect before continuing; pending ink is retained.')
        old={s['id'] for s in before.get('shapes',[])};new={s['id'] for s in after.get('shapes',[])}
        self.pending.append({'add':[s for s in after.get('shapes',[]) if s['id'] not in old],
                             'remove':old-new,'clear':clear,
                             'properties':{k:v for k,v in after.items() if k!='shapes' and v!=before.get(k)}})

    def observe(self,board,version):
        if not self.busy and version>=self.version:self.board=board;self.version=version
        self.paused=False

    def start(self):
        if self.busy or self.paused or not self.pending:return
        batch=list(self.pending);board=self.board;version=self.version
        send,fetch,results=self.send,self.fetch,self.results
        self.busy=True;self.inflight=len(batch)
        def work():
            current=board;expected=version
            try:
                for attempt in range(3):
                    candidate=current
                    for operation in batch:candidate=apply(candidate,operation)
                    try:
                        response=send(expected,candidate)
                        results.put((True,len(batch),candidate,int(response['version'])));return
                    except RuntimeError as error:
                        if attempt==2 or 'changed' not in str(error).lower():raise
                        state=fetch();current=state['board'];expected=int(state['version'])
            except Exception as error:results.put((False,str(error)))
        threading.Thread(target=work,daemon=True).start()

    def drain(self):
        try:result=self.results.get_nowait()
        except queue.Empty:return False
        self.busy=False;self.inflight=0
        if result[0]:
            _,count,self.board,self.version=result
            for _ in range(count):self.pending.popleft()
            self.error=''
        else:self.paused=True;self.error=result[1]
        return True
