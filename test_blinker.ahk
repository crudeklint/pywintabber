Gui, add, edit, vhwnd
Gui, add, button, gblinker, Blink!
Gui, show, h300 w300
return

blinker() {
	GuiControlGet, value,, hwnd
	DllCall( "FlashWindow", UInt, value, Int,True )

}

blinkme() {
	loop, 6 
	{
		gui, flash
		Sleep 500
	}
}