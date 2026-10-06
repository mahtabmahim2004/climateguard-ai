Option Explicit

' Recreate the current user's Desktop shortcut using paths relative to this script.
Dim shell, fileSystem, scriptFolder, projectRoot, hiddenLauncher, desktopPath, shortcut
Set shell = CreateObject("WScript.Shell")
Set fileSystem = CreateObject("Scripting.FileSystemObject")

scriptFolder = fileSystem.GetParentFolderName(WScript.ScriptFullName)
projectRoot = fileSystem.GetParentFolderName(scriptFolder)
hiddenLauncher = fileSystem.BuildPath(scriptFolder, "start_climateguard_hidden.vbs")
desktopPath = shell.SpecialFolders("Desktop")
Set shortcut = shell.CreateShortcut(fileSystem.BuildPath(desktopPath, "ClimateGuard AI.lnk"))

shortcut.TargetPath = shell.ExpandEnvironmentStrings("%SystemRoot%\System32\wscript.exe")
shortcut.Arguments = """" & hiddenLauncher & """"
shortcut.WorkingDirectory = projectRoot
shortcut.Description = "Start the local ClimateGuard AI research dashboard."
shortcut.IconLocation = shell.ExpandEnvironmentStrings("%SystemRoot%\System32\shell32.dll") & ",14"
shortcut.Save

shell.Popup "Desktop shortcut created: ClimateGuard AI", 4, "ClimateGuard AI", 64
