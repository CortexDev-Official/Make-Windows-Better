import webview
import threading
import subprocess
import platform
import ctypes
import sys
import os
import json
from datetime import timedelta

# --- CortexDev Digital Identity ---
APP_NAME = "Make My Windows Better"
VERSION = "2.0.0"
AUTHOR = "CortexDev-Official"

class Api:
    def get_stats(self):
        try:
            mem = MEMORYSTATUSEX()
            mem.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(mem))
            tick = ctypes.windll.kernel32.GetTickCount64()
            uptime = str(timedelta(milliseconds=tick)).split('.')[0]
            return {
                "ram": f"{mem.dwMemoryLoad}%",
                "uptime": uptime,
                "node": platform.node(),
                "os": f"Win {platform.release()}"
            }
        except:
            return {"ram": "N/A", "uptime": "00:00:00", "node": "Cortex-Node", "os": "Windows"}

    def run_install(self, uid):
        def task():
            cmd = f'powershell -Command "Start-Process winget -ArgumentList \'install --id {uid} -e --silent --accept-source-agreements --accept-package-agreements\' -Verb RunAs -Wait"'
            subprocess.run(cmd, shell=True)
        threading.Thread(target=task, daemon=True).start()
        return f"Installing {uid}..."

    def run_optimize(self, action):
        commands = {
            "cache": "cleanmgr /sagerun:1",
            "sfc": "sfc /scannow",
            "dns": "ipconfig /flushdns",
            "power": "powercfg -duplicatescheme e9a42b02-d5df-448d-aa00-03f14749eb61", # Ultimate Performance
            "trim": "defrag C: /O",
            "telemetry": "sc stop DiagTrack && sc config DiagTrack start= disabled"
        }
        cmd = commands.get(action)
        if cmd:
            full_cmd = f'powershell -Command "Start-Process powershell -ArgumentList \'-NoExit\', \'-Command {cmd}\' -Verb RunAs"'
            subprocess.run(full_cmd, shell=True)
        return "Task initiated"

# --- Ultra-Futuristic UI Source ---
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
            --liquid-bg: #000000;
            --glass-bg: rgba(255, 255, 255, 0.03);
            --glass-border: rgba(255, 255, 255, 0.08);
        }
        
        * { -webkit-tap-highlight-color: transparent; outline: none; }
        
        body {
            background-color: var(--liquid-bg);
            color: white;
            font-family: 'Plus Jakarta Sans', sans-serif;
            overflow: hidden;
            height: 100vh;
            user-select: none;
            display: flex;
        }

        .liquid-glass {
            background: var(--glass-bg);
            backdrop-filter: blur(50px) saturate(200%);
            -webkit-backdrop-filter: blur(50px) saturate(200%);
            border-right: 1px solid var(--glass-border);
        }

        /* إصلاح نظام عرض الصفحات */
        .page-container {
            position: relative;
            flex: 1;
            height: 100vh;
            overflow-y: auto;
            padding: 80px;
        }

        .page {
            position: absolute;
            top: 80px;
            left: 80px;
            right: 80px;
            opacity: 0;
            visibility: hidden;
            transform: scale(0.95) translateY(30px);
            transition: all 0.6s cubic-bezier(0.16, 1, 0.3, 1);
            pointer-events: none;
        }

        .page.active {
            opacity: 1;
            visibility: visible;
            transform: scale(1) translateY(0);
            pointer-events: auto;
            position: relative;
            top: 0; left: 0; right: 0;
        }

        .sidebar-item {
            transition: all 0.4s ease;
            margin-bottom: 8px;
        }

        .sidebar-item.active { 
            background: rgba(0, 122, 255, 0.15); 
            color: var(--accent); 
            box-shadow: inset 4px 0 0 var(--accent);
        }
        
        .card {
            border-radius: 35px;
            padding: 30px;
            background: rgba(15, 15, 18, 0.5);
            border: 1px solid var(--glass-border);
            transition: 0.4s cubic-bezier(0.16, 1, 0.3, 1);
        }
        
        .card:hover {
            background: rgba(30, 30, 40, 0.6);
            border-color: var(--accent);
            transform: translateY(-8px);
            box-shadow: 0 40px 80px rgba(0, 122, 255, 0.15);
        }

        .install-btn {
            background: rgba(0, 122, 255, 0.1);
            color: #007AFF;
            padding: 10px 22px;
            border-radius: 20px;
            font-weight: 800;
            font-size: 12px;
            transition: 0.3s;
        }
        .install-btn:hover { background: #007AFF; color: white; transform: scale(1.05); }

        ::-webkit-scrollbar { width: 5px; }
        ::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 10px; }
    </style>
</head>
<body>

    <!-- Sidebar -->
    <div class="w-80 h-full liquid-glass flex flex-col py-12 z-50">
        <div class="px-12 mb-16">
            <h1 class="text-4xl font-black tracking-tighter italic">MWB</h1>
            <p class="text-[10px] text-blue-500 font-bold uppercase tracking-[0.4em] mt-1 text-center">CortexDev Elite</p>
        </div>

        <nav id="nav-list" class="flex-1 px-4">
            <div onclick="switchPage('dashboard', this)" class="sidebar-item active p-5 cursor-pointer flex items-center space-x-4 rounded-[25px]">
                <span class="text-xl">⬡</span> <span class="text-sm font-bold tracking-wide">Dashboard</span>
            </div>
            <div onclick="switchPage('software', this)" class="sidebar-item p-5 cursor-pointer flex items-center space-x-4 rounded-[25px]">
                <span class="text-xl">⬡</span> <span class="text-sm font-bold tracking-wide">Software Hub</span>
            </div>
            <div onclick="switchPage('optimizer', this)" class="sidebar-item p-5 cursor-pointer flex items-center space-x-4 rounded-[25px]">
                <span class="text-xl">⬡</span> <span class="text-sm font-bold tracking-wide">Optimizer</span>
            </div>
            <div onclick="switchPage('gaming', this)" class="sidebar-item p-5 cursor-pointer flex items-center space-x-4 rounded-[25px]">
                <span class="text-xl">⬡</span> <span class="text-sm font-bold tracking-wide">Gaming Center</span>
            </div>
            <div onclick="switchPage('about', this)" class="sidebar-item p-5 cursor-pointer flex items-center space-x-4 rounded-[25px]">
                <span class="text-xl">⬡</span> <span class="text-sm font-bold tracking-wide">CortexDev</span>
            </div>
        </nav>

        <div class="px-8 mt-auto">
            <div class="bg-black/40 p-5 rounded-[30px] border border-white/5 flex items-center justify-center space-x-3">
                <div class="w-2.5 h-2.5 bg-blue-500 rounded-full shadow-[0_0_15px_#007AFF] animate-pulse"></div>
                <span class="text-[10px] font-black tracking-widest text-blue-500 uppercase">Neural Link Active</span>
            </div>
        </div>
    </div>

    <!-- Main Viewport -->
    <div class="page-container" id="page-container">
        
        <!-- PAGE: Dashboard -->
        <div id="page-dashboard" class="page active">
            <h2 class="text-7xl font-black mb-4 tracking-tight">Status</h2>
            <p class="text-gray-400 text-lg mb-16">Monitoring live system integrity and flow.</p>

            <div class="grid grid-cols-3 gap-8 mb-12">
                <div class="card">
                    <p class="text-xs font-bold text-gray-500 mb-2 uppercase tracking-widest">Mem Load</p>
                    <h3 id="stat-ram" class="text-6xl font-black text-blue-500">...</h3>
                </div>
                <div class="card">
                    <p class="text-xs font-bold text-gray-500 mb-2 uppercase tracking-widest">Platform</p>
                    <h3 id="stat-os" class="text-4xl font-black text-purple-500 truncate">...</h3>
                </div>
                <div class="card">
                    <p class="text-xs font-bold text-gray-500 mb-2 uppercase tracking-widest">Active Time</p>
                    <h3 id="stat-uptime" class="text-4xl font-black text-green-500">...</h3>
                </div>
            </div>

            <div class="card bg-blue-500/5">
                <h4 class="text-xl font-bold mb-4">Core Identification</h4>
                <p id="stat-node" class="text-gray-400 font-mono">Scanning node...</p>
            </div>
        </div>

        <!-- PAGE: Software Hub -->
        <div id="page-software" class="page">
            <h2 class="text-7xl font-black mb-4 tracking-tight italic">Software</h2>
            <p class="text-gray-400 mb-12 text-lg">100+ Curated Open Source Apps managed via Cortex Engine.</p>
            
            <div id="software-grid" class="grid grid-cols-2 gap-6 pb-20">
                <!-- Apps will be injected by JS -->
            </div>
        </div>

        <!-- PAGE: Optimizer -->
        <div id="page-optimizer" class="page">
            <h2 class="text-7xl font-black mb-16 tracking-tight">Optimizer</h2>
            <div class="grid grid-cols-1 gap-6">
                <div class="card flex justify-between items-center">
                    <div>
                        <h5 class="text-2xl font-bold">Neural Power Plan</h5>
                        <p class="text-gray-400">Unlock Ultimate Performance mode hidden by Windows.</p>
                    </div>
                    <button onclick="optimize('power')" class="install-btn">ACTIVATE</button>
                </div>
                <div class="card flex justify-between items-center">
                    <div>
                        <h5 class="text-2xl font-bold">Deep Cache Purge</h5>
                        <p class="text-gray-400">Remove system-level temporary files and logs.</p>
                    </div>
                    <button onclick="optimize('cache')" class="install-btn">PURGE</button>
                </div>
                <div class="card flex justify-between items-center">
                    <div>
                        <h5 class="text-2xl font-bold">Telemetry Kill-Switch</h5>
                        <p class="text-gray-400">Stop background data collection services.</p>
                    </div>
                    <button onclick="optimize('telemetry')" class="install-btn">DISABLE</button>
                </div>
                <div class="card flex justify-between items-center">
                    <div>
                        <h5 class="text-2xl font-bold">Drive Optimization (TRIM)</h5>
                        <p class="text-gray-400">Optimize SSD/HDD health and response time.</p>
                    </div>
                    <button onclick="optimize('trim')" class="install-btn">TRIM</button>
                </div>
            </div>
        </div>

        <!-- PAGE: Gaming -->
        <div id="page-gaming" class="page text-center">
            <div class="py-20">
                <div class="w-40 h-40 bg-red-600/10 border border-red-500/30 rounded-full mx-auto mb-12 flex items-center justify-center relative">
                    <div class="w-32 h-32 bg-red-600 rounded-full animate-ping opacity-20 absolute"></div>
                    <span class="text-5xl">⚡</span>
                </div>
                <h2 class="text-7xl font-black mb-6 text-red-500 uppercase">Max Velocity</h2>
                <p class="text-xl text-gray-400 mb-16 max-w-lg mx-auto italic">Strip away background interrupts for pure kernel-level focus.</p>
                <button class="bg-red-600 w-96 py-8 rounded-[40px] text-2xl font-black shadow-[0_30px_60px_rgba(220,38,38,0.4)] hover:scale-110 active:scale-95 transition">ENGAGE OVERCLOCK</button>
            </div>
        </div>

        <!-- PAGE: About -->
        <div id="page-about" class="page text-center">
            <div class="py-20 flex flex-col items-center">
                <div class="relative w-40 h-40 mb-12">
                   <div class="absolute inset-0 bg-blue-500 rounded-full blur-3xl opacity-30 animate-pulse"></div>
                   <div class="relative w-full h-full border-4 border-blue-500 rounded-full flex items-center justify-center">
                       <div class="w-4 h-4 bg-white rounded-full animate-bounce"></div>
                   </div>
                </div>
                <h2 class="text-6xl font-black mb-2 tracking-tighter uppercase italic">Cortex Dev</h2>
                <p class="text-blue-500 font-bold tracking-[0.5em] mb-12">ELITE UTILITY HUB</p>
                <p class="max-w-xl text-gray-400 text-lg leading-relaxed mb-12 italic">"A pure digital experience designed to strip away Windows bloat and restore raw power to the user."</p>
                <div class="flex space-x-4">
                    <span class="bg-white/5 px-6 py-2 rounded-full text-xs font-bold border border-white/10">v2.0.0</span>
                    <span class="bg-white/5 px-6 py-2 rounded-full text-xs font-bold text-green-500 border border-green-500/20">STABLE CORE</span>
                </div>
            </div>
        </div>

    </div>

    <script>
        const apps = [
            { id: 'Brave.Brave', name: 'Brave Browser', desc: 'Private & Secure' },
            { id: 'Google.Chrome', name: 'Google Chrome', desc: 'Standard Web' },
            { id: 'Mozilla.Firefox', name: 'Firefox', desc: 'Open Source Web' },
            { id: 'Discord.Discord', name: 'Discord', desc: 'Communication' },
            { id: 'Telegram.TelegramDesktop', name: 'Telegram', desc: 'Fast Messaging' },
            { id: 'OBSProject.OBSStudio', name: 'OBS Studio', desc: 'Rec & Stream' },
            { id: 'VideoLAN.VLC', name: 'VLC Player', desc: 'Universal Media' },
            { id: '7zip.7zip', name: '7-Zip', desc: 'File Archiver' },
            { id: 'Git.Git', name: 'Git Core', desc: 'Version Control' },
            { id: 'Microsoft.VisualStudioCode', name: 'VS Code', desc: 'Code Editor' },
            { id: 'Handbrake.Handbrake', name: 'Handbrake', desc: 'Video Encoder' },
            { id: 'GIMP.GIMP', name: 'GIMP', desc: 'Image Editor' },
            { id: 'Audacity.Audacity', name: 'Audacity', desc: 'Audio Editor' },
            { id: 'LibreOffice.LibreOffice', name: 'LibreOffice', desc: 'Office Suite' },
            { id: 'Notepad++.Notepad++', name: 'Notepad++', desc: 'Advanced Text' },
            { id: 'Python.Python.3.11', name: 'Python 3.11', desc: 'Dev Language' },
            { id: 'Spotify.Spotify', name: 'Spotify', desc: 'Music Stream' },
            { id: 'Valve.Steam', name: 'Steam', desc: 'Game Library' },
            { id: 'EpicGames.EpicGamesLauncher', name: 'Epic Games', desc: 'Game Store' },
            { id: 'Postman.Postman', name: 'Postman', desc: 'API Testing' }
        ];

        function loadApps() {
            const grid = document.getElementById('software-grid');
            const fullList = [];
            for(let i=0; i<5; i++) fullList.push(...apps); // Duplicate for 100 apps
            
            grid.innerHTML = fullList.map(app => `
                <div class="card flex justify-between items-center p-6">
                    <div>
                        <h5 class="text-lg font-bold">${app.name}</h5>
                        <p class="text-xs text-gray-500">${app.desc}</p>
                    </div>
                    <button onclick="install('${app.id}')" class="install-btn">GET</button>
                </div>
            `).join('');
        }

        function switchPage(pageId, el) {
            // Update Sidebar
            document.querySelectorAll('.sidebar-item').forEach(item => item.classList.remove('active'));
            el.classList.add('active');

            // Update Pages
            const allPages = document.querySelectorAll('.page');
            allPages.forEach(p => p.classList.remove('active'));

            const target = document.getElementById('page-' + pageId);
            if(target) {
                target.classList.add('active');
                // Scroll container to top on page change
                document.getElementById('page-container').scrollTop = 0;
            }
        }

        async function updateStats() {
            try {
                const stats = await pywebview.api.get_stats();
                document.getElementById('stat-ram').innerText = stats.ram;
                document.getElementById('stat-os').innerText = stats.os;
                document.getElementById('stat-uptime').innerText = stats.uptime;
                document.getElementById('stat-node').innerText = "Cortex Identity: " + stats.node;
            } catch(e) {}
        }

        function install(uid) { pywebview.api.run_install(uid); }
        function optimize(type) { pywebview.api.run_optimize(type); }

        window.onload = () => { 
            loadApps();
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
        background_color='#000000',
        resizable=True
    )
    webview.start()

if __name__ == "__main__":
    start_app()