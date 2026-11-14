Unicode true
!include "MUI2.nsh"
!include "nsDialogs.nsh"
!include "LogicLib.nsh"
Name "UMS Control"
OutFile "${OUTPUT}"
InstallDir "$LOCALAPPDATA\Programs\UMS Control"
RequestExecutionLevel user
SetCompressor /SOLID lzma
!define MUI_ABORTWARNING
!define MUI_ICON "..\assets\windows\ums-control.ico"
!define MUI_UNICON "..\assets\windows\ums-control.ico"
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "..\LICENSE"
Page custom LanguagePage LanguageLeave
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_LANGUAGE "English"
Var Dialog
Var LanguageBox
Var SelectedLanguage
Function LanguagePage
 nsDialogs::Create 1018
 Pop $Dialog
 ${If} $Dialog == error
  Abort
 ${EndIf}
 ${NSD_CreateLabel} 0 0 100% 28u "Select the language for the first launch of UMS Control."
 Pop $0
 ${NSD_CreateLabel} 0 30u 100% 30u "The language can also be changed later from the Language menu in the program. Existing user preferences are preserved."
 Pop $0
 ${NSD_CreateDropList} 0 70u 100% 100u ""
 Pop $LanguageBox
 ${NSD_CB_AddString} $LanguageBox "English [en]"
 ${NSD_CB_AddString} $LanguageBox "Spanish [es]"
 ${NSD_CB_AddString} $LanguageBox "French [fr]"
 ${NSD_CB_AddString} $LanguageBox "German [de]"
 ${NSD_CB_AddString} $LanguageBox "Italian [it]"
 ${NSD_CB_AddString} $LanguageBox "Chinese [zh]"
 ${NSD_CB_AddString} $LanguageBox "Japanese [ja]"
 ${NSD_CB_SelectString} $LanguageBox "English [en]"
 nsDialogs::Show
FunctionEnd
Function LanguageLeave
 ${NSD_GetText} $LanguageBox $0
 StrCpy $SelectedLanguage $0 2 -3
FunctionEnd
Section "UMS Control"
 SetShellVarContext current
 SetOutPath "$INSTDIR"
 File /r "${PAYLOAD}\*"
 ${If} $SelectedLanguage == ""
  StrCpy $SelectedLanguage "en"
 ${EndIf}
 FileOpen $0 "$INSTDIR\_internal\first-language.json" w
 FileWrite $0 '{$\"language$\":$\"$SelectedLanguage$\"}'
 FileClose $0
 CreateDirectory "$SMPROGRAMS\UMS Control"
 CreateShortcut "$SMPROGRAMS\UMS Control\UMS Control.lnk" "$INSTDIR\UMS-Control.exe" "" "$INSTDIR\UMS-Control.exe" 0
 WriteUninstaller "$INSTDIR\Uninstall.exe"
 WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\UMS Control" "DisplayName" "UMS Control"
 WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\UMS Control" "DisplayVersion" "1.0.0"
 WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\UMS Control" "Publisher" "N3ruk"
 WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\UMS Control" "DisplayIcon" '$\"$INSTDIR\UMS-Control.exe$\",0'
 WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\UMS Control" "UninstallString" '$\"$INSTDIR\Uninstall.exe$\"'
SectionEnd
Section "Uninstall"
 SetShellVarContext current
 ; Stop only our tracked process and disable our own session autostart.
 ExecWait '$\"$INSTDIR\UMS-Control.exe$\" --uninstall-panel' $0
 ${If} $0 != 0
  MessageBox MB_ICONSTOP "The managed server could not be stopped. Close UMS Control and retry. The application has not been removed."
  Abort
 ${EndIf}
 Delete "$SMPROGRAMS\UMS Control\UMS Control.lnk"
 RMDir "$SMPROGRAMS\UMS Control"
 DeleteRegKey HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\UMS Control"
 ; Remove only generated package payload; user settings/media are outside this directory.
 !include "${REMOVE_FILES}"
 Delete "$INSTDIR\Uninstall.exe"
 RMDir "$INSTDIR"
SectionEnd
