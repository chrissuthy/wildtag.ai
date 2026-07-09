' wildtag_launch.vbs
' Launches wildtag.ai with no console window at all.
' Uses pythonw.exe (the windowless Python interpreter) so there is no
' black cmd window that a user could accidentally close mid-run.
Set fso = CreateObject("Scripting.FileSystemObject")
Set sh  = CreateObject("WScript.Shell")

' Folder this script lives in (the wildtag.ai install folder)
here = fso.GetParentFolderName(WScript.ScriptFullName)
sh.CurrentDirectory = here

' Prefer the full runtime (wildtag_env); fall back to the volunteer
' runtime (validate_env). Prefer pythonw.exe (no console) but fall back
' to python.exe if a given env doesn't ship pythonw.
Dim candidates(5)
candidates(0) = here & "\wildtag_env\pythonw.exe"
candidates(1) = here & "\wildtag_env\Scripts\pythonw.exe"
candidates(2) = here & "\wildtag_env\python.exe"
candidates(3) = here & "\validate_env\pythonw.exe"
candidates(4) = here & "\validate_env\Scripts\pythonw.exe"
candidates(5) = here & "\validate_env\python.exe"
pyw = ""
For Each c In candidates
    If fso.FileExists(c) Then
        pyw = c
        Exit For
    End If
Next
If pyw = "" Then
    MsgBox "wildtag.ai could not find its Python runtime. The install may be incomplete.", 16, "wildtag.ai"
    WScript.Quit
End If

' Tcl/Tk env vars for the embeddable validate_env (harmless for wildtag_env)
sh.Environment("PROCESS")("TCL_LIBRARY") = here & "\validate_env\tcl\tcl8.6"
sh.Environment("PROCESS")("TK_LIBRARY")  = here & "\validate_env\tcl\tk8.6"

' Launch truly windowless via pythonw.exe (it has no console at all, so
' nothing can flash up or be accidentally closed). We don't wait; the GUI
' takes over from here.
On Error Resume Next
sh.Run """" & pyw & """ """ & here & "\wildtag.py""", 0, False
If Err.Number <> 0 Then
    MsgBox "wildtag.ai could not start:" & vbCrLf & Err.Description, 16, "wildtag.ai"
End If
On Error Goto 0
