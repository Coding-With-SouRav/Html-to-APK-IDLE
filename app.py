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

# ------------------ LOCAL REQUIREMENTS SETUP ------------------
def setup_local_requirements():
    """Setup local requirements paths similar to z.py"""
    # Get the directory where this script is located
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    
    # Define paths for local requirements
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
        # Cordova path
        cordova_path = os.path.join(requirements_dir, "nodejs", "node_modules", ".bin", "cordova")
        if sys.platform == "win32":
            cordova_path += ".cmd"
        if os.path.exists(cordova_path):
            paths["CORDOVA_CMD"] = cordova_path
        
        # Java Home
        jdk_path = os.path.join(requirements_dir, "jdk-17.0.17+10")
        if os.path.exists(jdk_path):
            paths["JAVA_HOME"] = jdk_path
        
        # Gradle
        gradle_path = os.path.join(requirements_dir, "gradle-8.5", "bin")
        if os.path.exists(gradle_path):
            paths["GRADLE_BIN"] = gradle_path
        
        # Android SDK
        android_sdk_path = os.path.join(requirements_dir, "Sdk")
        if os.path.exists(android_sdk_path):
            paths["ANDROID_SDK"] = android_sdk_path
    
    return paths

# ------------------ ENVIRONMENT SETUP ------------------
def get_local_environment():
    """Get environment with local requirements"""
    paths = setup_local_requirements()
    env = os.environ.copy()
    
    # Set JAVA_HOME if available
    if paths["JAVA_HOME"]:
        env["JAVA_HOME"] = paths["JAVA_HOME"]
    
    # Set Android SDK paths
    if paths["ANDROID_SDK"]:
        env["ANDROID_SDK_ROOT"] = paths["ANDROID_SDK"]
        env["ANDROID_HOME"] = paths["ANDROID_SDK"]
    
    # Update PATH with local tools
    path_parts = []
    
    if paths["GRADLE_BIN"]:
        path_parts.append(paths["GRADLE_BIN"])
    
    if paths["ANDROID_SDK"]:
        path_parts.append(os.path.join(paths["ANDROID_SDK"], "platform-tools"))
        path_parts.append(os.path.join(paths["ANDROID_SDK"], "tools"))
    
    # Add existing PATH
    path_parts.append(env.get("PATH", ""))
    
    env["PATH"] = os.pathsep.join(path_parts)
    
    return env, paths["CORDOVA_CMD"]

# ------------------ UI SETUP ------------------
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# ------------------ DEVICE PRESETS ------------------
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

# ------------------ ORIENTATION OPTIONS ------------------
ORIENTATION_OPTIONS = {
    "portrait": "Portrait (fixed)",
    "landscape": "Landscape (fixed)",
    "portrait-sensor": "Portrait (sensor - auto rotate)",
    "landscape-sensor": "Landscape (sensor - both orientations)",
    "sensor": "Auto Rotate (all orientations)",
    "unspecified": "Default (system controlled)"
}

# ------------------ HTML PREVIEW PROCESS ------------------
def run_webview_preview(html_path, device_size, title="HTML Preview - APK Builder"):
    """Run webview in a separate process"""
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
                    # Window might be closed
                    self.window_active = False
    
    try:
        # Check if html_path is a file or directory
        if os.path.isfile(html_path):
            index_path = html_path
        else:
            index_path = os.path.join(html_path, "index.html")
            
        if not os.path.exists(index_path):
            print(f"Error: index.html not found at {index_path}")
            return
            
        # Create webview window
        width, height = device_size if device_size else (800, 600)
        window = webview.create_window(
            title=title,
            url=f"file:///{index_path.replace(os.sep, '/')}",
            width=width,
            height=height,
            resizable=True,
            min_size=(300, 400)
        )
        
        # Start file watcher for live reload
        watch_path = os.path.dirname(index_path) if os.path.isfile(index_path) else html_path
        observer = Observer()
        handler = ReloadHandler(window)
        observer.schedule(handler, watch_path, recursive=True)
        observer.start()
        
        # Start webview
        webview.start()
        
        # Stop observer when window closes
        observer.stop()
        observer.join()
        
    except Exception as e:
        print(f"Preview error: {e}")
        import traceback
        traceback.print_exc()

# ------------------ PLACEHOLDER ENTRY CLASS ------------------
class PlaceholderEntry(ctk.CTkEntry):
    """Custom CTkEntry with placeholder functionality"""
    def __init__(self, master=None, placeholder="", placeholder_color="gray", **kwargs):
        super().__init__(master, **kwargs)
        self.placeholder = placeholder
        self.placeholder_color = placeholder_color
        self.default_fg_color = self.cget("text_color")
        
        self.bind("<FocusIn>", self._clear_placeholder)
        self.bind("<FocusOut>", self._add_placeholder)
        
        # Set initial placeholder
        self._add_placeholder()
        
    def _add_placeholder(self, event=None):
        """Add placeholder text if entry is empty"""
        if not self.get() and self.placeholder:
            self.configure(text_color=self.placeholder_color)
            self.insert(0, self.placeholder)
            
    def _clear_placeholder(self, event=None):
        """Clear placeholder text on focus"""
        if self.get() == self.placeholder:
            self.delete(0, "end")
            self.configure(text_color=self.default_fg_color)
    
    def get_value(self):
        """Get the actual value (empty string if placeholder)"""
        text = self.get()
        return "" if text == self.placeholder else text
    
    def set_value(self, value):
        """Set value and handle placeholder"""
        if value:
            self.delete(0, "end")
            self.insert(0, value)
            self.configure(text_color=self.default_fg_color)
        else:
            self._add_placeholder()

# ------------------ MAIN APPLICATION ------------------
class HTMLToAPKBuilderPRO:
    def __init__(self, root):
        self.root = root
        self.root.title("HTML → APK Builder")
        self.root.geometry("890x700")
        
        # Setup local requirements
        self.local_env, self.cordova_cmd = get_local_environment()
        
        if platform == "win32":
            config_dir = os.path.join(os.getenv('APPDATA'), "html2apk")
        os.makedirs(config_dir, exist_ok=True)
        self.config_file = os.path.join(config_dir, 'config.ini')

        # ---------------- VARIABLES ----------------
        self.preview_process = None
        self.username = getpass.getuser().lower()
        self.preview_size = ctk.StringVar(value="Android Small (360x640)")
        self.app_name = ctk.StringVar()
        self.app_id = ctk.StringVar(value=f"com.{self.username}.")
        self.html_path = ctk.StringVar()
        self.icon_path = ctk.StringVar(value="")  # Empty by default
        self.output_path = ctk.StringVar()

        self.version = ctk.StringVar(value="1.0.0")
        self.version_code = ctk.StringVar(value="1")

        # Changed orientation to support sensor modes
        self.orientation = ctk.StringVar(value="portrait")
        self.orientation_display = ctk.StringVar(value=ORIENTATION_OPTIONS["portrait"])

        self.fullscreen = ctk.BooleanVar(value=True)
        self.internet = ctk.BooleanVar(value=True)
        self.default_icon_path = resource_path("images/default_icon.png")
        self.icon_image = None
        
        # Build process control variables
        self.build_process = None
        self.build_thread = None
        self.is_building = False
        self.project_dir = None  # Store project directory for cleanup
        self.current_process = None  # Store current subprocess for termination
        self.process_tree = []  # Store all subprocesses for termination

        # Progress tracking
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
        
        # Handle window close to kill preview process
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.load_window_geometry()
        
        # Log local requirements status
        self.check_requirements()

    def check_requirements(self):
        """Check and log local requirements status"""
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

    # ---------------- PROGRESS BAR METHODS ----------------
    def update_progress(self, stage_index=None, stage_name=None, increment=False):
        """Update progress bar based on build stage"""
        if stage_index is not None:
            self.current_stage = stage_index
        
        if stage_name:
            self.status.set(stage_name)
        
        # Calculate progress percentage
        progress_percentage = (self.current_stage / self.total_stages)
        
        # Set progress bar value (0 to 1)
        self.progress.set(progress_percentage)
        
        # Update UI
        self.root.update_idletasks()
        
        if increment and self.current_stage < self.total_stages - 1:
            self.current_stage += 1

    def reset_progress(self):
        """Reset progress bar to initial state"""
        self.current_stage = 0
        self.progress.set(0)
        self.status.set("Idle") 

    # ---------------- UTIL ----------------
    def run_cmd(self, cmd, cwd=None, stage_name=None):
        """Run command with local environment and update progress"""
        if stage_name:
            self.status.set(stage_name)
            self.root.update_idletasks()
        
        # Replace 'cordova' with local cordova command if available
        if self.cordova_cmd and "cordova" in cmd and not cmd.startswith('"'):
            # Extract the cordova command and arguments
            if cmd.startswith("cordova"):
                cmd = cmd.replace("cordova", f'"{self.cordova_cmd}"', 1)
        
        self.log(f"Running: {cmd}", "info")
        
        # Create subprocess with creation flags for Windows to allow Ctrl+C
        if sys.platform == "win32":
            creationflags = subprocess.CREATE_NEW_PROCESS_GROUP
        else:
            creationflags = 0
        
        process = subprocess.Popen(
            cmd, cwd=cwd, shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            env=self.local_env,
            creationflags=creationflags,
            bufsize=1,
            universal_newlines=True
        )
        
        # Store current process for potential termination
        self.current_process = process
        self.process_tree.append(process)

        for line in process.stdout:
            # Check if build was cancelled - exit immediately
            if not self.is_building:  
                self.send_ctrl_c(process)
                break
                
            tag = "info"

            low = line.lower()
            if "error" in low or "failed" in low:
                tag = "error"
            elif "success" in low or "built" in low:
                tag = "success"
            elif "warning" in low:
                tag = "warning"

            self.log(line.rstrip(), tag)

        # Add immediate return when cancelled
        if not self.is_building:
            # Kill the entire process tree
            self.kill_process_tree(process)
            return 1

        process.wait()
        
        # Remove from process tree
        if process in self.process_tree:
            self.process_tree.remove(process)
        self.current_process = None
        return process.returncode
    
    def send_ctrl_c(self, process):
        """Send Ctrl+C to interrupt the process"""
        try:
            if sys.platform == "win32":
                # Windows: Send Ctrl+C to process group
                import ctypes
                ctypes.windll.kernel32.GenerateConsoleCtrlEvent(0, process.pid)
                time.sleep(0.5)
                # Force kill if still running
                if process.poll() is None:
                    process.kill()
            else:
                # Unix: Send SIGINT
                process.send_signal(signal.SIGINT)
                time.sleep(0.5)
                # Force kill if still running
                if process.poll() is None:
                    process.send_signal(signal.SIGKILL)
        except Exception as e:
            self.log(f"Error sending Ctrl+C: {e}", "warning")
            # Fallback to terminate
            process.terminate()
            time.sleep(0.2)
            if process.poll() is None:
                process.kill()
    
    def kill_process_tree(self, process):
        """Kill entire process tree including child processes"""
        try:
            if sys.platform == "win32":
                # Windows: Use taskkill to kill entire process tree
                subprocess.run(f'taskkill /F /T /PID {process.pid}', 
                             shell=True, capture_output=True)
            else:
                # Unix: Use psutil to find and kill child processes
                try:
                    parent = psutil.Process(process.pid)
                    children = parent.children(recursive=True)
                    for child in children:
                        try:
                            child.terminate()
                        except:
                            pass
                    gone, alive = psutil.wait_procs(children, timeout=3)
                    for p in alive:
                        p.kill()
                    parent.terminate()
                    parent.wait(5)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
        except Exception as e:
            self.log(f"Error killing process tree: {e}", "warning")
        
        # Ensure the main process is dead
        try:
            process.terminate()
            time.sleep(0.2)
            if process.poll() is None:
                process.kill()
        except:
            pass

    def clear_log(self):
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.configure(state="disabled")
        self.status.set("Log cleared")

    def build_apk(self):
        try:
            # Reset progress at start
            self.reset_progress()
            self.update_progress(0, "Validating project... Please Wait a moment...")

            app_name = self.app_name.get().strip()
            app_id = self.app_id.get().strip()
            html_dir = self.html_path.get().strip()
            
            # FIXED: Always get icon path from the entry widget directly
            if hasattr(self, 'icon_entry'):
                icon = self.icon_entry.get_value().strip()
            else:
                icon = self.icon_path.get().strip()
                
            out_dir = self.output_path.get().strip()

            if not all([app_name, app_id, html_dir, out_dir]):
                raise Exception("Please fill all required fields")

            if not os.path.isfile(os.path.join(html_dir, "index.html")):
                raise Exception("index.html not found in HTML folder")

            self.project_dir = os.path.join(out_dir, app_name)

            # Clean up existing project if it exists
            if os.path.exists(self.project_dir):
                self.log("Cleaning up existing project...", "info")
                shutil.rmtree(self.project_dir)

            # Check if build was cancelled before proceeding
            if not self.is_building:
                self.log("Build cancelled", "warning")
                self.cleanup_after_cancel()
                return

            # Stage 1: Creating Cordova project
            self.update_progress(1, "Creating Cordova project...")
            self.log("Creating Cordova project...", "info")
            create_cmd = f'"{self.cordova_cmd}" create "{self.project_dir}" {app_id} "{app_name}"'
            return_code = self.run_cmd(create_cmd, stage_name="Creating Cordova project...")
            
            if return_code != 0:
                raise Exception("Failed to create Cordova project")
                
            # Check if build was cancelled
            if not self.is_building:
                self.log("Build cancelled", "warning")
                self.cleanup_after_cancel()
                return

            # Stage 2: Adding Android platform
            self.update_progress(2, "Adding Android platform...")
            self.log("Adding Android platform...", "info")
            add_platform_cmd = f'"{self.cordova_cmd}" platform add android'
            return_code = self.run_cmd(add_platform_cmd, cwd=self.project_dir, stage_name="Adding Android platform...")
            
            if return_code != 0:
                raise Exception("Failed to add Android platform")
                
            # Check if build was cancelled
            if not self.is_building:
                self.log("Build cancelled", "warning")
                self.cleanup_after_cancel()
                return

            # Stage 3: Copying HTML files
            self.update_progress(3, "Copying HTML files...")
            # Replace www with HTML content
            www_dir = os.path.join(self.project_dir, "www")
            if os.path.exists(www_dir):
                shutil.rmtree(www_dir)
            shutil.copytree(html_dir, www_dir)
            self.log("HTML files copied", "success")
            
            # Check if build was cancelled
            if not self.is_building:
                self.log("Build cancelled", "warning")
                self.cleanup_after_cancel()
                return

            # Stage 4: Updating config.xml
            self.update_progress(4, "Updating config.xml...")
            # Update config.xml
            config = os.path.join(self.project_dir, "config.xml")
            with open(config, "r", encoding="utf-8") as f:
                data = f.read()

            data = data.replace(
                "<widget",
                f'<widget version="{self.version.get()}" android-versionCode="{self.version_code.get()}"'
            )

            # Orientation handling - Map UI selection to Cordova values
            orientation_key = self.orientation.get()
            import re
            
            # Map orientation selections to Cordova values
            orientation_map = {
                "Portrait (fixed)": "portrait",
                "Landscape (fixed)": "landscape",
                "Portrait (sensor - auto rotate)": "portrait",  # Will use Android-specific sensorPortrait
                "Landscape (sensor - both orientations)": "landscape",  # Will use Android-specific sensorLandscape
                "Auto Rotate (all orientations)": "all",
                "Default (system controlled)": "default"
            }
            
            # Map to Android-specific values for AndroidManifest.xml
            android_orientation_map = {
                "Portrait (fixed)": "portrait",
                "Landscape (fixed)": "landscape",
                "Portrait (sensor - auto rotate)": "sensorPortrait",
                "Landscape (sensor - both orientations)": "sensorLandscape",
                "Auto Rotate (all orientations)": "fullSensor",
                "Default (system controlled)": "unspecified"
            }
            
            # Remove any existing orientation preference
            data = re.sub(r'\s*<preference name="Orientation"[^>]*/>', '', data)
            data = re.sub(r'\s*<preference name="orientation"[^>]*/>', '', data)
            
            # Add orientation preference based on selection
            if orientation_key in orientation_map:
                cordova_value = orientation_map[orientation_key]
                android_value = android_orientation_map[orientation_key]
                
                # Add Cordova preference
                if cordova_value != "unspecified":
                    data = data.replace(
                        "</widget>",
                        f'    <preference name="orientation" value="{cordova_value}"/>\n</widget>'
                    )
                    self.log(f"Set Cordova orientation to: {cordova_value}", "info")
                
                # For sensor-specific orientations, we need Android-specific configuration
                if orientation_key in ["Portrait (sensor - auto rotate)", "Landscape (sensor - both orientations)"]:
                    # Remove any existing Android platform config for orientation
                    data = re.sub(r'\s*<platform name="android">[\s\S]*?</platform>', '', data)
                    
                    # Add Android platform with edit-config for screenOrientation
                    android_config = f'''
    <platform name="android">
        <edit-config file="AndroidManifest.xml" target="/manifest/application/activity[@android:name='MainActivity']" mode="merge">
            <activity android:screenOrientation="{android_value}" />
        </edit-config>
    </platform>'''
                    
                    # Find the last preference or icon tag before </widget>
                    # Insert Android platform config before </widget>
                    insert_position = data.rfind('</widget>')
                    if insert_position != -1:
                        data = data[:insert_position] + android_config + '\n' + data[insert_position:]
                    
                    self.log(f"Set Android screenOrientation to: {android_value}", "info")
                
                # For regular orientations, we still want to ensure Android gets the right value
                elif orientation_key not in ["Default (system controlled)"]:
                    # Check if android platform tag already exists
                    if '<platform name="android">' not in data:
                        android_config = f'''
    <platform name="android">
        <edit-config file="AndroidManifest.xml" target="/manifest/application/activity[@android:name='MainActivity']" mode="merge">
            <activity android:screenOrientation="{android_value}" />
        </edit-config>
    </platform>'''
                        
                        # Insert Android platform config before </widget>
                        insert_position = data.rfind('</widget>')
                        if insert_position != -1:
                            data = data[:insert_position] + android_config + '\n' + data[insert_position:]
                    
                    self.log(f"Set Android screenOrientation to: {android_value}", "info")

            if self.fullscreen.get():
                data = re.sub(r'\s*<preference name="Fullscreen"[^>]*/>', '', data)
                data = re.sub(r'\s*<preference name="fullscreen"[^>]*/>', '', data)
                data = data.replace(
                    "</widget>",
                    '    <preference name="fullscreen" value="true"/>\n</widget>'
                )

            if self.internet.get():
                data = re.sub(r'\s*<access origin="\*"[^>]*/>', '', data)
                data = re.sub(r'\s*<access origin="\*" />', '', data)
                data = data.replace(
                    "</widget>",
                    '    <access origin="*" />\n</widget>'
                )

            # FIXED: Icon handling - better validation and error handling
            icon_used = None
            if icon and icon != "Optional (uses default)":
                # Check if icon file exists and is a PNG
                if os.path.exists(icon) and icon.lower().endswith('.png'):
                    try:
                        # Test if it's a valid image
                        with Image.open(icon) as img:
                            img.verify()  # Verify it's a valid image
                        
                        # Re-open for actual use
                        img = Image.open(icon)
                        
                        # Copy custom icon to www directory
                        icon_dest = os.path.join(www_dir, "icon.png")
                        shutil.copy(icon, icon_dest)
                        
                        # Remove any existing icon configuration
                        data = re.sub(r'\s*<icon src="[^"]*"[^>]*/>', '', data)
                        
                        # Add icon configuration
                        data = data.replace(
                            "</widget>",
                            '    <icon src="www/icon.png"/>\n</widget>'
                        )
                        
                        icon_used = "custom"
                        self.log(f"✓ Using custom icon: {os.path.basename(icon)}", "success")
                        
                    except Exception as e:
                        self.log(f"⚠ Custom icon invalid, using default: {str(e)}", "warning")
                        icon = None  # Fall back to default
                else:
                    self.log(f"⚠ Custom icon not found or not PNG: {icon}", "warning")
                    icon = None  # Fall back to default
            
            # If no custom icon or custom icon failed, use default
            if not icon_used:
                if os.path.exists(self.default_icon_path):
                    # Copy default icon
                    icon_dest = os.path.join(www_dir, "icon.png")
                    shutil.copy(self.default_icon_path, icon_dest)
                    
                    # Remove any existing icon configuration
                    data = re.sub(r'\s*<icon src="[^"]*"[^>]*/>', '', data)
                    
                    # Add icon configuration
                    data = data.replace(
                        "</widget>",
                        '    <icon src="www/icon.png"/>\n</widget>'
                    )
                    icon_used = "default"
                    self.log("Using default app icon", "info")
                else:
                    self.log("⚠ No icon specified and default icon not found, skipping icon setup", "warning")

            with open(config, "w", encoding="utf-8") as f:
                f.write(data)
                
            self.log("config.xml updated", "success")

            # Check if build was cancelled
            if not self.is_building:
                self.log("Build cancelled", "warning")
                self.cleanup_after_cancel()
                return

            # Stage 5: Building APK (gradle)
            self.update_progress(5, "Building APK (this may take a few minutes)...")
            self.log("Building APK...", "info")
            build_cmd = f'"{self.cordova_cmd}" build android'
            return_code = self.run_cmd(build_cmd, cwd=self.project_dir, stage_name="Building APK with Gradle...")
            
            if return_code != 0:
                raise Exception("APK build failed")

            # Check if build was cancelled
            if not self.is_building:
                self.log("Build cancelled", "warning")
                self.cleanup_after_cancel()
                return

            # Stage 6: Finding and copying APK
            self.update_progress(6, "Finding generated APK...")
            # Find the generated APK
            apk_dir = os.path.join(
                self.project_dir, "platforms", "android",
                "app", "build", "outputs", "apk"
            )

            apk_file = None
            for root, _, files in os.walk(apk_dir):
                for f in files:
                    if f.endswith(".apk") and "debug" in root:
                        apk_file = os.path.join(root, f)
                        break
                if apk_file:
                    break

            if not apk_file:
                self.log("Searching for APK in alternative locations...", "info")
                # Try alternative locations
                apk_search_dirs = [
                    os.path.join(self.project_dir, "platforms", "android", "build", "outputs", "apk"),
                    os.path.join(self.project_dir, "platforms", "android", "app", "build", "outputs", "apk", "debug"),
                    os.path.join(self.project_dir, "platforms", "android", "build", "outputs", "apk", "debug"),
                ]
                
                for search_dir in apk_search_dirs:
                    if os.path.exists(search_dir):
                        for f in os.listdir(search_dir):
                            if f.endswith(".apk"):
                                apk_file = os.path.join(search_dir, f)
                                break
                    if apk_file:
                        break
            
            if not apk_file:
                raise Exception("APK not generated. Check build logs.")

            # Copy APK to output directory
            output_apk = os.path.join(out_dir, f"{app_name}.apk")
            shutil.copy(apk_file, output_apk)
            
            # Stage 7: Complete
            self.update_progress(self.total_stages - 1, "Build completed successfully!")
            self.log(f"✓ APK saved to: {output_apk}", "success")
            
            # Optional: Clean up project directory
            try:
                shutil.rmtree(self.project_dir)
                self.log("Cleaned up temporary project files", "info")
                self.project_dir = None
            except:
                pass

            self.status.set("Build completed successfully")
            self.log("✓ Build completed successfully!", "success")
            messagebox.showinfo("SUCCESS", f"APK build completed!\nSaved to: {output_apk}")
            self.progress.set(0)

        except Exception as e:
            self.status.set("Build failed")
            self.log(f"✗ Build failed: {str(e)}", "error")
            messagebox.showerror("ERROR", str(e))

        finally:
            self.reset_build_button()
            self.is_building = False
            self.project_dir = None
            # Clear process tree
            self.process_tree.clear()
            self.progress.set(0)
                      
    def start_build(self):
        """Start the APK build process"""
        if self.is_building:
            # If already building, cancel it
            self.cancel_build()
        else:
            # Start new build
            self.is_building = True
            self.process_tree.clear()  # Clear any old processes
            self.build_btn.configure(
                text="⏹ CANCEL BUILD",
                fg_color="#d32f2f",  # Red color for cancel
                hover_color="#b71c1c"
            )
            self.status.set("Building APK... Click CANCEL to stop")
            self.build_thread = threading.Thread(target=self.build_apk, daemon=True)
            self.build_thread.start()
            
    def cancel_build(self):
        """Cancel the ongoing build process"""
        if not self.is_building:
            return
        
        # Ask for confirmation
        confirm = messagebox.askyesno(
            "Confirm Cancellation", 
            "Are you sure you want to cancel the APK build?\n\nThis will send Ctrl+C to stop the build process and clean up temporary files."
        )
        
        if not confirm:
            return  # User clicked No, don't cancel
        
        # User confirmed, proceed with cancellation
        self.is_building = False
        self.status.set("Cancelling build (sending Ctrl+C)...")
        self.log("Build cancellation confirmed by user. Sending Ctrl+C to interrupt build...", "warning")
        
        # Send Ctrl+C to all running processes
        for process in self.process_tree:
            if process and process.poll() is None:  # Process is still running
                try:
                    self.send_ctrl_c(process)
                    self.log(f"Sent Ctrl+C to process PID: {process.pid}", "info")
                except Exception as e:
                    self.log(f"Error sending Ctrl+C to process: {str(e)}", "warning")
        
        # Clear process tree
        self.process_tree.clear()
        
        # Force cleanup of project directory
        self.cleanup_after_cancel()
        
        self.reset_build_button()
        self.reset_progress()
        self.status.set("Build cancelled - Process interrupted")
        self.log("✓ Build cancelled by user - Temporary files cleaned up", "warning")
        
        # Wait a bit for processes to terminate
        time.sleep(1)

    def cleanup_after_cancel(self):
        """Clean up project directory after cancellation"""
        # Add a small delay to ensure processes are terminated
        time.sleep(0.5)
        
        # Clean up temp project directory if it exists
        if self.project_dir and os.path.exists(self.project_dir):
            try:
                # Try multiple times to delete in case files are locked
                for attempt in range(3):
                    try:
                        shutil.rmtree(self.project_dir, ignore_errors=True)
                        # Verify deletion
                        if not os.path.exists(self.project_dir):
                            self.log(f"✓ Cleaned up temporary project: {os.path.basename(self.project_dir)}", "info")
                            self.project_dir = None
                            break
                        else:
                            time.sleep(1)  # Wait longer and retry
                    except Exception as e:
                        if attempt < 2:  # Don't wait on last attempt
                            time.sleep(1)
                        else:
                            self.log(f"⚠ Could not fully clean up project directory: {str(e)}", "warning")
            except Exception as e:
                self.log(f"⚠ Error during cleanup: {str(e)}", "warning")
    
    def reset_build_button(self):
        """Reset build button to original state"""
        self.build_btn.configure(
            text="BUILD APK",
            fg_color="#3365aa",  # Reset to default
            hover_color="#314e76",
            state="normal"
        )

    def log(self, text, tag="info"):
        self.log_box.configure(state="normal")
        self.log_box.insert("end", text + "\n", tag)
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def browse_dir(self, var):
        var.set(filedialog.askdirectory())

    def browse_file(self, var):
        file = filedialog.askopenfilename(filetypes=[("PNG Images", "*.png"), ("All files", "*.*")])
        if file:
            # Set the value in the PlaceholderEntry widget
            if hasattr(self, 'icon_entry'):
                self.icon_entry.set_value(file)
                self.icon_entry.configure(text_color=self.icon_entry.default_fg_color)
                self.icon_path.set(file)  # Still update the variable for compatibility
            
            # Update icon preview
            self.update_icon_preview()

    def update_icon_preview(self):
        """Update the icon preview image based on selected icon or default"""
        # Get the actual value from custom entry if available
        if hasattr(self, 'icon_entry'):
            icon_value = self.icon_entry.get_value()
        else:
            icon_value = self.icon_path.get()
        
        # Use default icon if no custom icon specified or if placeholder text
        if not icon_value or icon_value == "Optional (uses default)":
            path = self.default_icon_path
        else:
            path = icon_value
            
        try:
            # Try to load the specified icon
            img = Image.open(path)
            self.icon_image = CTkImage(light_image=img, dark_image=img, size=(80, 80))
            self.icon_preview.configure(image=self.icon_image)
            
            # Update the label text
            if not icon_value or icon_value == "Optional (uses default)":
                self.text.configure(text="Default Icon Preview")
            else:
                self.text.configure(text="Custom Icon Preview")
                self.log(f"Loaded custom icon: {os.path.basename(path)}", "info")
                
        except Exception as e:
            # If custom icon fails to load, show default
            try:
                img = Image.open(self.default_icon_path)
                self.icon_image = CTkImage(light_image=img, dark_image=img, size=(80, 80))
                self.icon_preview.configure(image=self.icon_image)
                self.text.configure(text="Default Icon Preview")
                if icon_value and icon_value != "Optional (uses default)":
                    self.log(f"Failed to load custom icon, using default: {e}", "warning")
            except Exception as default_e:
                # If default icon also fails
                self.text.configure(text="No Icon Available")
                self.icon_preview.configure(image=None, text="❌")
                self.log(f"Failed to load any icon: {default_e}", "error")
                
    def sync_app_id(self, *args):
        name = self.app_name.get().lower().replace(" ", "")
        self.app_id.set(f"com.{self.username}.{name}")

    def on_orientation_change(self, choice):
        """Handle orientation selection change"""
        # Map display value to internal value
        for key, value in ORIENTATION_OPTIONS.items():
            if value == choice:
                self.orientation.set(key)
                self.orientation_display.set(value)
                break
        
        # Update status
        if key == "landscape-sensor":
            self.log("Landscape (sensor) selected: App will rotate between both landscape orientations", "info")
        elif key == "portrait-sensor":
            self.log("Portrait (sensor) selected: App will rotate between both portrait orientations", "info")
        elif key == "sensor":
            self.log("Auto Rotate selected: App will support all orientations", "info")

    # ---------------- HTML PREVIEW METHODS ----------------
    def preview_html(self):
        """Open HTML preview in selected device size"""
        html_path = self.html_path.get().strip()
        
        if not html_path:
            messagebox.showwarning("No HTML Folder", "Please select an HTML folder first!")
            return
        
        # Check if index.html exists
        index_path = os.path.join(html_path, "index.html")
        if not os.path.exists(index_path):
            messagebox.showwarning("No index.html", "index.html not found in the selected folder!")
            return
        
        # Stop existing preview
        if self.preview_process and self.preview_process.is_alive():
            self.preview_process.terminate()
            time.sleep(0.5)
        
        # Get selected device size
        selected_preset = self.preview_size.get()
        if selected_preset == "Custom Size":
            # Open custom size dialog
            custom_dialog = ctk.CTkToplevel(self.root)
            custom_dialog.title("Custom Preview Size")
            custom_dialog.geometry("300x200")
            custom_dialog.transient(self.root)
            custom_dialog.grab_set()
            
            ctk.CTkLabel(custom_dialog, text="Width:", font=("Arial", 12)).pack(pady=(20, 5))
            width_var = ctk.StringVar(value="800")
            width_entry = ctk.CTkEntry(custom_dialog, textvariable=width_var,)
            width_entry.pack(pady=5)
            
            ctk.CTkLabel(custom_dialog, text="Height:", font=("Arial", 12)).pack(pady=(10, 5))
            height_var = ctk.StringVar(value="600")
            height_entry = ctk.CTkEntry(custom_dialog, textvariable=height_var)
            height_entry.pack(pady=5)
            
            def confirm_custom():
                try:
                    width = int(width_var.get())
                    height = int(height_var.get())
                    if width < 100 or height < 100:
                        messagebox.showwarning("Invalid Size", "Minimum size is 100x100")
                        return
                    device_size = (width, height)
                    custom_dialog.destroy()
                    self._launch_preview(html_path, device_size)
                except ValueError:
                    messagebox.showerror("Invalid Input", "Please enter valid numbers")
            
            ctk.CTkButton(custom_dialog, text="Launch Preview", command=confirm_custom).pack(pady=20)
            
        else:
            device_size = DEVICE_PRESETS[selected_preset]
            self._launch_preview(html_path, device_size)
    
    def _launch_preview(self, html_path, device_size):
        """Internal method to launch the preview in a separate process"""
        self.log(f"Launching HTML preview with size: {device_size}", "info")
        
        # Start preview in a separate process
        self.preview_process = multiprocessing.Process(
            target=run_webview_preview,
            args=(html_path, device_size, f"{self.app_name.get()} - Preview"),
            daemon=True
        )
        self.preview_process.start()
        
        self.status.set("Preview launched")
        self.log("HTML preview window opened. Changes will auto-reload.", "success")
    
    def on_closing(self):
        """Handle window close event"""
        # Terminate preview process if running
        if self.preview_process and self.preview_process.is_alive():
            self.preview_process.terminate()
            time.sleep(0.5)
        
        # Cancel build if in progress
        if self.is_building:
            self.cancel_build()
            
        self.save_window_geometry()
        self.root.destroy()

    def build_ui(self):
        ctk.CTkLabel(
            self.root,
            text="HTML → APK Builder",
            font=("Segoe UI", 26, "bold")
        ).pack(pady=10)

        main_container = ctk.CTkFrame(self.root)
        main_container.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Configure grid weights for main container
        main_container.grid_columnconfigure(0, weight=1)  # Left panel gets all extra space
        main_container.grid_columnconfigure(1, weight=0)  # Right panel fixed width
        
        left_main = ctk.CTkFrame(main_container)
        left_main.grid(row=0, column=0, sticky="nsew", padx=(0, 20), pady=0)

        right_main = ctk.CTkFrame(main_container)
        right_main.grid(row=0, column=1, sticky="ns", padx=(0, 0), pady=0)
        
        # Set fixed width for right panel based on content
        right_main.configure(width=280)  # Adjust this value as needed
        
        # Configure main container row weight
        main_container.grid_rowconfigure(0, weight=1)

        upper_frame = ctk.CTkFrame(left_main, height=40)
        upper_frame.pack(fill="x", side="top", expand=True, padx=(20, 20), pady=(10, 0))

        middle_frame = ctk.CTkFrame(left_main, height=50)
        middle_frame.pack(fill="x", side="top", expand=True, padx=(20, 20), pady=10)

        # Create progress bar with determinate mode
        self.progress = ctk.CTkProgressBar(left_main, mode="determinate")
        self.progress.set(0)  # Start at 0%
        self.progress.pack(fill="x", padx=20, pady=(0, 10))

        bottom_frame = ctk.CTkFrame(left_main)
        bottom_frame.pack(fill="both", side="bottom", expand=True, padx=(20, 20), pady=(0, 10))

        left_frame = ctk.CTkFrame(upper_frame)
        left_frame.pack(side="left", fill="both", expand=True, pady=10, padx=(10, 10))
        left_frame.grid_columnconfigure(1, weight=1)
        
        right_frame = ctk.CTkFrame(upper_frame, width=200)
        right_frame.pack(side="right", fill="y", padx=(10, 10), pady=10)
        
        def field(label, var, row, browse=False, file=False):
            ctk.CTkLabel(
                left_frame,
                text=label
            ).grid(
                row=row,
                column=0,
                pady=6,
                padx=(20, 5),
                sticky="w"
            )

            entry = ctk.CTkEntry(
                left_frame,
                textvariable=var
            )
            entry.grid(
                row=row,
                column=1,
                pady=6,
                sticky="ew",
                padx=(0, 10)
            )

            if browse:
                ctk.CTkButton(
                    left_frame,
                    text="Browse",
                    width=80,
                    command=lambda: self.browse_file(var) if file else self.browse_dir(var)
                ).grid(
                    row=row,
                    column=2,
                    padx=(0, 10)
                )

        # App Name field
        field("App Name", self.app_name, 0)
        
        # App ID field
        field("App ID", self.app_id, 1)
        
        # HTML Folder field
        field("HTML Folder", self.html_path, 2, True)
        
        # App Icon field - Using PlaceholderEntry instead of standard CTkEntry
        ctk.CTkLabel(
            left_frame,
            text="App Icon (png)"
        ).grid(
            row=3,
            column=0,
            pady=6,
            padx=(20, 5),
            sticky="w"
        )
        
        # Use PlaceholderEntry for icon
        self.icon_entry = PlaceholderEntry(
            left_frame,
            placeholder="Optional (uses default)",
            placeholder_color="gray",
            width=250
        )
        self.icon_entry.grid(
            row=3,
            column=1,
            pady=6,
            sticky="ew",
            padx=(0, 10)
        )

        # Add binding to update preview when text changes
        def on_icon_text_change(event):
            self.update_icon_preview()
            
        self.icon_entry.bind("<KeyRelease>", on_icon_text_change)
        self.icon_entry.bind("<FocusOut>", on_icon_text_change)
        
        # Browse button for icon
        ctk.CTkButton(
            left_frame,
            text="Browse",
            width=80,
            command=lambda: self.browse_file(self.icon_path)
        ).grid(
            row=3,
            column=2,
            padx=(0, 10)
        )
        
        # Output Folder field
        field("Output Folder", self.output_path, 4, True)

        # Version and Version Code fields
        ctk.CTkLabel(left_frame, text="Version").grid(
            row=5, column=0, padx=(20, 5), pady=6, sticky="w"
        )
        version_entry = ctk.CTkEntry(left_frame, textvariable=self.version)
        version_entry.grid(row=5, column=1, pady=6, sticky="ew", padx=(0, 10))

        ctk.CTkLabel(left_frame, text="Version Code").grid(
            row=6, column=0, padx=(20, 5), pady=6, sticky="w"
        )
        version_code_entry = ctk.CTkEntry(left_frame, textvariable=self.version_code)
        version_code_entry.grid(row=6, column=1, pady=6, sticky="ew", padx=(0, 10))
        
        ctk.CTkCheckBox(right_main, text="Fullscreen", variable=self.fullscreen, width=250).pack(side="top", fill="x", padx=10, pady=10)
        ctk.CTkCheckBox(right_main, text="Internet Access", variable=self.internet, width=250).pack(side="top", fill="x", padx=10, pady=10)

        # Update orientation frame to have fixed width
        orientation_frame = ctk.CTkFrame(right_main)
        orientation_frame.pack(pady=6, padx=(10, 10), fill="x")
        
        ctk.CTkLabel(orientation_frame, text="Orientation").pack(
            padx=(5, 5), pady=6, side="left"
        )
        orientation_values = list(ORIENTATION_OPTIONS.values())
        orientation_menu = ctk.CTkOptionMenu(
            orientation_frame,
            values=orientation_values,
            variable=self.orientation_display,
            command=self.on_orientation_change,
            width=180
        )
        orientation_menu.pack(pady=6, padx=(5, 5), side="left")

        # Icon preview on the right frame
        self.text = ctk.CTkLabel(right_frame, text="Default Icon Preview", font=('arial', 15))
        self.text.pack(pady=(15, 0))
        
        icon_container = ctk.CTkFrame(right_frame)
        icon_container.pack(expand=True, fill="both", padx=20, pady=10)
        
        self.icon_preview = ctk.CTkLabel(icon_container, text="")
        self.icon_preview.pack(expand=True, padx=30)

        # Update preview frame to have fixed width
        preview_frame = ctk.CTkFrame(right_main)
        preview_frame.pack(side="top", padx=10, pady=10, fill="x")
        
        ctk.CTkLabel(preview_frame, text="Preview:").pack(side="left", padx=(10, 5), pady=10)
        preview_options = list(DEVICE_PRESETS.keys())
        preview_menu = ctk.CTkOptionMenu(
            preview_frame, 
            values=preview_options,
            variable=self.preview_size, 
            width=180
        )
        preview_menu.pack(side="left", padx=(0, 10), pady=10)
        
        # Update preview button to have fixed width
        ctk.CTkButton(
            right_main, 
            text="Preview HTML", 
            width=250,
            command=self.preview_html
        ).pack(side="top", padx=10, pady=10)
        
        # Add a separator
        separator = ctk.CTkFrame(right_main, height=2, fg_color="gray25")
        separator.pack(fill="x", padx=10, pady=5)
        
        # Add some space at the bottom
        ctk.CTkLabel(right_main, text="").pack(side="bottom", pady=10)

        btn_frame = ctk.CTkFrame(middle_frame)
        btn_frame.pack()
        
        self.build_btn = ctk.CTkButton(
            btn_frame,
            text="BUILD APK",
            height=45,
            width=200,
            font=("Segoe UI", 16, "bold"),
            command=self.start_build
        )
        self.build_btn.pack(side="left", padx=10,pady=5)

        ctk.CTkButton(
            btn_frame,
            text="CLEAR LOG",
            height=45,
            width=140,
            font=("Segoe UI", 14),
            fg_color="#444",
            hover_color="#666",
            command=self.clear_log
        ).pack(side="left", padx=10,pady=5)

        self.status = ctk.StringVar(value="Idle")
        ctk.CTkLabel(bottom_frame, textvariable=self.status,font=("Times new roman", 18)).pack(pady=5)

        # Log box
        self.log_box = ctk.CTkTextbox(bottom_frame, wrap="word")
        self.log_box.pack(fill="both", expand=True, padx=10, pady=(5,5))
        self.log_box.configure(state="disabled")
        self.log_box.tag_config("info", foreground="#8ab4f8")
        self.log_box.tag_config("success", foreground="#00e676")
        self.log_box.tag_config("error", foreground="#ff5252")
        self.log_box.tag_config("warning", foreground="#ffb300")
       
# ---------------- START ----------------
if __name__ == "__main__":
    # Make sure multiprocessing works properly on Windows
    if sys.platform.startswith('win'):
        multiprocessing.freeze_support()
    
    root = ctk.CTk()
    app = HTMLToAPKBuilderPRO(root)
    root.mainloop()