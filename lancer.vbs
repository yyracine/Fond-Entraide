' lancer.vbs — démarre le Fonds d'Entraide SANS fenêtre de console noire.
'
' Utilise pythonw.exe (l'interpréteur Python sans console) sur app.py.
' Le dossier courant est fixé sur le dossier du script, mais db.py résout
' déjà ses chemins via __file__ : la base reste familles.db du projet.
'
' Double-clic sur ce fichier = l'application se lance avec son icône
' (relation.ico) dans la barre des tâches.
'
' Si Python n'est pas dans le PATH, décommentez la ligne CANDIDATS ci-dessous
' avec le chemin complet de votre pythonw.exe.

Option Explicit

Dim fso, shell, dossier, pythonw, script, cmd
Set fso = CreateObject("Scripting.FileSystemObject")
Set shell = CreateObject("WScript.Shell")

' Dossier de ce script (le dossier du projet)
dossier = fso.GetParentFolderName(WScript.ScriptFullName)
script = fso.BuildPath(dossier, "app.py")

If Not fso.FileExists(script) Then
    MsgBox "app.py est introuvable à côté de ce raccourci :" & vbCrLf & _
           script, vbCritical, "Fonds d'Entraide"
    WScript.Quit 1
End If

' --- trouver pythonw.exe : PATH d'abord, sinon emplacements courants ---
pythonw = ""

' 1) pythonw.exe présent dans le PATH ?
Dim valeurs, v, i
valeurs = Split(shell.ExpandEnvironmentStrings("%PATH%"), ";")
For i = 0 To UBound(valeurs)
    v = valeurs(i)
    If Len(v) > 0 Then
        If fso.FileExists(fso.BuildPath(v, "pythonw.exe")) Then
            pythonw = fso.BuildPath(v, "pythonw.exe")
            Exit For
        End If
    End If
Next

' 2) sinon, emplacements d'installation courants
If pythonw = "" Then
    Dim candidats, c
    candidats = Array( _
        shell.ExpandEnvironmentStrings("%LOCALAPPDATA%\Programs\Python\Python313\pythonw.exe"), _
        shell.ExpandEnvironmentStrings("%LOCALAPPDATA%\Programs\Python\Python312\pythonw.exe"), _
        shell.ExpandEnvironmentStrings("%LOCALAPPDATA%\Programs\Python\Python311\pythonw.exe"), _
        shell.ExpandEnvironmentStrings("%LOCALAPPDATA%\Programs\Python\Python310\pythonw.exe"), _
        "C:\Program Files\Python313\pythonw.exe", _
        "C:\Program Files\Python312\pythonw.exe", _
        "C:\Program Files\Python311\pythonw.exe", _
        "C:\Program Files\Python310\pythonw.exe")
    For Each c In candidats
        If fso.FileExists(c) Then
            pythonw = c
            Exit For
        End If
    Next
End If

If pythonw = "" Then
    MsgBox "Python (pythonw.exe) est introuvable." & vbCrLf & vbCrLf & _
           "Installez Python depuis python.org, ou éditez lancer.vbs " & _
           "pour indiquer le chemin complet de pythonw.exe.", _
           vbCritical, "Fonds d'Entraide"
    WScript.Quit 1
End If

' Lancement : dossier du projet comme répertoire courant, app.py en argument.
shell.CurrentDirectory = dossier
cmd = """" & pythonw & """ """ & script & """"
' 0 = fenêtre masquée, False = ne pas attendre la fin
shell.Run cmd, 0, False
