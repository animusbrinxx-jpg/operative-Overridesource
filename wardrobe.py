"""Named wardrobe presets. Only unpacked clothing fields are supported."""
from pathlib import Path
import json,uuid,datetime,unicodedata
from studio_backend import P,FIELDS,decode,encode,save_json

CLOTHING=('outfit','innerwear','outerwear','legwear','footwear','handwear','headwear','earrings','bag')

def unpacked(raw):
 return len(raw)==24 and int.from_bytes(raw,'big')>>183==12 and (int.from_bytes(raw,'big')>>179)&15==2

def validate(preset):
 required={'schema','name','operative_id','operative_name','model_id','clothing','captured_at'}
 if not isinstance(preset,dict) or set(preset)!=required or preset['schema']!='legion-wardrobe-v1':raise ValueError('Invalid wardrobe preset schema')
 ident=preset['operative_id']
 if not isinstance(ident,str) or len(ident)!=16 or any(c not in '0123456789ABCDEF' for c in ident):raise ValueError('Invalid source operative identity')
 name=preset['name']
 if not isinstance(name,str) or not name.strip() or len(name)>80 or any(unicodedata.category(c).startswith('C') for c in name):raise ValueError('Use a preset name of 1–80 characters without control characters')
 if not isinstance(preset['operative_name'],str) or not isinstance(preset['captured_at'],str):raise ValueError('Invalid capture metadata')
 if type(preset['model_id']) is not int or not 0<=preset['model_id']<1<<FIELDS['model']['width']:raise ValueError('Invalid source body model')
 values=preset['clothing']
 if not isinstance(values,dict) or set(values)!=set(CLOTHING):raise ValueError('A wardrobe preset must contain only the nine clothing/accessory fields')
 for key,value in values.items():
  if type(value) is not int or not 0<=value<1<<FIELDS[key]['width']:raise ValueError('Invalid clothing identifier: '+key)
 return preset

def capture(row,name):
 raw=bytes.fromhex(row['appearance'])
 if not unpacked(raw):raise ValueError('Current appearance is not in the supported unpacked format')
 return validate(dict(schema='legion-wardrobe-v1',name=name.strip(),operative_id=row['id'],operative_name=row['name'],model_id=decode(raw,'model'),clothing={key:decode(raw,key) for key in CLOTHING},captured_at=datetime.datetime.now(datetime.timezone.utc).isoformat()))

def incompatible(preset,row):
 validate(preset)
 if preset['operative_id']!=row['id']:return 'Incompatible: this outfit was captured from a different operative.'
 raw=bytes.fromhex(row['appearance']);defaults=bytes.fromhex(row['defaults'])
 if not unpacked(raw):return 'Incompatible: current appearance is not in the supported unpacked format.'
 if preset['model_id']!=decode(raw,'model'):return 'Incompatible: the operative’s body model has changed since this outfit was captured.'
 if not unpacked(defaults):return 'Incompatible: wardrobe defaults are still packed. This first version cannot safely convert them.'
 if decode(defaults,'model')!=decode(raw,'model'):return 'Incompatible: wardrobe defaults use a different body model.'
 return None

def patches(preset,row):
 reason=incompatible(preset,row)
 if reason:raise ValueError(reason)
 return {key:encode(bytes.fromhex(row[key]),preset['clothing']) for key in ('appearance','defaults')}

class Library:
 def __init__(self,root=None):self.root=Path(root) if root is not None else P/'WardrobePresets'
 def save(self,preset):
  validate(preset);folder=self.root/preset['operative_id'];folder.mkdir(parents=True,exist_ok=True)
  path=folder/(uuid.uuid4().hex+'.json');save_json(path,preset);return path
 def list(self,ident):
  if not isinstance(ident,str) or len(ident)!=16 or any(c not in '0123456789ABCDEF' for c in ident):raise ValueError('Invalid operative identity')
  result=[];errors=[]
  for path in (self.root/ident).glob('*.json'):
   try:
    if path.stat().st_size>32768:raise ValueError('Preset file is too large')
    item=validate(json.loads(path.read_text(encoding='utf-8')))
    if item['operative_id']!=ident:raise ValueError('Source identity does not match its library folder')
    result.append((path,item))
   except (OSError,ValueError) as e:errors.append(f'{path.name}: {e}')
  return sorted(result,key=lambda item:(item[1]['name'].casefold(),item[1]['captured_at'])),errors
