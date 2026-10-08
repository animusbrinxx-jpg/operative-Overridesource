"""Legion Operative Studio: independently written local desktop UI."""
import tkinter as tk
from tkinter import ttk,messagebox,filedialog,simpledialog
import json,threading,queue
from pathlib import Path
from studio_backend import Game,CAT,FIELDS,P,decode,encode,save_json,restore_baseline
from field_guide import GUIDE
from wardrobe import Library,CLOTHING,incompatible,capture
class Studio(tk.Tk):
 def __init__(self):
  super().__init__();self.title('Operative Override');self.geometry('1160x810');self.minsize(1000,740)
  self.configure(bg='#111214');self.rows=[];self.current=None;self.draft=None;self.queue=queue.Queue();self.busy=False
  self.loading=False;self.draft_cache={};self.last_selected=None;self.template_source=None
  try:
   saved=json.loads((P/'staged-drafts.json').read_text(encoding='utf-8'));self.draft_cache=saved.get('drafts',{});self.last_selected=saved.get('selected')
  except (OSError,ValueError):pass
  style=ttk.Style(self);style.theme_use('clam')
  style.configure('.',background='#111214',foreground='#e9ecef',font=('Segoe UI',10))
  style.configure('TFrame',background='#111214');style.configure('TLabel',background='#111214')
  style.configure('TButton',background='#272a2e',foreground='#e9ecef',padding=(12,8))
  style.map('TButton',background=[('active','#363b42')]);style.configure('TCombobox',fieldbackground='#202327',background='#272a2e',foreground='#e9ecef')
  style.map('TCombobox',fieldbackground=[('readonly','#202327')],foreground=[('readonly','#e9ecef')],selectbackground=[('readonly','#303e3c')],selectforeground=[('readonly','#ffffff')])
  style.configure('Treeview',background='#191b1f',fieldbackground='#191b1f',foreground='#e9ecef',rowheight=34)
  style.configure('Treeview.Heading',background='#272a2e',foreground='#e9ecef')
  style.map('Treeview',background=[('selected','#303e3c')]);style.configure('TNotebook',background='#111214')
  style.configure('TNotebook.Tab',background='#272a2e',foreground='#e9ecef',padding=(15,9))
  style.configure('TButton',borderwidth=1,relief='flat')
  style.map('TButton',foreground=[('disabled','#6e747d')])
  style.configure('Accent.TButton',background='#b7ef59',foreground='#111214')
  style.map('Accent.TButton',background=[('active','#d0ff83'),('disabled','#303638')],foreground=[('disabled','#858f8b'),('!disabled','#111214')])
  style.configure('TCheckbutton',background='#111214',foreground='#aebbc2',padding=(0,7))
  style.map('TCheckbutton',background=[('active','#111214')])
  style.configure('TNotebook',borderwidth=0,tabmargins=(0,0,0,8))
  style.configure('TNotebook.Tab',background='#202327',foreground='#9aabb2',borderwidth=0,padding=(16,10))
  style.map('TNotebook.Tab',background=[('selected','#303638')],foreground=[('selected','#b7ef59')])
  style.configure('Treeview.Heading',font=('Segoe UI',9,'bold'),padding=(8,10))
  style.configure('Vertical.TScrollbar',background='#30343a',troughcolor='#191b1f',borderwidth=0,arrowsize=12)
  self.option_add('*TCombobox*Listbox.background','#202327');self.option_add('*TCombobox*Listbox.foreground','#e9ecef')
  for widget_style in ('TCombobox','Treeview','Treeview.Heading','TNotebook','TNotebook.Tab','Vertical.TScrollbar'):
   style.configure(widget_style,bordercolor='#34383e',lightcolor='#34383e',darkcolor='#34383e')
  style.map('TCombobox',bordercolor=[('focus','#65d6d1'),('!focus','#34383e')],lightcolor=[('!focus','#34383e')],darkcolor=[('!focus','#34383e')])
  header=ttk.Frame(self,padding=(22,18,22,15));header.pack(fill='x')
  ttk.Button(header,text='HOW TO',command=self.how_to).pack(side='right',padx=(16,0))
  mark=tk.Canvas(header,width=46,height=53,bg='#111214',highlightthickness=0);mark.pack(side='right',padx=(20,0))
  mark.create_line(9,8,2,26,9,44,fill='#65d6d1',width=2);mark.create_line(32,8,39,26,32,44,fill='#65d6d1',width=2)
  mark.create_line(14,31,26,18,fill='#b7ef59',width=3);mark.create_rectangle(24,34,37,37,fill='#b7ef59',outline='')
  ttk.Label(header,text='Brought to you by DedSec',foreground='#9aabb2',font=('Segoe UI',9)).pack(side='right',padx=(12,8))
  ttk.Label(header,text='OPERATIVE OVERRIDE',font=('Segoe UI',23,'bold'),foreground='#b7ef59').pack(anchor='w')
  ttk.Label(header,text='DedSec Personnel Reconfiguration System',foreground='#9aabb2').pack(anchor='w',pady=(6,0))
  line=tk.Frame(self,bg='#30343a',height=1);line.pack(fill='x',padx=22,pady=(0,17))
  body=ttk.Frame(self,padding=(22,0,22,8));body.pack(fill='both',expand=True)
  left=ttk.Frame(body,width=275);left.pack(side='left',fill='y',padx=(0,22));left.pack_propagate(False)
  ttk.Label(left,text='01 / PERSONNEL',font=('Consolas',10,'bold'),foreground='#65d6d1').pack(anchor='w',pady=(0,12))
  ttk.Button(left,text='Connect / Refresh team',command=self.refresh).pack(fill='x',pady=(0,12))
  self.tree=ttk.Treeview(left,columns=('gender',),show='tree headings',selectmode='browse')
  self.tree.heading('#0',text='OPERATIVE');self.tree.heading('gender',text='BODY');self.tree.column('#0',width=175);self.tree.column('gender',width=75,stretch=False)
  self.tree.pack(fill='both',expand=True);self.tree.bind('<<TreeviewSelect>>',self.select)
  ttk.Label(left,text='Single-player · DirectX 11\nNo Cheat Engine required',foreground='#9aabb2').pack(anchor='w',pady=(14,0))
  right=ttk.Frame(body);right.pack(side='left',fill='both',expand=True)
  ttk.Label(right,text='02 / RECONFIGURATION',font=('Consolas',10,'bold'),foreground='#65d6d1').pack(anchor='w',pady=(0,8))
  self.title_var=tk.StringVar(value='Connect to your game');ttk.Label(right,textvariable=self.title_var,font=('Segoe UI',18,'bold')).pack(anchor='w')
  self.special_badge=ttk.Label(right,text='',foreground='#efbb68',font=('Segoe UI',9),wraplength=680)
  self.special_badge.pack(anchor='w')
  ttk.Label(right,text='Edit an inactive operative. For a gender change, start with a compatible team appearance.',wraplength=750,foreground='#9aabb2').pack(anchor='w',pady=(7,15))
  template=ttk.Frame(right);template.pack(fill='x',pady=(0,12));ttk.Label(template,text='Copy team look').pack(side='left')
  self.template=ttk.Combobox(template,state='readonly',width=32);self.template.pack(side='left',padx=10,fill='x',expand=True)
  ttk.Button(template,text='Use appearance',command=self.use_template).pack(side='left')
  notebook=ttk.Notebook(right);notebook.pack(fill='both',expand=True);self.notebook=notebook
  def scroll_tab(title):
   container=ttk.Frame(notebook);notebook.add(container,text=title)
   canvas=tk.Canvas(container,bg='#111214',highlightthickness=0,height=250)
   scrollbar=ttk.Scrollbar(container,orient='vertical',command=canvas.yview);scrollbar.pack(side='right',fill='y');canvas.pack(side='left',fill='both',expand=True);canvas.configure(yscrollcommand=scrollbar.set)
   page=ttk.Frame(canvas,padding=18);window=canvas.create_window((0,0),window=page,anchor='nw')
   page.bind('<Configure>',lambda event:canvas.configure(scrollregion=canvas.bbox('all')))
   canvas.bind('<Configure>',lambda event:canvas.itemconfigure(window,width=event.width))
   canvas.bind('<MouseWheel>',lambda event:canvas.yview_scroll(-int(event.delta/120),'units'))
   return page
  body_tab=scroll_tab('Body & voice');clothes=scroll_tab('Outfit');wardrobe_tab=scroll_tab('Wardrobe presets')
  self.wardrobe_library=Library();self.saved_outfits={}
  ttk.Label(wardrobe_tab,text='Save the outfit currently worn in-game. Presets are locked to this operative and body model.',wraplength=650).pack(anchor='w',pady=(0,10))
  self.capture_button=ttk.Button(wardrobe_tab,text='Save current outfit…',command=self.save_outfit);self.capture_button.pack(anchor='w',pady=(0,12))
  self.wardrobe_tree=ttk.Treeview(wardrobe_tab,columns=('model','compatible'),show='tree headings',selectmode='browse',height=6)
  self.wardrobe_tree.heading('#0',text='SAVED OUTFIT');self.wardrobe_tree.heading('model',text='BODY MODEL');self.wardrobe_tree.heading('compatible',text='STATUS')
  self.wardrobe_tree.column('#0',width=270);self.wardrobe_tree.column('model',width=100,stretch=False);self.wardrobe_tree.column('compatible',width=125,stretch=False)
  self.wardrobe_tree.pack(fill='x');self.wardrobe_tree.bind('<<TreeviewSelect>>',self.outfit_selected)
  self.wardrobe_warning=tk.StringVar(value='Select an operative to view their saved outfits.')
  ttk.Label(wardrobe_tab,textvariable=self.wardrobe_warning,wraplength=650,foreground='#b7ef59').pack(anchor='w',pady=12)
  self.inactive_confirmed=tk.BooleanVar(value=False)
  self.outfit_apply_button=ttk.Button(wardrobe_tab,text='Apply saved outfit only',style='Accent.TButton',command=self.apply_saved_outfit,state='disabled');self.outfit_apply_button.pack(anchor='w')
  ttk.Label(wardrobe_tab,text='Only clothing/accessories are applied. Body, grooming and voice choices staged in other tabs are not applied by this button. Use Undo last edit to restore the outfit.',wraplength=650,foreground='#9aabb2').pack(anchor='w',pady=12)
  self.gender=tk.StringVar(value='Female');self.voice=tk.StringVar();self.controls={}
  self.add_choice(body_tab,'Gender',self.gender,['Female','Male'],0)
  voices=[f'{name} · {code}' for code,name in CAT['voices'].items()];self.voice_lookup={f'{name} · {code}':int(code) for code,name in CAT['voices'].items()}
  self.add_choice(body_tab,'Player voice',self.voice,voices,1)
  body_keys=['model','hair','hair_color','makeup','head_tattoo','body_tattoo']
  outfit_keys=['outfit','innerwear','outerwear','legwear','footwear','handwear','headwear','earrings','bag']
  for tab,keys,start in [(body_tab,body_keys,2),(clothes,outfit_keys,0)]:
   for row,key in enumerate(keys,start):
    var=tk.StringVar();f=FIELDS[key];choices={f'{label} · {id}':int(id) for id,label in f['choices'].items()}
    self.controls[key]=(var,choices)
    self.add_choice(tab,{'outfit':'Full outfit','innerwear':'Top','outerwear':'Outer layer','legwear':'Trousers / skirt','footwear':'Shoes','handwear':'Gloves','headwear':'Hat','earrings':'Earrings','bag':'Bag'}.get(key,key.replace('_',' ').title()),var,list(choices),row,lambda key=key:self.search(key))
  ttk.Label(body_tab,text='Face and body come from the selected model. Voice modulation and scripted dialogue are not edited.',wraplength=700,foreground='#9aabb2').grid(row=8,column=0,columnspan=3,sticky='w',pady=(18,0))
  ttk.Checkbutton(right,text='Selected operative is inactive — I am playing as someone else',variable=self.inactive_confirmed,command=self.outfit_selected).pack(anchor='w',pady=(8,0),before=notebook)
  self.clothing_warning=tk.StringVar()
  ttk.Label(clothes,textvariable=self.clothing_warning,wraplength=650,foreground='#9aabb2').grid(row=9,column=0,columnspan=3,sticky='w',pady=12)
  bottom=ttk.Frame(right);bottom.pack(side='bottom',before=notebook,fill='x',pady=(14,0))
  ttk.Button(bottom,text='Export look',command=self.export).pack(side='left')
  ttk.Button(bottom,text='Import look',command=self.import_preset).pack(side='left',padx=8)
  ttk.Button(bottom,text='Undo',command=self.undo).pack(side='left')
  ttk.Button(bottom,text='Restore Baseline',command=self.restore_operative).pack(side='left',padx=(8,0))
  self.apply_button=ttk.Button(bottom,text='Apply appearance & voice',style='Accent.TButton',command=self.apply);self.apply_button.pack(side='right')
  notebook.bind('<<NotebookTabChanged>>',lambda event:self.update_apply_state())
  self.status=tk.StringVar(value='Ready to connect. Your save and appearance are backed up before each edit.')
  self.status_badge=ttk.Label(self,text='OFFLINE / AWAITING LINK',font=('Consolas',10,'bold'),foreground='#65d6d1',padding=(22,6));self.status_badge.pack(side='bottom',before=body,fill='x')
  self.status.trace_add('write',self.update_status_badge)
  self.status_label=ttk.Label(self,textvariable=self.status,padding=(22,8),wraplength=1080,foreground='#b7ef59');self.status_label.pack(side='bottom',before=body,fill='x')
  for variable in [self.gender,self.voice]+[var for var,choices in self.controls.values()]:variable.trace_add('write',self.persist_draft)
  self.after(100,self.poll);self.after(200,lambda:self.refresh(quiet=True))
 def how_to(self):
  if getattr(self,'guide_window',None) and self.guide_window.winfo_exists():self.guide_window.lift();return
  dialog=tk.Toplevel(self);self.guide_window=dialog;dialog.title('DedSec Field Guide / Operative Override');dialog.geometry('790x690');dialog.minsize(540,400);dialog.configure(bg='#111214')
  frame=ttk.Frame(dialog,padding=20);frame.pack(fill='both',expand=True)
  scroll=ttk.Scrollbar(frame);scroll.pack(side='right',fill='y')
  text=tk.Text(frame,wrap='word',bg='#191b1f',fg='#e9ecef',insertbackground='#65d6d1',selectbackground='#303e3c',font=('Segoe UI',11),padx=18,pady=16,relief='flat',yscrollcommand=scroll.set,spacing3=8)
  text.pack(fill='both',expand=True);scroll.configure(command=text.yview)
  text.tag_configure('heading',foreground='#b7ef59',font=('Consolas',12,'bold'))
  text.insert('1.0',GUIDE)
  for index,line in enumerate(GUIDE.splitlines(),1):
   if line and line==line.upper():text.tag_add('heading',f'{index}.0',f'{index}.end')
  text.configure(state='disabled');ttk.Button(dialog,text='Got it',command=dialog.destroy).pack(pady=(0,16));dialog.bind('<Escape>',lambda event:dialog.destroy());text.focus_set()
 def update_status_badge(self,*args):
  message=self.status.get().lower();color='#65d6d1'
  if 'unavailable' in message:label='OFFLINE / AWAITING LINK';color='#9aabb2'
  elif 'applied' in message and ('verified' in message or 'undo saved' in message):label='CHANGES APPLIED / BACKUP CREATED';color='#b7ef59'
  elif 'restored' in message:label='RESTORE COMPLETE';color='#b7ef59'
  elif message.startswith('connected'):label='OPERATIVE ACQUIRED';color='#b7ef59'
  elif 'backing up' in message:label='BACKUP IN PROGRESS'
  elif 'connecting' in message:label='ACQUIRING PERSONNEL'
  elif 'incompatible' in message or 'failed' in message or 'error' in message:label='ACTION STOPPED';color='#efbb68'
  elif 'staged' in message:label='DRAFT STAGED'
  elif 'saved' in message or 'exported' in message:label='LOCAL FILE SAVED'
  else:label='SYSTEM READY'
  self.status_badge.configure(text=label,foreground=color)
 def persist_draft(self,*args):
  if self.loading or not self.current or self.draft is None:return
  try:
   values={key:choices[var.get()] for key,(var,choices) in self.controls.items()}
   self.draft_cache[self.current['id']]=dict(appearance=encode(self.draft,values).hex(),gender=self.gender.get(),voice=self.voice_lookup[self.voice.get()])
   save_json(P/'staged-drafts.json',dict(selected=self.current['id'],drafts=self.draft_cache))
  except (KeyError,ValueError,OSError):pass
 def add_choice(self,parent,label,var,values,row,search=None):
  ttk.Label(parent,text=label,width=15).grid(row=row,column=0,sticky='w',pady=7)
  combo=ttk.Combobox(parent,textvariable=var,values=values,state='readonly',width=58);combo.grid(row=row,column=1,sticky='ew',padx=(8,0),pady=7)
  if search:ttk.Button(parent,text='Find',command=search).grid(row=row,column=2,padx=(8,0),pady=7)
  parent.columnconfigure(1,weight=1)
 def run(self,message,func,done,quiet=False):
  if self.busy:return
  self.busy=True;self.status.set(message);self.apply_button.configure(state='disabled');self.capture_button.configure(state='disabled');self.outfit_apply_button.configure(state='disabled')
  def worker():
   try:result=func();self.queue.put((done,result,None,quiet))
   except Exception as e:self.queue.put((done,None,str(e),quiet))
  threading.Thread(target=worker,daemon=True).start()
 def poll(self):
  try:
   done,result,error,quiet=self.queue.get_nowait();self.busy=False;self.update_apply_state();self.capture_button.configure(state='normal')
   if error:
    self.status.set('Game unavailable. Start Legion in single-player, then click Connect / Refresh team.' if quiet else error)
    if not quiet:messagebox.showerror('Action stopped',error)
   else:done(result)
   self.outfit_selected()
  except queue.Empty:pass
  self.after(100,self.poll)
 def update_apply_state(self):
  tab=self.notebook.index(self.notebook.select())
  enabled=bool(self.current) and not self.busy and self.inactive_confirmed.get() and tab!=2
  reason=None
  if tab==1 and self.current:
   try:self.clothing_preset()
   except (ValueError,KeyError) as e:reason=str(e);enabled=False
  self.clothing_warning.set(reason or 'Apply clothing only keeps your current body, gender, voice and grooming. Catalog pieces may not fit every model; check the result in-game.')
  self.apply_button.configure(text='Apply clothing only' if tab==1 else 'Apply appearance & voice',command=self.apply_clothing if tab==1 else self.apply,state='normal' if enabled else 'disabled')
 def refresh(self,confirmation=None,wardrobe_only=False,quiet=False):
  def work():
   with Game() as game:return game.roster()
  def done(rows):
   self.rows=rows;self.tree.delete(*self.tree.get_children())
   for r in rows:self.tree.insert('', 'end',iid=r['id'],text=r['name'],values=(r['gender'],))
   self.template['values']=[r['name'] for r in rows]
   selected_id=self.current['id'] if self.current else self.last_selected
   if confirmation and selected_id:
    if wardrobe_only and selected_id in self.draft_cache:
     fresh=next((r for r in rows if r['id']==selected_id),None)
     if fresh:
      saved=self.draft_cache[selected_id];saved['appearance']=encode(bytes.fromhex(saved['appearance']),{key:fresh['fields'][key] for key in CLOTHING}).hex()
    else:self.draft_cache.pop(selected_id,None)
   chosen=next((r for r in rows if r['id']==selected_id),None) or next((r for r in rows if r['name']=='Wrench'),rows[0]);self.tree.selection_set(chosen['id']);self.tree.see(chosen['id']);self.select()
   self.status.set(confirmation or f'Connected · {len(rows)} operatives. Select an inactive team member before applying edits.')
  self.run('Connecting to Legion and validating its build…',work,done,quiet=quiet)
 def select(self,event=None):
  selection=self.tree.selection()
  if not selection or self.busy:return
  previous=self.current['id'] if self.current else None
  self.current=next(r for r in self.rows if r['id']==selection[0]);self.title_var.set(self.current['name'])
  self.special_badge.configure(text='SPECIAL OPERATIVE / Wrench can have mixed voices. Original voice recommended; see HOW TO.' if self.current['name']=='Wrench' else '')
  if previous!=self.current['id']:self.inactive_confirmed.set(False);self.template_source=None
  self.load(self.draft_cache.get(self.current['id']) or dict(appearance=self.current['appearance'],gender=self.current['gender'],voice=self.current['voice']))
  self.refresh_outfits()
 def refresh_outfits(self,selected_path=None):
  self.wardrobe_tree.delete(*self.wardrobe_tree.get_children());self.saved_outfits={}
  if not self.current:return
  try:entries,errors=self.wardrobe_library.list(self.current['id'])
  except Exception as e:self.wardrobe_warning.set(str(e));return
  for path,preset in entries:
   key=str(path);self.saved_outfits[key]=preset
   reason=incompatible(preset,self.current)
   self.wardrobe_tree.insert('', 'end',iid=key,text=preset['name'],values=(preset['model_id'],'Incompatible' if reason else 'Compatible'))
  if selected_path and str(selected_path) in self.saved_outfits:self.wardrobe_tree.selection_set(str(selected_path))
  self.wardrobe_warning.set('Select a saved outfit. '+(f'{len(errors)} invalid preset file(s) ignored.' if errors else '') if entries else 'No saved outfits for this operative yet.')
  self.outfit_selected()
 def outfit_selected(self,event=None):
  selection=self.wardrobe_tree.selection();preset=self.saved_outfits.get(selection[0]) if selection else None
  enabled=False
  if preset and self.current:
   reason=incompatible(preset,self.current)
   self.wardrobe_warning.set(reason or f'Compatible: {preset["name"]}. Confirm the operative is inactive before applying.')
   enabled=not reason and self.inactive_confirmed.get() and not self.busy
  self.outfit_apply_button.configure(state='normal' if enabled else 'disabled')
  self.update_apply_state()
 def clothing_preset(self):
  if not self.current:raise ValueError('Connect and select an operative first.')
  preset=capture(self.current,'Clothing edit')
  preset['clothing']={key:options[var.get()] for key in CLOTHING for var,options in [self.controls[key]]}
  reason=incompatible(preset,self.current)
  if reason:raise ValueError(reason)
  return preset
 def apply_clothing(self):
  if self.busy:return
  try:
   if not self.inactive_confirmed.get():raise ValueError('Switch to another operative in-game and confirm the selected operative is inactive.')
   preset=self.clothing_preset();ident=self.current['id']
  except (ValueError,KeyError) as e:messagebox.showwarning('Clothing edit stopped',str(e));return
  def work():
   with Game(write=True) as game:return game.apply_wardrobe(ident,preset)
  self.run('Backing up your save and applying clothing only…',work,lambda record:self.refresh('Clothing applied. Switch to the operative in-game to check the look. Undo saved.',wardrobe_only=True))
 def save_outfit(self):
  if self.busy or not self.current:return
  name=simpledialog.askstring('Save current outfit','Name this in-game outfit:',parent=self)
  if name is None:return
  ident=self.current['id']
  def work():
   with Game() as game:preset=capture(game.target(ident),name)
   return self.wardrobe_library.save(preset)
  def done(path):self.refresh_outfits(path);self.status.set('Saved the current in-game outfit. Staged editor choices were not captured.')
  self.run('Reading the current outfit and saving its named preset…',work,done)
 def apply_saved_outfit(self):
  if self.busy or not self.current:return
  selection=self.wardrobe_tree.selection();preset=self.saved_outfits.get(selection[0]) if selection else None
  if not preset:return
  if not self.inactive_confirmed.get():messagebox.showwarning('Inactive operative required','Switch to another operative in-game, then tick the inactive-operative confirmation.');return
  reason=incompatible(preset,self.current)
  if reason:messagebox.showwarning('Incompatible outfit',reason);return
  ident=self.current['id']
  def work():
   with Game(write=True) as game:return game.apply_wardrobe(ident,preset)
  self.run('Backing up your save and applying clothing only…',work,lambda record:self.refresh('Saved outfit applied and verified. Switch to the operative in-game. Clothing-only undo saved.',wardrobe_only=True))
 def set_field(self,key,value):
  var,options=self.controls[key];label=next((label for label,id in options.items() if id==value),None)
  if label is None:label=f'Current value · {value}';options[label]=value
  var.set(label)
 def load(self,preset):
  self.loading=True
  self.draft=bytes.fromhex(preset['appearance']);self.gender.set(preset['gender'])
  label=next((label for label,id in self.voice_lookup.items() if id==preset['voice']),None)
  if not label:raise ValueError('Preset voice is not in this build catalog')
  self.voice.set(label)
  for key in self.controls:self.set_field(key,decode(self.draft,key))
  self.loading=False;self.persist_draft()
 def use_template(self):
  if self.busy or not self.current:return
  source=next((r for r in self.rows if r['name']==self.template.get()),None)
  if not source:return
  self.loading=True
  self.template_source=(source['fields']['model'],source['gender'])
  self.draft=bytes.fromhex(source['appearance']);self.gender.set(source['gender'])
  for key in self.controls:self.set_field(key,source['fields'][key])
  if self.voice.get().startswith('M -') and source['gender']=='Female':
   self.voice.set(next(label for label,id in self.voice_lookup.items() if id==source['voice']))
  self.loading=False;self.persist_draft()
  self.status.set(f'Staged {source["name"]}’s appearance for {self.current["name"]}. Nothing changed in-game yet.')
 def staged(self):
  if not self.current or self.draft is None:raise ValueError('Connect and select an operative first')
  values={key:options[var.get()] for key,(var,options) in self.controls.items()}
  voice=self.voice_lookup[self.voice.get()];gender=self.gender.get();model_label=FIELDS['model']['choices'].get(str(values['model']),'')
  if gender=='Female' and ('.male.' in model_label or '_male_' in model_label):raise ValueError('Choose a female body model or team appearance for this gender change')
  if gender=='Male' and ('.female.' in model_label or '_female_' in model_label):raise ValueError('Choose a male body model or team appearance for this gender change')
  expected='F -' if gender=='Female' else 'M -'
  if not CAT['voices'][str(voice)].startswith(expected):raise ValueError('Choose a voice matching the selected gender')
  return dict(appearance=encode(self.draft,values).hex(),gender=gender,voice=voice)
 def apply(self):
  if self.busy:return
  if not self.inactive_confirmed.get():messagebox.showwarning('Inactive operative required','Switch to another operative in-game and confirm it here.');return
  try:preset=self.staged();ident=self.current['id']
  except Exception as e:messagebox.showerror('Check your choices',str(e));return
  model=decode(bytes.fromhex(preset['appearance']),'model')
  if (model!=self.current['fields']['model'] or preset['gender']!=self.current['gender']) and self.template_source!=(model,preset['gender']):
   if not messagebox.askyesno('Body change: check compatibility','For the safest body or gender change, choose a compatible team member under Copy team look, click Use appearance, then customize. This manually assembled combination has not been validated. It may differ between the playable operative and their street appearance. Continue with this combination?'):return
  def work():
   with Game(write=True) as game:
    roster=game.roster();donor=next((r for r in roster if r['voice']==preset['voice'] and r['gender']==preset['gender']),None)
    return game.apply(ident,**preset,npc_voice=donor['npc_voice'] if donor else None)
  self.run('Backing up your save and applying the selected appearance…',work,lambda result:self.refresh('Applied and verified. Switch to this operative in-game to check the model and voice. Undo backup saved.'))
 def restore_operative(self):
  if self.busy or not self.current:return
  if not self.inactive_confirmed.get():messagebox.showwarning('Inactive operative required','Switch to another operative and confirm it here before restoring.');return
  try:baseline=restore_baseline(self.current['id'])
  except (OSError,ValueError) as e:messagebox.showwarning('Restore unavailable',str(e));return
  detail='Appearance, clothing, gender and general voice will return to their earliest recorded values. Gameplay data is preserved. This is the first captured state, which may differ from the vanilla original. A fresh backup allows Undo.'
  if 'npc_voice' not in baseline['values']:detail+=' No NPC/emote voice baseline exists; that field will remain unchanged.'
  if not messagebox.askyesno('Restore '+self.current['name']+'?',detail):return
  ident=self.current['id']
  def work():
   with Game(write=True) as game:return game.restore_captured(ident)
  self.run('Backing up your save and restoring the first captured state…',work,lambda record:self.refresh('Restored and verified. Undo can recover the look you had before restoration. Return to the main menu if the portrait is stale.'))
 def undo(self):
  if self.busy or not self.current:return
  if not self.inactive_confirmed.get():messagebox.showwarning('Inactive operative required','Switch to another operative in-game and confirm it here before Undo.');return
  records=[]
  for p in (P/'Backups').glob('*.json'):
   r=json.loads(p.read_text(encoding='utf-8'))
   if r.get('status')=='applied' and r.get('id')==self.current['id']:records.append(p)
  if not records:messagebox.showinfo('Undo','No applied edit exists for this operative.');return
  record=sorted(records)[-1]
  def work():
   with Game(write=True) as game:game.undo(record)
  wardrobe_only=json.loads(record.read_text(encoding='utf-8')).get('kind')=='wardrobe'
  self.run('Restoring the previous outfit…' if wardrobe_only else 'Restoring the previous appearance and voice…',work,lambda result:self.refresh('Restored and verified. Switch to the operative in-game to refresh their appearance.',wardrobe_only=wardrobe_only))
 def export(self):
  try:preset=self.staged()
  except Exception as e:messagebox.showerror('Export',str(e));return
  path=filedialog.asksaveasfilename(defaultextension='.json',initialfile=self.current['name']+'-appearance.json',filetypes=[('Appearance preset','*.json')])
  if path:Path(path).write_text(json.dumps(preset,indent=2));self.status.set('Appearance preset exported.')
 def import_preset(self):
  path=filedialog.askopenfilename(filetypes=[('Appearance preset','*.json')])
  if not path:return
  try:
   p=json.loads(Path(path).read_text());b=bytes.fromhex(p['appearance'])
   if len(b)!=24 or int.from_bytes(b,'big')>>183!=12 or (int.from_bytes(b,'big')>>179)&15!=2:raise ValueError('Unsupported appearance preset')
   self.load(p);self.status.set('Preset staged. Apply when the selected operative is inactive.')
  except Exception as e:messagebox.showerror('Import',str(e))
 def search(self,key):
  dialog=tk.Toplevel(self);dialog.title('Find '+key.replace('_',' '));dialog.geometry('820x510');dialog.configure(bg='#111214')
  query=tk.StringVar();entry=ttk.Entry(dialog,textvariable=query);entry.pack(fill='x',padx=15,pady=15)
  result=tk.Listbox(dialog,bg='#191b1f',fg='#e9ecef',selectbackground='#303e3c',font=('Segoe UI',10));result.pack(fill='both',expand=True,padx=15)
  var,choices=self.controls[key]
  def update(*args):
   result.delete(0,'end');terms=query.get().lower().split()
   for label in choices:
    if all(term in label.lower() for term in terms):result.insert('end',label)
  def pick(event=None):
   if result.curselection():var.set(result.get(result.curselection()[0]));dialog.destroy()
  query.trace_add('write',update);result.bind('<Double-Button-1>',pick);ttk.Button(dialog,text='Choose selected',command=pick).pack(pady=15);update();entry.focus_set()
if __name__=='__main__':
 Studio().mainloop()
