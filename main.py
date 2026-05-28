from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.clock import Clock
import threading, smtplib, json, os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

CONFIG = os.path.expanduser('~/.smsfwd.json')

def load_cfg():
    d = {'sender':'','password':'','recipient':'hamzatalat8@gmail.com'}
    try:
        if os.path.exists(CONFIG):
            d.update(json.load(open(CONFIG)))
    except: pass
    return d

def save_cfg(c):
    json.dump(c, open(CONFIG,'w'))

def send_mail(cfg, subj, body):
    try:
        msg = MIMEMultipart()
        msg['From'] = cfg['sender']
        msg['To'] = cfg['recipient']
        msg['Subject'] = subj
        msg.attach(MIMEText(body,'plain','utf-8'))
        with smtplib.SMTP_SSL('smtp.gmail.com',465,timeout=20) as s:
            s.login(cfg['sender'],cfg['password'])
            s.sendmail(cfg['sender'],cfg['recipient'],msg.as_string())
        return True,'OK'
    except Exception as e:
        return False,str(e)

class MainScreen(Screen):
    def __init__(self,**kw):
        super().__init__(**kw)
        self.active = False
        self._stop = threading.Event()
        self.cfg = load_cfg()
        root = BoxLayout(orientation='vertical',padding=20,spacing=10)
        root.add_widget(Label(text='SMS Forwarder',font_size=24,size_hint_y=None,height=60))
        self.status = Label(text='[color=ff4444]متوقف[/color]',markup=True,font_size=20,size_hint_y=None,height=50)
        root.add_widget(self.status)
        root.add_widget(Label(text='بريدك:',size_hint_y=None,height=30))
        self.inp_sender = TextInput(text=self.cfg.get('sender',''),multiline=False,size_hint_y=None,height=44)
        root.add_widget(self.inp_sender)
        root.add_widget(Label(text='App Password:',size_hint_y=None,height=30))
        self.inp_pass = TextInput(text=self.cfg.get('password',''),password=True,multiline=False,size_hint_y=None,height=44)
        root.add_widget(self.inp_pass)
        root.add_widget(Label(text='البريد المستقبل:',size_hint_y=None,height=30))
        self.inp_recv = TextInput(text=self.cfg.get('recipient','hamzatalat8@gmail.com'),multiline=False,size_hint_y=None,height=44)
        root.add_widget(self.inp_recv)
        self.btn = Button(text='تشغيل',size_hint_y=None,height=60,font_size=20)
        self.btn.bind(on_press=self.toggle)
        root.add_widget(self.btn)
        self.btn_test = Button(text='اختبار الارسال',size_hint_y=None,height=50)
        self.btn_test.bind(on_press=self.test)
        root.add_widget(self.btn_test)
        self.log = Label(text='جاهز',size_hint_y=None,height=80,halign='center')
        root.add_widget(self.log)
        self.add_widget(root)

    def save(self):
        self.cfg['sender'] = self.inp_sender.text.strip()
        self.cfg['password'] = self.inp_pass.text.strip()
        self.cfg['recipient'] = self.inp_recv.text.strip()
        save_cfg(self.cfg)

    def toggle(self,*a):
        if not self.active:
            self.save()
            self.active = True
            self._stop.clear()
            self.btn.text = 'ايقاف'
            self.status.text = '[color=00ff00]يعمل[/color]'
            threading.Thread(target=self._loop,daemon=True).start()
        else:
            self.active = False
            self._stop.set()
            self.btn.text = 'تشغيل'
            self.status.text = '[color=ff4444]متوقف[/color]'

    def test(self,*a):
        self.save()
        def _t():
            ok,msg = send_mail(self.cfg,'اختبار SMS Forwarder',f'التطبيق يعمل\n{datetime.now()}')
            Clock.schedule_once(lambda dt: setattr(self.log,'text','تم الارسال' if ok else f'خطا: {msg}'),0)
        threading.Thread(target=_t,daemon=True).start()
        self.log.text = 'جاري الارسال...'

    def _loop(self):
        sent_sms = set()
        sent_calls = set()
        try:
            from jnius import autoclass
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            Uri = autoclass('android.net.Uri')
            ANDROID = True
        except:
            ANDROID = False
        while not self._stop.is_set():
            try:
                if ANDROID:
                    ctx = PythonActivity.mActivity
                    uri = Uri.parse('content://sms/inbox')
                    cur = ctx.getContentResolver().query(uri,None,None,None,'date DESC')
                    if cur and cur.moveToFirst():
                        for _ in range(min(cur.getCount(),10)):
                            row = {c:cur.getString(cur.getColumnIndex(c)) for c in ['_id','address','body']}
                            if row['_id'] and row['_id'] not in sent_sms:
                                ok,_ = send_mail(self.cfg,f"SMS من {row['address']}",row['body'] or '')
                                if ok:
                                    sent_sms.add(row['_id'])
                                    Clock.schedule_once(lambda dt,n=row['address']: setattr(self.log,'text',f'SMS من {n}'),0)
                            if not cur.moveToNext(): break
                        cur.close()
                    uri2 = Uri.parse('content://call_log/calls')
                    cur2 = ctx.getContentResolver().query(uri2,None,None,None,'date DESC')
                    if cur2 and cur2.moveToFirst():
                        for _ in range(min(cur2.getCount(),5)):
                            row = {c:cur2.getString(cur2.getColumnIndex(c)) for c in ['number','type','duration','date']}
                            uid = str(row.get('date',''))+str(row.get('number',''))
                            t = {'1':'واردة','2':'صادرة','3':'فائتة'}.get(str(row.get('type','')),'؟')
                            if uid not in sent_calls:
                                ok,_ = send_mail(self.cfg,f"مكالمة {t} - {row['number']}",f"الرقم: {row['number']}\nالنوع: {t}\nالمدة: {row['duration']} ثانية")
                                if ok:
                                    sent_calls.add(uid)
                                    Clock.schedule_once(lambda dt,n=row['number'],tp=t: setattr(self.log,'text',f'مكالمة {tp} من {n}'),0)
                            if not cur2.moveToNext(): break
                        cur2.close()
            except Exception as e:
                Clock.schedule_once(lambda dt,err=str(e): setattr(self.log,'text',f'خطا: {err[:50]}'),0)
            self._stop.wait(30)

class SMSApp(App):
    def build(self):
        sm = ScreenManager()
        sm.add_widget(MainScreen(name='main'))
        return sm

if __name__ == '__main__':
    SMSApp().run()
