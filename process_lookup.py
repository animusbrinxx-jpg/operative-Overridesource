"""Native, read-only discovery of the named Legion process and DX11 module."""
import ctypes
from ctypes import wintypes as w
K=ctypes.WinDLL('kernel32',use_last_error=True)
class ProcessEntry(ctypes.Structure):
 _fields_=[('dwSize',w.DWORD),('cntUsage',w.DWORD),('th32ProcessID',w.DWORD),('th32DefaultHeapID',ctypes.c_size_t),('th32ModuleID',w.DWORD),('cntThreads',w.DWORD),('th32ParentProcessID',w.DWORD),('pcPriClassBase',w.LONG),('dwFlags',w.DWORD),('szExeFile',w.WCHAR*260)]
class ModuleEntry(ctypes.Structure):
 _fields_=[('dwSize',w.DWORD),('th32ModuleID',w.DWORD),('th32ProcessID',w.DWORD),('GlblcntUsage',w.DWORD),('ProccntUsage',w.DWORD),('modBaseAddr',ctypes.c_void_p),('modBaseSize',w.DWORD),('hModule',w.HMODULE),('szModule',w.WCHAR*256),('szExePath',w.WCHAR*260)]
K.CreateToolhelp32Snapshot.argtypes=[w.DWORD,w.DWORD];K.CreateToolhelp32Snapshot.restype=w.HANDLE
K.CloseHandle.argtypes=[w.HANDLE];K.CloseHandle.restype=w.BOOL
for name,kind in [('Process32FirstW',ProcessEntry),('Process32NextW',ProcessEntry),('Module32FirstW',ModuleEntry),('Module32NextW',ModuleEntry)]:
 function=getattr(K,name);function.argtypes=[w.HANDLE,ctypes.POINTER(kind)];function.restype=w.BOOL

def entries(flags,pid,kind,first,next_entry):
 handle=None
 for attempt in range(3):
  handle=K.CreateToolhelp32Snapshot(flags,pid)
  if handle!=ctypes.c_void_p(-1).value:break
  error=ctypes.get_last_error()
  if error!=24:raise ctypes.WinError(error)
 else:raise RuntimeError('Game modules changed while connecting; try Refresh again.')
 try:
  entry=kind();entry.dwSize=ctypes.sizeof(kind)
  if not first(handle,ctypes.byref(entry)):
   error=ctypes.get_last_error()
   if error==18:return
   raise ctypes.WinError(error)
  while True:
   yield entry
   if not next_entry(handle,ctypes.byref(entry)):
    error=ctypes.get_last_error()
    if error!=18:raise ctypes.WinError(error)
    break
 finally:K.CloseHandle(handle)

def process_metadata():
 hits=[entry.th32ProcessID for entry in entries(2,0,ProcessEntry,K.Process32FirstW,K.Process32NextW) if entry.szExeFile.lower()=='watchdogslegion.exe']
 if not hits:raise RuntimeError('Legion is not running. Load your single-player save first.')
 if len(hits)!=1:raise RuntimeError('Expected one Legion process; close duplicate game instances.')
 pid=hits[0]
 for entry in entries(8|16,pid,ModuleEntry,K.Module32FirstW,K.Module32NextW):
  if entry.szModule.lower()=='duniademo_clang_64_dx11.dll':return dict(Pid=pid,Base=entry.modBaseAddr,Path=entry.szExePath)
 raise RuntimeError('The Legion DirectX 11 module was not found. Use DirectX 11 and load your save.')
