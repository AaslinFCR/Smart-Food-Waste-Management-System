Set shell = CreateObject("WScript.Shell")
root = Left(WScript.ScriptFullName, InStrRev(WScript.ScriptFullName, "\\") - 1)
shell.Run "powershell.exe -ExecutionPolicy Bypass -File """ & root & "\run.ps1""", 0, False
