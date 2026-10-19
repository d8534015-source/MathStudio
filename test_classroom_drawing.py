"""Native annotation regressions using the actual extracted handlers."""
import unittest
import threading
from unittest import mock
from annotation_pipeline import BoardQueue
from types import SimpleNamespace,MethodType
from test_teaching_workflows import extracted_functions


class ModeTests(unittest.TestCase):
    def controller(self):
        calls=[]
        ns=extracted_functions('teacher_meeting_app.py',{'set_mode','set_clickthrough','pointer_up'}, {})
        obj=SimpleNamespace(draw_mode=True,draft={'type':'pen','points':[[0,0],[1,1]]},overlay=True,canvas=None,
            toolbar=SimpleNamespace(lift=lambda:calls.append('lift')),status_var=SimpleNamespace(set=lambda text:None),
            release_pointer=lambda:calls.append('release'),commit_shape=lambda shape:(calls.append(shape) or True),redraw=lambda:None,
            refresh_button_states=lambda:None,_show_input_capture=lambda mode:calls.append(mode),
            apply_overlay_transparency=lambda:(_ for _ in ()).throw(AssertionError('Reentrant idle/style flush')))
        for name in ('set_mode','set_clickthrough','pointer_up'):setattr(obj,name,MethodType(ns[name],obj))
        return obj,calls

    def test_active_stroke_is_completed_once_and_capture_released_without_idle_flush(self):
        obj,calls=self.controller()
        for _ in range(1000):obj.set_mode(False);obj.set_mode(True)
        self.assertIsNone(obj.draft)
        self.assertEqual(sum(isinstance(x,dict) for x in calls),1)
        self.assertIn('release',calls);self.assertTrue(obj.draw_mode)

    def test_disconnected_switch_never_waits_for_network_or_rebinds_input(self):
        obj,calls=self.controller();obj.connected=False
        obj.commit_shape=lambda shape:(calls.append('queued-offline') or True)
        obj.set_mode(False);obj.set_mode(False)
        self.assertEqual(calls.count('queued-offline'),1);self.assertFalse(obj.draw_mode)


class PipelineTests(unittest.TestCase):
    def test_rapid_pen_splits_at_protocol_limit_without_dropping_samples_or_endpoint(self):
        import math,copy
        samples=[];committed=[]
        canvas=SimpleNamespace(winfo_width=lambda:1920,winfo_height=lambda:1080,create_line=lambda *a,**kw:None)
        obj=SimpleNamespace(draw_mode=True,draft={'type':'pen','points':[[0,0]],'color':'#f00','width':4},canvas=canvas,input_canvas=canvas,
            new_shape=lambda kind:{'type':kind,'color':'#f00','width':4},
            commit_shape=lambda shape:(committed.append(copy.deepcopy(shape)) or True),release_pointer=lambda:None,redraw=lambda:None)
        ns=extracted_functions('teacher_meeting_app.py',{'pointer_move','pointer_up','normalized'},{'math':math})
        for name in ('pointer_move','pointer_up','normalized'):setattr(obj,name,MethodType(ns[name],obj))
        for i in range(20000):
            event=SimpleNamespace(widget=canvas,x=i%1919,y=500+100*math.sin(i/12));samples.append(list(obj.normalized(event)));obj.pointer_move(event)
        obj.pointer_up(event)
        restored=[]
        for shape in committed:
            self.assertLessEqual(len(shape['points']),1500)
            for point in shape['points']:
                if not restored or restored[-1]!=point:restored.append(point)
        self.assertEqual(restored,[[0,0],*samples]);self.assertIsNone(obj.draft)

    def test_network_delay_does_not_block_local_projection_and_queue_is_bounded(self):
        gate=threading.Event();calls=[]
        def send(version,board):gate.wait(2);calls.append(board);return {'version':version+1}
        sync=BoardQueue({'shapes':[]},0,send,lambda:None)
        try:
            for i in range(128):
                before=sync.projected();sync.enqueue(before,{'shapes':[*before['shapes'],{'id':str(i)}]});sync.start()
            self.assertEqual(len(sync.projected()['shapes']),128)
            with self.assertRaises(RuntimeError):sync.enqueue(sync.projected(),{'shapes':[]})
            sync.enqueue(sync.projected(),{'shapes':[]},clear=True)
            self.assertEqual(sync.projected()['shapes'],[])
            self.assertLessEqual(len(sync.pending),129)
        finally:gate.set()

    def test_failure_retains_endpoint_and_reconnect_retries_without_duplicates(self):
        fail=[True]
        def send(version,board):
            if fail[0]:raise RuntimeError('disconnected')
            return {'version':version+1}
        sync=BoardQueue({'shapes':[]},0,send,lambda:None)
        shape={'id':'stroke','points':[[0,0],[1,1]]}
        sync.enqueue(sync.board,{'shapes':[shape]})
        with mock.patch('annotation_pipeline.threading.Thread',lambda target,**kw:SimpleNamespace(start=target)):
            sync.start();sync.drain()
            self.assertEqual(sync.projected()['shapes'][0]['points'][-1],[1,1]);self.assertTrue(sync.paused)
            fail[0]=False;sync.observe({'shapes':[{'id':'remote'}]},1);sync.start();sync.drain()
        self.assertEqual([x['id'] for x in sync.projected()['shapes']],['remote','stroke']);self.assertFalse(sync.pending)


class ReviewProfileTests(unittest.TestCase):
    def test_frozen_profile_is_distinct_from_production_and_pr9(self):
        import runtime_paths,tempfile,json
        from pathlib import Path
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'teacher_package_role.json').write_text(json.dumps({'review':True,'review_profile':'MathStudioClassroomReview'}))
            with mock.patch.object(runtime_paths,'__file__',str(root/'runtime_paths.py')),mock.patch('sys.frozen',True,create=True),mock.patch.dict('os.environ',{'LOCALAPPDATA':directory}):
                self.assertEqual(runtime_paths.state_directory(),root/'MathStudioClassroomReview')


class DispatchTests(unittest.TestCase):
    def test_worker_never_schedules_tk_and_completion_runs_on_main_thread(self):
        import queue
        ns=extracted_functions('teacher_meeting_app.py',{'post_ui','drain_ui'},{'queue':queue})
        main=threading.get_ident();seen=[]
        obj=SimpleNamespace(ui_stopped=threading.Event(),ui_queue=queue.Queue(maxsize=64),closed=False,
                            root=SimpleNamespace(after=lambda delay,cb:seen.append(('after',threading.get_ident()))))
        obj.post_ui=MethodType(ns['post_ui'],obj);obj.drain_ui=MethodType(ns['drain_ui'],obj)
        worker=threading.Thread(target=lambda:obj.post_ui(lambda:seen.append(('done',threading.get_ident()))));worker.start();worker.join(1)
        self.assertEqual(seen,[]);obj.drain_ui();self.assertEqual(seen,[('done',main),('after',main)])


if __name__=='__main__':unittest.main()
