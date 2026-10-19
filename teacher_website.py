"""Teacher-only HTTPS content client and Tk editor. No server/inference imports."""
import copy
from concurrent.futures import ThreadPoolExecutor
import tkinter as tk
from tkinter import ttk,messagebox,simpledialog


class WebsiteService:
    def __init__(self,client):
        # Dedicated session snapshot: background requests never mutate the main
        # app's cookie jar/CSRF state while its classroom polling continues.
        self.client=type(client)(client.base)
        for cookie in client.jar:self.client.jar.set_cookie(copy.copy(cookie))
        self.client.csrf=client.csrf

    def load(self):
        return (self.client.json('/api/admin/website-content'),self.client.json('/api/admin/content-translations'))

    def content(self,entry,action,text=None,title=None):
        data={'action':action,'key':entry['key'],'revision':entry['revision'],'base_hash':entry['base_hash']}
        if text is not None:data.update(text=text,title=title)
        return self.client.json('/api/admin/website-content',data)

    def create_post(self,title,text):
        return self.client.json('/api/admin/website-content',{'action':'create_post','title':title,'text':text})

    def translation(self,source,row,target,action,text,regenerate=False):
        return self.client.json('/api/admin/content-translations',dict(action=action,key=source['key'],
            source_hash=source['source_hash'],target=target,revision=row['revision'] if row else 0,
            text=text,regenerate=regenerate,offline_only=True),timeout=45)

    def configure(self,enabled,terms):
        return self.client.json('/api/admin/content-translations',{'action':'config','enabled':enabled,'terms':terms})


def translation_row(state,key,target):
    return next((r for r in state['translations'] if r['source_key']==key and r['target']==target),None)


def preview_text(state,key,target,original):
    source=next((s for s in state['sources'] if s['key']==key),None)
    if not source or source['original']!=original:return original
    row=translation_row(state,key,target)
    # Preview only. Never writes approved/public content or falls back to a stale row.
    return row['draft'] if row else original


class WebsiteManagement(ttk.Frame):
    def __init__(self,parent,client,tr,navigate):
        super().__init__(parent)
        self._mathstudio_no_translate=True
        self.tr=tr;self.navigate=navigate;self.service=WebsiteService(client)
        self.pool=ThreadPoolExecutor(max_workers=1,thread_name_prefix='website-editor')
        self.pending=None;self.poll_job=None;self.loaded=False;self.alive=True;self.dirty=False
        self.entries=[];self.translations={'sources':[],'translations':[]};self.labels=[];self.controls=[]
        self.bind('<Destroy>',self._destroy,add='+')
        bar=ttk.Frame(self);bar.pack(fill='x')
        self.button(bar,'Reload',self.reload).pack(side='left')
        self.button(bar,'Files & codes',lambda:navigate('files')).pack(side='left',padx=8)
        self.button(bar,'Schedule',lambda:navigate('schedule')).pack(side='left')
        self.status_key='';self.status=ttk.Label(self,wraplength=540);self.status.pack(fill='x')
        self.book=ttk.Notebook(self);self.book.pack(fill='both',expand=True,pady=8)
        self.content_tab=ttk.Frame(self.book);self.trans_tab=ttk.Frame(self.book)
        self.config_tab=ttk.Frame(self.book)
        self.book.add(self.content_tab,text=tr('Public content'));self.book.add(self.trans_tab,text=tr('Translations'))
        self.book.add(self.config_tab,text=tr('Translation settings'));self.tab_index=0
        self.book.bind('<<NotebookTabChanged>>',self.tab_changed)
        self.content_fields=self.scrollable(self.content_tab)
        self.translation_fields=self.scrollable(self.trans_tab)
        self.config_fields=self.scrollable(self.config_tab)
        self.build_content();self.build_translations();self.set_language();self.reload()

    def scrollable(self,parent):
        canvas=tk.Canvas(parent,highlightthickness=0)
        scrollbar=ttk.Scrollbar(parent,orient='vertical',command=canvas.yview)
        scrollbar.pack(side='right',fill='y');canvas.pack(fill='both',expand=True)
        canvas.configure(yscrollcommand=scrollbar.set)
        inner=ttk.Frame(canvas,padding=10);item=canvas.create_window(0,0,anchor='nw',window=inner)
        inner.bind('<Configure>',lambda e:canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.bind('<Configure>',lambda e:canvas.itemconfigure(item,width=e.width,height=max(e.height,inner.winfo_reqheight())))
        return inner

    def tab_changed(self,event=None):
        index=self.book.index(self.book.select())
        if index!=self.tab_index and (self.dirty or self.pending):
            self.book.select(self.tab_index)
            messagebox.showinfo(self.tr('Website Management'),self.tr('Save changes or reload before changing sections.'),parent=self)
        else:self.tab_index=index

    def label(self,parent,text,**kw):
        widget=ttk.Label(parent,text=self.tr(text),**kw);self.labels.append((widget,text));return widget

    def button(self,parent,text,command):
        widget=ttk.Button(parent,text=self.tr(text),command=command)
        self.labels.append((widget,text));self.controls.append(widget);return widget

    def textbox(self,parent,height=6,readonly=False):
        box=tk.Text(parent,height=height,width=32,wrap='word',undo=True)
        box._mathstudio_no_translate=True
        if readonly:box.configure(state='disabled')
        else:box.bind('<<Modified>>',lambda e:self.modified(box))
        return box

    def modified(self,box):
        if box.edit_modified():self.dirty=True;box.edit_modified(False)

    def put(self,box,text,readonly=False):
        box.configure(state='normal');box.delete('1.0','end');box.insert('1.0',text)
        box.edit_modified(False)
        if readonly:box.configure(state='disabled')

    def build_content(self):
        p=self.content_fields
        self.label(p,'Select public content').pack(anchor='w')
        self.content_choice=ttk.Combobox(p,state='readonly');self.content_choice.pack(fill='x')
        self.content_choice.bind('<<ComboboxSelected>>',self.select_content)
        self.label(p,'Announcement title').pack(anchor='w',pady=(8,0))
        self.title=tk.StringVar();self.title_entry=ttk.Entry(p,textvariable=self.title);self.title_entry.pack(fill='x')
        self.title_entry.bind('<KeyRelease>',lambda e:setattr(self,'dirty',True))
        self.label(p,'Source draft (never translated automatically)').pack(anchor='w',pady=(8,0))
        self.content_text=self.textbox(p,8);self.content_text.pack(fill='both',expand=True)
        self.content_status=ttk.Label(p);self.content_status.pack(anchor='w',pady=4)
        actions=ttk.Frame(p);actions.pack(fill='x')
        for index,(text,action) in enumerate([('Save draft','save'),('Publish content','publish'),('Unpublish content','unpublish')]):
            self.button(actions,text,lambda a=action:self.content_action(a)).grid(row=index//2,column=index%2,sticky='w',padx=(0,8),pady=3)
        self.button(actions,'New announcement',self.new_post).grid(row=1,column=1,sticky='w')
        for language,text in [('en','Preview English'),('zh','Preview Chinese')]:
            self.button(p,text,lambda lang=language:self.preview(lang)).pack(side='left',padx=(0,8),pady=8)

    def build_translations(self):
        p=self.translation_fields
        self.label(p,'Translations run on OWNER. Review before publishing.',wraplength=750).pack(anchor='w')
        self.translation_choice=ttk.Combobox(p,state='readonly');self.translation_choice.pack(fill='x',pady=6)
        self.translation_choice.bind('<<ComboboxSelected>>',self.select_translation)
        self.label(p,'Target language: zh = Simplified Chinese; en = English').pack(anchor='w')
        self.target=ttk.Combobox(p,state='readonly',values=['zh','en'],width=6);self.target.set('zh');self.target.pack(anchor='w')
        self.target.bind('<<ComboboxSelected>>',self.select_translation)
        pane=ttk.Panedwindow(p,orient='horizontal');pane.pack(fill='both',expand=True,pady=8)
        left=ttk.Frame(pane);right=ttk.Frame(pane);pane.add(left,weight=1);pane.add(right,weight=1)
        self.label(left,'Original source').pack(anchor='w');self.source_text=self.textbox(left,7,True);self.source_text.pack(fill='both',expand=True)
        self.label(right,'Translation draft').pack(anchor='w');self.trans_text=self.textbox(right,7);self.trans_text.pack(fill='both',expand=True)
        self.label(p,'Previously approved text (reference only)').pack(anchor='w')
        self.previous=self.textbox(p,3,True);self.previous.pack(fill='x')
        self.translation_status=ttk.Label(p);self.translation_status.pack(anchor='w')
        actions=ttk.Frame(p);actions.pack(fill='x',pady=6)
        for index,(text,action,regenerate) in enumerate([('Generate draft','generate',False),('Regenerate draft','generate',True),('Save translation draft','save',False),('Approve & publish translation','approve',False)]):
            self.button(actions,text,lambda a=action,r=regenerate:self.translation_action(a,r)).grid(row=index//2,column=index%2,sticky='w',padx=(0,6),pady=3)
        p=self.config_fields
        self.provider_status=ttk.Label(p,wraplength=600);self.provider_status.pack(anchor='w',pady=8)
        self.enabled=tk.BooleanVar();self.optin=ttk.Checkbutton(p,variable=self.enabled,command=lambda:setattr(self,'dirty',True));self.optin.pack(anchor='w')
        self.labels.append((self.optin,'Enable OWNER offline translation'));self.controls.append(self.optin)
        self.label(p,'Protected names and terms (one per line)').pack(anchor='w')
        self.terms=self.textbox(p,2);self.terms.pack(fill='x')
        self.button(p,'Save translation settings',self.config_action).pack(anchor='e',pady=4)

    def _destroy(self,event):
        if event.widget is self:
            self.alive=False
            if self.poll_job:self.after_cancel(self.poll_job);self.poll_job=None
            self.pool.shutdown(wait=False,cancel_futures=True)

    def request(self,fn,success=None):
        if self.pending:return
        self.status_key='Working…';self.status.configure(text=self.tr(self.status_key))
        self.pending=self.pool.submit(fn)
        for widget in self.controls:widget.configure(state='disabled')
        for widget in (self.content_choice,self.translation_choice,self.target):widget.configure(state='disabled')
        for widget in (self.content_text,self.trans_text,self.terms,self.title_entry):widget.configure(state='disabled')
        def check():
            self.poll_job=None
            if not self.alive:return
            if not self.pending.done():self.poll_job=self.after(80,check);return
            future=self.pending;self.pending=None
            for widget in self.controls:widget.configure(state='normal')
            for widget in (self.content_choice,self.translation_choice,self.target):widget.configure(state='readonly')
            for widget in (self.content_text,self.trans_text,self.terms):widget.configure(state='normal')
            self.title_entry.configure(state='normal' if self.entry() and self.entry()['key'].startswith('posts:') else 'disabled')
            try:
                result=future.result()
                self.status_key='Saved / loaded successfully';self.status.configure(text=self.tr(self.status_key))
                if success:success(result)
            except Exception as error:
                self.status_key='Request failed. Your editor text is unchanged.';self.status.configure(text=self.tr(self.status_key))
                messagebox.showerror(self.tr('Website Management'),self.tr(str(error)),parent=self)
        self.poll_job=self.after(80,check)

    def reload(self):
        if self.dirty and not messagebox.askyesno(self.tr('Website Management'),self.tr('Discard unsaved editor changes?'),parent=self):return
        self.request(self.service.load,self.loaded_state)

    def loaded_state(self,result):
        old=getattr(self,'next_key',None) or (self.entry()['key'] if self.entry() else None);self.next_key=None
        old_source=self.source()['key'] if self.source() else None
        content,self.translations=result;self.entries=content['entries'];self.loaded=True
        self.content_choice['values']=[self.caption(e) for e in self.entries]
        self.translation_choice['values']=[self.caption(e) for e in self.translations['sources']]
        if self.entries:self.content_choice.current(next((i for i,e in enumerate(self.entries) if e['key']==old),0))
        if self.translations['sources']:self.translation_choice.current(next((i for i,e in enumerate(self.translations['sources']) if e['key']==old_source),0))
        self.enabled.set(self.translations['config']['enabled'])
        self.put(self.terms,'\n'.join(self.translations['config']['terms']))
        self.select_content(force=True);self.select_translation(force=True);self.dirty=False
        self.set_language()

    def caption(self,entry):
        key=entry['key'];kind,identifier,field=key.split(':')
        label={'headline':'Headline','intro':'Introduction','about':'About teacher','name':'Studio name','teacher':'Teacher name','contact':'Contact'}.get(field)
        if kind=='settings':return self.tr(label)
        item=next((e for e in self.entries if e['key']==key),entry)
        title=item.get('draft_title') or item.get('title','')
        return self.tr({'posts':'Announcement','courses':'Lesson description','groups':'Group description'}[kind])+' #'+identifier+(' — '+title if title else '')

    def entry(self):
        index=self.content_choice.current()
        return self.entries[index] if 0<=index<len(self.entries) else None

    def source(self):
        index=self.translation_choice.current();sources=self.translations['sources']
        return sources[index] if 0<=index<len(sources) else None

    def select_content(self,event=None,force=False):
        entry=self.entry()
        if not entry:return
        # Keep the current editor on accidental selection when it is dirty.
        previous=getattr(self,'selected_content',None)
        if not force and self.dirty and not messagebox.askyesno(self.tr('Website Management'),self.tr('Discard unsaved editor changes?'),parent=self):
            if previous:self.content_choice.current(next(i for i,e in enumerate(self.entries) if e['key']==previous))
            return
        self.selected_content=entry['key'];self.put(self.content_text,entry['draft']);self.title.set(entry['draft_title'])
        self.title_entry.configure(state='normal' if entry['key'].startswith('posts:') else 'disabled')
        self.content_status.configure(text=self.tr({'published':'Published','draft':'Draft','conflict':'Outdated — reload and save again'}[entry['status']]))
        self.dirty=False
        sources=self.translations['sources']
        index=next((i for i,s in enumerate(sources) if s['key']==entry['key']),None)
        if index is not None:self.translation_choice.current(index);self.select_translation(force=True)

    def select_translation(self,event=None,force=False):
        source=self.source()
        if not source:return
        selection=(source['key'],self.target.get());previous_selection=getattr(self,'selected_translation',None)
        if not force and self.dirty and not messagebox.askyesno(self.tr('Website Management'),self.tr('Discard unsaved editor changes?'),parent=self):
            if previous_selection:
                self.translation_choice.current(next(i for i,e in enumerate(self.translations['sources']) if e['key']==previous_selection[0]));self.target.set(previous_selection[1])
            return
        self.selected_translation=selection
        row=translation_row(self.translations,source['key'],self.target.get())
        previous=next((r for r in self.translations.get('previous_translations',[]) if r['source_key']==source['key'] and r['target']==self.target.get() and r['approved'] is not None),None)
        self.put(self.source_text,source['original'],True);self.put(self.trans_text,row['draft'] if row else '')
        self.put(self.previous,previous['approved'] if previous else row['approved'] if row and row['approved'] else '',True)
        status='Approved' if row and row['approved']==row['draft'] else 'Draft' if row else 'Outdated' if previous else 'Missing'
        self.translation_status.configure(text=self.tr(status));self.dirty=False

    def saved(self,result):
        self.next_key=result.get('key')
        self.dirty=False;self.reload()

    def content_action(self,action):
        entry=self.entry()
        if not entry:return
        if action!='save':
            if self.dirty:
                messagebox.showinfo(self.tr('Website Management'),self.tr('Save the source draft before publishing or previewing.'),parent=self);return
            if not messagebox.askyesno(self.tr('Website Management'),self.tr('Publish content?' if action=='publish' else 'Unpublish content?'),parent=self):return
        text=self.content_text.get('1.0','end-1c');title=self.title.get()
        self.request(lambda:self.service.content(entry,action,text if action=='save' else None,title),self.saved)

    def new_post(self):
        if self.dirty:
            messagebox.showinfo(self.tr('Website Management'),self.tr('Save the source draft before publishing or previewing.'),parent=self);return
        title=simpledialog.askstring(self.tr('New announcement'),self.tr('Announcement title'),parent=self)
        if not title:return
        text=simpledialog.askstring(self.tr('New announcement'),self.tr('Announcement message'),parent=self)
        if text:self.request(lambda:self.service.create_post(title,text),self.saved)

    def translation_action(self,action,regenerate=False):
        source=self.source();target=self.target.get()
        if not source:return
        config=self.translations['config']
        if action=='generate' and (config['provider']!='argos' or not config['configured'] or not config['enabled']):
            messagebox.showinfo(self.tr('Website Management'),self.tr('Ask OWNER to enable and set up offline translation.'),parent=self);return
        if action=='generate' and self.dirty and not messagebox.askyesno(self.tr('Website Management'),self.tr('Replace the unsaved translation draft? Approved text stays unchanged.'),parent=self):return
        if action=='approve' and not messagebox.askyesno(self.tr('Website Management'),self.tr('Approve and publish this reviewed translation?'),parent=self):return
        row=translation_row(self.translations,source['key'],target);text=self.trans_text.get('1.0','end-1c')
        self.request(lambda:self.service.translation(source,row,target,action,text,regenerate),self.saved)

    def config_action(self):
        enabled=self.enabled.get();terms=[x.strip() for x in self.terms.get('1.0','end-1c').splitlines() if x.strip()]
        self.request(lambda:self.service.configure(enabled,terms),self.saved)

    def preview(self,target):
        entry=self.entry()
        if not entry:return
        if self.dirty:
            messagebox.showinfo(self.tr('Website Management'),self.tr('Save the source draft before publishing or previewing.'),parent=self);return
        window=tk.Toplevel(self);window.title(self.tr('Content preview — unpublished'));window.geometry('740x440')
        self.label(window,'Preview English' if target=='en' else 'Preview Chinese').pack(anchor='w',padx=12)
        self.label(window,'Preview only. Publishing requires explicit approval.',wraplength=700).pack(padx=12,pady=8)
        if entry['key'].startswith('posts:'):
            title=ttk.Label(window,text=entry['draft_title']);title._mathstudio_no_translate=True;title.pack(anchor='w',padx=12)
        box=self.textbox(window,readonly=True);box.pack(fill='both',expand=True,padx=12,pady=12)
        self.put(box,preview_text(self.translations,entry['key'],target,entry['draft']),True)

    def set_language(self):
        self.status.configure(text=self.tr(self.status_key))
        for widget,key in self.labels:
            if widget.winfo_exists():widget.configure(text=self.tr(key))
        self.book.tab(0,text=self.tr('Public content'));self.book.tab(1,text=self.tr('Translations'))
        self.book.tab(2,text=self.tr('Translation settings'))
        if self.loaded:
            config=self.translations['config']
            self.provider_status.configure(text=self.tr('OWNER offline translation is ready' if config['provider']=='argos' and config['configured'] else 'Ask OWNER to enable and set up offline translation.'))
            content_index=self.content_choice.current();translation_index=self.translation_choice.current()
            self.content_choice['values']=[self.caption(e) for e in self.entries]
            self.translation_choice['values']=[self.caption(e) for e in self.translations['sources']]
            if content_index>=0:self.content_choice.current(content_index)
            if translation_index>=0:self.translation_choice.current(translation_index)
            entry=self.entry();source=self.source()
            if entry:self.content_status.configure(text=self.tr({'published':'Published','draft':'Draft','conflict':'Outdated — reload and save again'}[entry['status']]))
            if source:
                row=translation_row(self.translations,source['key'],self.target.get())
                previous=any(r['source_key']==source['key'] and r['target']==self.target.get() for r in self.translations.get('previous_translations',[]))
                self.translation_status.configure(text=self.tr('Approved' if row and row['approved']==row['draft'] else 'Draft' if row else 'Outdated' if previous else 'Missing'))
