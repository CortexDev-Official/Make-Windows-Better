import webview
import threading
import subprocess
import platform
import ctypes
import sys
import os
import shutil
import json
from datetime import timedelta

# --- CortexDev Digital Identity ---
APP_NAME = "Make My Windows Better"
VERSION = "4.0.0"
AUTHOR = "CortexDev-Official"

class Api:
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
                gpu_out = subprocess.check_output(gpu_cmd, shell=True).decode().split('\n')
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
            return {"ram": "N/A", "ram_raw": 0, "uptime": "00:00:00", "node": "Cortex-Node", "os": "Windows", "cpu": "Detecting...", "gpu": "Scanning...", "is_admin": False}

    # --- New Dashboard Functions ---
    def run_health_check(self):
        def task():
            try:
                
                result = subprocess.run("sfc /verifyonly", shell=True, capture_output=True, text=True)
                if "found integrity violations" in result.stdout.lower() or result.returncode != 0:
                    webview.active_window().evaluate_js("showToast('Integrity issues found! Run sfc /scannow as Admin.')")
                else:
                    webview.active_window().evaluate_js("showToast('System Integrity Secured (No errors).')")
            except:
                webview.active_window().evaluate_js("showToast('Health Check Failed to initialize.')")
        
        threading.Thread(target=task, daemon=True).start()
        return "Scan Started"

    def run_system_cleaner(self):
        def task():
            folders = [
                os.environ.get('TEMP'),
                os.path.join(os.environ.get('SystemRoot', 'C:\\Windows'), 'Temp'),
                os.path.join(os.environ.get('SystemRoot', 'C:\\Windows'), 'Prefetch')
            ]
            for folder in folders:
                if folder and os.path.exists(folder):
                    for filename in os.listdir(folder):
                        file_path = os.path.join(folder, filename)
                        try:
                            if os.path.isfile(file_path) or os.path.islink(file_path):
                                os.unlink(file_path)
                            elif os.path.isdir(file_path):
                                shutil.rmtree(file_path)
                        except:
                            continue
            webview.active_window().evaluate_js("showToast('Purge Complete: Junk Files Obliterated')")
        
        threading.Thread(target=task, daemon=True).start()
        return "Cleaning..."

    def run_install(self, uid):
        def task():
            cmd = f'powershell -Command "Start-Process winget -ArgumentList \'install --id {uid} -e --silent --accept-source-agreements --accept-package-agreements\' -Verb RunAs"'
            subprocess.run(cmd, shell=True)
        threading.Thread(target=task, daemon=True).start()
        return f"Installing {uid}..."

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
                full_cmd = f'powershell -Command "Start-Process powershell -ArgumentList \'-Command {cmd}\' -Verb RunAs"'
                subprocess.run(full_cmd, shell=True)
            threading.Thread(target=task, daemon=True).start()
        return "Task initiated"

    def run_gaming_boost(self):
        def task():
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
                subprocess.run(c, shell=True)
        threading.Thread(target=task, daemon=True).start()
        return "Velocity Mode Active"


HTML_UI = """
<!DOCTYPE html>
<html lang="ar">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;600;800&display=swap" rel="stylesheet">
    <style>
        :root {
            --accent: #007AFF;
            --liquid-bg: #050507;
            --glass-bg: rgba(255, 255, 255, 0.02);
            --glass-border: rgba(255, 255, 255, 0.06);
            --dynamic-glow: rgba(0, 122, 255, 0.3);
        }
        
        * { -webkit-tap-highlight-color: transparent; outline: none; scroll-behavior: smooth; }
        
        body {
            background-color: var(--liquid-bg);
            color: white;
            font-family: 'Plus Jakarta Sans', sans-serif;
            overflow: hidden;
            height: 100vh;
            user-select: none;
            display: flex;
        }

        .liquid-sidebar {
            background: linear-gradient(180deg, rgba(255,255,255,0.03) 0%, rgba(255,255,255,0) 100%);
            backdrop-filter: blur(50px);
            -webkit-backdrop-filter: blur(50px);
            border-right: 1px solid var(--glass-border);
            box-shadow: 10px 0 30px rgba(0,0,0,0.5);
            transition: all 0.5s cubic-bezier(0.4, 0, 0.2, 1);
        }

        .page-container {
            position: relative;
            flex: 1;
            height: 100vh;
            overflow-y: auto;
            padding: 40px 60px;
            background: radial-gradient(circle at 50% -20%, var(--dynamic-glow), transparent 70%);
            transition: background 1.2s ease;
        }

        .page {
            position: absolute;
            top: 40px; left: 60px; right: 60px;
            opacity: 0;
            visibility: hidden;
            transform: translateY(30px) scale(0.98);
            transition: all 0.6s cubic-bezier(0.34, 1.56, 0.64, 1);
        }

        .page.active {
            opacity: 1;
            visibility: visible;
            transform: translateY(0) scale(1);
            position: relative;
            top: 0; left: 0; right: 0;
        }

        .sidebar-item {
            transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
            margin: 6px 16px;
            padding: 14px 20px;
            border-radius: 20px;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 15px;
            color: #888;
        }

        .sidebar-item:hover {
            background: rgba(255, 255, 255, 0.03);
            color: #fff;
            transform: translateX(8px);
        }

        .sidebar-item.active { 
            background: rgba(255, 255, 255, 0.06);
            color: var(--accent);
            box-shadow: 0 4px 15px rgba(0,0,0,0.2);
        }

        .card {
            border-radius: 24px;
            padding: 24px;
            background: rgba(255, 255, 255, 0.02);
            border: 1px solid var(--glass-border);
            backdrop-filter: blur(15px);
            transition: all 0.5s cubic-bezier(0.23, 1, 0.32, 1);
        }
        
        .card:hover {
            background: rgba(255, 255, 255, 0.05);
            border-color: rgba(255, 255, 255, 0.15);
            transform: translateY(-8px) scale(1.01);
            box-shadow: 0 20px 40px rgba(0,0,0,0.3);
        }

        #toast-container {
            position: fixed;
            bottom: 30px;
            right: 30px;
            z-index: 9999;
        }

        .toast-msg {
            background: rgba(10, 10, 15, 0.8);
            backdrop-filter: blur(25px);
            border: 1px solid var(--accent);
            color: white;
            padding: 16px 28px;
            border-radius: 20px;
            margin-top: 10px;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 15px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.5);
            animation: toastIn 0.6s cubic-bezier(0.68, -0.55, 0.265, 1.55) forwards;
        }

        @keyframes toastIn {
            from { transform: translateX(120%) scale(0.5); opacity: 0; }
            to { transform: translateX(0) scale(1); opacity: 1; }
        }

        .install-btn {
            background: var(--accent);
            color: white;
            padding: 10px 24px;
            border-radius: 16px;
            font-weight: 800;
            font-size: 11px;
            letter-spacing: 1px;
            transition: 0.4s;
            text-transform: uppercase;
        }
        .install-btn:hover { 
            transform: scale(1.1) translateY(-2px); 
            box-shadow: 0 8px 20px var(--dynamic-glow);
        }

        .ram-pulse { animation: pulse-glow 2.5s infinite; }
        @keyframes pulse-glow {
            0% { box-shadow: 0 0 0 0 rgba(0, 122, 255, 0.2); }
            50% { box-shadow: 0 0 30px 5px rgba(0, 122, 255, 0.1); }
            100% { box-shadow: 0 0 0 0 rgba(0, 122, 255, 0.2); }
        }

        ::-webkit-scrollbar { width: 5px; }
        ::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 10px; }
    </style>
</head>
<body>

    <div id="toast-container"></div>

    <div class="w-80 h-full liquid-sidebar flex flex-col py-12 z-50">
        <div class="px-12 mb-16">
            <h1 class="text-4xl font-black tracking-tighter italic">MWB</h1>
            <p class="text-[10px] text-blue-500 font-bold uppercase tracking-[0.4em] mt-2 opacity-80">CortexDev Official</p>
        </div>

        <nav id="nav-list" class="flex-1">
            <div onclick="switchPage('dashboard', this)" class="sidebar-item active">
                <span class="text-xl">⌬</span> <span class="text-[11px] font-black uppercase tracking-[0.2em]">Dashboard</span>
            </div>
            <div onclick="switchPage('software', this)" class="sidebar-item">
                <span class="text-xl">⧉</span> <span class="text-[11px] font-black uppercase tracking-[0.2em]">Software Hub</span>
            </div>
            <div onclick="switchPage('optimizer', this)" class="sidebar-item">
                <span class="text-xl">⚙</span> <span class="text-[11px] font-black uppercase tracking-[0.2em]">Optimizer</span>
            </div>
            <div onclick="switchPage('gaming', this)" class="sidebar-item">
                <span class="text-xl">⚡</span> <span class="text-[11px] font-black uppercase tracking-[0.2em]">Gaming Center</span>
            </div>
            <div onclick="switchPage('about', this)" class="sidebar-item">
                <span class="text-xl">◈</span> <span class="text-[11px] font-black uppercase tracking-[0.2em]">CortexDev</span>
            </div>
        </nav>

        <div class="px-8 mt-auto">
            <div class="bg-white/5 p-5 rounded-3xl border border-white/5 flex items-center space-x-4">
                <div class="w-2.5 h-2.5 bg-blue-500 rounded-full animate-pulse"></div>
                <span class="text-[10px] font-black text-gray-400 uppercase tracking-widest">System Link Active</span>
            </div>
        </div>
    </div>

    <div class="page-container" id="page-container">
        
        <div id="page-dashboard" class="page active">
            <h2 class="text-7xl font-black mb-4 tracking-tighter italic">System Flow</h2>
            <p class="text-gray-500 text-sm mb-16 uppercase tracking-[0.3em]">Neural monitoring initiated.</p>

            <div class="grid grid-cols-3 gap-8 mb-10">
                <div class="card bg-blue-500/5 group">
                    <p class="text-[10px] font-black text-blue-400 mb-3 uppercase tracking-widest">Health Check</p>
                    <h3 class="text-2xl font-black text-white italic mb-4">Integrity</h3>
                    <button onclick="runHealthCheck()" class="install-btn !py-2 !px-4">Scan System</button>
                </div>

                <div class="card bg-red-500/5">
                    <p class="text-[10px] font-black text-red-400 mb-3 uppercase tracking-widest">System Cleaner</p>
                    <h3 class="text-2xl font-black text-white italic mb-4">Storage Junk</h3>
                    <button onclick="runSystemCleaner()" class="install-btn !bg-red-600 !py-2 !px-4">Purge Junk</button>
                </div>

                <div class="card border-orange-500/20 bg-orange-500/5">
                    <p class="text-[10px] font-black text-orange-400 mb-3 uppercase tracking-widest">Thermal Node</p>
                    <h3 id="stat-thermal" class="text-xl font-black text-orange-500 italic">Admin Required</h3>
                </div>
            </div>

            <div class="grid grid-cols-3 gap-8 mb-10">
                <div class="card ram-pulse" id="ram-card">
                    <p class="text-[10px] font-black text-gray-500 mb-3 uppercase tracking-widest">Memory Load</p>
                    <h3 id="stat-ram" class="text-6xl font-black text-blue-500 tracking-tighter italic">...</h3>
                </div>
                <div class="card">
                    <p class="text-[10px] font-black text-gray-500 mb-3 uppercase tracking-widest">Platform</p>
                    <h3 id="stat-os" class="text-2xl font-black text-white truncate italic">...</h3>
                </div>
                <div class="card">
                    <p class="text-[10px] font-black text-gray-500 mb-3 uppercase tracking-widest">Power On Time</p>
                    <h3 id="stat-uptime" class="text-2xl font-black text-green-500 italic">...</h3>
                </div>
            </div>

            <div class="grid grid-cols-2 gap-8">
                <div class="card bg-blue-500/[0.03]">
                    <h4 class="text-[11px] font-black mb-6 uppercase text-blue-400 tracking-[0.3em]">Logic Processor</h4>
                    <p id="stat-cpu" class="text-white font-bold text-xl mb-4 leading-tight italic">Detecting...</p>
                    <div class="w-full bg-white/5 h-1.5 rounded-full overflow-hidden">
                        <div class="bg-blue-500 h-full w-3/4 animate-pulse"></div>
                    </div>
                </div>
                <div class="card bg-purple-500/[0.03]">
                    <h4 class="text-[11px] font-black mb-6 uppercase text-purple-400 tracking-[0.3em]">Render Engine</h4>
                    <p id="stat-gpu" class="text-white font-bold text-xl mb-4 leading-tight italic">Scanning...</p>
                    <div class="w-full bg-white/5 h-1.5 rounded-full overflow-hidden">
                        <div class="bg-purple-500 h-full w-1/2 animate-pulse"></div>
                    </div>
                </div>
            </div>
        </div>

        <div id="page-software" class="page">
            <h2 class="text-7xl font-black mb-4 tracking-tighter italic">Repository</h2>
            <p class="text-gray-500 text-sm mb-12 uppercase tracking-[0.3em]">CortexDev Verified Library.</p>
            <div id="software-grid" class="grid grid-cols-3 gap-6 pb-24"></div>
        </div>

        <div id="page-optimizer" class="page">
            <h2 class="text-7xl font-black mb-4 tracking-tighter italic">Engine Boost</h2>
            <p class="text-gray-500 text-sm mb-16 uppercase tracking-[0.3em]">Fine-tuning OS parameters.</p>
            <div id="optimizer-grid" class="grid grid-cols-2 gap-6 pb-20"></div>
        </div>

        <div id="page-gaming" class="page text-center">
            <div class="py-24">
                <div class="w-40 h-40 border-2 border-red-500/30 rounded-full mx-auto mb-12 flex items-center justify-center relative">
                    <div class="absolute inset-0 bg-red-500/10 rounded-full animate-ping"></div>
                    <span class="text-6xl">⚡</span>
                </div>
                <h2 class="text-8xl font-black mb-6 text-red-600 italic uppercase tracking-tighter">Velocity</h2>
                <p class="text-xs text-gray-500 mb-16 tracking-[0.5em] font-bold">BYPASSING KERNEL LIMITATIONS</p>
                <button onclick="engageGaming()" class="bg-red-600 hover:bg-red-500 px-24 py-7 rounded-3xl text-2xl font-black shadow-2xl transition-all transform hover:scale-110 active:scale-95">ENGAGE OVERCLOCK</button>
            </div>
        </div>

        <div id="page-about" class="page text-center">
            <div class="py-32 flex flex-col items-center">
                <div class="w-20 h-20 bg-blue-600 rounded-3xl mb-8 flex items-center justify-center transform rotate-12 shadow-2xl">
                    <span class="text-4xl font-black italic">C</span>
                </div>
                <h2 class="text-6xl font-black mb-4 tracking-tighter italic text-white">CortexDev Official</h2>
                <p class="text-blue-500 font-bold tracking-[0.6em] mb-12 text-[11px]">ADVANCED WINDOWS UTILITY</p>
                <p class="max-w-xl text-gray-400 text-sm leading-relaxed mb-16 italic font-medium px-10">
                    Built by CortexDev to redefine system interaction. No bloat, no trackers, just pure performance and elite aesthetics.
                </p>
                <div class="flex space-x-6">
                    <span class="bg-white/5 px-10 py-3 rounded-full text-[11px] font-black border border-white/10 uppercase tracking-widest">Build v4.0.0</span>
                    <span class="bg-green-500/10 px-10 py-3 rounded-full text-[11px] font-black text-green-500 border border-green-500/10 uppercase tracking-widest">Kernel Verified</span>
                </div>
            </div>
        </div>

    </div>

    <script>
        const apps = [
            { id: 'Brave.Brave', name: 'Brave Browser', desc: 'Secure & Fast' },
            { id: 'Discord.Discord', name: 'Discord', desc: 'Communication' },
            { id: 'Valve.Steam', name: 'Steam', desc: 'Gaming Platform' },
            { id: 'Microsoft.VisualStudioCode', name: 'VS Code', desc: 'Code Editor' },
            { id: '7zip.7zip', name: '7-Zip', desc: 'Compression' },
            { id: 'VideoLAN.VLC', name: 'VLC Media Player', desc: 'Multimedia' },
            { id: 'Spotify.Spotify', name: 'Spotify', desc: 'Music Streaming' },
            { id: 'EpicGames.EpicGamesLauncher', name: 'Epic Games', desc: 'Gaming Launcher' },
            { id: 'Mozilla.Firefox', name: 'Firefox', desc: 'Privacy Browser' },
            { id: 'GIMP.GIMP', name: 'GIMP', desc: 'Image Editing' },
            { id: 'OBSProject.OBSStudio', name: 'OBS Studio', desc: 'Recording/Stream' },
            { id: 'Telegram.TelegramDesktop', name: 'Telegram', desc: 'Messaging' },
            { id: 'Handbrake.Handbrake', name: 'Handbrake', desc: 'Video Transcoder' },
            { id: 'Inkscape.Inkscape', name: 'Inkscape', desc: 'Vector Graphics' },
            { id: 'Audacity.Audacity', name: 'Audacity', desc: 'Audio Editor' },
            { id: 'WinRAR.WinRAR', name: 'WinRAR', desc: 'Archive Utility' },
            { id: 'Notepad++.Notepad++', name: 'Notepad++', desc: 'Advanced Text' },
            { id: 'PuTTY.PuTTY', name: 'PuTTY', desc: 'SSH Client' },
            { id: 'Zoom.Zoom', name: 'Zoom', desc: 'Video Meetings' },
            { id: 'Docker.DockerDesktop', name: 'Docker', desc: 'Containers' }
        ];

        const optimizers = [
            { id: 'power', name: 'Ultra Power', desc: 'Hidden Performance Plan' },
            { id: 'cache', name: 'Deep Clean', desc: 'Clear System Junk' },
            { id: 'dns', name: 'DNS Flush', desc: 'Reset Network Cache' },
            { id: 'telemetry', name: 'No Spy', desc: 'Disable Data Tracking' },
            { id: 'hibernation', name: 'Disk Space', desc: 'Disable Hibernation' },
            { id: 'updates', name: 'Pause Update', desc: 'Disable Auto Updates' },
            { id: 'trim', name: 'SSD Trim', desc: 'Optimize Drive Speed' },
            { id: 'gamebar', name: 'Game Bar Off', desc: 'Reduce Latency' },
            { id: 'transparency', name: 'Visual Boost', desc: 'Disable Glass Effects' },
            { id: 'sfc', name: 'Core Repair', desc: 'Verify System Integrity' },
            { id: 'startup', name: 'App Check', desc: 'List Startup Apps' },
            { id: 'visuals', name: 'Max Performance', desc: 'Visual Optimization' }
        ];

        function showToast(msg) {
            const container = document.getElementById('toast-container');
            const toast = document.createElement('div');
            toast.className = 'toast-msg';
            toast.innerHTML = `<span class="text-blue-500">◈</span> <span>${msg}</span>`;
            container.appendChild(toast);
            setTimeout(() => {
                toast.style.transform = 'translateX(150%)';
                toast.style.opacity = '0';
                setTimeout(() => toast.remove(), 600);
            }, 3000);
        }

        function loadApps() {
            const grid = document.getElementById('software-grid');
            grid.innerHTML = apps.map(app => `
                <div class="card flex flex-col justify-between h-40">
                    <div>
                        <h5 class="text-sm font-black text-white italic mb-1">${app.name}</h5>
                        <p class="text-[9px] text-gray-500 uppercase font-bold tracking-widest">${app.desc}</p>
                    </div>
                    <button onclick="installApp('${app.id}')" class="install-btn w-full">Deploy</button>
                </div>
            `).join('');
        }

        function loadOptimizers() {
            const grid = document.getElementById('optimizer-grid');
            grid.innerHTML = optimizers.map(opt => `
                <div class="card flex justify-between items-center">
                    <div>
                        <h5 class="text-sm font-black italic text-white">${opt.name}</h5>
                        <p class="text-[10px] text-gray-500 font-bold uppercase tracking-tight">${opt.desc}</p>
                    </div>
                    <button onclick="runOpt('${opt.id}', '${opt.name} Initiated')" class="install-btn">RUN</button>
                </div>
            `).join('');
        }

        function switchPage(pageId, el) {
            document.querySelectorAll('.sidebar-item').forEach(item => item.classList.remove('active'));
            el.classList.add('active');
            document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
            document.getElementById('page-' + pageId).classList.add('active');
            document.getElementById('page-container').scrollTop = 0;
        }

        async function updateStats() {
            try {
                const stats = await pywebview.api.get_stats();
                document.getElementById('stat-ram').innerText = stats.ram;
                document.getElementById('stat-os').innerText = stats.os;
                document.getElementById('stat-uptime').innerText = stats.uptime;
                document.getElementById('stat-cpu').innerText = stats.cpu;
                document.getElementById('stat-gpu').innerText = stats.gpu;

                // Thermal Node Logic
                const thermalNode = document.getElementById('stat-thermal');
                if (stats.is_admin) {
                    thermalNode.innerText = "Sensors Active";
                    thermalNode.classList.remove('text-orange-500');
                    thermalNode.classList.add('text-green-500');
                } else {
                    thermalNode.innerText = "Admin Required";
                    thermalNode.classList.add('text-orange-500');
                    thermalNode.classList.remove('text-green-500');
                }

                const ramCard = document.getElementById('ram-card');
                const container = document.getElementById('page-container');
                if (stats.ram_raw > 80) {
                    container.style.background = "radial-gradient(circle at 50% -20%, rgba(220,38,38,0.25), transparent 70%)";
                    document.documentElement.style.setProperty('--accent', '#ef4444');
                } else if (stats.ram_raw > 50) {
                    container.style.background = "radial-gradient(circle at 50% -20%, rgba(168,85,247,0.25), transparent 70%)";
                    document.documentElement.style.setProperty('--accent', '#a855f7');
                } else {
                    container.style.background = "radial-gradient(circle at 50% -20%, rgba(0,122,255,0.25), transparent 70%)";
                    document.documentElement.style.setProperty('--accent', '#007AFF');
                }
            } catch(e) {}
        }

        // New Logic Functions
        function runHealthCheck() {
            pywebview.api.run_health_check();
            showToast("System Health Scan Initiated...");
        }

        function runSystemCleaner() {
            pywebview.api.run_system_cleaner();
            showToast("Purging Junk Files...");
        }

        function installApp(id) {
            pywebview.api.run_install(id);
            showToast("Deployment queued: " + id);
        }

        function runOpt(type, msg) {
            pywebview.api.run_optimize(type);
            showToast(msg);
        }

        function engageGaming() {
            pywebview.api.run_gaming_boost();
            showToast("Velocity Overclock Engaged");
        }

        window.onload = () => { 
            loadApps();
            loadOptimizers();
            updateStats();
            setInterval(updateStats, 3000);
        };
    </script>
</body>
</html>
"""

class MEMORYSTATUSEX(ctypes.Structure):
    _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong), ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong), ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong), ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong), ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]

def start_app():
    api = Api()
    window = webview.create_window(
        title=APP_NAME,
        html=HTML_UI,
        js_api=api,
        width=1350,
        height=950,
        background_color='#050507',
        resizable=True
    )
    webview.start()

if __name__ == "__main__":
    start_app()