from flask import Flask, render_template, jsonify, request, redirect
import psutil
import time
from flask import Blueprint

sysmon_bp = Blueprint('sysmon', __name__, url_prefix='/sysmon')

visitor_ips = set()
current_visitors = set()
maintenance_mode = False

@sysmon_bp.before_request
def track_ip():
    ip = request.remote_addr
    visitor_ips.add(ip)
    current_visitors.add(ip)
    if maintenance_mode and request.endpoint not in ('maintenance', 'toggle_maintenance'):
        return redirect('/maintenance')

@sysmon_bp.route('/')
def monitor_dashboard():
    return render_template('monitor_dashboard.html')


@sysmon_bp.after_request
def untrack_ip(response):
    current_visitors.discard(request.remote_addr)
    return response

@sysmon_bp.route('/maintenance')
def maintenance():
    return '<h1>🛠 Site Under Maintenance</h1>', 503

@sysmon_bp.route('/toggle_maintenance', methods=['POST'])
def toggle_maintenance():
    global maintenance_mode
    maintenance_mode = not maintenance_mode
    return redirect('/')

@sysmon_bp.route('/status', strict_slashes=False)
def sysmon():
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    net = psutil.net_io_counters()
    battery = psutil.sensors_battery()

    return jsonify({
        "cpu": psutil.cpu_percent(interval=5),
        "ram_used": round(mem.used / 1024 / 1024),
        "ram_total": round(mem.total / 1024 / 1024),
        "disk_used": round(disk.used / 1024 / 1024 / 1024),
        "disk_total": round(disk.total / 1024 / 1024 / 1024),
        "net_sent": round(net.bytes_sent / 1024 / 1024),
        "net_recv": round(net.bytes_recv / 1024 / 1024),
        "battery": {
            "percent": battery.percent,
            "plugged": battery.power_plugged
        } if battery else None,
        "total_visitors": len(visitor_ips),
        "current_visitors": len(current_visitors),
        "maintenance": maintenance_mode
    })



