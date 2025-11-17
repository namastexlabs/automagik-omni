; Custom NSIS installer script for Automagik Omni
; Sets custom installation directory

; Override the default installation directory
!macro customInstall
  ; Add Windows Firewall rule to allow WSL/Docker to reach the backend
  ; This is required when Evolution API runs in WSL Docker
  DetailPrint "Adding Windows Firewall rule for port 8882..."
  nsExec::ExecToLog 'netsh advfirewall firewall delete rule name="Automagik Omni - WSL Access"'
  nsExec::ExecToLog 'netsh advfirewall firewall add rule name="Automagik Omni - WSL Access" dir=in action=allow protocol=TCP localport=8882 interfacetype=any profile=any'
  Pop $0
  ${If} $0 == 0
    DetailPrint "Firewall rule added successfully"
  ${Else}
    DetailPrint "Warning: Failed to add firewall rule (code: $0)"
  ${EndIf}
!macroend

; Called when initializing the installer
!macro preInit
  ; Set the default installation directory using registry
  ; This is the proper way according to electron-builder documentation
  SetRegView 64
  WriteRegExpandStr HKLM "${INSTALL_REGISTRY_KEY}" InstallLocation "$LOCALAPPDATA\Programs\Automagik"
  WriteRegExpandStr HKCU "${INSTALL_REGISTRY_KEY}" InstallLocation "$LOCALAPPDATA\Programs\Automagik"
  SetRegView 32
  WriteRegExpandStr HKLM "${INSTALL_REGISTRY_KEY}" InstallLocation "$LOCALAPPDATA\Programs\Automagik"
  WriteRegExpandStr HKCU "${INSTALL_REGISTRY_KEY}" InstallLocation "$LOCALAPPDATA\Programs\Automagik"
!macroend

; Called during uninstallation
!macro customUnInstall
  ; Remove Windows Firewall rule
  DetailPrint "Removing Windows Firewall rule..."
  nsExec::ExecToLog 'netsh advfirewall firewall delete rule name="Automagik Omni - WSL Access"'
  Pop $0
  ${If} $0 == 0
    DetailPrint "Firewall rule removed successfully"
  ${Else}
    DetailPrint "Note: Firewall rule may not exist or require manual removal"
  ${EndIf}
!macroend
