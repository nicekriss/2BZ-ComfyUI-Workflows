"""Windows GUI; frozen with Python/Tk so clients need no separate installer Python."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import queue
import sys
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from setup_core import Engine, SetupError, resolve_root

DATA=Path(getattr(sys,'_MEIPASS',Path(__file__).parent))/'data'
def state_for(root):
    identity=hashlib.sha256(str(Path(root).resolve()).lower().encode()).hexdigest()[:12]
    return Path(os.environ.get('LOCALAPPDATA',Path.home()))/'TooBusyAI'/'Setup'/identity

def cli():
    parser=argparse.ArgumentParser();parser.add_argument('--inspect');parser.add_argument('--verify');parser.add_argument('--url',default='http://127.0.0.1:8188');parser.add_argument('--data');parser.add_argument('--report')
    args=parser.parse_args()
    root=args.inspect or args.verify
    if not root:return False
    messages=[];engine=Engine(args.data or DATA,state_for(root),messages.append)
    result={}
    try:
        if args.inspect:result=engine.inspect(root)
        else:engine.verify(root,args.url);result={'verified':True}
        result['ok']=True
    except Exception as exc:result={'ok':False,'error':str(exc)}
    result['messages']=messages
    if args.report:Path(args.report).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    elif sys.stdout:print(json.dumps(result,ensure_ascii=False,indent=2))
    if not result['ok']:raise SystemExit(1)
    return True

def gui():
    window=tk.Tk();window.title('TooBusy AI 설치 도우미');window.geometry('800x730');window.minsize(760,680)
    window.configure(bg='#17212c');style=ttk.Style();style.theme_use('clam')
    style.configure('.',font=('맑은 고딕',10));style.configure('TFrame',background='#17212c');style.configure('TLabel',background='#17212c',foreground='#e5edf7')
    style.configure('TButton',padding=(12,8),background='#31465b',foreground='#e5edf7');style.map('TButton',background=[('active','#44617d')])
    style.configure('Accent.TButton',background='#83d6ff',foreground='#122432');style.configure('Title.TLabel',font=('맑은 고딕',22,'bold'))
    frame=ttk.Frame(window,padding=24);frame.pack(fill='both',expand=True)
    ttk.Label(frame,text='TooBusy AI 설치',style='Title.TLabel').pack(anchor='w')
    ttk.Label(frame,text='기존 ComfyUI에 필요한 노드·모델과 포토샵 플러그인을 준비합니다.').pack(anchor='w',pady=(6,20))
    rootvar=tk.StringVar();extrav=tk.StringVar();urlvar=tk.StringVar(value='http://127.0.0.1:8188');status=tk.StringVar(value='ComfyUI 폴더를 선택하고 설치 전 점검을 누르세요.')
    controls=[]
    def browse(variable):
        folder=filedialog.askdirectory(parent=window)
        if folder:variable.set(folder)
    for label,var in [('ComfyUI 폴더 (main.py가 있는 폴더)',rootvar),('공유 모델 폴더 (선택 · 모델을 다른 드라이브에서 쓰는 경우)',extrav)]:
        ttk.Label(frame,text=label).pack(anchor='w');row=ttk.Frame(frame);row.pack(fill='x',pady=(4,10))
        entry=ttk.Entry(row,textvariable=var);entry.pack(side='left',fill='x',expand=True);controls.append(entry)
        button=ttk.Button(row,text='폴더 선택',command=lambda v=var:browse(v));button.pack(side='right',padx=(8,0));controls.append(button)
    row=ttk.Frame(frame);row.pack(fill='x');ttk.Label(row,text='ComfyUI 주소').pack(side='left');entry=ttk.Entry(row,textvariable=urlvar,width=36);entry.pack(side='left',padx=12);controls.append(entry)
    ttk.Label(frame,text='① 점검 → ComfyUI 종료 → ② 설치 → ComfyUI 재실행 → ③ 연결 검사',foreground='#90d9ff').pack(anchor='w',pady=(18,8))
    actions=ttk.Frame(frame);actions.pack(fill='x')
    events=queue.Queue();working=False;cancel=threading.Event()
    log=tk.Text(frame,height=13,bg='#0f1720',fg='#d5e3f1',insertbackground='white',relief='flat',font=('맑은 고딕',9),wrap='word',state='disabled');log.pack(fill='both',expand=True,pady=(14,10))
    def engine():
        root=resolve_root(rootvar.get());return root,Engine(DATA,state_for(root),lambda text:events.put(('log',text)),cancel.is_set)
    def task(action):
        nonlocal working
        if working:return
        try:root,e=engine()
        except Exception as exc:messagebox.showerror('폴더 확인',str(exc),parent=window);return
        url=urlvar.get().strip();extra=extrav.get().strip() or None;working=True;cancel.clear()
        for c in controls:c.configure(state='disabled')
        stop.configure(state='normal');status.set('진행 중… 자세한 내용은 아래 기록에서 확인하세요.')
        def worker():
            try:
                if action=='inspect':e.inspect(root,extra);message='점검 완료. 설치할 때는 ComfyUI를 종료하세요.'
                elif action=='install':e.install(root,url,extra);message='파일 준비 완료. ComfyUI를 다시 실행하고 연결 검사를 누르세요.'
                else:e.verify(root,url);message='연결 검사 통과. 포토샵 설치 후 연결 파일을 열어주세요.'
                events.put(('done',message))
            except Exception as exc:events.put(('error',str(exc)))
        threading.Thread(target=worker,daemon=True).start()
    for title,action in [('① 설치 전 점검','inspect'),('② 필요한 항목 설치','install'),('③ 연결 검사','verify')]:
        b=ttk.Button(actions,text=title,command=lambda a=action:task(a),style='Accent.TButton' if action=='install' else 'TButton');b.pack(side='left',padx=(0,8));controls.append(b)
    stop=ttk.Button(actions,text='중지',command=cancel.set,state='disabled');stop.pack(side='right')
    ttk.Label(frame,textvariable=status,wraplength=735).pack(anchor='w',pady=(0,10))
    bottom=ttk.Frame(frame);bottom.pack(fill='x')
    def install_ps():
        try:
            root,e=engine();os.startfile(e.export_plugin());status.set('Creative Cloud의 설치 안내를 완료하세요. 이후 플러그인 연결 설정에서 연결 파일을 열면 됩니다.')
        except Exception as exc:messagebox.showerror('포토샵 설치',str(exc),parent=window)
    def connection_folder():
        try:
            root,e=engine();os.startfile(e.state)
        except Exception as exc:messagebox.showerror('설치 결과',str(exc),parent=window)
    for title,command in [('④ 포토샵 플러그인 설치',install_ps),('연결 파일·설치 결과 폴더',connection_folder)]:
        b=ttk.Button(bottom,text=title,command=command);b.pack(side='left',padx=(0,10));controls.append(b)
    ttk.Label(frame,text='최초 모델 다운로드는 약 18 GiB입니다. 이미 설치된 동일 파일은 확인 후 재사용합니다.\nAdobe 설치 확인과 Photoshop에서 TooBusy-connection.json 열기는 한 번만 진행하세요.',font=('맑은 고딕',9),foreground='#9aafc4',wraplength=735).pack(anchor='w',pady=(12,0))
    def poll():
        nonlocal working
        try:
            while True:
                kind,text=events.get_nowait();log.configure(state='normal');log.insert('end',text+'\n');log.see('end');log.configure(state='disabled')
                if kind in ('done','error'):
                    working=False;stop.configure(state='disabled');status.set(text)
                    for c in controls:c.configure(state='normal')
                    if kind=='error':messagebox.showerror('설치 확인 필요',text,parent=window)
        except queue.Empty:pass
        window.after(150,poll)
    def close():
        if working:cancel.set();status.set('중지 중입니다. 현재 파일 처리나 Python 의존성 설치가 끝날 때까지 기다려주세요.')
        else:window.destroy()
    window.protocol('WM_DELETE_WINDOW',close);poll();window.mainloop()

if __name__=='__main__':
    if not cli():gui()
