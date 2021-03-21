;@Ahk2Exe-ConsoleApp

#SingleInstance, Force
#NoTrayIcon

loop
{
	fileAppend, %a_index%`n, *
	sleep, 1000
}

