[app]
title = TEG La Revancha
package.name = teglarevancha
package.domain = org.tegrevancha.offline
source.dir = .
source.include_exts = py,png,jpg,jpeg,kv,ttf,json
source.exclude_dirs = reference,desktop_reference,tests,.github,__pycache__,.buildozer,bin
version = 0.1.0
requirements = python3,kivy==2.3.1
orientation = landscape
fullscreen = 1
android.api = 35
android.minapi = 24
android.archs = arm64-v8a
android.accept_sdk_license = True
android.presplash_color = #0C1727
# Intencionalmente NO se solicitan permisos; la aplicación funciona offline.
# android.permissions =

[buildozer]
log_level = 2
warn_on_root = 1
