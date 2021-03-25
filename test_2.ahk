;@Ahk2Exe-ConsoleApp

#singleInstance, Force

DetectHiddenWindows, On
Script_Hwnd := WinExist("ahk_class AutoHotkey ahk_pid " DllCall("GetCurrentProcessId"))
DllCall("RegisterShellHookWindow", "uint", Script_Hwnd)
OnMessage(DllCall("RegisterWindowMessage", "str", "SHELLHOOK"), "ShellEvent")

ShellEvent(wParam, lParam) {
    if (wParam = 0x8006) ; HSHELL_FLASH
    {
        FileAppend, %lParam%`n, *
    }

	return
}

ExitFunction() {
	FileAppend, Deregistering hook`n, *
	DllCall("DeregisterShellHookWindow", "uint", Script_Hwnd)
	FileAppend, Quitting`n, *
	return
}

OnExit("ExitFunction")