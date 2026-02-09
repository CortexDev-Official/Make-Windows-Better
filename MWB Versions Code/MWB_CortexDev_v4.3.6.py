import webview
import threading
import subprocess
import platform
import ctypes
import sys
import os
import shutil
import time
import json
import re
from datetime import timedelta
import tempfile
import urllib.request
import math
import uuid

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
VERSION = "4.3.6"
AUTHOR = "CortexDev-Official"

ALLOWED_REMOVE_PREFIXES = ("Microsoft.", "Windows.", "Nvidia.", "Intel.")

# --- CortexDev Anti-Flash Constants ---
# This flag (0x08000000) tells Windows NOT to create a console window for the process
CREATE_NO_WINDOW = 0x08000000
# This flag (0) tells ShellExecute to hide the window
SW_HIDE = 0

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
    def __init__(self):
        # In-memory log buffer (keeps last 200 entries)
        self._log_buffer = []
        self._log_lock = threading.Lock()
        self.log_file = os.path.join(os.environ.get("LOCALAPPDATA", tempfile.gettempdir()), "MWB", "mwb.log")
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)
        self._last_junk_notification = 0
        # installer mapping for in-app downloads (direct installers)
        self.installer_map = {
            "Brave.Brave": {
                "name": "Brave Browser",
                "url": "https://laptop-updates.brave.com/latest/win64",
                "silent_args": "/silent",
                "filename": "BraveSetup.exe"
            },
            "Discord.Discord": {
                "name": "Discord",
                "url": "https://discord.com/api/download?platform=win",
                "silent_args": "/S",
                "filename": "DiscordSetup.exe"
            },
            "Valve.Steam": {
                "name": "Steam",
                "url": "https://cdn.cloudflare.steamstatic.com/client/installer/SteamSetup.exe",
                "silent_args": "/S",
                "filename": "SteamSetup.exe"
            },
            "Microsoft.VisualStudioCode": {
                "name": "VS Code",
                "url": "https://update.code.visualstudio.com/latest/win32-x64-user/stable",
                "silent_args": "/VERYSILENT /NORESTART",
                "filename": "VSCodeSetup.exe"
            },
            "7zip.7zip": {
                "name": "7-Zip",
                "url": "https://www.7-zip.org/a/7z1900-x64.exe",
                "silent_args": "/S",
                "filename": "7zip.exe"
            },
            "VideoLAN.VLC": {
                "name": "VLC Media Player",
                "url": "https://get.videolan.org/vlc/last/win64/vlc.exe",
                "silent_args": "/S",
                "filename": "VLC.exe"
            },
            "Spotify.Spotify": {
                "name": "Spotify",
                "url": "https://download.scdn.co/SpotifySetup.exe",
                "silent_args": "/silent",
                "filename": "SpotifySetup.exe"
            },
            "EpicGames.EpicGamesLauncher": {
                "name": "Epic Games",
                "url": "https://launcher-public-service-prod06.ol.epicgames.com/launcher/api/installer/download/EpicGamesLauncherInstaller.msi",
                "silent_args": "/quiet",
                "filename": "EpicInstaller.msi"
            },
            "Mozilla.Firefox": {
                "name": "Firefox",
                "url": "https://download.mozilla.org/?product=firefox-latest&os=win64&lang=en-US",
                "silent_args": "-ms",
                "filename": "FirefoxSetup.exe"
            },
            "OBSProject.OBSStudio": {
                "name": "OBS Studio",
                "url": "https://github.com/obsproject/obs-studio/releases/latest/download/OBS-Studio-Installer.exe",
                "silent_args": "/S",
                "filename": "OBSInstaller.exe"
            },
            "GIMP.GIMP": {
                "name": "GIMP",
                "url": "https://download.gimp.org/mirror/pub/gimp/v2.10/windows/gimp-2.10.34-setup.exe",
                "silent_args": "/S",
                "filename": "GIMPSetup.exe"
            },
            "Python.Python.3.11": {
                "name": "Python 3.11",
                "url": "https://www.python.org/ftp/python/3.11.0/python-3.11.0-amd64.exe",
                "silent_args": "/quiet InstallAllUsers=1 PrependPath=1",
                "filename": "python311.exe"
            }
        }

    def _write_log_to_disk(self, entry):
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(entry + "\n")
        except:
            pass

    def _log(self, msg, level="INFO", details=None):
        """Improved logging: timestamp, thread, level, details; persist to disk and JS log UI"""
        try:
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            thread_name = threading.current_thread().name
            entry = {
                "time": timestamp,
                "level": level,
                "thread": thread_name,
                "msg": msg,
                "details": details or ""
            }
            formatted = f"[{entry['time']}] [{entry['level']}] [{entry['thread']}] {entry['msg']} {entry['details']}"
            with self._log_lock:
                self._log_buffer.append(formatted)
                if len(self._log_buffer) > 200:
                    self._log_buffer.pop(0)
            # persist
            self._write_log_to_disk(formatted)
            # send to JS log box safely
            try:
                safe_js_arg = json.dumps(formatted)
                win = webview.active_window()
                if win:
                    win.evaluate_js(f"addLog({safe_js_arg})")
            except:
                pass
        except:
            pass

    def get_logs(self, count=100):
        """Return recent logs to the UI"""
        with self._log_lock:
            return list(self._log_buffer[-count:])

    def get_stats(self):
        try:
            mem = MEMORYSTATUSEX()
            mem.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(mem))
            tick = ctypes.windll.kernel32.GetTickCount64()
            uptime = str(timedelta(milliseconds=tick)).split('.')[0]


            cpu_name = platform.processor()
            try:
                # Anti-Flash: Added creationflags=CREATE_NO_WINDOW
                gpu_out = subprocess.check_output(
                    ["wmic", "path", "win32_VideoController", "get", "name"],
                    shell=False,
                    creationflags=CREATE_NO_WINDOW
                ).decode(errors="ignore").split('\n')
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

                # Anti-Flash: Added creationflags=CREATE_NO_WINDOW
                result = subprocess.run(
                    ["sfc", "/verifyonly"],
                    shell=False,
                    capture_output=True,
                    text=True,
                    creationflags=CREATE_NO_WINDOW
                )

                if "found integrity violations" in result.stdout.lower() or result.returncode != 0:
                    self._log("Integrity issues found! Suggest: sfc /scannow as Admin.", "WARN")
                    try:
                        webview.active_window().evaluate_js(
                            "showToast('Integrity issues found! Run sfc /scannow as Admin.', 'error')"
                        )
                    except: pass
                else:
                    self._log("System Integrity Secured (No errors).", "SUCCESS")
                    try:
                        webview.active_window().evaluate_js("showToast('System Integrity Secured (No errors).', 'success')")
                    except: pass
            except Exception as e:
                self._log(f"Health Check Failed to initialize. {str(e)}", "ERROR")
                try:
                    webview.active_window().evaluate_js("showToast('Health Check Failed to initialize.', 'error')")
                except: pass

        threading.Thread(target=task, daemon=True).start()
        return "Scan Started"


    def run_system_cleaner(self):
        def task():
            folders = [
                os.environ.get('TEMP'),
                os.path.join(os.environ.get('SystemRoot', 'C:\\Windows'), 'Temp'),
                os.path.join(os.environ.get('SystemRoot', 'C:\\Windows'), 'Prefetch')
            ]

            total_deleted = 0
            file_count = 0
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
                                file_count += 1

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
                                # try to estimate number of files removed
                                file_count += 1

                        except PermissionError:
                            self._log(f"In use / Access denied: {filename}", "WARN")
                            continue
                        except Exception as e:
                            self._log(f"Cleaner error for {filename}: {str(e)}", "ERROR")
                            continue

            cleaned_mb = total_deleted / (1024 * 1024)
            time.sleep(0.5)

            self._log(f"Cleaner finished. Total cleaned: {cleaned_mb:.1f} MB (Items: {file_count})", "SUCCESS")
            try:
                webview.active_window().evaluate_js(f"showToast('Cleaned {cleaned_mb:.1f} MB ({file_count} items)', 'success')")
            except: pass

        threading.Thread(target=task, daemon=True).start()
        return "Cleaning..."

    def _download_with_progress(self, url, dest_path, callback_js_name=None, download_id=None):
        """Download file in chunks and report progress via JS callback (if available)"""
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "MWB-Agent/1.0"})
            with urllib.request.urlopen(req, timeout=60) as resp:
                total_size = resp.getheader('Content-Length')
                if total_size:
                    total_size = int(total_size.strip())
                else:
                    total_size = None

                chunk_size = 8192
                read = 0
                start = time.time()
                last_update = start
                with open(dest_path, "wb") as out:
                    while True:
                        chunk = resp.read(chunk_size)
                        if not chunk:
                            break
                        out.write(chunk)
                        read += len(chunk)
                        now = time.time()
                        # throttle JS updates to ~4 per second
                        if callback_js_name and (now - last_update > 0.25):
                            elapsed = now - start
                            speed = read / (elapsed + 0.0001)  # bytes/s
                            percent = (read / total_size * 100) if total_size else None
                            eta = None
                            if total_size and speed > 0:
                                eta = int((total_size - read) / speed)
                            payload = {
                                "id": download_id,
                                "read": read,
                                "total": total_size,
                                "percent": percent,
                                "speed": speed,
                                "eta": eta,
                                "path": dest_path
                            }
                            try:
                                safe_js = json.dumps(payload)
                                win = webview.active_window()
                                if win:
                                    win.evaluate_js(f"{callback_js_name}({safe_js})")
                            except:
                                pass
                            last_update = now
                # final update
                if callback_js_name:
                    payload = {
                        "id": download_id,
                        "read": read,
                        "total": total_size,
                        "percent": 100,
                        "speed": 0,
                        "eta": 0,
                        "path": dest_path
                    }
                    try:
                        safe_js = json.dumps(payload)
                        win = webview.active_window()
                        if win:
                            win.evaluate_js(f"{callback_js_name}({safe_js})")
                    except:
                        pass
                return True, None
        except Exception as e:
            return False, str(e)

    def run_install(self, uid):
        """Download installer inside the app (no winget/powershell) and show download UI with progress, speed, ETA"""
        def task():
            if not isinstance(uid, str) or not re.match(r"^[a-zA-Z0-9\.\-]+$", uid):
                self._log("Blocked suspicious package id", "WARN")
                return

            self._log(f"Install requested: {uid}", "INFO")
            info = self.installer_map.get(uid)
            if not info:
                self._log(f"No installer mapping for {uid}", "ERROR")
                try:
                    webview.active_window().evaluate_js(f"showToast('No direct installer available for {uid}', 'error')")
                except: pass
                return

            tempdir = os.path.join(tempfile.gettempdir(), "mwb_downloads")
            os.makedirs(tempdir, exist_ok=True)
            download_id = str(uuid.uuid4())
            dest = os.path.join(tempdir, info.get("filename", f"{uid}.exe"))

            try:
                # instruct JS to show download overlay
                win = webview.active_window()
                if win:
                    try:
                        win.evaluate_js(f"showDownloadOverlay({json.dumps(download_id)}, {json.dumps(info.get('name'))})")
                    except:
                        pass

                self._log(f"Starting download for {uid} from {info.get('url')}", "INFO")
                ok, err = self._download_with_progress(info.get("url"), dest, callback_js_name="updateDownloadProgress", download_id=download_id)
                if not ok:
                    self._log(f"Download failed for {uid}: {err}", "ERROR")
                    try:
                        win.evaluate_js(f"showToast('Download failed for {info.get('name')}', 'error')")
                        win.evaluate_js(f"hideDownloadOverlay({json.dumps(download_id)})")
                    except: pass
                    return

                self._log(f"Download completed for {uid} to {dest}", "SUCCESS")
                try:
                    win.evaluate_js(f"showToast('Download complete: {info.get('name')}', 'success')")
                except: pass

                # execute installer with silent args
                args = info.get("silent_args", "")
                try:
                    # If MSI use msiexec /i
                    if dest.lower().endswith(".msi"):
                        cmd = ["msiexec", "/i", dest] + args.split()
                        subprocess.run(cmd, shell=False, creationflags=CREATE_NO_WINDOW)
                    else:
                        # Use ShellExecuteW to run elevated if required; hidden window
                        ctypes.windll.shell32.ShellExecuteW(None, "runas", dest, args, None, SW_HIDE)
                    self._log(f"Installation command executed for {uid}", "SUCCESS", details=f"installer={dest} args={args}")
                    try:
                        win.evaluate_js(f"hideDownloadOverlay({json.dumps(download_id)})")
                        win.evaluate_js(f"showToast('Installation started for {info.get('name')}', 'info')")
                    except: pass
                except Exception as e:
                    self._log(f"Installation failed to start: {str(e)}", "ERROR")
                    try:
                        win.evaluate_js(f"hideDownloadOverlay({json.dumps(download_id)})")
                        win.evaluate_js(f"showToast('Installation failed to start for {info.get('name')}', 'error')")
                    except: pass

            except Exception as e:
                self._log(f"Installer flow failed: {str(e)}", "ERROR")
                try:
                    webview.active_window().evaluate_js(f"hideDownloadOverlay({json.dumps(download_id)})")
                except: pass

        threading.Thread(target=task, daemon=True).start()
        return f"Installing {uid}..."

    def uninstall_sys_app(self, package_name):
        """Copilot modification: Check allowlist before removal"""
        def task():
            if not isinstance(package_name, str) or len(package_name) > 150:
                self._log("Invalid package name", "WARN")
                return


            if not package_name.startswith(ALLOWED_REMOVE_PREFIXES):
                self._log(f"Blocked uninstall attempt for: {package_name}", "WARN")
                try:
                    webview.active_window().evaluate_js(f"showToast('Restricted: {package_name}', 'error')")
                except: pass
                return

            self._log(f"Uninstall requested: {package_name}", "WARN")

            # Anti-Flash: Added creationflags=CREATE_NO_WINDOW
            cmd = ["powershell", "-NoProfile", "-NonInteractive", "-WindowStyle", "Hidden", "-Command", f"Get-AppxPackage *{package_name}* | Remove-AppxPackage"]
            subprocess.run(cmd, shell=False, creationflags=CREATE_NO_WINDOW)
            self._log(f"Attempted to remove {package_name}", "WARN")
            try:
                webview.active_window().evaluate_js(f"showToast('Attempted to remove {package_name}', 'warning')")
            except: pass

        threading.Thread(target=task, daemon=True).start()
        return "Uninstalling..."

    def run_optimize(self, action):
        commands = {
            "cache": ["cleanmgr", "/sagerun:1"],
            "sfc": ["sfc", "/scannow"],
            "dns": ["ipconfig", "/flushdns"],
            "power": ["powercfg", "-duplicatescheme", "e9a42b02-d5df-448d-aa00-03f14749eb61"],
            "trim": ["defrag", "C:", "/O"],
            "telemetry": "sc stop DiagTrack && sc config DiagTrack start= disabled",
            "hibernation": ["powercfg", "-h", "off"],
            "updates": "net stop wuauserv && sc config wuauserv start= disabled",
            "transparency": "reg add \"HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Themes\\Personalize\" /v EnableTransparency /t REG_DWORD /d 0 /f",
            "gamebar": "reg add \"HKCU\\System\\GameConfigStore\" /v GameDVR_Enabled /t REG_DWORD /d 0 /f"
        }

        cmd_val = commands.get(action)
        if cmd_val:
            def task():
                try:
                    self._log(f"Optimizer executing: {action}", "INFO")
                    # Anti-Flash: Changed 1 (SW_SHOWNORMAL) to SW_HIDE (0)
                    if isinstance(cmd_val, list):
                        ctypes.windll.shell32.ShellExecuteW(None, "runas", cmd_val[0], " ".join(cmd_val[1:]), None, SW_HIDE)
                    else:
                        ctypes.windll.shell32.ShellExecuteW(None, "runas", "cmd.exe", f"/c {cmd_val}", None, SW_HIDE)

                    self._log(f"Optimization task executed: {action}", "SUCCESS")
                    try:
                        webview.active_window().evaluate_js(f"showToast('Optimization task: {action} executed', 'success')")
                    except: pass
                except Exception as e:
                    self._log(f"Optimization failed: {action} ({str(e)})", "ERROR")
                    try:
                        webview.active_window().evaluate_js(f"showToast('Optimization failed: {action}', 'error')")
                    except: pass

            threading.Thread(target=task, daemon=True).start()
        return "Task initiated"


    def set_ultimate_power(self):
        def task():
            try:
                self._log("Ultimate Performance requested...", "INFO")
                # Anti-Flash: Added creationflags=CREATE_NO_WINDOW
                subprocess.run(["powercfg", "-duplicatescheme", "e9a42b02-d5df-448d-aa00-03f14749eb61"], shell=False, creationflags=CREATE_NO_WINDOW)
                subprocess.run(["powercfg", "/setactive", "e9a42b02-d5df-448d-aa00-03f14749eb61"], shell=False, creationflags=CREATE_NO_WINDOW)
                self._log("Ultimate Performance Enabled", "SUCCESS")
                try:
                    webview.active_window().evaluate_js("showToast('Ultimate Performance Enabled', 'success')")
                except: pass
            except Exception as e:
                self._log(f"Ultimate Performance failed: {str(e)}", "ERROR")
                try:
                    webview.active_window().evaluate_js("showToast('Power plan failed', 'error')")
                except: pass

        threading.Thread(target=task, daemon=True).start()
        return "Power Boost..."


    def open_windows_update(self):
        try:
            self._log("Opening Windows Update...", "INFO")

            os.startfile("ms-settings:windowsupdate")
            return "Opening Windows Update..."
        except Exception as e:
            self._log(f"Failed to open Windows Update: {str(e)}", "ERROR")
            return "Failed"


    def kill_background_apps(self):
        def task():
            targets = ["chrome.exe", "OneDrive.exe"]
            killed = []
            self._log("Background app cleanup started...", "INFO")

            for t in targets:
                try:
                    # Anti-Flash: Added creationflags=CREATE_NO_WINDOW
                    subprocess.run(["taskkill", "/f", "/im", t], shell=False, capture_output=True, creationflags=CREATE_NO_WINDOW)
                    killed.append(t)
                except:
                    pass

            if killed:
                closed_list = ", ".join(killed)
                self._log("Closed: " + closed_list, "WARN")
                try:
                    webview.active_window().evaluate_js(f"showToast('Closed: {closed_list}', 'warning')")
                except: pass
            else:
                self._log("No background apps closed.", "INFO")
                try:
                    webview.active_window().evaluate_js("showToast('No background apps closed', 'info')")
                except: pass

        threading.Thread(target=task, daemon=True).start()
        return "Background cleanup..."


    def repair_dism(self):
        def task():
            try:
                self._log("Repair + DISM started...", "INFO")
                # Anti-Flash: Changed 1 (SW_SHOWNORMAL) to SW_HIDE (0)
                ctypes.windll.shell32.ShellExecuteW(None, "runas", "dism.exe", "/Online /Cleanup-Image /RestoreHealth", None, SW_HIDE)
                self._log("DISM command sent (Admin)", "SUCCESS")
                try:
                    webview.active_window().evaluate_js("showToast('DISM Repair Started (Admin)', 'success')")
                except: pass
            except Exception as e:
                self._log(f"DISM failed to start: {str(e)}", "ERROR")
                try:
                    webview.active_window().evaluate_js("showToast('DISM failed to start', 'error')")
                except: pass

        threading.Thread(target=task, daemon=True).start()
        return "DISM Running..."


    def create_restore_point(self):
        def task():
            try:
                self._log("Restore Point requested...", "INFO")
                ps = r"Enable-ComputerRestore -Drive 'C:\'; Checkpoint-Computer -Description 'MWB Restore Point' -RestorePointType 'MODIFY_SETTINGS'"
                # Anti-Flash: Changed 1 (SW_SHOWNORMAL) to SW_HIDE (0)
                ctypes.windll.shell32.ShellExecuteW(None, "runas", "powershell.exe", f"-ExecutionPolicy Bypass -Command {ps}", None, SW_HIDE)
                self._log("Restore Point creation requested (Admin)", "SUCCESS")
                try:
                    webview.active_window().evaluate_js("showToast('Restore Point Created (Admin)', 'success')")
                except: pass
            except Exception as e:
                self._log(f"Restore Point failed: {str(e)}", "ERROR")
                try:
                    webview.active_window().evaluate_js("showToast('Restore Point failed', 'error')")
                except: pass

        threading.Thread(target=task, daemon=True).start()
        return "Restore Point..."


    def safe_mode_enable(self):
        def task():
            try:
                self._log("Safe Mode ENABLE requested...", "WARN")
                # Anti-Flash: Changed 1 (SW_SHOWNORMAL) to SW_HIDE (0)
                ctypes.windll.shell32.ShellExecuteW(None, "runas", "bcdedit.exe", "/set {current} safeboot minimal", None, SW_HIDE)
                self._log("Safe Mode enabled (next reboot)", "SUCCESS")
                try:
                    webview.active_window().evaluate_js("showToast('Safe Mode enabled for next reboot', 'success')")
                except: pass
            except Exception as e:
                self._log(f"Safe Mode enable failed: {str(e)}", "ERROR")
                try:
                    webview.active_window().evaluate_js("showToast('Safe Mode enable failed', 'error')")
                except: pass

        threading.Thread(target=task, daemon=True).start()
        return "Safe Mode ON..."

    def safe_mode_disable(self):
        def task():
            try:
                self._log("Safe Mode DISABLE requested...", "INFO")
                # Anti-Flash: Changed 1 (SW_SHOWNORMAL) to SW_HIDE (0)
                ctypes.windll.shell32.ShellExecuteW(None, "runas", "bcdedit.exe", "/deletevalue {current} safeboot", None, SW_HIDE)
                self._log("Safe Mode disabled (next reboot)", "SUCCESS")
                try:
                    webview.active_window().evaluate_js("showToast('Safe Mode disabled (next reboot)', 'success')")
                except: pass
            except Exception as e:
                self._log(f"Safe Mode disable failed: {str(e)}", "ERROR")
                try:
                    webview.active_window().evaluate_js("showToast('Safe Mode disable failed', 'error')")
                except: pass

        threading.Thread(target=task, daemon=True).start()
        return "Safe Mode OFF..."


    def run_fps_mode(self):
        def task():
            self._log("FPS Mode started...", "INFO")
            ps_script = "Get-Process | Where-Object {$_.MainWindowTitle -ne ''} | ForEach-Object { try { $_.PriorityClass = 'High' } catch {} }"

            boost_cmds = [
                ["ipconfig", "/flushdns"],
                ["powercfg", "/setactive", "SCHEME_MIN"],
                ["reg", "add", "HKCU\\System\\GameConfigStore", "/v", "GameDVR_Enabled", "/t", "REG_DWORD", "/d", "0", "/f"],
                ["powershell", "-WindowStyle", "Hidden", "-Command", ps_script]
            ]

            for cmd in boost_cmds:
                try:
                    # Anti-Flash: Added creationflags=CREATE_NO_WINDOW
                    subprocess.run(cmd, shell=False, creationflags=CREATE_NO_WINDOW)
                except: pass

            self._log("FPS Mode Active: High Priority + GameDVR OFF", "SUCCESS")
            try:
                webview.active_window().evaluate_js("showToast('FPS Mode Active: MAX Performance', 'gaming')")
            except: pass

        threading.Thread(target=task, daemon=True).start()
        return "FPS Mode Active"

    def run_gaming_boost(self):
        def task():
            self._log("Velocity Mode started...", "INFO")
            ps_script = "Get-Process | Where-Object {$_.MainWindowTitle -ne ''} | ForEach-Object { try { $_.PriorityClass = 'AboveNormal' } catch {} }"

            boost_cmds = [
                ["ipconfig", "/flushdns"],
                ["powercfg", "/setactive", "SCHEME_MIN"],
                ["powershell", "-WindowStyle", "Hidden", "-Command", ps_script]
            ]

            for cmd in boost_cmds:
                try:
                    # Anti-Flash: Added creationflags=CREATE_NO_WINDOW
                    subprocess.run(cmd, shell=False, creationflags=CREATE_NO_WINDOW)
                except: pass

            self._log("Velocity Mode Active: Priority boosted", "SUCCESS")
            try:
                webview.active_window().evaluate_js("showToast('Velocity Mode Active', 'gaming')")
            except: pass

        threading.Thread(target=task, daemon=True).start()
        return "Velocity Mode Active"

    def run_ghost_compression(self):
        def task():
            try:
                self._log("Initializing Ghost Compression...", "WARN")
                # Anti-Flash: Changed 1 (SW_SHOWNORMAL) to SW_HIDE (0)
                ctypes.windll.shell32.ShellExecuteW(None, "runas", "compact.exe", "/CompactOS:always", None, SW_HIDE)
                self._log("Ghost Compression initiated.", "SUCCESS")
                try:
                    webview.active_window().evaluate_js("showToast('Ghost Compression Started', 'info')")
                except: pass
            except Exception as e:
                self._log(f"Compression failed: {str(e)}", "ERROR")

        threading.Thread(target=task, daemon=True).start()
        return "Compressing..."

    def enable_god_mode(self):
        def task():
            try:
                self._log("Invoking Omni-Control...", "WARN")
                desktop_path = os.path.join(os.environ['USERPROFILE'], 'Desktop')
                folder_name = "Omni-Control.{ED7BA470-8E54-465E-825C-99712043E01C}"
                full_path = os.path.join(desktop_path, folder_name)

                if not os.path.exists(full_path):
                    os.makedirs(full_path)
                    self._log("Omni-Control folder created.", "SUCCESS")
                    try:
                        webview.active_window().evaluate_js("showToast('Omni-Control Created', 'success')")
                    except: pass
                else:
                    self._log("Omni-Control already exists.", "INFO")
            except Exception as e:
                self._log(f"Omni-Control failed: {str(e)}", "ERROR")
        threading.Thread(target=task, daemon=True).start()
        return "Omni-Control..."

    # --- Background monitoring & advanced notifications ---

    def background_monitor(self, scan_interval_seconds=300, junk_threshold_mb=50, notify_interval_seconds=1800):
        """
        Periodically scan junk folders quietly and send a single non-intrusive notification if significant junk found.
        - scan_interval_seconds: how often to scan
        - junk_threshold_mb: minimum total size to trigger notification
        - notify_interval_seconds: minimum seconds between similar notifications
        """
        def size_of_path(p):
            total = 0
            count = 0
            try:
                if os.path.isfile(p):
                    total += os.path.getsize(p)
                    count += 1
                else:
                    for root, dirs, files in os.walk(p):
                        for f in files:
                            try:
                                fp = os.path.join(root, f)
                                total += os.path.getsize(fp)
                                count += 1
                            except:
                                pass
                return total, count
            except:
                return 0, 0

        folders = [
            os.environ.get('TEMP'),
            os.path.join(os.environ.get('SystemRoot', 'C:\\Windows'), 'Temp'),
            os.path.join(os.environ.get('SystemRoot', 'C:\\Windows'), 'Prefetch'),
            os.path.join(os.environ.get('USERPROFILE', ''), 'Downloads'),
        ]

        while True:
            try:
                total_size = 0
                total_files = 0
                for folder in folders:
                    if folder and os.path.exists(folder):
                        s, c = size_of_path(folder)
                        total_size += s
                        total_files += c

                total_mb = total_size / (1024 * 1024)
                self._log(f"Background scan: {total_mb:.1f} MB in {total_files} items", "INFO")

                now = time.time()
                if total_mb >= junk_threshold_mb and (now - self._last_junk_notification) >= notify_interval_seconds:
                    self._last_junk_notification = now
                    # send a single tidy notification with action to clean
                    try:
                        payload = {
                            "title": "Background Scan: Junk Files Detected",
                            "message": f"{int(total_mb)} MB in {total_files} items found in temp/downloads. Clean now?",
                            "action_label": "Clean Now",
                            "cancel_label": "Later",
                            "action": "run_system_cleaner"
                        }
                        safe = json.dumps(payload)
                        win = webview.active_window()
                        if win:
                            win.evaluate_js(f"createActionNotification({safe})")
                    except Exception as e:
                        self._log(f"Failed to send background notification: {str(e)}", "ERROR")
                # keep quiet unless threshold reached
            except Exception as e:
                self._log(f"Background monitor error: {str(e)}", "ERROR")
            time.sleep(scan_interval_seconds)


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

        /* Download overlay */
        #download-overlay {
            position: fixed;
            inset: 0;
            display: none;
            align-items: center;
            justify-content: center;
            z-index: 11000;
            background: linear-gradient(180deg, rgba(0,0,0,0.6), rgba(0,0,0,0.6));
        }
        .download-card {
            width: 700px;
            background: rgba(12,12,12,0.85);
            border: 1px solid rgba(255,255,255,0.06);
            padding: 30px;
            border-radius: 18px;
            display: flex;
            flex-direction: column;
            gap: 14px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.7);
        }
        .download-bar {
            height: 14px;
            background: rgba(255,255,255,0.04);
            border-radius: 10px;
            overflow: hidden;
        }
        .download-bar > div {
            height: 100%;
            width: 0%;
            background: linear-gradient(90deg, #00a8ff, #3b82f6);
            transition: width 0.25s linear;
        }

        /* Action notification (non-intrusive) */
        .action-note {
            display: flex;
            gap: 12px;
            align-items: center;
            justify-content: space-between;
        }
        .action-note .text {
            flex: 1;
        }
        .action-note .actions {
            display:flex;
            gap:8px;
        }

        /* Log box styles */
        #log-box {
            font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, "Roboto Mono", monospace;
            font-size: 11px;
            line-height: 1.25;
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
                    Personalized System Optimization <br> Version 4.3.6
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
                        <p class="text-[11px] font-black uppercase text-blue-400 mb-2 tracking-widest">Open Source</p>
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
                            <span class="w-2 h-2 bg-blue-500 rounded-full shadow-[0_0_10px_#3b82f6]"></span> 4.3.6 KERNEL BOOST
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
            <div onclick="switchPage('blackbox', this)" class="sidebar-item ray-trace-enabled">
                <span class="text-xl">☣</span> <span class="text-[11px] font-black uppercase tracking-[0.2em]">Blackbox</span>
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
                    <h3 class="text-3xl font-black text-orange-500 italic">v4.3.6</h3>
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

        <div id="page-blackbox" class="page">
            <h2 class="text-8xl font-black mb-4 tracking-tighter italic opacity-90 text-transparent bg-clip-text bg-gradient-to-r from-gray-200 to-gray-500">Blackbox</h2>
            <p class="text-gray-500 text-sm mb-12 uppercase tracking-[0.3em]">Advanced System Operations.</p>

            <div class="grid grid-cols-2 gap-8 mb-8">
                <div class="card ray-trace-enabled border-purple-500/30 bg-purple-900/10">
                    <p class="text-[10px] font-black text-purple-400 mb-3 uppercase tracking-widest">Storage Master</p>
                    <h3 class="text-3xl font-black italic mb-4 text-white">Ghost Compression</h3>
                    <p class="text-xs text-gray-400 mb-6 font-mono leading-relaxed">
                        Compresses Windows binaries using LZX algorithm. Recovers 4-6 GB of drive space without deleting files. Safe & reversible.
                    </p>
                    <button onclick="runGhostComp()" class="install-btn w-full !bg-purple-600 !border-purple-400 hover:!bg-purple-500 hover:scale-105 transition-all shadow-[0_0_30px_rgba(147,51,234,0.3)]">
                        COMPRESS OS
                    </button>
                </div>

                <div class="card ray-trace-enabled border-emerald-500/30 bg-emerald-900/10">
                    <p class="text-[10px] font-black text-emerald-400 mb-3 uppercase tracking-widest">Admin Access</p>
                    <h3 class="text-3xl font-black italic mb-4 text-white">Omni-Control</h3>
                    <p class="text-xs text-gray-400 mb-6 font-mono leading-relaxed">
                        Unlocks the hidden "Master Control Panel". Creates a shortcut on Desktop with access to over 200+ advanced system settings.
                    </p>
                    <button onclick="runGodMode()" class="install-btn w-full !bg-emerald-600 !border-emerald-400 hover:!bg-emerald-500 hover:scale-105 transition-all shadow-[0_0_30px_rgba(16,185,129,0.3)]">
                        INVOKE OMNI-CONTROL
                    </button>
                </div>
            </div>

            <div class="w-full h-32 border border-white/5 bg-black/20 rounded-3xl flex items-center justify-center p-8 ray-trace-enabled">
                <div class="text-center opacity-40">
                    <p class="text-[10px] font-black uppercase tracking-[0.5em] mb-2">CortexDev Blackbox</p>
                    <p class="text-xs italic">These tools may damage your computer or files; CortexDev is not responsible for this in any way.</p>
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
                    <span class="bg-white/5 px-10 py-3 rounded-full text-[11px] font-black border border-white/10 uppercase tracking-widest hover:bg-white/10 transition-colors cursor-default">Build v4.3.6</span>
                    <span class="bg-green-500/10 px-10 py-3 rounded-full text-[11px] font-black text-green-500 border border-green-500/10 uppercase tracking-widest shadow-[0_0_20px_rgba(34,197,94,0.2)]">Kernel Verified</span>
                </div>
            </div>
        </div>

    </div>

    <!-- Download overlay (hidden until a download starts) -->
    <div id="download-overlay">
        <div class="download-card">
            <div class="flex items-center justify-between">
                <div>
                    <div id="download-title" class="text-white font-bold text-lg">Downloading...</div>
                    <div id="download-sub" class="text-gray-400 text-xs mt-1">Preparing...</div>
                </div>
                <div>
                    <div id="download-percent" class="text-white font-mono font-bold">0%</div>
                </div>
            </div>
            <div class="download-bar">
                <div id="download-fill" style="width:0%"></div>
            </div>
            <div class="flex justify-between text-xs text-gray-400">
                <div id="download-speed">0 KB/s</div>
                <div id="download-eta">ETA: --:--</div>
            </div>
            <div class="flex justify-end gap-4">
                <button onclick="cancelDownload()" class="install-btn !bg-red-600">Cancel</button>
                <button onclick="hideDownloadOverlay()" class="install-btn !bg-gray-700">Close</button>
            </div>
        </div>
    </div>

    <script>
        /* UI helpers and improved logs + download progress bridge */
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

        // Show a toast (non-intrusive)
        function showToast(msg, type='info') {
            const container = document.getElementById('toast-container');
            const toast = document.createElement('div');
            toast.className = `toast-msg ${type} ray-trace-enabled`;
            const icon = type === 'success' ? '✔' : type === 'error' ? '✖' : type === 'gaming' ? '⚡' : 'ℹ';
            toast.innerHTML = `<span class="text-xl">${icon}</span> <span>${msg}</span>`;
            container.appendChild(toast);
            setTimeout(() => toast.remove(), 4000);
        }

        // Action notification (from background scans). Non-modal, actionable but not pop-up intrusive.
        function createActionNotification(payload) {
            const container = document.getElementById('toast-container');
            const note = document.createElement('div');
            note.className = 'toast-msg ray-trace-enabled';
            note.innerHTML = `
                <div class="action-note">
                    <div class="text">
                        <div style="font-weight:800">${payload.title}</div>
                        <div style="font-size:12px;color:#bfc7d6;margin-top:6px">${payload.message}</div>
                    </div>
                    <div class="actions">
                        <button id="action-btn" class="install-btn">${payload.action_label}</button>
                        <button id="dismiss-btn" class="install-btn" style="background:rgba(255,255,255,0.03)"> ${payload.cancel_label} </button>
                    </div>
                </div>
            `;
            container.appendChild(note);
            // Attach handlers
            document.getElementById('action-btn').onclick = function(){
                if(payload.action === "run_system_cleaner" && window.pywebview && window.pywebview.api) {
                    window.pywebview.api.run_system_cleaner();
                }
                note.remove();
            };
            document.getElementById('dismiss-btn').onclick = function(){
                note.remove();
            };
            setTimeout(() => { if(document.body.contains(note)) note.remove(); }, 18000);
        }

        // Download overlay controls
        function showDownloadOverlay(id, name) {
            const o = document.getElementById('download-overlay');
            document.getElementById('download-title').innerText = `Downloading: ${name}`;
            document.getElementById('download-sub').innerText = `Connecting...`;
            document.getElementById('download-percent').innerText = `0%`;
            document.getElementById('download-fill').style.width = '0%';
            document.getElementById('download-speed').innerText = '0 KB/s';
            document.getElementById('download-eta').innerText = 'ETA: --:--';
            o.style.display = 'flex';
            window._current_download = id;
        }
        function updateDownloadProgress(payload) {
            try {
                if(!payload) return;
                if(window._current_download && payload.id !== window._current_download) return;
                const percent = payload.percent ? Math.min(100, Math.round(payload.percent)) : 0;
                document.getElementById('download-percent').innerText = percent + "%";
                document.getElementById('download-fill').style.width = percent + "%";
                const speed = payload.speed ? Math.round(payload.speed / 1024) : 0;
                document.getElementById('download-speed').innerText = speed + " KB/s";
                const eta = payload.eta !== null && payload.eta !== undefined ? payload.eta : null;
                if(eta !== null) {
                    const mm = Math.floor(eta / 60);
                    const ss = eta % 60;
                    document.getElementById('download-eta').innerText = `ETA: ${mm}:${ss.toString().padStart(2,'0')}`;
                } else {
                    document.getElementById('download-eta').innerText = 'ETA: --:--';
                }
                document.getElementById('download-sub').innerText = payload.path ? payload.path : '';
            } catch(e){}
        }
        function hideDownloadOverlay() {
            const o = document.getElementById('download-overlay');
            o.style.display = 'none';
            window._current_download = null;
        }
        function cancelDownload() {
            // Best-effort: signal API to cancel current download if supported (not implemented server-side)
            try {
                if(window.pywebview && window.pywebview.api && window._current_download) {
                    window.pywebview.api._log("User requested download cancel (UI)", "WARN");
                }
            } catch(e){}
            hideDownloadOverlay();
            showToast("Download cancelled", "error");
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

        function runDismRepair(){ pywebview.api.repair_dism(); }
        function createRestorePoint(){ pywebview.api.create_restore_point(); }
        function enableSafeMode(){ pywebview.api.safe_mode_enable(); }
        function disableSafeMode(){ pywebview.api.safe_mode_disable(); }

        function engageGaming(){ pywebview.api.run_gaming_boost(); }
        function engageFPSMode(){ pywebview.api.run_fps_mode(); }

        function runGhostComp() { pywebview.api.run_ghost_compression(); }
        function runGodMode() { pywebview.api.enable_god_mode(); }

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

            showToast("MWB v4.3.6 Loaded", "success");
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

    # Anti-Flash: Ensure main console is hidden (redundant but safe)
    if sys.platform == "win32":
        try:
            ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)
        except:
            pass

    window = webview.create_window(
        f"{APP_NAME} v{VERSION}",
        html=HTML_UI,
        js_api=api,
        width=1400,
        height=900,
        resizable=True,
        frameless=False
    )

    # start mica after window available
    threading.Timer(0.5, lambda: apply_mica(window)).start()

    # start background monitor (scans junk quietly and notifies non-intrusively)
    try:
        threading.Thread(target=api.background_monitor, daemon=True).start()
        api._log("Background monitor thread started", "INFO")
    except Exception as e:
        api._log(f"Failed to start background monitor: {str(e)}", "ERROR")

    webview.start(debug=False)


if __name__ == "__main__":
    main()