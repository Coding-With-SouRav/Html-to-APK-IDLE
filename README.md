# Html-to-APK-IDLE

## demo images

<img width="1439" height="922" alt="image" src="https://github.com/user-attachments/assets/c911f6b4-a53e-428b-a8e7-eb230b4d6105" />

### **Core Features:**
- 📱 **Convert HTML/Web projects to Android APK**
- 🎨 **Graphical interface** with dark theme support
- 📁 **Local environment management**: Auto-detects and configures Cordova, JDK, Gradle, Android SDK
- 👁️ **Live preview**: Preview HTML in selected device sizes with hot reload
- ⚙️ **Highly configurable**:
  - App name, package ID, version
  - Screen orientation (with sensor rotation support)
  - Fullscreen mode, internet permissions
  - Custom app icons
- 🛠️ **Build control**:
  - Progress tracking with stages
  - Cancelable builds
  - Automatic cleanup of temporary files
- 📄 **Logging system**: Color-coded messages for info, warnings, errors, and success

### **Technical Architecture:**
- Uses **Apache Cordova** as the build engine
- Supports both **local dependencies** (bundled in app) or system-wide tools
- Multiprocessing for preview and build operations
- Cross-platform (Windows, macOS, Linux compatible)
- Saves and restores window state/configurations

### **Target Users:**
- Web developers wanting to convert websites/web apps to Android APKs
- Educators and rapid prototyping
- Users needing lightweight APK building without Android Studio

### **Key Workflow:**
1. Select HTML folder containing `index.html`
2. Configure app metadata and settings
3. Preview in simulated device sizes
4. Build APK using Cordova with progress tracking
5. Output signed APK file

This is an **all-in-one APK packaging tool** ideal for frontend developers or anyone needing to quickly generate Android install packages from web content without complex Android development setup.


<!-- AUTO UPDATE -->
Last maintenance: 2026-08-06 07:15 UTC
