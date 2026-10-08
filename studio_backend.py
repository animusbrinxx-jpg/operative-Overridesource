"""Independently implemented Windows backend for a local, single-player editor."""
from pathlib import Path
import ctypes,struct,json,hashlib,datetime,uuid,os,sys
from process_lookup import process_metadata
P=Path(sys.executable).resolve().parent if getattr(sys,'frozen',False) else Path(__file__).resolve().parent
CAT=json.loads((P/'catalog.json').read_text(encoding='utf-8'))
PROFILE=json.loads((P/'build-profile.json').read_text())
FIELDS={f['key']:f for f in CAT['fields']}
def decode(data,key):
 f=FIELDS[key];offset=f['byte']*8+f['bit'];shift=192-offset-f['width']
 return (int.from_bytes(data,'big')>>shift)&((1<<f['width'])-1)
def encode(data,values):
 bits=int.from_bytes(data,'big')
 for key,value in values.items():
  f=FIELDS[key];offset=f['byte']*8+f['bit'];shift=192-offset-f['width'];mask=(1<<f['width'])-1
  if not 0<=value<=mask:raise ValueError(f'{key} is outside its encoded range.')
  bits=(bits&~(mask<<shift))|(value<<shift)
 return bits.to_bytes(24,'big')
def save_json(path,obj):
 temp=path.with_suffix('.tmp');temp.write_text(json.dumps(obj,indent=2),encoding='utf-8');os.replace(temp,path)
K=ctypes.WinDLL('kernel32',use_last_error=True)
K.OpenProcess.argtypes=[ctypes.c_ulong,ctypes.c_int,ctypes.c_ulong];K.OpenProcess.restype=ctypes.c_void_p
K.ReadProcessMemory.argtypes=[ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_size_t,ctypes.POINTER(ctypes.c_size_t)];K.ReadProcessMemory.restype=ctypes.c_int
K.WriteProcessMemory.argtypes=K.ReadProcessMemory.argtypes;K.WriteProcessMemory.restype=ctypes.c_int
K.CloseHandle.argtypes=[ctypes.c_void_p]
class Game:
 def __init__(self,write=False):
  meta=process_metadata();self.pid=int(meta['Pid']);self.base=int(meta['Base']);self.write_allowed=write
  path=Path(meta['Path']);h=hashlib.sha256()
  with path.open('rb') as f:
   while b:=f.read(8*1024*1024):h.update(b)
  if h.hexdigest()!=PROFILE['sha256']:raise RuntimeError('This game build has not been validated.')
  self.handle=K.OpenProcess(0x438 if write else 0x410,False,self.pid)
  if not self.handle:raise ctypes.WinError(ctypes.get_last_error())
  try:self.resolve()
  except BaseException:self.close();raise
 def close(self):
  if self.handle:K.CloseHandle(self.handle);self.handle=None
 def __enter__(self):return self
 def __exit__(self,*args):self.close()
 def read(self,address,n):
  if not 0x10000<=address<0x7fffffffffff or not 0<n<=16*1024*1024:raise RuntimeError('Invalid memory range')
  buf=ctypes.create_string_buffer(n);got=ctypes.c_size_t()
  if not K.ReadProcessMemory(self.handle,address,buf,n,ctypes.byref(got)):raise ctypes.WinError(ctypes.get_last_error())
  if got.value!=n:raise RuntimeError('Incomplete memory read')
  return buf.raw
 def u64(self,a):return struct.unpack('<Q',self.read(a,8))[0]
 def u32(self,a):return struct.unpack('<I',self.read(a,4))[0]
 def write(self,address,data):
  if not self.write_allowed:raise RuntimeError('Read-only connection')
  n=ctypes.c_size_t();buf=ctypes.create_string_buffer(data)
  if not K.WriteProcessMemory(self.handle,address,buf,len(data),ctypes.byref(n)):raise ctypes.WinError(ctypes.get_last_error())
  if n.value!=len(data) or self.read(address,len(data))!=data:raise RuntimeError('Memory write verification failed')
 def resolve(self):
  site=self.base+PROFILE['manager_call_rva'];code=self.read(site,24)
  if code[0]!=0xe8 or code[17:24]!=bytes.fromhex('4c8b8120020000'):raise RuntimeError('Operative signature mismatch')
  getter=site+5+struct.unpack_from('<i',code,1)[0];code=self.read(getter,80)
  if code[5:8]!=bytes.fromhex('488b35') or code[39:42]!=bytes.fromhex('488d15'):raise RuntimeError('Manager lookup layout mismatch')
  engine=self.u64(getter+12+struct.unpack_from('<i',code,8)[0]);key_ptr=getter+46+struct.unpack_from('<i',code,42)[0]
  if self.read(key_ptr+8,22)!=b'COperativeTeamManager\0':raise RuntimeError('Wrong service key')
  registry=self.u64(engine+0x78);flags=self.u64(registry+0x20);count=(flags>>32)&0x7fffffff
  if not 0<count<4096:raise RuntimeError('Invalid service count')
  array=registry+0x28 if flags&(1<<63) else self.u64(registry+0x28);records=self.read(array,count*16);key=self.u32(key_ptr)
  hits=[struct.unpack_from('<Q',records,i*16+8)[0] for i in range(count) if struct.unpack_from('<I',records,i*16)[0]==key]
  if len(hits)!=1:raise RuntimeError('Operative manager is not unique')
  self.manager=hits[0];ca=self.base+PROFILE['census_instruction_rva'];code=self.read(ca,7)
  if code[:3]!=bytes.fromhex('488935'):raise RuntimeError('Census signature mismatch')
  self.census=self.u64(ca+7+struct.unpack_from('<i',code,3)[0])
 def roster(self):
  n=self.u32(self.manager+0xe0)
  if not 0<n<=64:raise RuntimeError('Team is unavailable. Load single-player first.')
  actors={};count=self.u32(self.census+0x9c)
  if not 0<count<100000:raise RuntimeError('Invalid census count')
  for ptr in struct.unpack('<'+'Q'*count,self.read(self.u64(self.census+0xa0),count*8)):
   ident,npc=struct.unpack('<QQ',self.read(ptr+0x10,16));actors[ident]=npc
  result=[]
  for index in range(n):
   op=self.u64(self.manager+0x108+8*index);ident=self.u64(op+0x1a0);npc=actors.get(ident)
   if not npc:raise RuntimeError('A team member could not be resolved through census data')
   appearance=self.read(op+0x150,24);bits=int.from_bytes(appearance,'big')
   if bits>>183!=12 or (bits>>179)&15!=2:raise RuntimeError('Unsupported appearance format')
   metadata=self.u64(npc+0xb8);tags=self.u64(metadata+0x18);desc=self.u64(metadata+0x60)
   first=CAT['first_names'].get(str(self.u32(desc+0x214)),'Unknown');last=CAT['last_names'].get(str(self.u32(desc+0x32c)),'')
   last='' if last=='<Empty>' else last
   gender=self.read(tags+0x98,16);gender_id=struct.unpack_from('<I',gender)[0]
   if gender_id not in (1,2) or struct.unpack_from('<I',gender,12)[0]!=gender_id:raise RuntimeError('Unsupported gender-tag representation')
   voice=self.u32(npc+0x48);profile=self.u64(self.u64(npc+0x40)+8);deck=self.u64(self.u64(npc+0x70)+8)
   result.append(dict(index=index,id=f'{ident:016X}',name=(first+' '+last).strip(),op=op,npc=npc,tags=tags,gender='Male' if gender_id==1 else 'Female',voice=voice,voice_profile=profile,deck_id=f'{deck:016X}',appearance=appearance.hex(),defaults=self.read(op+0xf8,24).hex(),npc_voice=self.read(tags+0x230,16).hex(),fields={k:decode(appearance,k) for k in FIELDS}))
  return result
 def target(self,ident):
  hits=[r for r in self.roster() if r['id']==ident]
  if len(hits)!=1:raise RuntimeError('Selected operative is no longer in this team')
  return hits[0]
 def locations(self,row):return dict(appearance=(row['op']+0x150,24),defaults=(row['op']+0xf8,24),gender=(row['tags']+0x98,16),voice=(row['npc']+0x48,4),npc_voice=(row['tags']+0x230,16))
 def apply(self,ident,appearance,gender,voice,npc_voice=None):
  row=self.target(ident);b=bytes.fromhex(appearance)
  if len(b)!=24 or int.from_bytes(b,'big')>>183!=12 or (int.from_bytes(b,'big')>>179)&15!=2:raise RuntimeError('Invalid appearance preset')
  if gender not in ('Male','Female'):raise RuntimeError('Invalid gender')
  if str(voice) not in CAT['voices']:raise RuntimeError('Unknown voice choice')
  g=1 if gender=='Male' else 2;new=dict(appearance=b,defaults=b,gender=struct.pack('<IIII',g,0,0,g),voice=struct.pack('<I',voice))
  if npc_voice is not None:
   nv=bytes.fromhex(npc_voice)
   if len(nv)!=16:raise RuntimeError('Invalid NPC voice tag')
   new['npc_voice']=nv
  locations=self.locations(row);old={k:self.read(*locations[k]) for k in new};backup=backup_saves()
  log=dict(status='prepared',pid=self.pid,id=ident,name=row['name'],original_deck_id=row['deck_id'],save_backup=str(backup),before={k:v.hex() for k,v in old.items()},after={k:v.hex() for k,v in new.items()})
  folder=P/'Backups';folder.mkdir(exist_ok=True);record=folder/(datetime.datetime.now().strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:8]+'.json');save_json(record,log)
  changed=[]
  try:
   current=self.target(ident)
   if current['op']!=row['op'] or current['npc']!=row['npc'] or current['tags']!=row['tags']:raise RuntimeError('Operative moved during preparation')
   for key in new:
    if self.read(*locations[key])!=old[key]:raise RuntimeError('Game data changed while preparing the edit')
   for key,value in new.items():
    changed.append(key);self.write(locations[key][0],value)
   current=self.target(ident)
   if current['deck_id']!=row['deck_id']:raise RuntimeError('Character deck changed unexpectedly')
   log['status']='applied';save_json(record,log)
   return str(record)
  except BaseException:
   for key in reversed(changed):self.write(locations[key][0],old[key])
   log['status']='rolled_back';save_json(record,log);raise
 def undo(self,record):
  record=Path(record);log=json.loads(record.read_text(encoding='utf-8'))
  if log['status']!='applied':raise RuntimeError('This change cannot be undone again')
  row=self.target(log['id']);locations=self.locations(row)
  for key,expected in log['after'].items():
   if self.read(*locations[key]).hex()!=expected:raise RuntimeError('Operative appearance changed since this edit. Undo stopped to preserve later changes.')
  changed=[]
  try:
   for key,old in log['before'].items():changed.append(key);self.write(locations[key][0],bytes.fromhex(old))
  except BaseException:
   for key in reversed(changed):self.write(locations[key][0],bytes.fromhex(log['after'][key]))
   raise
  log['status']='undone';save_json(record,log)
 def restore_captured(self,ident):
  baseline=restore_baseline(ident);row=self.target(ident);locations=self.locations(row)
  new={key:bytes.fromhex(value) for key,value in baseline['values'].items()}
  old={key:self.read(*locations[key]) for key in new}
  if old==new:raise RuntimeError('This operative already matches the first captured state.')
  guard=self.wardrobe_guard(row)
  protected={key:value for key,value in guard.items() if key not in ('gender','voice','npc_voice')}
  backup=backup_saves()
  log=dict(kind='restore',status='prepared',pid=self.pid,id=ident,name=row['name'],baseline_sources=baseline['sources'],save_backup=str(backup),before={k:v.hex() for k,v in old.items()},after={k:v.hex() for k,v in new.items()})
  folder=P/'Backups';folder.mkdir(exist_ok=True);record=folder/(datetime.datetime.now().strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:8]+'.json');save_json(record,log)
  changed=[]
  try:
   current=self.target(ident)
   if any(current[key]!=row[key] for key in ('op','npc','tags')):raise RuntimeError('Operative moved during restoration preparation')
   if {k:v for k,v in self.wardrobe_guard(current).items() if k not in ('gender','voice','npc_voice')}!=protected:raise RuntimeError('Protected state changed; restoration stopped')
   if any(self.read(*locations[key])!=old[key] for key in new):raise RuntimeError('Appearance changed during backup; refresh and try again')
   for key,value in new.items():changed.append(key);self.write(locations[key][0],value)
   current=self.target(ident)
   if any(current[key]!=row[key] for key in ('op','npc','tags')):raise RuntimeError('Operative moved during restoration')
   if {k:v for k,v in self.wardrobe_guard(current).items() if k not in ('gender','voice','npc_voice')}!=protected:raise RuntimeError('Protected state changed during restoration')
   if any(self.read(*locations[key])!=value for key,value in new.items()):raise RuntimeError('Restoration verification failed')
   log['status']='applied';save_json(record,log);return str(record)
  except BaseException:
   for key in reversed(changed):self.write(locations[key][0],old[key])
   log['status']='rolled_back';save_json(record,log);raise
 def wardrobe_guard(self,row):
  """Read stable protected values; they are never transaction write targets."""
  npc=row['npc'];op=row['op'];tags=row['tags']
  capacity,count=struct.unpack('<II',self.read(op+0xa8,8));inventory=self.u64(op+0xb0)
  if not 0<=count<=capacity<=512:raise RuntimeError('Unsupported inventory header; no outfit edit made')
  perks=self.read(npc+0x90,16);cap,length,flags=struct.unpack_from('<IHH',perks)
  if not 0<=length<=cap<=256:raise RuntimeError('Unsupported perk header; no outfit edit made')
  if flags&0x8000:
   if length>2:raise RuntimeError('Unsupported inline perk data')
   perkdata=perks[8:8+length*4]
  else:perkdata=self.read(self.u64(npc+0x98),length*4) if length else b''
  values=dict(identity=self.read(op+0x1a0,8),gender=self.read(tags+0x98,16),voice=self.read(npc+0x48,4),npc_voice=self.read(tags+0x230,16),voice_profile=self.read(npc+0x40,8)+struct.pack('<Q',row['voice_profile']),deck=self.read(npc+0x70,8)+struct.pack('<Q',self.u64(self.u64(npc+0x70)+8)),perks=perks+perkdata,inventory_header=self.read(op+0xa8,16),inventory=self.read(inventory,count*24) if count else b'',occupation_group=self.read(tags+0x1b8,16))
  return {key:value.hex() for key,value in values.items()}
 def apply_wardrobe(self,ident,preset):
  from wardrobe import patches,CLOTHING
  row=self.target(ident);new=patches(preset,row)
  locations={key:self.locations(row)[key] for key in new}
  old={key:self.read(*locations[key]) for key in new}
  if any(old[key].hex()!=row[key] for key in old):raise RuntimeError('Appearance changed during preparation; refresh and try again')
  if all(new[key]==old[key] for key in new):raise RuntimeError('This outfit is already applied; no edit or backup was needed')
  guard=self.wardrobe_guard(row);backup=backup_saves()
  log=dict(kind='wardrobe',status='prepared',pid=self.pid,id=ident,name=row['name'],preset_name=preset['name'],model_id=preset['model_id'],write_fields=list(new),clothing_fields=list(CLOTHING),original_deck_id=row['deck_id'],protected_before=guard,save_backup=str(backup),before={k:v.hex() for k,v in old.items()},after={k:v.hex() for k,v in new.items()})
  folder=P/'Backups';folder.mkdir(exist_ok=True);record=folder/(datetime.datetime.now().strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:8]+'.json');save_json(record,log)
  changed=[]
  try:
   current=self.target(ident)
   if any(current[key]!=row[key] for key in ('op','npc','tags')):raise RuntimeError('Operative moved during preparation')
   patches(preset,current)
   if self.wardrobe_guard(current)!=guard:raise RuntimeError('Protected operative state changed during preparation')
   for key in new:
    if self.read(*locations[key])!=old[key]:raise RuntimeError('Outfit changed while backing up; refresh and try again')
   for key,value in new.items():
    changed.append(key);self.write(locations[key][0],value)
   current=self.target(ident)
   if any(current[key]!=row[key] for key in ('op','npc','tags')):raise RuntimeError('Operative moved during the edit')
   if self.wardrobe_guard(current)!=guard:raise RuntimeError('Protected operative state changed during the edit; clothing rolled back')
   for key,value in new.items():
    if self.read(*locations[key])!=value:raise RuntimeError('Outfit readback differs')
   log['protected_after']=self.wardrobe_guard(current);log['status']='applied';save_json(record,log);return str(record)
  except BaseException:
   for key in reversed(changed):self.write(locations[key][0],old[key])
   log['status']='rolled_back';save_json(record,log);raise
def restore_baseline(ident):
 if not isinstance(ident,str) or len(ident)!=16 or any(c not in '0123456789ABCDEF' for c in ident):raise ValueError('Invalid operative identity')
 widths=dict(appearance=24,defaults=24,gender=16,voice=4,npc_voice=16);values={};sources={}
 for path in sorted((P/'Backups').glob('*.json')):
  log=json.loads(path.read_text(encoding='utf-8'))
  if log.get('id')!=ident or log.get('status') not in ('applied','undone') or log.get('kind')=='restore':continue
  if log.get('kind') not in (None,'wardrobe'):continue
  for key,value in log.get('before',{}).items():
   if key not in widths or key in values:continue
   raw=bytes.fromhex(value)
   if len(raw)!=widths[key]:raise ValueError('Invalid baseline record: '+path.name)
   values[key]=raw.hex();sources[key]=path.name
 if not all(key in values for key in ('appearance','defaults','gender','voice')):raise ValueError('No complete appearance/voice baseline is available for this operative. No restoration made.')
 raw=bytes.fromhex(values['appearance']);bits=int.from_bytes(raw,'big')
 if bits>>183!=12 or (bits>>179)&15!=2:raise ValueError('Unsupported captured appearance format')
 if bytes.fromhex(values['gender']) not in (struct.pack('<IIII',1,0,0,1),struct.pack('<IIII',2,0,0,2)):raise ValueError('Invalid captured gender tags')
 if str(struct.unpack('<I',bytes.fromhex(values['voice']))[0]) not in CAT['voices']:raise ValueError('Unknown captured voice')
 return dict(values=values,sources=sources)

def backup_saves():
 root=Path(r'C:\Program Files (x86)\Ubisoft\Ubisoft Game Launcher\savegames')
 folders=list(root.glob('*/7017'))+list(root.glob('*/3353'))
 folders=[p for p in folders if any(p.glob('*.save'))]
 if not folders:raise RuntimeError('Legion save directory was not found; no edit made')
 files=[p for folder in folders for p in folder.glob('*.save')];payload=None
 for attempt in range(3):
  candidate={p:p.read_bytes() for p in files}
  if all(p.read_bytes()==blob for p,blob in candidate.items()):payload=candidate;break
 if payload is None:raise RuntimeError('An autosave is in progress; try again after it finishes')
 dest=P/'Backups'/('saves-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:8]);dest.mkdir(parents=True)
 manifest=[]
 for src,data in payload.items():
  out=dest/src.parent.name/src.name;out.parent.mkdir(exist_ok=True);out.write_bytes(data)
  if out.read_bytes()!=data:raise RuntimeError('Save backup verification failed')
  manifest.append(dict(source=str(src),file=str(out.relative_to(dest)),sha256=hashlib.sha256(data).hexdigest()))
 save_json(dest/'manifest.json',manifest);return dest
