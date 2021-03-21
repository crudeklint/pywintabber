gui, new,, test window
gui, add, button, gblinkme, Blinka
gui, show, w300 h200

blinkme() {
	loop, 6 
	{
		gui, flash
		Sleep 500
	}
}