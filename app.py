import configparser
import ctypes
import customtkinter as ctk
from tkinter import filedialog, messagebox
import subprocess
import threading
import os
import shutil
import getpass
from PIL import Image
from customtkinter import CTkImage
import sys
from sys import platform
import multiprocessing
import time
import signal
import psutil

if sys.platform == "win32":
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("com.example.Html2Apk")

def resource_path(relative_path):

    try:
        base_path = sys._MEIPASS

    except Exception:
        base_path = os.path.abspath(".")
    full_path = os.path.join(base_path, relative_path)

    if not os.path.exists(full_path):
        raise FileNotFoundError(f"Resource not found: {full_path}")
    return full_path

def setup_local_requirements():
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    requirements_dir = os.path.join(BASE_DIR, "HTML2APK_Requirements")
    paths = {
        "BASE_DIR": BASE_DIR,
        "REQUIREMENTS_DIR": requirements_dir,
        "CORDOVA_CMD": None,
        "JAVA_HOME": None,
        "GRADLE_BIN": None,
        "ANDROID_SDK": None
    }

    if os.path.exists(requirements_dir):
        cordova_path = os.path.join(requirements_dir, "nodejs", "node_modules", ".bin", "cordova")

        if sys.platform == "win32":
            cordova_path += ".cmd"

        if os.path.exists(cordova_path):
            paths["CORDOVA_CMD"] = cordova_path
        jdk_path = os.path.join(requirements_dir, "jdk-17.0.17+10")

        if os.path.exists(jdk_path):
            paths["JAVA_HOME"] = jdk_path
        gradle_path = os.path.join(requirements_dir, "gradle-8.5", "bin")

        if os.path.exists(gradle_path):
            paths["GRADLE_BIN"] = gradle_path
        android_sdk_path = os.path.join(requirements_dir, "Sdk")

        if os.path.exists(android_sdk_path):
            paths["ANDROID_SDK"] = android_sdk_path
    return paths

def get_local_environment():
    paths = setup_local_requirements()
    env = os.environ.copy()

    if paths["JAVA_HOME"]:
        env["JAVA_HOME"] = paths["JAVA_HOME"]

    if paths["ANDROID_SDK"]:
        env["ANDROID_SDK_ROOT"] = paths["ANDROID_SDK"]
        env["ANDROID_HOME"] = paths["ANDROID_SDK"]
    path_parts = []

    if paths["GRADLE_BIN"]:
        path_parts.append(paths["GRADLE_BIN"])

    if paths["ANDROID_SDK"]:
        path_parts.append(os.path.join(paths["ANDROID_SDK"], "platform-tools"))
        path_parts.append(os.path.join(paths["ANDROID_SDK"], "tools"))
    path_parts.append(env.get("PATH", ""))
    env["PATH"] = os.pathsep.join(path_parts)
    return env, paths["CORDOVA_CMD"]
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")
DEVICE_PRESETS = {
    "Android Small (360x640)": (360, 640),
    "Android Medium (412x732)": (412, 732),
    "Android Large (480x800)": (480, 800),
    "Android Tablet (600x960)": (600, 960),
    "Android Full HD (1080x1920)": (1080, 1920),
    "iPhone SE (375x667)": (375, 667),
    "iPhone 14 (390x844)": (390, 844),
    "iPhone 14 Pro Max (430x932)": (430, 932),
    "iPad Mini (768x1024)": (768, 1024),
    "iPad Pro (1024x1366)": (1024, 1366),
    "Custom Size": None
}
ORIENTATION_OPTIONS = {
    "portrait": "Portrait (fixed)",
    "landscape": "Landscape (fixed)",
    "portrait-sensor": "Portrait (sensor - auto rotate)",
    "landscape-sensor": "Landscape (sensor - both orientations)",
    "sensor": "Auto Rotate (all orientations)",
    "unspecified": "Default (system controlled)"
}

def run_webview_preview(html_path, device_size, title="HTML Preview - APK Builder"):
    import webview
    import os
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    import time

    class ReloadHandler(FileSystemEventHandler):

        def __init__(self, webview_window):
            self.webview_window = webview_window
            self.window_active = True

        def on_modified(self, event):

            if event.src_path.endswith('.html') and self.window_active:
                time.sleep(0.1)

                try:
                    self.webview_window.evaluate_js("location.reload();")

                except Exception:
                    self.window_active = False

    try:

        if os.path.isfile(html_path):
            index_path = html_path
        else:
            index_path = os.path.join(html_path, "index.html")

        if not os.path.exists(index_path):
            print(f"Error: index.html not found at {index_path}")
            return
        width, height = device_size if device_size else (800, 600)
        window = webview.create_window(
            title=title,
            url=f"file:///{index_path.replace(os.sep, '/')}",
            width=width,
            height=height,
            resizable=True,
            min_size=(300, 400)
        )
        watch_path = os.path.dirname(index_path) if os.path.isfile(index_path) else html_path
        observer = Observer()
        handler = ReloadHandler(window)
        observer.schedule(handler, watch_path, recursive=True)
        observer.start()
        webview.start()
        observer.stop()
        observer.join()

    except Exception as e:
        print(f"Preview error: {e}")
        import traceback
        traceback.print_exc()

class PlaceholderEntry(ctk.CTkEntry):

    def __init__(self, master=None, placeholder="", placeholder_color="gray", **kwargs):
        super().__init__(master, **kwargs)
        self.placeholder = placeholder
        self.placeholder_color = placeholder_color
        self.default_fg_color = self.cget("text_color")
        self.bind("<FocusIn>", self._clear_placeholder)
        self.bind("<FocusOut>", self._add_placeholder)
        self._add_placeholder()

    def _add_placeholder(self, event=None):

        if not self.get() and self.placeholder:
            self.configure(text_color=self.placeholder_color)
            self.insert(0, self.placeholder)

    def _clear_placeholder(self, event=None):

        if self.get() == self.placeholder:
            self.delete(0, "end")
            self.configure(text_color=self.default_fg_color)

    def get_value(self):
        text = self.get()
        return "" if text == self.placeholder else text

    def set_value(self, value):

        if value:
            self.delete(0, "end")
            self.insert(0, value)
            self.configure(text_color=self.default_fg_color)
        else:
            self._add_placeholder()

class HTMLToAPKBuilderPRO:

    def __init__(self, root):
        self.root = root
        self.root.title("HTML → APK Builder")
        self.root.geometry("890x700")
        self.local_env, self.cordova_cmd = get_local_environment()

        if platform == "win32":
            config_dir = os.path.join(os.getenv('APPDATA'), "html2apk")
        os.makedirs(config_dir, exist_ok=True)
        self.config_file = os.path.join(config_dir, 'config.ini')
        self.preview_process = None
        self.username = getpass.getuser().lower()
        self.preview_size = ctk.StringVar(value="Android Small (360x640)")
        self.app_name = ctk.StringVar()
        self.app_id = ctk.StringVar(value=f"com.{self.username}.")
        self.html_path = ctk.StringVar()
        self.icon_path = ctk.StringVar(value="")
        self.output_path = ctk.StringVar()
        self.version = ctk.StringVar(value="1.0.0")
        self.version_code = ctk.StringVar(value="1")
        self.orientation = ctk.StringVar(value="portrait")
        self.orientation_display = ctk.StringVar(value=ORIENTATION_OPTIONS["portrait"])
        self.fullscreen = ctk.BooleanVar(value=True)
        self.internet = ctk.BooleanVar(value=True)
        self.default_icon_path = resource_path("images/default_icon.png")
        self.icon_image = None
        self.build_process = None
        self.build_thread = None
        self.is_building = False
        self.project_dir = None
        self.current_process = None
        self.process_tree = []
        self.build_stages = [
            "Validating project",
            "Creating Cordova project",
            "Adding Android platform",
            "Copying HTML files",
            "Updating config.xml",
            "Building APK (gradle)",
            "Finding and copying APK"
        ]
        self.current_stage = 0
        self.total_stages = len(self.build_stages)
        self.build_ui()
        self.update_icon_preview()
        self.app_name.trace_add("write", self.sync_app_id)
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.load_window_geometry()
        self.check_requirements()

    def check_requirements(self):
        self.log("=== Local Requirements Check ===", "info")

        if self.cordova_cmd and os.path.exists(self.cordova_cmd):
            self.log(f"✓ Local Cordova found: {self.cordova_cmd}", "success")
        else:
            self.log("⚠ Local Cordova not found, using system Cordova", "warning")
            self.cordova_cmd = "cordova"

        if self.local_env.get("JAVA_HOME"):
            self.log(f"✓ Local Java found: {self.local_env['JAVA_HOME']}", "success")
        else:
            self.log("⚠ Local Java not found, using system Java", "warning")

        if self.local_env.get("ANDROID_SDK_ROOT"):
            self.log(f"✓ Local Android SDK found: {self.local_env['ANDROID_SDK_ROOT']}", "success")
        else:
            self.log("⚠ Local Android SDK not found, using system SDK", "warning")
        self.log("================================", "info")

    def load_window_geometry(self):

        if os.path.exists(self.config_file):
            config = configparser.ConfigParser()
            config.read(self.config_file)

            if "Geometry" in config:
                geometry = config["Geometry"].get("size", "")
                state = config["Geometry"].get("state", "normal")

                if geometry:
                    self.root.geometry(geometry)
                    self.root.update_idletasks()
                    self.root.update()

                if state == "zoomed":
                    self.root.state("zoomed")
                elif state == "iconic":
                    self.root.iconify()

    def save_window_geometry(self):
        config = configparser.ConfigParser()
        config["Geometry"] = {
            "size": self.root.geometry(),
            "state": self.root.state()
        }

        with open(self.config_file, "w") as f:
            config.write(f)

    def update_progress(self, stage_index=None, stage_name=None, increment=False):

        if stage_index is not None:
            self.current_stage = stage_index

        if stage_name:
            self.status.set(stage_name)
        progress_percentage = (self.current_stage / self.total_stages)
        self.progress.set(progress_percentage)
        self.root.update_idletasks()

        if increment and self.current_stage < self.total_stages - 1:
            self.current_stage += 1

    def reset_progress(self):
        self.current_stage = 0
        self.progress.set(0)
        self.status.set("Idle")

    def run_cmd(self, cmd, cwd=None, stage_name=None):

        if stage_name:
            self.status.set(stage_name)
            self.root.update_idletasks()
