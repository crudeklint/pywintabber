import tkinter as tk
from tkinter import ttk
from tkinter import font as tkfont
import win32gui, win32con

class WinTabber():

	tab_buttons = []
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
	
	def win_corner_inside( self, main_win_rect, test_win_rect ):
		a = main_win_rect
		b = test_win_rect

		if( a[0] > b[0] or a[1] > b[1] or a[2] < b[0] or a[3] < b[1] ):
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
			
			if( self.win_corner_inside( a, b ) and hwnd not in self.captured_hwnds ):
				# print( name + " is contained in me" )
				self.add_window( hwnd )
				return
				# print( hwnd )
			elif( self.win_intersects( a, b ) ):
				print( name + " intersects me" )
					
		
		# self.update_win_position( 1 )
		
		# print( win_coords )

	def add_window( self, hwnd ):
		tab_buttons = self.tab_buttons
		windowname = win32gui.GetWindowText( hwnd )
	
		self.captured_hwnds.append( hwnd )
		
		insert_index = 0 if( len( tab_buttons ) == 1 ) else 1
		new_button = tk.Button( self.top_frame, text=windowname, command=lambda: self.tab_cb( hwnd ) )
		
		tab_buttons.insert( insert_index, new_button )
		
		for i in range( 0, len( tab_buttons ) ):
			tab_buttons[i].grid( row=0, column=i, sticky="ns" )
			tab_buttons[i]
	
		return

	def tab_cb( self, hwnd ):
		win32gui.SetForegroundWindow( hwnd )
		return

	def update_wins_position( self ):
		root = self.root
		bottom_frame = self.bottom_frame
		
		win_coords = (
			bottom_frame.winfo_rootx(), 
			bottom_frame.winfo_rooty(),
			bottom_frame.winfo_width(),
			bottom_frame.winfo_height()
		)

		a = win_coords
		# win32gui.MoveWindow( hwnd, a[0]+10, a[1]+105, a[2]-5, a[3]-75, 1 )
		
		for hwnd in self.captured_hwnds:
			win32gui.SetWindowPos( hwnd, win32con.HWND_TOPMOST, a[0], a[1], a[2], a[3], int( "0x0010", 0 ) )
		# win32gui.MoveWindow( hwnd, a[0]+5, a[1]+a[3]+30, a[2]+5, 200, 1 )
		# win32gui.SetForegroundWindow( hwnd )
		return


	def configure_cb( self, event ):
		pre_rect = self.pre_rect

		# if event.widget.widgetName == "toplevel":
		rect = [event.x, event.y, event.width, event.height]
	
		for i in range( 0, 4 ):
			if( rect[i] != pre_rect[i] ):
				self.update_wins_position()
				return
		

	def gui_show( self ):
		root = tk.Tk()
		self.root = root
		tab_buttons = self.tab_buttons
		
		root.attributes("-transparentcolor", "red")
		
		font = tkfont.Font( size=14 )
		
		root.geometry( "800x900" )
		root.title("Tab Widget") 
		
		# bgcol = ttk.Style()
		# bgcol.configure( "TFrame", background="red" )
		
		button_font = tkfont.Font( size=8 )
		
		top_frame = tk.Frame( root, height=30, background="red" )
		bottom_frame = tk.Frame( root )
		
		top_frame.grid( row=0, column=0, sticky="nsew" )
		bottom_frame.grid( row=1, column=0, sticky="nsew" )
		
		root.columnconfigure( 0, weight=1  )
		root.rowconfigure( 1, weight=1  )

		add_button = tk.Button( top_frame, text=" + ", command=self.get_captured_windows, font=font  )
		add_button.grid( row=0, column=0, sticky="e" )
		
		tab_buttons.append( add_button )

		self.top_frame = top_frame
		self.bottom_frame = bottom_frame
		
		root.bind( "<Configure>", self.configure_cb )

		
		root.mainloop()

		return

if( __name__ == "__main__" ):
	thisGui = WinTabber()
