import webview
import threading
import subprocess
import platform
import ctypes
import sys
import os
import shutil
import time
from datetime import timedelta

# --- NEW: Mica/Acrylic + Temp Monitor ---
try:
    import pywinstyles
except:
    pywinstyles = None

try:
    import wmi
except:
    wmi = None

# --- CortexDev Digital Identity ---
APP_NAME = "Make My Windows Better"
VERSION = "4.2.5"
AUTHOR = "CortexDev-Official"


class MEMORYSTATUSEX(ctypes.Structure):
    _fields_ = [
        ("dwLength", ctypes.c_ulong),
        ("dwMemoryLoad", ctypes.c_ulong),
        ("ullTotalPhys", ctypes.c_ulonglong),
        ("ullAvailPhys", ctypes.c_ulonglong),
        ("ullTotalPageFile", ctypes.c_ulonglong),
        ("ullAvailPageFile", ctypes.c_ulonglong),
        ("ullTotalVirtual", ctypes.c_ulonglong),
        ("ullAvailVirtual", ctypes.c_ulonglong),
        ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
    ]


class Api:
    # --- NEW: Internal Logger Helper ---
    def _log(self, msg, level="INFO"):
        try:
            safe = str(msg).replace("'", "\\'")
            webview.active_window().evaluate_js(f"addLog('[{level}] {safe}')")
        except:
            pass

    def get_stats(self):
        try:
            mem = MEMORYSTATUSEX()
            mem.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(mem))
            tick = ctypes.windll.kernel32.GetTickCount64()
            uptime = str(timedelta(milliseconds=tick)).split('.')[0]

            cpu_name = platform.processor()
            try:
                gpu_cmd = "wmic path win32_VideoController get name"
                gpu_out = subprocess.check_output(gpu_cmd, shell=True).decode(errors="ignore").split('\n')
                gpu_name = gpu_out[1].strip() if len(gpu_out) > 1 else "Standard Graphics"
            except:
                gpu_name = "Integrated GPU"

            is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0

            return {
                "ram": f"{mem.dwMemoryLoad}%",
                "ram_raw": mem.dwMemoryLoad,
                "uptime": uptime,
                "node": platform.node(),
                "os": f"Win {platform.release()}",
                "cpu": cpu_name,
                "gpu": gpu_name,
                "is_admin": is_admin
            }
        except:
            return {
                "ram": "N/A",
                "ram_raw": 0,
                "uptime": "00:00:00",
                "node": "Cortex-Node",
                "os": "Windows",
                "cpu": "Detecting...",
                "gpu": "Scanning...",
                "is_admin": False
            }

    # --- NEW: Disk Space ---
    def get_disk_space(self):
        try:
            total, used, free = shutil.disk_usage("C:")
            percent = (used / total) * 100
            return {
                "free_gb": f"{free // (2**30)} GB",
                "percent": f"{percent:.1f}%"
            }
        except:
            return {"free_gb": "N/A", "percent": "N/A"}

    # --- NEW: CPU Temp ---
    def get_cpu_temp(self):
        try:
            if wmi is None:
                return {"temp": "WMI Missing", "temp_raw": 0}

            w = wmi.WMI(namespace="root\\wmi")
            temps = w.MSAcpi_ThermalZoneTemperature()
            if not temps:
                return {"temp": "N/A", "temp_raw": 0}

            temp_info = temps[0]
            temp_c = (temp_info.CurrentTemperature / 10.0) - 273.15
            return {"temp": f"{temp_c:.1f}°C", "temp_raw": temp_c}
        except:
            return {"temp": "N/A", "temp_raw": 0}

    def run_health_check(self):
        def task():
            try:
                self._log("Health check started...", "INFO")
                time.sleep(1)
                result = subprocess.run("sfc /verifyonly", shell=True, capture_output=True, text=True)

                if "found integrity violations" in result.stdout.lower() or result.returncode != 0:
                    self._log("Integrity issues found! Suggest: sfc /scannow as Admin.", "WARN")
                    webview.active_window().evaluate_js(
                        "showToast('Integrity issues found! Run sfc /scannow as Admin.', 'error')"
                    )
                else:
                    self._log("System Integrity Secured (No errors).", "SUCCESS")
                    webview.active_window().evaluate_js("showToast('System Integrity Secured (No errors).', 'success')")
            except:
                self._log("Health Check Failed to initialize.", "ERROR")
                webview.active_window().evaluate_js("showToast('Health Check Failed to initialize.', 'error')")

        threading.Thread(target=task, daemon=True).start()
        return "Scan Started"

    # --- UPDATED: Cleaner with space calc + in-use handling + logs ---
    def run_system_cleaner(self):
        def task():
            folders = [
                os.environ.get('TEMP'),
                os.path.join(os.environ.get('SystemRoot', 'C:\\Windows'), 'Temp'),
                os.path.join(os.environ.get('SystemRoot', 'C:\\Windows'), 'Prefetch')
            ]

            total_deleted = 0
            self._log("Cleaner started...", "INFO")

            for folder in folders:
                if folder and os.path.exists(folder):
                    self._log(f"Scanning: {folder}", "INFO")

                    for filename in os.listdir(folder):
                        file_path = os.path.join(folder, filename)
                        try:
                            if os.path.isfile(file_path) or os.path.islink(file_path):
                                try:
                                    size = os.path.getsize(file_path)
                                except:
                                    size = 0
                                os.unlink(file_path)
                                total_deleted += size

                            elif os.path.isdir(file_path):
                                folder_size = 0
                                for root, dirs, files in os.walk(file_path):
                                    for f in files:
                                        fp = os.path.join(root, f)
                                        try:
                                            folder_size += os.path.getsize(fp)
                                        except:
                                            pass

                                shutil.rmtree(file_path, ignore_errors=True)
                                total_deleted += folder_size

                        except PermissionError:
                            self._log(f"In use / Access denied: {filename}", "WARN")
                            continue
                        except:
                            continue

            cleaned_mb = total_deleted / (1024 * 1024)
            time.sleep(0.5)

            self._log(f"Cleaner finished. Total cleaned: {cleaned_mb:.1f} MB", "SUCCESS")
            webview.active_window().evaluate_js(f"showToast('Cleaned {cleaned_mb:.1f} MB', 'success')")

        threading.Thread(target=task, daemon=True).start()
        return "Cleaning..."

    def run_install(self, uid):
        def task():
            self._log(f"Install requested: {uid}", "INFO")
            cmd = f'powershell -Command "Start-Process winget -ArgumentList \'install --id {uid} -e --silent --accept-source-agreements --accept-package-agreements\' -Verb RunAs"'
            subprocess.run(cmd, shell=True)
            self._log(f"Installation command sent for {uid}", "SUCCESS")
            webview.active_window().evaluate_js(f"showToast('Installation command sent for {uid}', 'info')")

        threading.Thread(target=task, daemon=True).start()
        return f"Installing {uid}..."

    def uninstall_sys_app(self, package_name):
        def task():
            self._log(f"Uninstall requested: {package_name}", "WARN")
            cmd = f'powershell -Command "Get-AppxPackage *{package_name}* | Remove-AppxPackage"'
            subprocess.run(cmd, shell=True)
            self._log(f"Attempted to remove {package_name}", "WARN")
            webview.active_window().evaluate_js(f"showToast('Attempted to remove {package_name}', 'warning')")

        threading.Thread(target=task, daemon=True).start()
        return "Uninstalling..."

    def run_optimize(self, action):
        commands = {
            "cache": "cleanmgr /sagerun:1",
            "sfc": "sfc /scannow",
            "dns": "ipconfig /flushdns",
            "power": "powercfg -duplicatescheme e9a42b02-d5df-448d-aa00-03f14749eb61",
            "trim": "defrag C: /O",
            "telemetry": "sc stop DiagTrack && sc config DiagTrack start= disabled",
            "hibernation": "powercfg -h off",
            "updates": "net stop wuauserv && sc config wuauserv start= disabled",
            "startup": "Get-CimInstance Win32_StartupCommand | ForEach-Object { $_.Caption }",
            "transparency": "reg add 'HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Themes\\Personalize' /v EnableTransparency /t REG_DWORD /d 0 /f",
            "visuals": "visual_boost_internal",
            "gamebar": "reg add 'HKCU\\System\\GameConfigStore' /v GameDVR_Enabled /t REG_DWORD /d 0 /f"
        }

        cmd = commands.get(action)
        if cmd:
            def task():
                try:
                    self._log(f"Optimizer executing: {action}", "INFO")
                    full_cmd = f'powershell -Command "Start-Process powershell -ArgumentList \'-Command {cmd}\' -Verb RunAs"'
                    subprocess.run(full_cmd, shell=True)
                    self._log(f"Optimization task executed: {action}", "SUCCESS")
                    webview.active_window().evaluate_js(f"showToast('Optimization task: {action} executed', 'success')")
                except:
                    self._log(f"Optimization failed: {action}", "ERROR")
                    webview.active_window().evaluate_js(f"showToast('Optimization failed: {action}', 'error')")

            threading.Thread(target=task, daemon=True).start()
        return "Task initiated"

    # --- NEW: Ultimate Performance ON ---
    def set_ultimate_power(self):
        def task():
            try:
                self._log("Ultimate Performance requested...", "INFO")
                subprocess.run("powercfg -duplicatescheme e9a42b02-d5df-448d-aa00-03f14749eb61", shell=True)
                subprocess.run("powercfg /setactive e9a42b02-d5df-448d-aa00-03f14749eb61", shell=True)
                self._log("Ultimate Performance Enabled", "SUCCESS")
                webview.active_window().evaluate_js("showToast('Ultimate Performance Enabled', 'success')")
            except:
                self._log("Ultimate Performance failed", "ERROR")
                webview.active_window().evaluate_js("showToast('Power plan failed', 'error')")

        threading.Thread(target=task, daemon=True).start()
        return "Power Boost..."

    # --- NEW: Driver updater shortcut ---
    def open_windows_update(self):
        try:
            self._log("Opening Windows Update...", "INFO")
            subprocess.run("start ms-settings:windowsupdate", shell=True)
            return "Opening Windows Update..."
        except:
            return "Failed"

    # --- NEW: Close background apps (light version) ---
    def kill_background_apps(self):
        def task():
            targets = ["chrome.exe", "OneDrive.exe"]
            killed = []
            self._log("Background app cleanup started...", "INFO")

            for t in targets:
                try:
                    subprocess.run(f"taskkill /f /im {t}", shell=True, capture_output=True, text=True)
                    killed.append(t)
                except:
                    pass

            if killed:
                closed_list = ", ".join(killed)
                self._log("Closed: " + closed_list, "WARN")
                webview.active_window().evaluate_js(f"showToast('Closed: {closed_list}', 'warning')")
            else:
                self._log("No background apps closed.", "INFO")
                webview.active_window().evaluate_js("showToast('No background apps closed', 'info')")

        threading.Thread(target=task, daemon=True).start()
        return "Background cleanup..."

    # ==========================
    # NEW v4.2.5 FEATURES
    # ==========================

    # ✅ Repair + DISM
    def repair_dism(self):
        def task():
            try:
                self._log("Repair + DISM started...", "INFO")
                cmd = r'DISM /Online /Cleanup-Image /RestoreHealth'
                full_cmd = f'powershell -Command "Start-Process cmd -ArgumentList \'/c {cmd}\' -Verb RunAs"'
                subprocess.run(full_cmd, shell=True)
                self._log("DISM command sent (Admin)", "SUCCESS")
                webview.active_window().evaluate_js("showToast('DISM Repair Started (Admin)', 'success')")
            except:
                self._log("DISM failed to start", "ERROR")
                webview.active_window().evaluate_js("showToast('DISM failed to start', 'error')")

        threading.Thread(target=task, daemon=True).start()
        return "DISM Running..."

    # ✅ Restore Point
    def create_restore_point(self):
        def task():
            try:
                self._log("Restore Point requested...", "INFO")
                ps = r"""
                Enable-ComputerRestore -Drive "C:\"
                Checkpoint-Computer -Description "MWB Restore Point" -RestorePointType "MODIFY_SETTINGS"
                """
                full_cmd = f'powershell -Command "Start-Process powershell -ArgumentList \'-ExecutionPolicy Bypass -Command {ps}\' -Verb RunAs"'
                subprocess.run(full_cmd, shell=True)
                self._log("Restore Point creation requested (Admin)", "SUCCESS")
                webview.active_window().evaluate_js("showToast('Restore Point Created (Admin)', 'success')")
            except:
                self._log("Restore Point failed", "ERROR")
                webview.active_window().evaluate_js("showToast('Restore Point failed', 'error')")

        threading.Thread(target=task, daemon=True).start()
        return "Restore Point..."

    # ✅ Safe Mode Control
    def safe_mode_enable(self):
        def task():
            try:
                self._log("Safe Mode ENABLE requested...", "WARN")
                cmd = r'bcdedit /set {current} safeboot minimal'
                full_cmd = f'powershell -Command "Start-Process cmd -ArgumentList \'/c {cmd}\' -Verb RunAs"'
                subprocess.run(full_cmd, shell=True)
                self._log("Safe Mode enabled (next reboot)", "SUCCESS")
                webview.active_window().evaluate_js("showToast('Safe Mode enabled for next reboot', 'success')")
            except:
                self._log("Safe Mode enable failed", "ERROR")
                webview.active_window().evaluate_js("showToast('Safe Mode enable failed', 'error')")

        threading.Thread(target=task, daemon=True).start()
        return "Safe Mode ON..."

    def safe_mode_disable(self):
        def task():
            try:
                self._log("Safe Mode DISABLE requested...", "INFO")
                cmd = r'bcdedit /deletevalue {current} safeboot'
                full_cmd = f'powershell -Command "Start-Process cmd -ArgumentList \'/c {cmd}\' -Verb RunAs"'
                subprocess.run(full_cmd, shell=True)
                self._log("Safe Mode disabled (next reboot)", "SUCCESS")
                webview.active_window().evaluate_js("showToast('Safe Mode disabled (next reboot)', 'success')")
            except:
                self._log("Safe Mode disable failed", "ERROR")
                webview.active_window().evaluate_js("showToast('Safe Mode disable failed', 'error')")

        threading.Thread(target=task, daemon=True).start()
        return "Safe Mode OFF..."

    # ✅ FPS Mode (Gaming Boost أقوى)
    def run_fps_mode(self):
        def task():
            self._log("FPS Mode started...", "INFO")

            ps_script = r"""
            $procs = Get-Process | Where-Object {$_.MainWindowTitle -ne ''}
            foreach ($p in $procs) {
                try { $p.PriorityClass = 'High' } catch { continue }
            }
            """

            boost_cmds = [
                "ipconfig /flushdns",
                "powercfg /setactive SCHEME_MIN",
                "reg add \"HKCU\\System\\GameConfigStore\" /v GameDVR_Enabled /t REG_DWORD /d 0 /f",
                "reg add \"HKCU\\Software\\Microsoft\\GameBar\" /v AllowAutoGameMode /t REG_DWORD /d 1 /f",
                f"PowerShell -Command \"{ps_script}\""
            ]

            for c in boost_cmds:
                try:
                    subprocess.run(c, shell=True)
                except:
                    pass

            self._log("FPS Mode Active: High Priority + GameDVR OFF", "SUCCESS")
            time.sleep(0.5)
            webview.active_window().evaluate_js("showToast('FPS Mode Active: MAX Performance', 'gaming')")

        threading.Thread(target=task, daemon=True).start()
        return "FPS Mode Active"

    def run_gaming_boost(self):
        def task():
            self._log("Velocity Mode started...", "INFO")

            ps_script = """
            $procs = Get-Process | Where-Object {$_.MainWindowTitle -ne ''}
            foreach ($p in $procs) {
                try { $p.PriorityClass = 'AboveNormal' } catch { continue }
            }
            """

            boost_cmds = [
                "ipconfig /flushdns",
                "powercfg /setactive SCHEME_MIN",
                f"PowerShell -Command \"{ps_script}\""
            ]

            for c in boost_cmds:
                try:
                    subprocess.run(c, shell=True)
                except:
                    pass

            self._log("Velocity Mode Active: Priority boosted + power scheme set", "SUCCESS")
            time.sleep(0.5)
            webview.active_window().evaluate_js("showToast('Velocity Mode Active: System Overclocked', 'gaming')")

        threading.Thread(target=task, daemon=True).start()
        return "Velocity Mode Active"


HTML_UI = r"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MWB - CortexDev</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;600;800&display=swap" rel="stylesheet">
    <style>
        :root {
            --accent: #007AFF;
            --accent-glow: rgba(0, 122, 255, 0.6);
            --liquid-bg: #030304;
            --glass-bg: rgba(255, 255, 255, 0.015);
            --glass-border: rgba(255, 255, 255, 0.08);
            --ray-reflect: linear-gradient(115deg, transparent 0%, rgba(255,255,255,0.05) 30%, rgba(255,255,255,0.4) 50%, rgba(255,255,255,0.05) 70%, transparent 100%);
        }

        * { -webkit-tap-highlight-color: transparent; outline: none; scroll-behavior: smooth; cursor: default; }

        body {
            background-color: var(--liquid-bg);
            background-image: radial-gradient(circle at 15% 50%, rgba(0, 122, 255, 0.08), transparent 25%), radial-gradient(circle at 85% 30%, rgba(120, 0, 255, 0.05), transparent 25%);
            color: white;
            font-family: 'Plus Jakarta Sans', sans-serif;
            overflow: hidden;
            height: 100vh;
            user-select: none;
            display: flex;
        }

        .ray-trace-enabled {
            position: relative;
            overflow: hidden;
            isolation: isolate;
        }

        .ray-trace-enabled::before {
            content: '';
            position: absolute;
            top: 0; left: 0; right: 0; bottom: 0;
            background: var(--ray-reflect);
            transform: translateX(-150%) skewX(-20deg);
            transition: transform 0s;
            z-index: 2;
            pointer-events: none;
        }

        .ray-trace-enabled:hover::before {
            transform: translateX(150%) skewX(-20deg);
            transition: transform 0.8s ease-in-out;
        }

        .ray-trace-enabled::after {
            content: '';
            position: absolute;
            inset: 0;
            border-radius: inherit;
            box-shadow: inset 0 0 20px rgba(255,255,255,0.02);
            z-index: 1;
            pointer-events: none;
        }

        #log-box::-webkit-scrollbar { width: 6px; }
        #log-box::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 10px; }

        #welcome-overlay {
            position: fixed;
            inset: 0;
            background: #030304;
            z-index: 10000;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 1s cubic-bezier(0.6, 0, 0.2, 1);
        }

        #welcome-overlay.fade-out {
            opacity: 0;
            pointer-events: none;
            filter: blur(20px);
            transform: scale(1.1);
        }

        .welcome-container {
            width: 900px;
            height: 600px;
            background: rgba(10, 10, 12, 0.6);
            backdrop-filter: blur(80px) saturate(180%);
            -webkit-backdrop-filter: blur(80px) saturate(180%);
            border: 1px solid rgba(255, 255, 255, 0.1);
            box-shadow: 0 0 100px rgba(0, 122, 255, 0.15), inset 0 0 60px rgba(0,0,0,0.5);
            border-radius: 40px;
            display: flex;
            overflow: hidden;
            position: relative;
        }

        .welcome-sidebar {
            width: 320px;
            background: linear-gradient(160deg, rgba(255,255,255,0.03) 0%, rgba(0,0,0,0.2) 100%);
            border-right: 1px solid rgba(255, 255, 255, 0.05);
            padding: 60px 40px;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            position: relative;
        }

        .welcome-sidebar::before {
            content: '';
            position: absolute;
            top: 0; left: 0; width: 100%; height: 2px;
            background: linear-gradient(90deg, transparent, var(--accent), transparent);
            opacity: 0.5;
        }

        .welcome-content {
            flex: 1;
            padding: 70px;
            position: relative;
            display: flex;
            flex-direction: column;
        }

        .step-indicator {
            display: flex;
            gap: 12px;
            margin-bottom: 50px;
        }

        .step-dot {
            height: 4px;
            width: 40px;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 4px;
            transition: all 0.5s ease;
        }

        .step-dot.active {
            background: var(--accent);
            box-shadow: 0 0 15px var(--accent);
            width: 60px;
        }

        .welcome-stage {
            display: none;
            opacity: 0;
            transform: translateY(20px);
            transition: all 0.6s ease;
        }

        .welcome-stage.active {
            display: block;
            opacity: 1;
            transform: translateY(0);
            animation: slideUp 0.6s cubic-bezier(0.2, 1, 0.3, 1) forwards;
        }

        @keyframes slideUp {
            from { opacity: 0; transform: translateY(30px); }
            to { opacity: 1; transform: translateY(0); }
        }

        .action-btn {
            background: linear-gradient(135deg, var(--accent) 0%, #0056b3 100%);
            color: white;
            padding: 18px 36px;
            border-radius: 20px;
            font-weight: 800;
            font-size: 14px;
            letter-spacing: 1.5px;
            text-transform: uppercase;
            transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
            margin-top: auto;
            align-self: flex-start;
            border: 1px solid rgba(255,255,255,0.2);
            box-shadow: 0 10px 30px rgba(0, 122, 255, 0.3);
            cursor: pointer;
        }

        .action-btn:hover {
            transform: translateY(-4px) scale(1.03);
            box-shadow: 0 20px 50px rgba(0, 122, 255, 0.5);
            border-color: rgba(255,255,255,0.5);
        }

        .liquid-sidebar {
            background: rgba(10, 10, 12, 0.7);
            backdrop-filter: blur(40px);
            -webkit-backdrop-filter: blur(40px);
            border-right: 1px solid var(--glass-border);
            box-shadow: 10px 0 40px rgba(0,0,0,0.5);
            transition: all 0.5s;
            z-index: 50;
        }

        .page-container {
            position: relative;
            flex: 1;
            height: 100vh;
            overflow-y: auto;
            padding: 50px 70px;
            background: transparent;
        }

        .page-container::-webkit-scrollbar { width: 6px; }
        .page-container::-webkit-scrollbar-track { background: transparent; }
        .page-container::-webkit-scrollbar-thumb {
            background: rgba(255,255,255,0.1);
            border-radius: 10px;
        }
        .page-container::-webkit-scrollbar-thumb:hover { background: rgba(255,255,255,0.2); }

        .page {
            position: absolute;
            top: 50px; left: 70px; right: 70px;
            opacity: 0;
            visibility: hidden;
            transform: translateY(40px) scale(0.96);
            transition: all 0.7s cubic-bezier(0.2, 0.8, 0.2, 1);
            filter: blur(10px);
        }

        .page.active {
            opacity: 1;
            visibility: visible;
            transform: translateY(0) scale(1);
            position: relative;
            top: 0; left: 0; right: 0;
            filter: blur(0);
        }

        .sidebar-item {
            transition: all 0.4s;
            margin: 8px 20px;
            padding: 16px 24px;
            border-radius: 18px;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 16px;
            color: #7a7a7a;
            border: 1px solid transparent;
        }

        .sidebar-item:hover {
            background: rgba(255, 255, 255, 0.04);
            color: #fff;
            transform: translateX(6px);
            border-color: rgba(255,255,255,0.05);
            box-shadow: 0 4px 20px rgba(0,0,0,0.2);
        }

        .sidebar-item.active {
            background: linear-gradient(90deg, rgba(0,122,255,0.1) 0%, transparent 100%);
            color: var(--accent);
            border: 1px solid rgba(0,122,255,0.2);
            box-shadow: 0 0 30px rgba(0, 122, 255, 0.15);
        }

        .card {
            border-radius: 30px;
            padding: 30px;
            background: linear-gradient(145deg, rgba(255,255,255,0.03) 0%, rgba(255,255,255,0.01) 100%);
            border: 1px solid var(--glass-border);
            backdrop-filter: blur(20px);
            transition: all 0.5s cubic-bezier(0.23, 1, 0.32, 1);
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }

        .card:hover {
            background: linear-gradient(145deg, rgba(255,255,255,0.06) 0%, rgba(255,255,255,0.02) 100%);
            border-color: rgba(255, 255, 255, 0.15);
            transform: translateY(-10px) scale(1.02);
            box-shadow: 0 30px 60px rgba(0,0,0,0.5), 0 0 40px rgba(0, 122, 255, 0.1);
        }

        #toast-container {
            position: fixed;
            bottom: 40px;
            right: 40px;
            z-index: 9999;
            display: flex;
            flex-direction: column;
            gap: 10px;
        }

        .toast-msg {
            background: rgba(15, 15, 20, 0.9);
            backdrop-filter: blur(30px);
            border-left: 4px solid var(--accent);
            color: white;
            padding: 20px 30px;
            border-radius: 16px;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 15px;
            box-shadow: 0 20px 50px rgba(0,0,0,0.6);
            animation: toastEnter 0.6s cubic-bezier(0.175, 0.885, 0.32, 1.275) forwards;
            min-width: 300px;
            border: 1px solid rgba(255,255,255,0.1);
        }

        .toast-msg.success { border-left-color: #22c55e; }
        .toast-msg.error { border-left-color: #ef4444; }
        .toast-msg.gaming { border-left-color: #f59e0b; box-shadow: 0 0 30px rgba(245, 158, 11, 0.2); }

        @keyframes toastEnter {
            from { transform: translateX(100%) scale(0.8); opacity: 0; }
            to { transform: translateX(0) scale(1); opacity: 1; }
        }

        .install-btn {
            background: rgba(255,255,255,0.05);
            color: white;
            padding: 12px 28px;
            border-radius: 14px;
            font-weight: 700;
            font-size: 11px;
            letter-spacing: 1px;
            transition: 0.3s;
            text-transform: uppercase;
            border: 1px solid rgba(255,255,255,0.1);
            cursor: pointer;
        }
        .install-btn:hover {
            background: var(--accent);
            border-color: var(--accent);
            transform: translateY(-3px);
            box-shadow: 0 10px 25px var(--accent-glow);
        }

        .ram-pulse { animation: pulse-glow 3s infinite ease-in-out; }
        @keyframes pulse-glow {
            0% { box-shadow: 0 0 0 0 rgba(0, 122, 255, 0); }
            50% { box-shadow: 0 0 40px 10px rgba(0, 122, 255, 0.15); border-color: rgba(0,122,255,0.4); }
            100% { box-shadow: 0 0 0 0 rgba(0, 122, 255, 0); }
        }
    </style>
</head>
<body>

    <div id="welcome-overlay">
        <div class="welcome-container ray-trace-enabled">
            <div class="welcome-sidebar">
                <div>
                    <h1 class="text-5xl font-black italic tracking-tighter text-blue-500 mb-2 drop-shadow-[0_0_15px_rgba(0,122,255,0.5)]">MWB</h1>
                    <p class="text-[10px] font-bold uppercase tracking-[0.4em] opacity-60">CortexDev Official</p>
                </div>
                <div class="text-[10px] font-bold text-gray-500 uppercase tracking-widest leading-relaxed">
                    Personalized System Optimization <br> Version 4.2.5
                </div>
            </div>

            <div class="welcome-content">
                <div class="step-indicator">
                    <div id="dot-1" class="step-dot active"></div>
                    <div id="dot-2" class="step-dot"></div>
                    <div id="dot-3" class="step-dot"></div>
                </div>

                <div id="w-stage-1" class="welcome-stage active">
                    <h2 class="text-6xl font-black italic tracking-tighter mb-6 bg-clip-text text-transparent bg-gradient-to-r from-white to-gray-400">Welcome</h2>
                    <p class="text-gray-400 text-sm leading-relaxed mb-10 font-medium">
                        Thank you for choosing <span class="text-white font-bold italic">Make My Windows Better (MWB)</span>.
                        "MWB" It's Free And Open Source Software (FOSS), We appreciate your support in making Windows a cleaner and faster environment.
                    </p>
                    <div class="card bg-blue-500/[0.03] border-blue-500/20 mb-8 p-6 ray-trace-enabled">
                        <p class="text-[11px] font-black uppercase text-blue-400 tracking-widest mb-2">Open Source</p>
                        <p class="text-xs text-gray-400 mb-3 italic">Help us grow by starring our project on GitHub!</p>
                        <a href="https://github.com/CortexDev-Official/Make-Windows-Better" target="_blank" class="text-xs font-bold text-white hover:text-blue-500 transition-colors">github.com/CortexDev-Official/MWB</a>
                    </div>
                    <button onclick="nextStep(2)" class="action-btn ray-trace-enabled">Initialize System</button>
                </div>

                <div id="w-stage-2" class="welcome-stage">
                    <h2 class="text-5xl font-black italic tracking-tighter mb-6">Capabilities</h2>
                    <p class="text-gray-400 text-sm leading-relaxed mb-8">
                        MWB isn't just a tool; it's a statement. We aim to purge unnecessary <span class="text-white font-bold">Bloatware</span>,
                        neutralize tracking services, and eliminate Windows system clutter.
                    </p>
                    <ul class="space-y-5 mb-10">
                        <li class="flex items-center gap-4 text-xs font-bold text-gray-300">
                            <span class="w-2 h-2 bg-blue-500 rounded-full shadow-[0_0_10px_#3b82f6]"></span> DEEP SYSTEM CLEANING
                        </li>
                        <li class="flex items-center gap-4 text-xs font-bold text-gray-300">
                            <span class="w-2 h-2 bg-blue-500 rounded-full shadow-[0_0_10px_3b82f6]"></span> PRIVACY ENFORCEMENT
                        </li>
                        <li class="flex items-center gap-4 text-xs font-bold text-gray-300">
                            <span class="w-2 h-2 bg-blue-500 rounded-full shadow-[0_0_10px_#3b82f6]"></span> 4.2.5 KERNEL BOOST
                        </li>
                    </ul>
                    <button onclick="nextStep(3)" class="action-btn ray-trace-enabled">Configure Core</button>
                </div>

                <div id="w-stage-3" class="welcome-stage">
                    <h2 class="text-5xl font-black italic tracking-tighter mb-6">Ready</h2>
                    <p class="text-gray-400 text-sm leading-relaxed mb-10">
                        Your system is ready for its transformation. Welcome to the CortexDev ecosystem.
                        Explore our software repository and advanced optimizer.
                    </p>
                    <div class="h-28 flex items-center justify-center bg-white/5 rounded-3xl mb-10 border border-white/10 ray-trace-enabled">
                        <div class="flex gap-4">
                            <div class="w-3 h-3 bg-blue-500 rounded-full animate-ping"></div>
                            <div class="w-3 h-3 bg-blue-500 rounded-full animate-ping delay-75"></div>
                            <div class="w-3 h-3 bg-blue-500 rounded-full animate-ping delay-150"></div>
                        </div>
                    </div>
                    <button onclick="finishWelcome()" class="action-btn !bg-white !text-black hover:!bg-blue-500 hover:!text-white ray-trace-enabled">Launch Dashboard</button>
                </div>
            </div>
        </div>
    </div>

    <div id="toast-container"></div>

    <div class="w-80 h-full liquid-sidebar flex flex-col py-12 z-50">
        <div class="px-12 mb-16">
            <h1 class="text-5xl font-black tracking-tighter italic drop-shadow-[0_0_10px_rgba(255,255,255,0.3)]">MWB</h1>
            <p class="text-[10px] text-blue-500 font-bold uppercase tracking-[0.4em] mt-3 opacity-90">CortexDev Official</p>
        </div>

        <nav id="nav-list" class="flex-1 space-y-2">
            <div onclick="switchPage('dashboard', this)" class="sidebar-item active ray-trace-enabled">
                <span class="text-xl">⌬</span> <span class="text-[11px] font-black uppercase tracking-[0.2em]">Dashboard</span>
            </div>
            <div onclick="switchPage('software', this)" class="sidebar-item ray-trace-enabled">
                <span class="text-xl">⧉</span> <span class="text-[11px] font-black uppercase tracking-[0.2em]">Software Hub</span>
            </div>
            <div onclick="switchPage('appmanager', this)" class="sidebar-item ray-trace-enabled">
                <span class="text-xl">📂</span> <span class="text-[11px] font-black uppercase tracking-[0.2em]">App Manager</span>
            </div>
            <div onclick="switchPage('optimizer', this)" class="sidebar-item ray-trace-enabled">
                <span class="text-xl">⚙</span> <span class="text-[11px] font-black uppercase tracking-[0.2em]">Optimizer</span>
            </div>
            <div onclick="switchPage('gaming', this)" class="sidebar-item ray-trace-enabled">
                <span class="text-xl">⚡</span> <span class="text-[11px] font-black uppercase tracking-[0.2em]">Gaming Center</span>
            </div>
            <div onclick="switchPage('about', this)" class="sidebar-item ray-trace-enabled">
                <span class="text-xl">◈</span> <span class="text-[11px] font-black uppercase tracking-[0.2em]">CortexDev</span>
            </div>
        </nav>

        <div class="px-8 mt-auto">
            <div class="bg-gradient-to-r from-blue-900/20 to-transparent p-5 rounded-3xl border border-blue-500/20 flex items-center space-x-4">
                <div class="w-2.5 h-2.5 bg-green-500 rounded-full animate-pulse shadow-[0_0_10px_#22c55e]"></div>
                <span class="text-[10px] font-black text-gray-300 uppercase tracking-widest">SYSTEM LINK ACTIVE</span>
            </div>
        </div>
    </div>

    <div class="page-container" id="page-container">

        <div id="page-dashboard" class="page active">
            <div class="flex justify-between items-end mb-12">
                <div>
                    <h2 class="text-8xl font-black tracking-tighter italic text-transparent bg-clip-text bg-gradient-to-b from-white to-gray-600">System Flow</h2>
                    <p class="text-blue-500 text-xs mt-2 uppercase tracking-[0.5em] font-bold">Neural monitoring initiated</p>
                </div>
            </div>

            <div class="grid grid-cols-3 gap-8 mb-10">
                <div class="card bg-blue-500/5 group ray-trace-enabled">
                    <p class="text-[10px] font-black text-blue-400 mb-3 uppercase tracking-widest">Health Check</p>
                    <h3 class="text-3xl font-black text-white italic mb-6">Integrity</h3>
                    <button onclick="runHealthCheck()" class="install-btn w-full ray-trace-enabled">Scan System</button>
                </div>

                <div class="card bg-red-500/5 ray-trace-enabled">
                    <p class="text-[10px] font-black text-red-400 mb-3 uppercase tracking-widest">System Cleaner</p>
                    <h3 class="text-3xl font-black text-white italic mb-6">Storage Junk</h3>
                    <button onclick="runSystemCleaner()" class="install-btn !bg-red-500/10 !text-red-400 hover:!bg-red-500 hover:!text-white w-full border-red-500/30 ray-trace-enabled">Purge Junk</button>
                </div>

                <div class="card border-orange-500/20 bg-orange-500/5 ray-trace-enabled">
                    <p class="text-[10px] font-black text-orange-400 mb-3 uppercase tracking-widest">Version</p>
                    <h3 class="text-3xl font-black text-orange-500 italic">v4.2.5</h3>
                    <p class="text-xs text-gray-500 mt-2">Stable Build</p>
                </div>
            </div>

            <div class="grid grid-cols-4 gap-8 mb-10">
                <div class="card ram-pulse ray-trace-enabled" id="ram-card">
                    <p class="text-[10px] font-black text-gray-500 mb-3 uppercase tracking-widest">Memory Load</p>
                    <h3 id="stat-ram" class="text-7xl font-black text-blue-500 tracking-tighter italic drop-shadow-[0_0_20px_rgba(0,122,255,0.4)]">...</h3>
                </div>

                <div class="card ray-trace-enabled">
                    <p class="text-[10px] font-black text-gray-500 mb-3 uppercase tracking-widest">Platform</p>
                    <h3 id="stat-os" class="text-2xl font-black text-white truncate italic mt-2">...</h3>
                </div>

                <div class="card ray-trace-enabled">
                    <p class="text-[10px] font-black text-gray-500 mb-3 uppercase tracking-widest">Power On Time</p>
                    <h3 id="stat-uptime" class="text-2xl font-black text-green-500 italic mt-2">...</h3>
                </div>

                <div class="card ray-trace-enabled">
                    <p class="text-[10px] font-black text-gray-500 mb-3 uppercase tracking-widest">CPU Temp</p>
                    <h3 id="stat-temp" class="text-2xl font-black text-red-400 italic mt-2">...</h3>
                </div>
            </div>

            <div class="grid grid-cols-2 gap-8">
                <div class="card bg-blue-500/[0.03] ray-trace-enabled">
                    <h4 class="text-[11px] font-black mb-6 uppercase text-blue-400 tracking-[0.3em]">Logic Processor</h4>
                    <p id="stat-cpu" class="text-white font-bold text-xl mb-6 leading-tight italic">Detecting...</p>
                    <div class="w-full bg-white/5 h-1.5 rounded-full overflow-hidden">
                        <div class="bg-blue-500 h-full w-3/4 animate-pulse shadow-[0_0_10px_#3b82f6]"></div>
                    </div>
                </div>

                <div class="card bg-purple-500/[0.03] ray-trace-enabled">
                    <h4 class="text-[11px] font-black mb-6 uppercase text-purple-400 tracking-[0.3em]">Render Engine</h4>
                    <p id="stat-gpu" class="text-white font-bold text-xl mb-6 leading-tight italic">Scanning...</p>
                    <div class="w-full bg-white/5 h-1.5 rounded-full overflow-hidden">
                        <div class="bg-purple-500 h-full w-1/2 animate-pulse shadow-[0_0_10px_#a855f7]"></div>
                    </div>
                </div>
            </div>

            <div class="grid grid-cols-2 gap-8 mt-8">
                <div class="card ray-trace-enabled">
                    <p class="text-[10px] font-black text-gray-500 mb-3 uppercase tracking-widest">Disk Space (C:)</p>
                    <h3 id="stat-diskfree" class="text-4xl font-black text-blue-400 italic mt-2">...</h3>
                    <p id="stat-diskpercent" class="text-xs text-gray-500 mt-2 uppercase tracking-wider">...</p>
                </div>

                <div class="card ray-trace-enabled">
                    <p class="text-[10px] font-black text-gray-500 mb-3 uppercase tracking-widest">Action Logs</p>
                    <div id="log-box" class="text-xs text-gray-300 font-mono h-32 overflow-y-auto bg-black/20 p-4 rounded-2xl border border-white/10"></div>
                </div>
            </div>

            <!-- NEW v4.2.5 ACTIONS -->
            <div class="grid grid-cols-4 gap-8 mt-8">
                <div class="card ray-trace-enabled">
                    <p class="text-[10px] font-black text-gray-500 mb-3 uppercase tracking-widest">Repair</p>
                    <h3 class="text-2xl font-black italic mb-6">DISM</h3>
                    <button onclick="runDismRepair()" class="install-btn w-full ray-trace-enabled">Repair + DISM</button>
                </div>

                <div class="card ray-trace-enabled">
                    <p class="text-[10px] font-black text-gray-500 mb-3 uppercase tracking-widest">Safety</p>
                    <h3 class="text-2xl font-black italic mb-6">Restore Point</h3>
                    <button onclick="createRestorePoint()" class="install-btn w-full ray-trace-enabled">Create Point</button>
                </div>

                <div class="card ray-trace-enabled">
                    <p class="text-[10px] font-black text-gray-500 mb-3 uppercase tracking-widest">Safe Mode</p>
                    <h3 class="text-2xl font-black italic mb-6">Enable</h3>
                    <button onclick="enableSafeMode()" class="install-btn w-full ray-trace-enabled">Enable Safe</button>
                </div>

                <div class="card ray-trace-enabled">
                    <p class="text-[10px] font-black text-gray-500 mb-3 uppercase tracking-widest">Safe Mode</p>
                    <h3 class="text-2xl font-black italic mb-6">Disable</h3>
                    <button onclick="disableSafeMode()" class="install-btn w-full ray-trace-enabled">Disable Safe</button>
                </div>
            </div>

            <div class="grid grid-cols-3 gap-8 mt-8">
                <div class="card ray-trace-enabled">
                    <p class="text-[10px] font-black text-gray-500 mb-3 uppercase tracking-widest">Drivers</p>
                    <h3 class="text-2xl font-black italic mb-6">Windows Update</h3>
                    <button onclick="openWindowsUpdate()" class="install-btn w-full ray-trace-enabled">Open Windows Update</button>
                </div>

                <div class="card ray-trace-enabled">
                    <p class="text-[10px] font-black text-gray-500 mb-3 uppercase tracking-widest">Gaming</p>
                    <h3 class="text-2xl font-black italic mb-6">Ultimate Power</h3>
                    <button onclick="enableUltimatePower()" class="install-btn w-full ray-trace-enabled">Enable Ultimate</button>
                </div>

                <div class="card ray-trace-enabled">
                    <p class="text-[10px] font-black text-gray-500 mb-3 uppercase tracking-widest">Gaming</p>
                    <h3 class="text-2xl font-black italic mb-6">Close Background</h3>
                    <button onclick="closeBackgroundApps()" class="install-btn w-full ray-trace-enabled">Cleanup Apps</button>
                </div>
            </div>

        </div>

        <div id="page-software" class="page">
            <h2 class="text-8xl font-black mb-4 tracking-tighter italic opacity-90">Repository</h2>
            <p class="text-gray-500 text-sm mb-12 uppercase tracking-[0.3em]">CortexDev Verified Library.</p>
            <div id="software-grid" class="grid grid-cols-3 gap-6 pb-24"></div>
        </div>

        <div id="page-appmanager" class="page">
            <h2 class="text-8xl font-black mb-4 tracking-tighter italic opacity-90">App Manager</h2>
            <p class="text-red-500 text-[10px] font-black uppercase tracking-[0.2em] mb-4 bg-red-500/10 inline-block px-3 py-1 rounded">
                 Warning: The developer, CortexDev, is not responsible for any harm or damage to your computer
                 or files caused by the use of this tool. Use at your own risk.
            </p>
            <p class="text-gray-500 text-sm mb-12 uppercase tracking-[0.3em]">System Debloat & Management.</p>
            <div id="appmanager-grid" class="grid grid-cols-3 gap-6 pb-24"></div>
        </div>

        <div id="page-optimizer" class="page">
            <h2 class="text-8xl font-black mb-4 tracking-tighter italic opacity-90">Engine Boost</h2>
            <p class="text-gray-500 text-sm mb-16 uppercase tracking-[0.3em]">Fine-tuning OS parameters.</p>
            <div id="optimizer-grid" class="grid grid-cols-2 gap-6 pb-20"></div>
        </div>

        <div id="page-gaming" class="page text-center">
            <div class="h-full flex flex-col items-center justify-center">
                <div class="w-48 h-48 border border-red-500/30 rounded-full mb-12 flex items-center justify-center relative ray-trace-enabled bg-red-500/5">
                    <div class="absolute inset-0 bg-red-500/10 rounded-full animate-ping"></div>
                    <span class="text-7xl drop-shadow-[0_0_15px_rgba(239,68,68,0.8)]">⚡</span>
                </div>
                <h2 class="text-9xl font-black mb-6 text-red-600 italic uppercase tracking-tighter drop-shadow-[0_0_30px_rgba(220,38,38,0.4)]">Velocity</h2>
                <p class="text-xs text-gray-500 mb-10 tracking-[0.8em] font-bold">BYPASSING KERNEL LIMITATIONS</p>

                <div class="flex gap-6">
                    <button onclick="engageGaming()" class="ray-trace-enabled bg-red-600 hover:bg-red-500 px-16 py-7 rounded-3xl text-xl font-black shadow-[0_0_50px_rgba(220,38,38,0.4)] transition-all transform hover:scale-105 active:scale-95 border border-red-400/50">
                        VELOCITY MODE
                    </button>
                    <button onclick="engageFPSMode()" class="ray-trace-enabled bg-orange-500 hover:bg-orange-400 px-16 py-7 rounded-3xl text-xl font-black shadow-[0_0_50px_rgba(245,158,11,0.35)] transition-all transform hover:scale-105 active:scale-95 border border-orange-300/50">
                        FPS MODE
                    </button>
                </div>

            </div>
        </div>

        <div id="page-about" class="page text-center">
            <div class="py-32 flex flex-col items-center">
                <div class="w-24 h-24 bg-blue-600 rounded-3xl mb-10 flex items-center justify-center transform rotate-12 shadow-[0_0_60px_rgba(37,99,235,0.6)] ray-trace-enabled">
                    <span class="text-5xl font-black italic text-white">C</span>
                </div>
                <h2 class="text-7xl font-black mb-4 tracking-tighter italic text-white">CortexDev Official</h2>
                <p class="text-blue-500 font-bold tracking-[0.6em] mb-12 text-[11px]">ADVANCED WINDOWS UTILITY</p>
                <p class="max-w-xl text-gray-400 text-sm leading-relaxed mb-16 italic font-medium px-10">
                    Built by CortexDev to redefine system interaction. No bloat, no trackers, just pure performance and elite aesthetics.
                </p>
                <div class="flex space-x-6">
                    <span class="bg-white/5 px-10 py-3 rounded-full text-[11px] font-black border border-white/10 uppercase tracking-widest hover:bg-white/10 transition-colors cursor-default">Build v4.2.5</span>
                    <span class="bg-green-500/10 px-10 py-3 rounded-full text-[11px] font-black text-green-500 border border-green-500/10 uppercase tracking-widest shadow-[0_0_20px_rgba(34,197,94,0.2)]">Kernel Verified</span>
                </div>
            </div>
        </div>

    </div>

    <script>
        function nextStep(step) {
            document.querySelectorAll('.welcome-stage').forEach(s => s.classList.remove('active'));
            document.querySelectorAll('.step-dot').forEach(d => d.classList.remove('active'));

            setTimeout(() => {
                document.getElementById('w-stage-' + step).classList.add('active');
                for(let i=1; i<=step; i++) {
                    document.getElementById('dot-' + i).classList.add('active');
                }
            }, 100);
        }

        function finishWelcome() {
            const overlay = document.getElementById('welcome-overlay');
            overlay.classList.add('fade-out');
            setTimeout(() => { overlay.style.display = 'none'; }, 1000);
        }

        function addLog(msg){
            const box = document.getElementById("log-box");
            if(!box) return;
            const line = document.createElement("div");
            line.innerText = msg;
            box.appendChild(line);
            box.scrollTop = box.scrollHeight;
        }

        const apps = [
            { id: 'Brave.Brave', name: 'Brave Browser', desc: 'Secure & Fast' },
            { id: 'Discord.Discord', name: 'Discord', desc: 'Communication' },
            { id: 'Valve.Steam', name: 'Steam', desc: 'Gaming Platform' },
            { id: 'Microsoft.VisualStudioCode', name: 'VS Code', desc: 'Code Editor' },
            { id: '7zip.7zip', name: '7-Zip', desc: 'Compression' },
            { id: 'VideoLAN.VLC', name: 'VLC Media Player', desc: 'Multimedia' },
            { id: 'Spotify.Spotify', name: 'Spotify', desc: 'Music Streaming' },
            { id: 'EpicGames.EpicGamesLauncher', name: 'Epic Games', desc: 'Gaming Launcher' },
            { id: 'Mozilla.Firefox', name: 'Firefox', desc: 'Web Browser' },
            { id: 'OBSProject.OBSStudio', name: 'OBS Studio', desc: 'Streaming' },
            { id: 'GIMP.GIMP', name: 'GIMP', desc: 'Image Editor' },
            { id: 'Python.Python.3.11', name: 'Python 3.11', desc: 'Programming' }
        ];

        const bloatware = [
            { id: 'Microsoft.YourPhone', name: 'Your Phone', desc: 'Link to mobile' },
            { id: 'Microsoft.XboxGamingOverlay', name: 'Xbox Game Bar', desc: 'Overlay junk' },
            { id: 'Microsoft.GetHelp', name: 'Get Help', desc: 'Useless support app' },
            { id: 'Microsoft.People', name: 'People', desc: 'Contacts bloat' },
            { id: 'Microsoft.WindowsFeedbackHub', name: 'Feedback Hub', desc: 'Telemetry tool' },
            { id: 'Microsoft.MicrosoftSolitaireCollection', name: 'Solitaire', desc: 'Pre-installed game' },
            { id: 'Microsoft.ZuneVideo', name: 'Movies & TV', desc: 'Stock video player' },
            { id: 'Microsoft.ZuneMusic', name: 'Groove Music', desc: 'Stock music player' },
            { id: 'Microsoft.WindowsMaps', name: 'Windows Maps', desc: 'Map service' },
            { id: 'Microsoft.BingWeather', name: 'Weather', desc: 'Weather updates' },
            { id: 'Microsoft.BingNews', name: 'News', desc: 'News feed' },
            { id: 'Microsoft.WindowsAlarms', name: 'Alarms & Clock', desc: 'System clock' },
            { id: 'Microsoft.WindowsCalculator', name: 'Calculator', desc: 'Stock calculator' },
            { id: 'Microsoft.WindowsCamera', name: 'Camera', desc: 'System camera' },
            { id: 'Microsoft.SkypeApp', name: 'Skype', desc: 'Communication' },
            { id: 'Microsoft.MicrosoftStickyNotes', name: 'Sticky Notes', desc: 'Note taking' },
            { id: 'Microsoft.MSPaint', name: 'Paint 3D', desc: '3D modeling' },
            { id: 'Microsoft.Office.OneNote', name: 'OneNote', desc: 'Digital notebook' },
            { id: 'Microsoft.WindowsSoundRecorder', name: 'Voice Recorder', desc: 'Audio recording' },
            { id: 'Microsoft.WindowsCommunicationsApps', name: 'Mail & Calendar', desc: 'Email client' },
            { id: 'Microsoft.Wallet', name: 'Windows Wallet', desc: 'Payment storage' },
            { id: 'Microsoft.BingSports', name: 'Sports', desc: 'Sports news' },
            { id: 'Microsoft.BingFinance', name: 'Money', desc: 'Finance tracking' },
            { id: 'Microsoft.PowerAutomateDesktop', name: 'Power Automate', desc: 'Automation tool' },
            { id: 'Microsoft.Todos', name: 'Microsoft To Do', desc: 'Task manager' }
        ];

        const optimizations = [
            { id: 'cache', name: 'Clear Cache', desc: 'Delete temp files' },
            { id: 'sfc', name: 'Repair System', desc: 'Run SFC Scan' },
            { id: 'dns', name: 'Flush DNS', desc: 'Fix network lag' },
            { id: 'power', name: 'Ultimate Power', desc: 'Unlock max performance' },
            { id: 'trim', name: 'SSD Trim', desc: 'Optimize drive speed' },
            { id: 'telemetry', name: 'Kill Telemetry', desc: 'Stop Windows spying' },
            { id: 'hibernation', name: 'Disable Sleep', desc: 'Save disk space' },
            { id: 'visuals', name: 'Boost Visuals', desc: 'Reduce UI lag' }
        ];

        function switchPage(pageId, element) {
            document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
            document.querySelectorAll('.sidebar-item').forEach(i => i.classList.remove('active'));

            setTimeout(() => {
                document.getElementById('page-' + pageId).classList.add('active');
            }, 50);

            if(element) element.classList.add('active');
        }

        function showToast(msg, type='info') {
            const container = document.getElementById('toast-container');
            const toast = document.createElement('div');
            toast.className = `toast-msg ${type} ray-trace-enabled`;
            toast.innerHTML = `<span class="text-xl">${type === 'success' ? '✔' : type === 'error' ? '✖' : type === 'gaming' ? '⚡' : 'ℹ'}</span> <span>${msg}</span>`;
            container.appendChild(toast);
            setTimeout(() => toast.remove(), 4000);
        }

        function populateSoftware() {
            const grid = document.getElementById('software-grid');
            if(!grid) return;
            grid.innerHTML = "";
            apps.forEach(app => {
                const card = document.createElement('div');
                card.className = 'card group cursor-pointer ray-trace-enabled';
                card.innerHTML = `
                    <div class="flex justify-between items-start mb-4">
                        <div class="w-10 h-10 bg-white/5 rounded-full flex items-center justify-center text-lg group-hover:bg-blue-500 group-hover:text-white transition-colors">⬇</div>
                    </div>
                    <h3 class="text-lg font-bold text-white mb-1">${app.name}</h3>
                    <p class="text-xs text-gray-500 uppercase tracking-wider mb-4">${app.desc}</p>
                    <button onclick="installApp('${app.id}')" class="install-btn w-full">Install</button>
                `;
                grid.appendChild(card);
            });
        }

        function populateAppManager() {
            const grid = document.getElementById('appmanager-grid');
            if(!grid) return;
            grid.innerHTML = "";
            bloatware.forEach(app => {
                const card = document.createElement('div');
                card.className = 'card border-red-500/20 bg-red-500/5 hover:bg-red-500/10 ray-trace-enabled';
                card.innerHTML = `
                    <h3 class="text-lg font-bold text-white mb-1">${app.name}</h3>
                    <p class="text-xs text-red-400 uppercase tracking-wider mb-4">${app.desc}</p>
                    <button onclick="uninstallApp('${app.id}')" class="install-btn !bg-red-900/20 !border-red-500/30 hover:!bg-red-600 w-full">Uninstall</button>
                `;
                grid.appendChild(card);
            });
        }

        function populateOptimizer() {
            const grid = document.getElementById('optimizer-grid');
            if(!grid) return;
            grid.innerHTML = "";
            optimizations.forEach(opt => {
                const card = document.createElement('div');
                card.className = 'card hover:border-blue-500/30 ray-trace-enabled';
                card.innerHTML = `
                    <div class="flex items-center gap-4 mb-4">
                        <div class="w-2 h-2 bg-blue-500 rounded-full shadow-[0_0_10px_#3b82f6]"></div>
                        <h3 class="text-lg font-bold text-white">${opt.name}</h3>
                    </div>
                    <p class="text-xs text-gray-500 uppercase tracking-wider mb-4 pl-6">${opt.desc}</p>
                    <button onclick="runOptimizer('${opt.id}')" class="install-btn w-full">Execute</button>
                `;
                grid.appendChild(card);
            });
        }

        function installApp(id) { pywebview.api.run_install(id); }
        function uninstallApp(id) { pywebview.api.uninstall_sys_app(id); }
        function runOptimizer(action) { pywebview.api.run_optimize(action); }
        function runHealthCheck() { pywebview.api.run_health_check(); }
        function runSystemCleaner() { pywebview.api.run_system_cleaner(); }

        function enableUltimatePower(){ pywebview.api.set_ultimate_power(); }
        function openWindowsUpdate(){ pywebview.api.open_windows_update(); }
        function closeBackgroundApps(){ pywebview.api.kill_background_apps(); }

        // NEW v4.2.5 Buttons
        function runDismRepair(){ pywebview.api.repair_dism(); }
        function createRestorePoint(){ pywebview.api.create_restore_point(); }
        function enableSafeMode(){ pywebview.api.safe_mode_enable(); }
        function disableSafeMode(){ pywebview.api.safe_mode_disable(); }

        function engageGaming(){ pywebview.api.run_gaming_boost(); }
        function engageFPSMode(){ pywebview.api.run_fps_mode(); }

        async function refreshStats(){
            try{
                const s = await pywebview.api.get_stats();
                document.getElementById("stat-ram").innerText = s.ram;
                document.getElementById("stat-os").innerText = s.os;
                document.getElementById("stat-uptime").innerText = s.uptime;
                document.getElementById("stat-cpu").innerText = s.cpu;
                document.getElementById("stat-gpu").innerText = s.gpu;
            }catch(e){}
        }

        async function refreshDisk(){
            try{
                const d = await pywebview.api.get_disk_space();
                document.getElementById("stat-diskfree").innerText = d.free_gb;
                document.getElementById("stat-diskpercent").innerText = "Used: " + d.percent;
            }catch(e){}
        }

        async function refreshTemp(){
            try{
                const t = await pywebview.api.get_cpu_temp();
                document.getElementById("stat-temp").innerText = t.temp;
            }catch(e){}
        }

        window.addEventListener("pywebviewready", () => {
            populateSoftware();
            populateAppManager();
            populateOptimizer();

            refreshStats();
            refreshDisk();
            refreshTemp();

            setInterval(refreshStats, 2500);
            setInterval(refreshDisk, 6000);
            setInterval(refreshTemp, 3000);

            showToast("MWB v4.2.5 Loaded", "success");
        });
    </script>

</body>
</html>
"""


def apply_mica(window):
    try:
        if pywinstyles is None:
            return
        hwnd = window._hwnd
        pywinstyles.apply_style(hwnd, "mica")
    except:
        pass


def main():
    api = Api()

    window = webview.create_window(
        f"{APP_NAME} v{VERSION}",
        html=HTML_UI,
        js_api=api,
        width=1400,
        height=900,
        resizable=True,
        frameless=False
    )

    # Apply Mica/Acrylic
    threading.Timer(0.5, lambda: apply_mica(window)).start()

    webview.start(debug=False)


if __name__ == "__main__":
    main()
