; Windows installer borrowed from editra

; HM NIS Edit Wizard helper defines
!define PRODUCT_NAME "peppy"
!define PRODUCT_VERSION "0.16.0"
!define PRODUCT_PUBLISHER "Rob McMullen"
!define PRODUCT_WEB_SITE "http://peppy.flipturn.org/"
!define PRODUCT_DIR_REGKEY "Software\Microsoft\Windows\CurrentVersion\App Paths\peppy.exe"
!define PRODUCT_UNINST_KEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}"
!define PRODUCT_UNINST_ROOT_KEY "HKLM"

SetCompressor lzma

; MUI 1.67 compatible ------
!include "MUI.nsh"

; MUI Settings
!define MUI_ABORTWARNING
!define MUI_ICON "peppy48.ico"
!define MUI_UNICON "peppy48.ico"

; Welcome page
!insertmacro MUI_PAGE_WELCOME
; License page
!insertmacro MUI_PAGE_LICENSE "..\LICENSE.v3"
; Directory page
!insertmacro MUI_PAGE_DIRECTORY
; Instfiles page
!insertmacro MUI_PAGE_INSTFILES
; Finish page
!define MUI_FINISHPAGE_RUN
!define MUI_FINISHPAGE_RUN_TEXT "Run peppy"
!define MUI_FINISHPAGE_RUN_FUNCTION "LaunchProg"
!insertmacro MUI_PAGE_FINISH

; Uninstaller pages
!insertmacro MUI_UNPAGE_INSTFILES

; Language files
!insertmacro MUI_LANGUAGE "English"

; Reserve files
!insertmacro MUI_RESERVEFILE_INSTALLOPTIONS

; MUI end ------

Name "${PRODUCT_NAME} ${PRODUCT_VERSION}"
OutFile "peppy-0.16.0-win32.exe"
InstallDir "$PROGRAMFILES\peppy"
InstallDirRegKey HKLM "${PRODUCT_DIR_REGKEY}" ""
ShowInstDetails show
ShowUnInstDetails show

; Section "MainSection" SEC01
;   FindProcDLL::FindProc "peppy.exe"
;   StrCmp $R0 0 continueInstall
;     MessageBox MB_ICONSTOP|MB_OK "${PRODUCT_NAME} is still running please close all running instances and try to install again"
;     Abort
;   continueInstall:
; SectionEnd

Section "MainSection" SEC02
  SetOverwrite try
  SetOutPath "$INSTDIR\"
  File /r "..\dist\*.*"
  CreateDirectory "$SMPROGRAMS\peppy"
  CreateShortCut "$SMPROGRAMS\peppy\peppy.lnk" "$INSTDIR\peppy.exe"
  CreateShortCut "$DESKTOP\peppy.lnk" "$INSTDIR\peppy.exe"
SectionEnd

Section -AdditionalIcons
  WriteIniStr "$INSTDIR\${PRODUCT_NAME}.url" "InternetShortcut" "URL" "${PRODUCT_WEB_SITE}"
  CreateShortCut "$SMPROGRAMS\peppy\Website.lnk" "$INSTDIR\${PRODUCT_NAME}.url"
  CreateShortCut "$SMPROGRAMS\peppy\Uninstall.lnk" "$INSTDIR\uninst.exe"
SectionEnd

Section -Post
  WriteUninstaller "$INSTDIR\uninst.exe"
  WriteRegStr HKLM "${PRODUCT_DIR_REGKEY}" "" "$INSTDIR\peppy.exe"
  WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "DisplayName" "$(^Name)"
  WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "UninstallString" "$INSTDIR\uninst.exe"
  WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "DisplayIcon" "$INSTDIR\peppy.exe"
  WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "DisplayVersion" "${PRODUCT_VERSION}"
  WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "URLInfoAbout" "${PRODUCT_WEB_SITE}"
  WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "Publisher" "${PRODUCT_PUBLISHER}"
SectionEnd

; Functions
Function LaunchProg
  Exec '"$INSTDIR\peppy.exe"'
FunctionEnd

Function un.onUninstSuccess
  HideWindow
  MessageBox MB_ICONINFORMATION|MB_OK "$(^Name) was successfully removed from your computer."
FunctionEnd

Function un.onInit
  MessageBox MB_ICONQUESTION|MB_YESNO|MB_DEFBUTTON2 "Are you sure you want to completely remove $(^Name) and all of its components?" IDYES +2
  Abort
FunctionEnd

Section Uninstall
  RmDir /r "$INSTDIR\"
  Delete "$SMPROGRAMS\peppy\Uninstall.lnk"
  Delete "$SMPROGRAMS\peppy\Website.lnk"
  Delete "$DESKTOP\peppy.lnk"
  Delete "$SMPROGRAMS\peppy\peppy.lnk"
  RMDir "$SMPROGRAMS\peppy"
  DeleteRegKey ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}"
  DeleteRegKey HKLM "${PRODUCT_DIR_REGKEY}"
  SetAutoClose true
SectionEnd

