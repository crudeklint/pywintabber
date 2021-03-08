import tkinter as tk
import win32gui

class WinTabber():

	HWNDLIST = {}
	SKIPLIST = [
		"Microsoft Text Input Application",
		"Program Manager"
		]

	def __init__( self ):
		self.gui_show()
		return

	def getallwins( self ):
		win32gui.EnumWindows( self.winEnumHandler, None )
		
		return self.HWNDLIST

	def winEnumHandler( self, hwnd, ctx ):
		if win32gui.IsWindowVisible( hwnd ):
			# print (hex(hwnd), win32gui.GetWindowText( hwnd ))
			self.HWNDLIST[hwnd] = win32gui.GetWindowText( hwnd )

	def get_captured_windows( self ):
		root = self.root
	
		hwnds = self.getallwins()
		win_coords = (
			root.winfo_x(), 
			root.winfo_y(),
			root.winfo_width()+root.winfo_x(),
			root.winfo_height()+root.winfo_y()
		)
		
		a = win_coords
		this_hwnd = int( root.frame(), 16 )
		
		for hwnd in hwnds:
			b = win32gui.GetWindowRect( hwnd )
			
			if( a[0] > b[2] or a[1] > b[3] or a[2] < b[0] or a[3] < b[1] ):
				continue
			
			name = hwnds[hwnd]
			
			if( hwnd == this_hwnd or name in self.SKIPLIST):
				continue
			
			if( name == "tk" ):
				print( hwnd )
				print( this_hwnd )
				print()
			
			print( name )
			
				
		
		
		# print( win_coords )

	def gui_show( self ):
		root = tk.Tk()
		self.root = root
		
		root.geometry( "400x300" )

		button = tk.Button( root, text="test", command=self.get_captured_windows )
		button.grid( row=0, column=0 )

		root.mainloop()

		return

if( __name__ == "__main__" ):
	thisGui = WinTabber()
