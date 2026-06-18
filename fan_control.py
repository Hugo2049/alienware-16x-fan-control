#!/usr/bin/env python3
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GLib
import subprocess, math

HELPER   = '/home/hbwal/Desktop/fanController/fan_helper.sh'
CPU_COLOR = (0.216, 0.540, 0.867)
GPU_COLOR = (0.114, 0.620, 0.459)
MAX_RPM   = 7000

def read_hwmon(path):
    try:
        with open(path) as f: return int(f.read().strip())
    except: return 0

def run_helper(*args):
    try: subprocess.run(['sudo', HELPER] + list(args), check=True)
    except Exception as e: print(f"Helper error: {e}")

def get_cpu_temp():
    best = 0
    for i in range(30):
        v = read_hwmon(f'/sys/class/hwmon/hwmon8/temp{i}_input')
        if v > best: best = v
    return best // 1000 if best > 1000 else best

def get_gpu_temp():
    v = read_hwmon('/sys/class/hwmon/hwmon3/temp2_input')
    return v // 1000 if v > 1000 else v

def get_fan_rpm(fan):
    for hwmon in range(10):
        try:
            name = open(f'/sys/class/hwmon/hwmon{hwmon}/name').read().strip()
            if name == 'alienware_wmi':
                return read_hwmon(f'/sys/class/hwmon/hwmon{hwmon}/fan{fan}_input')
        except: pass
    return 0

class FanGauge(Gtk.DrawingArea):
    def __init__(self, color):
        super().__init__()
        self.color   = color
        self.percent = 0
        self.rpm     = 0
        self.set_size_request(170, 170)
        self.set_draw_func(self.draw)

    def set_value(self, percent, rpm):
        self.percent = max(0, min(100, percent))
        self.rpm     = rpm
        self.queue_draw()

    def draw(self, widget, cr, w, h):
        cx, cy = w/2, h/2
        r      = min(w,h)/2 - 18
        start  = math.pi * 0.75
        end    = math.pi * 2.25
        span   = end - start

        cr.set_line_width(11)
        cr.set_line_cap(1)

        cr.set_source_rgba(0.5, 0.5, 0.5, 0.18)
        cr.arc(cx, cy, r, start, end)
        cr.stroke()

        if self.percent > 0:
            r2, g2, b2 = self.color
            cr.set_source_rgba(r2, g2, b2, 0.85)
            cr.arc(cx, cy, r, start, start + span * self.percent / 100)
            cr.stroke()

        cr.select_font_face('Sans', 0, 1)
        cr.set_font_size(22)
        cr.set_source_rgba(0.95, 0.95, 0.95, 1)
        t = f'{self.rpm:,}'
        e = cr.text_extents(t)
        cr.move_to(cx - e.width/2 - e.x_bearing, cy - 6)
        cr.show_text(t)

        cr.set_font_size(11)
        cr.set_source_rgba(0.55, 0.55, 0.55, 1)
        e2 = cr.text_extents('RPM')
        cr.move_to(cx - e2.width/2 - e2.x_bearing, cy + 13)
        cr.show_text('RPM')

        cr.set_font_size(13)
        cr.set_source_rgb(*self.color)
        pt = f'{self.percent}%'
        e3 = cr.text_extents(pt)
        cr.move_to(cx - e3.width/2 - e3.x_bearing, cy + 33)
        cr.show_text(pt)


class RpmGraph(Gtk.DrawingArea):
    HISTORY = 60

    def __init__(self):
        super().__init__()
        self.cpu_hist = []
        self.gpu_hist = []
        self.set_size_request(-1, 120)
        self.set_hexpand(True)
        self.set_draw_func(self.draw)

    def push(self, cpu_rpm, gpu_rpm):
        self.cpu_hist.append(cpu_rpm)
        self.gpu_hist.append(gpu_rpm)
        if len(self.cpu_hist) > self.HISTORY:
            self.cpu_hist.pop(0)
            self.gpu_hist.pop(0)
        self.queue_draw()

    def draw(self, widget, cr, w, h):
        pad_l, pad_r, pad_t, pad_b = 46, 10, 8, 6
        gw = w - pad_l - pad_r
        gh = h - pad_t - pad_b
        rpm_min, rpm_max = 0, MAX_RPM

        cr.set_line_width(0.5)
        cr.set_font_size(9)
        for rpm in (2000, 4000, 6000):
            y = pad_t + gh - rpm / rpm_max * gh
            cr.set_source_rgba(0.5, 0.5, 0.5, 0.15)
            cr.move_to(pad_l, y)
            cr.line_to(pad_l + gw, y)
            cr.stroke()
            cr.set_source_rgba(0.5, 0.5, 0.5, 0.55)
            lbl = f'{rpm//1000}k'
            e = cr.text_extents(lbl)
            cr.move_to(pad_l - e.width - 4, y + e.height / 2)
            cr.show_text(lbl)

        def draw_line(history, color):
            if len(history) < 2:
                return
            r, g, b = color
            cr.set_source_rgba(r, g, b, 0.85)
            cr.set_line_width(1.8)
            for i, rpm in enumerate(history):
                x = pad_l + i / (self.HISTORY - 1) * gw
                y = pad_t + gh - max(0, min(rpm, rpm_max)) / rpm_max * gh
                if i == 0:
                    cr.move_to(x, y)
                else:
                    cr.line_to(x, y)
            cr.stroke()

        draw_line(self.cpu_hist, CPU_COLOR)
        draw_line(self.gpu_hist, GPU_COLOR)

        cr.set_font_size(10)
        for i, (label, color) in enumerate([('CPU', CPU_COLOR), ('GPU', GPU_COLOR)]):
            r, g, b = color
            cr.set_source_rgba(r, g, b, 0.9)
            cr.move_to(pad_l + 6 + i * 55, pad_t + 11)
            cr.show_text(f'● {label}')


class TempGraph(Gtk.DrawingArea):
    HISTORY = 60

    def __init__(self):
        super().__init__()
        self.cpu_hist = []
        self.gpu_hist = []
        self.set_size_request(-1, 120)
        self.set_hexpand(True)
        self.set_draw_func(self.draw)

    def push(self, cpu_temp, gpu_temp):
        self.cpu_hist.append(cpu_temp)
        self.gpu_hist.append(gpu_temp)
        if len(self.cpu_hist) > self.HISTORY:
            self.cpu_hist.pop(0)
            self.gpu_hist.pop(0)
        self.queue_draw()

    def draw(self, widget, cr, w, h):
        pad_l, pad_r, pad_t, pad_b = 34, 10, 8, 6
        gw = w - pad_l - pad_r
        gh = h - pad_t - pad_b
        temp_min, temp_max = 20, 110

        # grid lines + y-axis labels
        cr.set_line_width(0.5)
        cr.set_font_size(9)
        for temp in (40, 60, 80, 100):
            y = pad_t + gh - (temp - temp_min) / (temp_max - temp_min) * gh
            cr.set_source_rgba(0.5, 0.5, 0.5, 0.15)
            cr.move_to(pad_l, y)
            cr.line_to(pad_l + gw, y)
            cr.stroke()
            cr.set_source_rgba(0.5, 0.5, 0.5, 0.55)
            lbl = f'{temp}°'
            e = cr.text_extents(lbl)
            cr.move_to(pad_l - e.width - 4, y + e.height / 2)
            cr.show_text(lbl)

        def draw_line(history, color):
            if len(history) < 2:
                return
            r, g, b = color
            cr.set_source_rgba(r, g, b, 0.85)
            cr.set_line_width(1.8)
            for i, temp in enumerate(history):
                x = pad_l + i / (self.HISTORY - 1) * gw
                y = pad_t + gh - (temp - temp_min) / (temp_max - temp_min) * gh
                y = max(pad_t, min(pad_t + gh, y))
                if i == 0:
                    cr.move_to(x, y)
                else:
                    cr.line_to(x, y)
            cr.stroke()

        draw_line(self.cpu_hist, CPU_COLOR)
        draw_line(self.gpu_hist, GPU_COLOR)

        # legend
        cr.set_font_size(10)
        for i, (label, color) in enumerate([('CPU', CPU_COLOR), ('GPU', GPU_COLOR)]):
            r, g, b = color
            cr.set_source_rgba(r, g, b, 0.9)
            cr.move_to(pad_l + 6 + i * 55, pad_t + 11)
            cr.show_text(f'● {label}')


class FanApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id='com.hbwal.fancontrol')
        self.connect('activate', self.on_activate)
        self.manual_mode = False

    def on_activate(self, app):
        self.win = Adw.ApplicationWindow(application=app)
        self.win.set_title('Fan Control')
        self.win.set_default_size(500, 960)
        self.win.set_resizable(False)

        tb = Adw.ToolbarView()
        header = Adw.HeaderBar()
        tb.add_top_bar(header)

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        root.set_margin_start(16)
        root.set_margin_end(16)
        root.set_margin_top(8)
        root.set_margin_bottom(16)

        # Title row
        tr = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        tb2 = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        tb2.set_hexpand(True)
        t1 = Gtk.Label(label='Fan control')
        t1.set_halign(Gtk.Align.START)
        t1.add_css_class('title-2')
        t2 = Gtk.Label(label='Alienware 16X Aurora · RTX 5070')
        t2.set_halign(Gtk.Align.START)
        t2.add_css_class('caption')
        t2.add_css_class('dim-label')
        tb2.append(t1)
        tb2.append(t2)
        self.mode_badge = Gtk.Label(label='Auto')
        self.mode_badge.add_css_class('tag')
        tr.append(tb2)
        tr.append(self.mode_badge)
        root.append(tr)

        # Gauges row
        gbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        for side in ('cpu', 'gpu'):
            card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            card.add_css_class('card')
            card.set_hexpand(True)

            hdr = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
            hdr.set_margin_start(12)
            hdr.set_margin_end(12)
            hdr.set_margin_top(12)

            lbl = Gtk.Label(label='CPU fan' if side=='cpu' else 'GPU fan')
            lbl.set_halign(Gtk.Align.START)
            lbl.set_hexpand(True)
            lbl.add_css_class('caption')
            lbl.add_css_class('dim-label')

            badge = Gtk.Label(label='--°C')
            badge.add_css_class('tag')
            badge.add_css_class('success')

            hdr.append(lbl)
            hdr.append(badge)
            card.append(hdr)

            gauge = FanGauge(CPU_COLOR if side=='cpu' else GPU_COLOR)
            gauge.set_halign(Gtk.Align.CENTER)
            card.append(gauge)

            slider = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1)
            slider.set_value(50)
            slider.set_margin_start(12)
            slider.set_margin_end(12)
            slider.set_margin_bottom(12)
            slider.add_mark(0, Gtk.PositionType.BOTTOM, '0%')
            slider.add_mark(50, Gtk.PositionType.BOTTOM, '50%')
            slider.add_mark(100, Gtk.PositionType.BOTTOM, '100%')
            slider.connect('value-changed', self.on_cpu_slider if side=='cpu' else self.on_gpu_slider)
            card.append(slider)

            gbox.append(card)

            if side == 'cpu':
                self.cpu_badge  = badge
                self.cpu_gauge  = gauge
                self.cpu_slider = slider
            else:
                self.gpu_badge  = badge
                self.gpu_gauge  = gauge
                self.gpu_slider = slider

        root.append(gbox)

        # Presets
        pcard = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        pcard.add_css_class('card')
        pl = Gtk.Label(label='Presets')
        pl.set_halign(Gtk.Align.START)
        pl.add_css_class('caption')
        pl.add_css_class('dim-label')
        pl.set_margin_start(12)
        pl.set_margin_top(12)
        pcard.append(pl)

        prow = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        prow.set_homogeneous(True)
        prow.set_margin_start(12)
        prow.set_margin_end(12)
        prow.set_margin_bottom(12)

        self.preset_btns = {}
        for key, label in [('auto','Auto'),('quiet','Quiet'),('balanced','Balanced'),('performance','Performance'),('gameshift','Game Shift')]:
            btn = Gtk.Button(label=label)
            btn.connect('clicked', self.on_preset, key)
            if key == 'balanced':
                btn.add_css_class('suggested-action')
            prow.append(btn)
            self.preset_btns[key] = btn

        pcard.append(prow)
        root.append(pcard)

        # Stats row
        scard = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        scard.add_css_class('card')
        self.stat_labels = {}
        for i, (key, label) in enumerate([('cpu_rpm','CPU RPM'),('gpu_rpm','GPU RPM'),('cpu_temp','CPU temp'),('gpu_temp','GPU temp')]):
            sb = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            sb.set_hexpand(True)
            sb.set_margin_top(12)
            sb.set_margin_bottom(12)
            if i > 0:
                scard.append(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL))
            l = Gtk.Label(label=label)
            l.add_css_class('caption')
            l.add_css_class('dim-label')
            l.set_halign(Gtk.Align.CENTER)
            v = Gtk.Label(label='--')
            v.add_css_class('title-4')
            v.set_halign(Gtk.Align.CENTER)
            sb.append(l)
            sb.append(v)
            scard.append(sb)
            self.stat_labels[key] = v
        root.append(scard)

        # Temperature graph
        gcard = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        gcard.add_css_class('card')
        gl = Gtk.Label(label='Temperature history  (2 min)')
        gl.set_halign(Gtk.Align.START)
        gl.add_css_class('caption')
        gl.add_css_class('dim-label')
        gl.set_margin_start(12)
        gl.set_margin_top(12)
        gcard.append(gl)
        self.temp_graph = TempGraph()
        self.temp_graph.set_margin_start(8)
        self.temp_graph.set_margin_end(8)
        self.temp_graph.set_margin_top(4)
        self.temp_graph.set_margin_bottom(10)
        gcard.append(self.temp_graph)
        root.append(gcard)

        # RPM graph
        rcard = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        rcard.add_css_class('card')
        rl = Gtk.Label(label='Fan RPM history  (2 min)')
        rl.set_halign(Gtk.Align.START)
        rl.add_css_class('caption')
        rl.add_css_class('dim-label')
        rl.set_margin_start(12)
        rl.set_margin_top(12)
        rcard.append(rl)
        self.rpm_graph = RpmGraph()
        self.rpm_graph.set_margin_start(8)
        self.rpm_graph.set_margin_end(8)
        self.rpm_graph.set_margin_top(4)
        self.rpm_graph.set_margin_bottom(10)
        rcard.append(self.rpm_graph)
        root.append(rcard)

        tb.set_content(root)
        self.win.set_content(tb)
        self.win.present()

        self.update_sensors()
        GLib.timeout_add(2000, self.update_sensors)

    def set_manual(self):
        for b in self.preset_btns.values():
            b.remove_css_class('suggested-action')
        self.mode_badge.set_label('Manual')
        self.manual_mode = True

    def on_cpu_slider(self, s):
        self.set_manual()
        pct = int(s.get_value())
        run_helper('cpu', str(pct))

    def on_gpu_slider(self, s):
        self.set_manual()
        pct = int(s.get_value())
        run_helper('gpu', str(pct))

    def on_preset(self, btn, key):
        for b in self.preset_btns.values():
            b.remove_css_class('suggested-action')
        btn.add_css_class('suggested-action')
        self.manual_mode = False

        presets = {
            'auto':        (None, None, 'balanced', 'Auto'),
            'quiet':       (20,   20,   'quiet',    'Quiet'),
            'balanced':    (50,   50,   'balanced', 'Balanced'),
            'performance': (80,   80,   'performance', 'Performance'),
            'gameshift':   (100,  100,  'gameshift', 'Game Shift'),
        }

        cv, gv, profile, badge_label = presets[key]
        self.mode_badge.set_label(badge_label)
        run_helper('profile', profile)

        if cv is not None:
            self.cpu_slider.set_value(cv)
            self.gpu_slider.set_value(gv)
            run_helper('both', str(cv), str(gv))

    def update_badge(self, badge, temp):
        badge.remove_css_class('success')
        badge.remove_css_class('warning')
        badge.remove_css_class('error')
        if temp < 70:   badge.add_css_class('success')
        elif temp < 85: badge.add_css_class('warning')
        else:           badge.add_css_class('error')
        badge.set_label(f'{temp}°C')

    def update_sensors(self):
        cpu_rpm  = get_fan_rpm(1)
        gpu_rpm  = get_fan_rpm(2)
        cpu_temp = get_cpu_temp()
        gpu_temp = get_gpu_temp()

        if self.manual_mode:
            cpu_pct = int(self.cpu_slider.get_value())
            gpu_pct = int(self.gpu_slider.get_value())
        else:
            cpu_pct = min(100, int(cpu_rpm / MAX_RPM * 100))
            gpu_pct = min(100, int(gpu_rpm / MAX_RPM * 100))

        self.cpu_gauge.set_value(cpu_pct, cpu_rpm)
        self.gpu_gauge.set_value(gpu_pct, gpu_rpm)
        self.update_badge(self.cpu_badge, cpu_temp)
        self.update_badge(self.gpu_badge, gpu_temp)

        self.stat_labels['cpu_rpm'].set_label(f'{cpu_rpm:,}')
        self.stat_labels['gpu_rpm'].set_label(f'{gpu_rpm:,}')
        self.stat_labels['cpu_temp'].set_label(f'{cpu_temp}°C')
        self.stat_labels['gpu_temp'].set_label(f'{gpu_temp}°C')
        self.temp_graph.push(cpu_temp, gpu_temp)
        self.rpm_graph.push(cpu_rpm, gpu_rpm)
        return True

FanApp().run()
