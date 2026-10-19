import ast,subprocess,math,time,json,statistics,sys
from pathlib import Path
from types import SimpleNamespace,MethodType
root=Path(__file__).resolve().parents[1]
source=subprocess.check_output(['git','show','d0580ff:teacher_meeting_app.py'],cwd=root,text=True) if '--baseline' in sys.argv else (root/'teacher_meeting_app.py').read_text(encoding='utf-8')
tree=ast.parse(source);cls=next(x for x in tree.body if isinstance(x,ast.ClassDef) and x.name=='TeacherMeetingApp')
ns={'math':math,'tk':SimpleNamespace(ROUND='round')}
exec(compile(ast.fix_missing_locations(ast.Module(body=[n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name in {'pointer_move','normalized','redraw','draw_shape'}],type_ignores=[])),'baseline','exec'),ns)
class Canvas:
 def __init__(self):self.commands=0;self.coordinates=0
 def winfo_width(self):return 1920
 def winfo_height(self):return 1080
 def delete(self,*args):self.commands+=1
 def create_line(self,*coords,**kwargs):self.commands+=1;self.coordinates+=len(coords)
canvas=Canvas();obj=SimpleNamespace(canvas=canvas,input_canvas=canvas,toolbar=SimpleNamespace(lift=lambda:None),draw_mode=True,ink_visible=True,board={'shapes':[{'type':'pen','points':[[i/100,i/100] for i in range(64)],'color':'#f00','width':4} for _ in range(100)]},draft={'type':'pen','points':[[0,0]],'color':'#f00','width':4})
for name in ('pointer_move','normalized','redraw','draw_shape'):setattr(obj,name,MethodType(ns[name],obj))
times=[]
for i in range(1200):
 e=SimpleNamespace(widget=canvas,x=i%1900,y=300+100*math.sin(i/12));t=time.perf_counter();obj.pointer_move(e);times.append((time.perf_counter()-t)*1000)
print(json.dumps({'samples':len(times),'handler_ms_p50':statistics.median(times),'handler_ms_p95':sorted(times)[int(.95*len(times))],'canvas_commands':canvas.commands,'coordinate_values_submitted':canvas.coordinates,'stored_points':len(obj.draft['points']),'scope':'Python/Canvas-command workload, not physical input-to-photon latency'},indent=2))
