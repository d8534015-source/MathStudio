"""Teacher-only cloud recording library; network work never calls Tk."""
import copy
import queue
import threading
import tkinter as tk
from tkinter import ttk,messagebox
import webbrowser


class Recordings(ttk.Frame):
    def __init__(self,parent,client,tr,fmt_time):
        super().__init__(parent);self.client=type(client)(client.base)
        for cookie in client.jar:self.client.jar.set_cookie(copy.copy(cookie))
        self.client.csrf=client.csrf;self.tr=tr;self.fmt_time=fmt_time;self.results=queue.Queue(maxsize=1);self.busy=False;self.rows={}
        self.status=ttk.Label(self,text=tr('Private cloud recordings'));self.status.pack(anchor='w',pady=8)
        self.table=ttk.Treeview(self,columns=('date','meeting','duration','state'),show='headings',selectmode='browse')
        for key,label in [('date','Date'),('meeting','Meeting'),('duration','Duration'),('state','Status')]:self.table.heading(key,text=tr(label))
        self.table.pack(fill='both',expand=True)
        bar=ttk.Frame(self);bar.pack(fill='x',pady=8)
        for label,action in [('Refresh',self.reload),('Play',lambda:self.open(False)),('Download',lambda:self.open(True)),('Manage sharing / upload',lambda:self.open(False,True)),('Delete',self.delete)]:ttk.Button(bar,text=tr(label),command=action).pack(side='left',padx=4)
        self.after(50,self.drain);self.after(2000,self.refresh_pending);self.reload()

    def task(self,fn,done):
        if self.busy:return
        self.busy=True;self.status.config(text=self.tr('Loading…'));out=self.results
        def work():
            try:out.put((done,fn(),None))
            except Exception as error:out.put((done,None,str(error)))
        threading.Thread(target=work,daemon=True).start()

    def drain(self):
        if not self.winfo_exists():return
        try:
            done,result,error=self.results.get_nowait();self.busy=False
            if error:self.status.config(text=self.tr(error))
            else:self.status.config(text=self.tr('Private cloud recordings'));done(result)
        except queue.Empty:pass
        self.after(50,self.drain)

    def reload(self):
        def display(result):
            from datetime import datetime
            selection=self.table.selection()
            for item in self.table.get_children():self.table.delete(item)
            self.rows={row['id']:row for row in result['recordings']}
            for row in result['recordings']:
                self.table.insert('', 'end',iid=row['id'],values=(self.fmt_time(row['created']),row['meeting'] or '',str(round(row['duration']))+'s',self.tr(row['state'])+(' ['+row['error']+']' if row.get('error') else '')+(' / '+self.tr('Interrupted') if row['interrupted'] else '')))
            if selection and selection[0] in self.rows:self.table.selection_set(selection[0])
        self.task(lambda:self.client.json('/api/admin/recordings'),display)

    def refresh_pending(self):
        if not self.winfo_exists():return
        if not self.busy and any(r['state'] in ('capturing','finalizing','processing','uploading','indexing','importing') for r in self.rows.values()):self.reload()
        self.after(2000,self.refresh_pending)

    def selected(self):
        items=self.table.selection();return self.rows.get(items[0]) if items else None

    def open(self,download,manage=False):
        row=self.selected()
        if not row:return
        if not manage and row['state']!='ready':self.status.config(text=self.tr('Recording is not ready.'));return
        def show(result):
            from urllib.parse import urljoin
            webbrowser.open(urljoin(self.client.base+'/',result['url']))
        self.task(lambda:self.client.json('/api/admin/recordings/handoff',{'id':row['id'],'download':download,'manage':manage}),show)

    def delete(self):
        row=self.selected()
        if not row or not messagebox.askyesno(self.tr('Recordings'),self.tr('Permanently delete this private recording?'),parent=self):return
        self.task(lambda:self.client.json('/api/admin/recordings/delete',{'id':row['id']}),lambda _:self.reload())
