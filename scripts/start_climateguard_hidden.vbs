Option Explicit

' Keep the console hidden while the batch launcher manages the local server.
Dim shell, fileSystem, scriptFolder, batchPath
Set shell = CreateObject("WScript.Shell")
Set fileSystem = CreateObject("Scripting.FileSystemObject")
scriptFolder = fileSystem.GetParentFolderName(WScript.ScriptFullName)
batchPath = fileSystem.BuildPath(scriptFolder, "start_climateguard.bat")

shell.Run """" & batchPath & """", 0, False
