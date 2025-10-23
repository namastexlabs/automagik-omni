; Custom NSIS installer script for Automagik Omni
; This script adds custom behavior to the installer and uninstaller

; ==========================================
; CUSTOM INSTALL ACTIONS
; ==========================================
!macro customInstall
  ; Create application directories
  CreateDirectory "$INSTDIR\logs"
  CreateDirectory "$APPDATA\${PRODUCT_NAME}"
  CreateDirectory "$APPDATA\${PRODUCT_NAME}\backend"
  CreateDirectory "$APPDATA\${PRODUCT_NAME}\backend\logs"

  ; Set directory permissions
  AccessControl::GrantOnFile "$APPDATA\${PRODUCT_NAME}" "(S-1-5-32-545)" "FullAccess"

  ; Create desktop shortcut with custom icon
  CreateShortcut "$DESKTOP\${PRODUCT_NAME}.lnk" \
    "$INSTDIR\${PRODUCT_FILENAME}.exe" \
    "" \
    "$INSTDIR\${PRODUCT_FILENAME}.exe" 0 \
    SW_SHOWNORMAL \
    "" \
    "Automagik Omni - Multi-channel messaging platform"

  ; Create quick launch shortcut
  CreateShortcut "$QUICKLAUNCH\${PRODUCT_NAME}.lnk" \
    "$INSTDIR\${PRODUCT_FILENAME}.exe"

  ; Register file associations for .omni files (if needed in future)
  ; WriteRegStr HKCU "Software\Classes\.omni" "" "AutomagikOmniFile"
  ; WriteRegStr HKCU "Software\Classes\AutomagikOmniFile\DefaultIcon" "" "$INSTDIR\${PRODUCT_FILENAME}.exe,0"
  ; WriteRegStr HKCU "Software\Classes\AutomagikOmniFile\shell\open\command" "" '"$INSTDIR\${PRODUCT_FILENAME}.exe" "%1"'

  ; Register uninstaller in Windows Programs list
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}" \
    "DisplayName" "${PRODUCT_NAME}"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}" \
    "DisplayIcon" "$INSTDIR\${PRODUCT_FILENAME}.exe"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}" \
    "DisplayVersion" "${VERSION}"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}" \
    "Publisher" "Namastex Labs"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}" \
    "URLInfoAbout" "https://github.com/namastexlabs/automagik-omni"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}" \
    "UninstallString" "$INSTDIR\Uninstall.exe"

  ; Log successful installation
  FileOpen $0 "$APPDATA\${PRODUCT_NAME}\install.log" w
  FileWrite $0 "Installation completed successfully at: "
  FileWrite $0 "$INSTDIR"
  FileClose $0
!macroend

; ==========================================
; CUSTOM UNINSTALL ACTIONS
; ==========================================
!macro customUnInstall
  ; Ask user if they want to keep their data
  MessageBox MB_YESNO|MB_ICONQUESTION \
    "Do you want to keep your Automagik Omni data and settings?$\n$\nClick 'Yes' to keep your data, or 'No' to remove everything." \
    IDYES KeepData

  ; User chose to remove data
  RMDir /r "$APPDATA\${PRODUCT_NAME}"
  Goto AfterDataRemoval

  KeepData:
    ; Keep data but clean up logs
    RMDir /r "$APPDATA\${PRODUCT_NAME}\backend\logs"
    RMDir /r "$INSTDIR\logs"

  AfterDataRemoval:

  ; Remove shortcuts
  Delete "$DESKTOP\${PRODUCT_NAME}.lnk"
  Delete "$QUICKLAUNCH\${PRODUCT_NAME}.lnk"
  Delete "$SMPROGRAMS\${PRODUCT_NAME}\${PRODUCT_NAME}.lnk"
  Delete "$SMPROGRAMS\${PRODUCT_NAME}\Uninstall ${PRODUCT_NAME}.lnk"
  RMDir "$SMPROGRAMS\${PRODUCT_NAME}"

  ; Remove file associations
  ; DeleteRegKey HKCU "Software\Classes\.omni"
  ; DeleteRegKey HKCU "Software\Classes\AutomagikOmniFile"

  ; Remove uninstaller registry entry
  DeleteRegKey HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}"

  ; Final cleanup message
  MessageBox MB_OK "Automagik Omni has been successfully removed from your computer.$\n$\nThank you for using Automagik Omni!"
!macroend

; ==========================================
; CUSTOM WELCOME PAGE
; ==========================================
!macro customHeader
  ; Add custom branding and welcome message
  !system 'echo "Automagik Omni - Multi-channel Messaging Platform"'
  !system 'echo "Copyright © 2025 Namastex Labs"'
!macroend

; ==========================================
; CUSTOM INSTALLER INIT
; ==========================================
!macro customInit
  ; Check if app is already running
  System::Call 'kernel32::CreateMutex(i 0, i 0, t "AutomagikOmniMutex") i .r1 ?e'
  Pop $R0

  StrCmp $R0 0 +3
    MessageBox MB_OK|MB_ICONEXCLAMATION \
      "Automagik Omni is currently running. Please close it before installing." \
      /SD IDOK
    Abort
!macroend

; ==========================================
; CUSTOM UNINSTALLER INIT
; ==========================================
!macro customUnInit
  ; Check if app is running before uninstall
  System::Call 'kernel32::CreateMutex(i 0, i 0, t "AutomagikOmniMutex") i .r1 ?e'
  Pop $R0

  StrCmp $R0 0 +3
    MessageBox MB_OK|MB_ICONEXCLAMATION \
      "Automagik Omni is currently running. Please close it before uninstalling." \
      /SD IDOK
    Abort
!macroend

; ==========================================
; CUSTOM INSTALL MODE PAGE
; ==========================================
!macro customInstallMode
  ; Show custom installation mode selection if needed
  ; Currently using default per-user installation
!macroend
