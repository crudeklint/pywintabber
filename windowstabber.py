import tkinter as tk
from tkinter import ttk
from tkinter import font as tkfont
import win32gui

class WinTabber():

	tabs = []
	hwndlist = {}
	captured_hwnds = []
	pre_rect = [0,0,0,0]
	
	SKIPLIST = [
		"Microsoft Text Input Application",
		"Program Manager",
		"Microsoft Store"
		]

	def __init__( self ):
		self.gui_show()
		return

	def getallwins( self ):
		win32gui.EnumWindows( self.winEnumHandler, None )
		
		return self.hwndlist

	def winEnumHandler( self, hwnd, ctx ):
		if win32gui.IsWindowVisible( hwnd ):
			# print (hex(hwnd), win32gui.GetWindowText( hwnd ))
			self.hwndlist[hwnd] = win32gui.GetWindowText( hwnd )

	def win_intersects( self, main_win_rect, test_win_rect ):
		a = main_win_rect
		b = test_win_rect
		
		if( a[0] > b[2] or a[1] > b[3] or a[2] < b[0] or a[3] < b[1] ):
			return False
		else: 
			return True
		
	def win_is_inside( self, main_win_rect, test_win_rect ):
		a = main_win_rect
		b = test_win_rect
		
		if( a[0] < b[0] and a[1] < b[1] and a[2] > b[2] and a[3] > b[3] ):
			return True
		else:
			return False

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

			name = hwnds[hwnd]
			if( hwnd == this_hwnd or name in self.SKIPLIST):
				continue
			
			if( self.win_is_inside( a, b ) ):
				# print( name + " is contained in me" )
				print( hwnd )
			elif( self.win_intersects( a, b ) ):
				print( name + " intersects me" )
					
		
		self.update_win_position( 1 )
		
		# print( win_coords )


	def update_win_position( self, hwnd ):
		hwnd = 264456

		root = self.root
		
		win_coords = (
			root.winfo_x(), 
			root.winfo_y(),
			root.winfo_width(),
			root.winfo_height()
		)

		a = win_coords
		win32gui.MoveWindow( hwnd, a[0]+5, a[1]+a[3]+30, a[2]+5, 200, 1 )
		# win32gui.SetForegroundWindow( hwnd )
		return


	def configure_cb( self, event ):
		pre_rect = self.pre_rect

		# if event.widget.widgetName == "toplevel":
		rect = [event.x, event.y, event.width, event.height]
	
		for i in range( 0, 4 ):
			if( rect[i] != pre_rect[i] ):
				self.update_win_position( 1 )
				return

		
		

	def gui_show( self ):
		root = tk.Tk()
		self.root = root
		tabs = self.tabs
		
		root.geometry( "800x75" )
		root.title("Tab Widget") 
		
		# bgcol = ttk.Style()
		# bgcol.configure( "TFrame", background="red" )
		
		button_font = tkfont.Font( size=12 )
		
		top_frame = ttk.Frame( root, height=50, padding=10 )
		bottom_frame = ttk.Frame( root )

		capture_button = tk.Button( top_frame, text="Capture active window", font=button_font, command=self.get_captured_windows )
		capture_button.grid( row=0, column=0, sticky="nsew" )
		top_frame.columnconfigure( 0, weight=1 )
		
		top_frame.grid( row=0, column=0, sticky="nsew" )
		bottom_frame.grid( row=1, column=0, sticky="nsew" )

		root.columnconfigure( 0, weight=1 )
		root.rowconfigure( 1, weight=1 )
		
		tabControl = ttk.Notebook(bottom_frame) 
		
		tabs.append( ttk.Frame(tabControl) )
		  
		tabControl.add(tabs[0], text ='Add windows') 
		tabControl.pack(expand = 1, fill ="both") 
		  
		ttk.Label(tabs[0],  
				  text ="Welcome to GeeksForGeeks").grid(column = 0,  
									   row = 0, 
									   padx = 30, 
									   pady = 30)   
		
		root.bind( "<Configure>", self.configure_cb )
		
		root.mainloop()

		return

if( __name__ == "__main__" ):
	thisGui = WinTabber()
