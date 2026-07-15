[app]

# App identity
title = 4 Pics 1 Word
package.name = fourpicsoneword
package.domain = org.game
version = 1.0.0

# Source
source.dir = .
source.include_exts = py,png,jpg,kv,json,atlas

# App icon (512x512 PNG)
icon.filename = %(source.dir)s/icon.png

# Python / Kivy requirements
# Pin Python to 3.12.9 to avoid Python 3.14 C-API incompatibilities with
# Kivy 2.3.0 (specifically _PyLong_AsByteArray gained a 6th argument in 3.14)
requirements = python3==3.12.9,kivy==2.3.0,requests,pillow,certifi,charset-normalizer,idna,urllib3

# Orientation
orientation = portrait

# Android API levels  (target 33 = Android 13, min 21 = Android 5)
android.api    = 33
android.minapi = 21
android.ndk    = 25b
android.sdk    = 33
android.archs  = arm64-v8a, armeabi-v7a
android.accept_sdk_license = True

# Permissions
android.permissions = INTERNET, WRITE_EXTERNAL_STORAGE, READ_EXTERNAL_STORAGE

# Gradle  
android.gradle_dependencies =

# Build options
android.release_artifact = apk

[buildozer]
log_level = 2
warn_on_root = 1
