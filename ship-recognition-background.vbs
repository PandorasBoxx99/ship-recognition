' Ship Recognition Platform — Silent Background Starter
' Startet den Server unsichtbar im Hintergrund (kein CMD-Fenster).
' Kann im Windows Autostart abgelegt werden.

Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "C:\Projects\ship-scraper"

If CreateObject("Scripting.FileSystemObject").FileExists("C:\Projects\ship-venv\Scripts\pythonw.exe") Then
    WshShell.Run "C:\Projects\ship-venv\Scripts\pythonw.exe run.py", 0, False
Else
    WshShell.Run "pythonw run.py", 0, False
End If
