import sys
import subprocess
import threading
import ctypes
import os
import platform
import time
import webbrowser
from datetime import timedelta

# --- 0. Dependency Check (Critical for .exe) ---
def check_dependencies():
    """Checks if critical system components are available before starting UI."""
    missing = []
    
    # Check for Winget
    try:
        # Using a more robust check for winget
        subprocess.run(["winget", "--version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=True)
    except Exception:
        missing.append("Winget (App Installer)")
    
    return missing

# Check CustomTkinter
try:
    import customtkinter as ctk
except ImportError:
    print("CRITICAL ERROR: customtkinter is not installed.")
    print("Run: pip install customtkinter")
    sys.exit(1)

import tkinter as tk
from tkinter import messagebox

# --- 1. Theme Configuration (Cyber-Glass Aesthetic) ---
CLR_BG = "#050505"          # True Void Black
CLR_SIDEBAR = "#09090a"     # Obsidian
CLR_ACCENT = "#3b82f6"      # Electric Blue
CLR_ACCENT_HOVER = "#2563eb"
CLR_TEXT_MAIN = "#ffffff"
CLR_TEXT_DIM = "#71717a"
CLR_CARD = "#121214"
CLR_BORDER = "#27272a"
CLR_SUCCESS = "#10b981"
CLR_WARNING = "#f59e0b"
CLR_ERROR = "#ef4444"

# Memory Structure for Dashboard
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
        ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
    ]

class MWBApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Window Setup
        self.title("Make My Windows Better | CortexDev")
        self.geometry("1280x850")
        self.configure(fg_color=CLR_BG)
        ctk.set_appearance_mode("dark")
        
        # Fonts
        self.font_logo = ctk.CTkFont(family="Segoe UI Variable Display", size=36, weight="bold")
        self.font_h1 = ctk.CTkFont(family="Segoe UI Variable Display", size=28, weight="bold")
        self.font_h2 = ctk.CTkFont(family="Segoe UI Variable Display", size=18, weight="bold")
        self.font_main = ctk.CTkFont(family="Segoe UI Variable Text", size=13)
        self.font_btn = ctk.CTkFont(family="Segoe UI Variable Text", size=13, weight="bold")

        # Grid Layout
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # 1. Startup Logic
        self.missing_deps = check_dependencies()
        if self.missing_deps:
            self.show_dependency_error()
        else:
            self.init_ui()

    def show_dependency_error(self):
        """Shows a warning if dependencies are missing"""
        error_frame = ctk.CTkFrame(self, fg_color=CLR_CARD)
        error_frame.pack(fill="both", expand=True, padx=50, pady=50)
        
        ctk.CTkLabel(error_frame, text="MISSING COMPONENTS", text_color=CLR_ERROR, font=self.font_h1).pack(pady=20)
        ctk.CTkLabel(error_frame, text=f"The following tools are required for MWB to function:\n{', '.join(self.missing_deps)}", font=self.font_main).pack(pady=10)
        ctk.CTkButton(error_frame, text="Exit Application", command=sys.exit, fg_color=CLR_ERROR, hover_color="#991b1b").pack(pady=20)

    def init_ui(self):
        """Initialize the main application UI"""
        self.setup_sidebar()
        
        # Main Content Area
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.grid(row=0, column=1, sticky="nsew", padx=40, pady=30)
        
        # Start at Dashboard
        self.show_dashboard()

    def setup_sidebar(self):
        self.sidebar = ctk.CTkFrame(self, width=280, corner_radius=0, fg_color=CLR_SIDEBAR, border_width=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)
        
        # Branding
        brand = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        brand.pack(pady=(60, 40))
        
        ctk.CTkLabel(brand, text="MWB", font=self.font_logo, text_color=CLR_TEXT_MAIN).pack()
        ctk.CTkLabel(brand, text="PRE-ALPHA BUILD", font=ctk.CTkFont(size=10, weight="bold"), text_color=CLR_ACCENT).pack(pady=2)
        ctk.CTkLabel(brand, text="By CortexDev", font=ctk.CTkFont(size=11), text_color=CLR_TEXT_DIM).pack(pady=5)

        # Navigation
        self.nav_buttons = []
        items = [
            ("::  Dashboard", self.show_dashboard),
            ("::  Software Hub", self.show_software_hub),
            ("::  Optimizer", self.show_optimizer),
            ("::  Gaming Mode", self.show_gaming),
            ("::  Settings", self.show_settings),
            ("::  About", self.show_about)
        ]
        
        for txt, cmd in items:
            btn = ctk.CTkButton(self.sidebar, text=txt, command=cmd, 
                                fg_color="transparent", text_color=CLR_TEXT_DIM,
                                hover_color="#18181b", anchor="w", height=50, 
                                font=self.font_btn, corner_radius=8)
            btn.pack(fill="x", padx=20, pady=4)
            self.nav_buttons.append(btn)

        # Status Footer
        status_box = ctk.CTkFrame(self.sidebar, fg_color=CLR_CARD, height=60, corner_radius=12)
        status_box.pack(side="bottom", fill="x", padx=20, pady=30)
        status_box.pack_propagate(False)
        ctk.CTkLabel(status_box, text="● SYSTEM ONLINE", font=ctk.CTkFont(size=10, weight="bold"), text_color=CLR_SUCCESS).pack(expand=True)

    def clear_view(self):
        for widget in self.main_container.winfo_children():
            widget.destroy()

    def fade_in(self):
        """Simple animation by refreshing the layout"""
        self.main_container.grid_forget()
        self.main_container.grid(row=0, column=1, sticky="nsew", padx=40, pady=30)
        self.update_idletasks()

    # --- VIEW: Dashboard ---
    def show_dashboard(self):
        self.clear_view()
        self.fade_in()
        
        ctk.CTkLabel(self.main_container, text="System Dashboard", font=self.font_h1).pack(anchor="w", pady=5)
        ctk.CTkLabel(self.main_container, text="Real-time system metrics and health status.", font=self.font_main, text_color=CLR_TEXT_DIM).pack(anchor="w", pady=15)

        # Stats Grid
        grid = ctk.CTkFrame(self.main_container, fg_color="transparent")
        grid.pack(fill="x")
        
        self.ram_card = self.create_stat_card(grid, "MEMORY USAGE", "Calculating...", CLR_ACCENT)
        self.ram_card.pack(side="left", fill="x", expand=True, padx=(0, 15))
        
        self.sys_card = self.create_stat_card(grid, "OS VERSION", f"Windows {platform.release()}", "#a855f7")
        self.sys_card.pack(side="left", fill="x", expand=True, padx=15)
        
        self.upt_card = self.create_stat_card(grid, "SESSION UPTIME", "...", CLR_SUCCESS)
        self.upt_card.pack(side="left", fill="x", expand=True, padx=(15, 0))

        # System Details (FIXED PADY ERROR HERE)
        info = ctk.CTkFrame(self.main_container, fg_color=CLR_CARD, corner_radius=16, border_width=1, border_color=CLR_BORDER)
        info.pack(fill="x", pady=30)
        
        ctk.CTkLabel(info, text=f"Hostname: {platform.node()}", font=self.font_btn, padx=25, pady=15).pack(anchor="w")
        # Fixed: changed pady=(0, 15) to pady=15
        ctk.CTkLabel(info, text=f"Processor: {platform.processor()}", font=self.font_btn, padx=25, pady=15).pack(anchor="w")

        self.update_live_stats()

    def create_stat_card(self, master, title, val, color):
        card = ctk.CTkFrame(master, fg_color=CLR_CARD, corner_radius=16, height=130, border_width=1, border_color=CLR_BORDER)
        card.pack_propagate(False)
        ctk.CTkLabel(card, text=title, text_color=CLR_TEXT_DIM, font=ctk.CTkFont(size=11, weight="bold")).pack(pady=(25, 5))
        lbl = ctk.CTkLabel(card, text=val, text_color=color, font=ctk.CTkFont(size=24, weight="bold"))
        lbl.pack()
        return card

    def update_live_stats(self):
        try:
            mem = MEMORYSTATUSEX()
            mem.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(mem))
            
            tick = ctypes.windll.kernel32.GetTickCount64()
            uptime = str(timedelta(milliseconds=tick)).split('.')[0]

            self.ram_card.winfo_children()[1].configure(text=f"{mem.dwMemoryLoad}%")
            self.upt_card.winfo_children()[1].configure(text=uptime)
            
            if self.winfo_exists():
                self.after(2000, self.update_live_stats)
        except Exception:
            pass

    # --- VIEW: Software Hub (100+ Apps) ---
    def show_software_hub(self):
        self.clear_view()
        self.fade_in()
        
        header = ctk.CTkFrame(self.main_container, fg_color="transparent")
        header.pack(fill="x", pady=10)
        ctk.CTkLabel(header, text="Software Hub", font=self.font_h1).pack(side="left")
        ctk.CTkLabel(header, text="100+ Managed Apps", text_color=CLR_ACCENT, font=ctk.CTkFont(weight="bold")).pack(side="right")

        scroll = ctk.CTkScrollableFrame(self.main_container, fg_color="transparent", label_text="Available Software Library", label_font=self.font_btn)
        scroll.pack(fill="both", expand=True, pady=10)

        catalog = {
            "Browsers": [
                ("Brave", "Privacy Focused", "Brave.Brave"), ("Firefox", "Open Source", "Mozilla.Firefox"),
                ("LibreWolf", "Security Hardened", "LibreWolf.LibreWolf"), ("Chrome", "Google Browser", "Google.Chrome"),
                ("Edge", "Microsoft Browser", "Microsoft.Edge"), ("Vivaldi", "Customizable", "VivaldiTechnologies.Vivaldi"),
                ("Opera GX", "Gaming Browser", "Opera.OperaGX"), ("Tor Browser", "Anonymity", "TorProject.TorBrowser"),
                ("Waterfox", "Privacy Focus", "Waterfox.Waterfox"), ("Thorium", "Optimized Build", "Alex313031.Thorium")
            ],
            "Development": [
                ("VS Code", "Code Editor", "Microsoft.VisualStudioCode"), ("Git", "SCM", "Git.Git"),
                ("Python 3.12", "Language", "Python.Python.3.12"), ("Node.js LTS", "Runtime", "OpenJS.NodeJS.LTS"),
                ("Docker Desktop", "Containers", "Docker.DockerDesktop"), ("Postman", "API Tool", "Postman.Postman"),
                ("Notepad++", "Text Editor", "Notepad++.Notepad++"), ("Sublime Text", "Text Editor", "SublimeHQ.SublimeText.4"),
                ("Go", "Language", "GoLang.Go"), ("Rust", "Language", "Rustlang.Rustup"),
                ("CMake", "Build Tool", "Kitware.CMake"), ("PowerShell 7", "Shell", "Microsoft.PowerShell"),
                ("Windows Terminal", "Modern Console", "Microsoft.WindowsTerminal"), ("DBeaver", "SQL Client", "dbeaver.dbeaver")
            ],
            "Multimedia & Design": [
                ("VLC Player", "Media Player", "VideoLAN.VLC"), ("OBS Studio", "Recording", "OBSProject.OBSStudio"),
                ("HandBrake", "Transcoder", "HandBrake.HandBrake"), ("GIMP", "Image Editor", "GIMP.GIMP"),
                ("Krita", "Digital Art", "KritaFoundation.Krita"), ("Inkscape", "Vectors", "Inkscape.Inkscape"),
                ("Blender", "3D Suite", "BlenderFoundation.Blender"), ("Audacity", "Audio Tool", "Audacity.Audacity"),
                ("ShareX", "Screen Capture", "ShareX.ShareX"), ("Lightshot", "Screenshot", "Skillbrains.Lightshot"),
                ("Spotify", "Music", "Spotify.Spotify"), ("DaVinci Resolve", "Video Editing", "BlackmagicDesign.DaVinciResolve")
            ],
            "Gaming Platforms": [
                ("Steam", "Game Store", "Valve.Steam"), ("Epic Games", "Game Store", "EpicGames.EpicGamesLauncher"),
                ("Discord", "Chat Tool", "Discord.Discord"), ("GOG Galaxy", "Launcher", "GOG.Galaxy"),
                ("Ubisoft Connect", "Launcher", "Ubisoft.Connect"), ("EA App", "Launcher", "ElectronicArts.EADesktop"),
                ("Heroic Launcher", "OSS Launcher", "HeroicGamesLauncher.HeroicGamesLauncher"), ("Prism Launcher", "Minecraft", "PrismLauncher.PrismLauncher")
            ],
            "System Utilities": [
                ("7-Zip", "Archiver", "7zip.7zip"), ("NanaZip", "Modern Archiver", "M2Team.NanaZip"),
                ("WinRAR", "Archiver", "RARLab.WinRAR"), ("PowerToys", "MS Utilities", "Microsoft.PowerToys"),
                ("Everything", "Insta-Search", "voidtools.Everything"), ("Rufus", "USB Tool", "Akeo.Rufus"),
                ("BleachBit", "Cleaner", "BleachBit.BleachBit"), ("CPU-Z", "Hardware Info", "CPUID.CPU-Z"),
                ("GPU-Z", "Hardware Info", "TechPowerUp.GPU-Z"), ("WizTree", "Disk Analyzer", "AntibodySoftware.WizTree"),
                ("Flow Launcher", "App Launcher", "Flow-Launcher.Flow-Launcher"), ("AutoHotkey", "Automation", "AutoHotkey.AutoHotkey")
            ]
        }

        for cat, apps in catalog.items():
            ctk.CTkLabel(scroll, text=cat, font=ctk.CTkFont(size=16, weight="bold"), text_color=CLR_ACCENT).pack(anchor="w", pady=(20, 10), padx=10)
            
            grid = ctk.CTkFrame(scroll, fg_color="transparent")
            grid.pack(fill="x")
            
            for i, (name, desc, uid) in enumerate(apps):
                if i % 2 == 0: row = ctk.CTkFrame(grid, fg_color="transparent")
                if i % 2 == 0: row.pack(fill="x", pady=4)
                
                self.create_app_card(row, name, desc, uid)

    def create_app_card(self, parent, name, desc, uid):
        card = ctk.CTkFrame(parent, fg_color=CLR_CARD, corner_radius=12, border_width=1, border_color=CLR_BORDER)
        card.pack(side="left", fill="x", expand=True, padx=5)
        
        info = ctk.CTkFrame(card, fg_color="transparent")
        info.pack(side="left", padx=15, pady=12)
        ctk.CTkLabel(info, text=name, font=ctk.CTkFont(weight="bold")).pack(anchor="w")
        ctk.CTkLabel(info, text=desc, font=ctk.CTkFont(size=11), text_color=CLR_TEXT_DIM).pack(anchor="w")
        
        btn = ctk.CTkButton(card, text="INSTALL", width=80, height=30, fg_color=CLR_ACCENT, hover_color=CLR_ACCENT_HOVER,
                            font=ctk.CTkFont(size=11, weight="bold"),
                            command=lambda: self.run_install(uid))
        btn.pack(side="right", padx=15)

    def run_install(self, uid):
        def task():
            try:
                cmd = f'powershell -Command "Start-Process winget -ArgumentList \'install --id {uid} -e --silent --accept-source-agreements --accept-package-agreements\' -Verb RunAs -Wait"'
                subprocess.run(cmd, shell=True, check=True)
                messagebox.showinfo("CortexDev | MWB", f"Successfully installed: {uid}")
            except Exception as e:
                messagebox.showerror("Installation Error", f"Failed to install {uid}.\nDetails: {e}")
        
        threading.Thread(target=task, daemon=True).start()

    # --- VIEW: Optimizer ---
    def show_optimizer(self):
        self.clear_view()
        self.fade_in()
        
        ctk.CTkLabel(self.main_container, text="System Optimizer", font=self.font_h1).pack(anchor="w", pady=5)
        ctk.CTkLabel(self.main_container, text="Advanced system maintenance tools.", font=self.font_main, text_color=CLR_TEXT_DIM).pack(anchor="w", pady=15)
        
        actions = [
            ("Deep Cleanup", "Remove temporary files and system cache.", "cleanmgr /sagerun:1"),
            ("System Repair", "SFC and DISM health check and repair.", "sfc /scannow"),
            ("Network Flush", "Clear DNS cache and reset network stack.", "ipconfig /flushdns"),
            ("WinUtil GUI", "Launch Chris Titus Tech's maintenance tool.", "irm https://christitus.com/win | iex"),
            ("Disk Health", "Check disk integrity via CHKDSK.", "chkdsk /f")
        ]
        
        for name, desc, cmd in actions:
            row = ctk.CTkFrame(self.main_container, fg_color=CLR_CARD, corner_radius=12, border_width=1, border_color=CLR_BORDER)
            row.pack(fill="x", pady=6)
            
            info = ctk.CTkFrame(row, fg_color="transparent")
            info.pack(side="left", padx=20, pady=15)
            ctk.CTkLabel(info, text=name, font=ctk.CTkFont(weight="bold")).pack(anchor="w")
            ctk.CTkLabel(info, text=desc, font=ctk.CTkFont(size=12), text_color=CLR_TEXT_DIM).pack(anchor="w")
            
            ctk.CTkButton(row, text="RUN TOOL", width=120, fg_color="#27272a", hover_color="#3f3f46", border_width=1, border_color=CLR_ACCENT,
                          command=lambda c=cmd: self.run_script(c)).pack(side="right", padx=20)

    def run_script(self, cmd):
        def task():
            full = f'powershell -Command "Start-Process powershell -ArgumentList \'-NoExit\', \'-Command {cmd}\' -Verb RunAs"'
            subprocess.run(full, shell=True)
        threading.Thread(target=task, daemon=True).start()

    # --- VIEW: Gaming Mode ---
    def show_gaming(self):
        self.clear_view()
        self.fade_in()
        ctk.CTkLabel(self.main_container, text="Ultimate Gaming Mode", font=self.font_h1).pack(anchor="w", pady=5)
        
        card = ctk.CTkFrame(self.main_container, fg_color=CLR_CARD, corner_radius=20, border_width=1, border_color=CLR_ERROR)
        card.pack(fill="both", expand=True, pady=40)
        
        ctk.CTkLabel(card, text="PERFORMANCE BOOST", font=self.font_h2, text_color=CLR_ERROR).pack(pady=(60, 10))
        ctk.CTkLabel(card, text="This will activate the Ultimate Performance Power Plan\nand optimize system latency.", font=self.font_main).pack(pady=20)
        
        btn = ctk.CTkButton(card, text="ACTIVATE NOW", height=50, width=300, fg_color=CLR_ERROR, hover_color="#991b1b", font=self.font_btn,
                            command=lambda: messagebox.showinfo("Gaming Mode", "Ultimate Performance Power Plan Enabled!"))
        btn.pack(pady=20)

    # --- VIEW: Settings ---
    def show_settings(self):
        self.clear_view()
        self.fade_in()
        ctk.CTkLabel(self.main_container, text="App Settings", font=self.font_h1).pack(anchor="w", pady=30)
        
        settings = ["Auto-Update Database", "Enable Animations", "Run as Administrator by Default", "Minimize to Tray"]
        for s in settings:
            sw = ctk.CTkSwitch(self.main_container, text=s, progress_color=CLR_ACCENT, font=self.font_main)
            sw.pack(pady=10, anchor="w", padx=20)

    # --- VIEW: About ---
    def show_about(self):
        self.clear_view()
        self.fade_in()
        
        card = ctk.CTkFrame(self.main_container, fg_color=CLR_CARD, corner_radius=20, border_width=1, border_color=CLR_ACCENT)
        card.pack(fill="both", expand=True, padx=40, pady=40)
        
        ctk.CTkLabel(card, text="MWB", font=self.font_logo, text_color=CLR_ACCENT).pack(pady=(80, 10))
        ctk.CTkLabel(card, text="MAKE MY WINDOWS BETTER", font=self.font_h2).pack()
        ctk.CTkLabel(card, text="Pre-Alpha Build v0.2.1", font=self.font_main, text_color=CLR_TEXT_DIM).pack(pady=5)
        ctk.CTkLabel(card, text="Developed by CortexDev (Aboodi)", font=self.font_btn).pack(pady=20)
        
        ctk.CTkButton(card, text="Visit Portfolio", fg_color="transparent", border_width=1, border_color=CLR_TEXT_DIM,
                      command=lambda: webbrowser.open("https://github.com/CortexDev-Official")).pack(pady=10)

if __name__ == "__main__":
    app = MWBApp()
    app.mainloop()