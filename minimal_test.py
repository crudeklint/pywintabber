import tkinter as tk
from tkinter import ttk
from tkinter import font as tkfont

import win32gui, win32con
import os
import signal
import threading
import subprocess
import time

from subprocess import check_output

global SUB_PROCESS

class Config():
	tab_height = 20
	start_width = 600
	start_height = 600
	orientation = "horizontal"
	btn_font_size = 12
	idle_threshold = 5

class WindowHandler():
	captured_windows = {}
	gui_root = None
	gui_hwnd = None
	active_win = None
	ignorelist = []

	def __init__( self, gui_root ):
		self.gui_root = gui_root
		self.gui_hwnd = int( gui_root.frame(), 16 )
		self.ignorelist.append( self.gui_hwnd )

	def get_all( self ):
		self.hwndlist = []

		win32gui.EnumWindows( self._winEnumHandler, None )

		return self.hwndlist		

	def _winEnumHandler( self, hwnd, ctx ):
		if win32gui.IsWindowVisible( hwnd ) and not hwnd in self.ignorelist:
			self.hwndlist.append( hwnd )
	
	def set_size( self, hwnd, rect ):
		x = rect[0]
		y = rect[1]
		w = rect[2]-x
		h = rect[3]-y

		win32gui.MoveWindow( hwnd, x, y, w, h, True )
		return
	
	def get_size( self, hwnd ):
		rect = win32gui.GetWindowRect( hwnd )
		return rect

	def get_title( self, hwnd ):
		name = win32gui.GetWindowText( hwnd )
		return name

	def hide( self, hwnd ):
		win32gui.ShowWindow( hwnd, win32con.SW_HIDE )
		return

	def show( self, hwnd ):
		win32gui.ShowWindow( hwnd, win32con.SW_SHOW )
		return

	def make_active( self, hwnd ):
		win32gui.SetActiveWindow( hwnd )
		return

	def corner_inside( self, main_win_rect, test_win_rect ):
		a = main_win_rect
		b = test_win_rect

		# Use g.e and l.e to not capture the same window...
		if( a[0] >= b[0] or a[1] >= b[1] or a[2] <= b[0] or a[3] <= b[1] ):
			return False
		else:
			return True

	def find_capture_target( self, main_win, exclude_list = [] ):
		# gui = self.gui_root

		# main_geo = (
			# gui.winfo_x(), 
			# gui.winfo_y(),
			# gui.winfo_width()+gui.winfo_x(),
			# gui.winfo_height()+gui.winfo_y()
		# )
		main_geo = self.get_size( main_win )

		for hwnd in self.get_all():
			other_geo = win32gui.GetWindowRect( hwnd )
			title = self.get_title( hwnd )

			if( self.corner_inside( main_geo, other_geo ) and hwnd not in exclude_list ):
				return hwnd

		return None

class Gui():
	counter = 0
	run_daemon = True
	daemon_has_quit = False
	window_handler = None
	captured_windows = {}
	tab_buttons = []
	default_font = None
	active_window = None
	pre_geo = None
	captured_pre_geo = {}

	def __init__( self ):
		self.show()
		return

	def show( self ):	
		root = tk.Tk()
		self.root = root

		self.window_handler = WindowHandler( root )

		default_font = tkfont.nametofont( "TkDefaultFont" )
		default_font.configure( size=Config.btn_font_size )

		th = Config.tab_height

		spacer_image = tk.PhotoImage(data = b'R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7') 

		tab_frame = tk.Frame( root, height=th, bg="red" )
		info_frame = tk.Frame( root, bg="blue" )

		tab_frame.grid( row=0, column=0, sticky="ew" )
		info_frame.grid( row=1, column=0, sticky="nsew" )

		label1 = tk.Label( info_frame, text="Drag window here and press +" )
		label1.grid( row=0, column=0 )

		add_btn = tk.Button( tab_frame, text="+", width=th, command=self.add_btn_cb, image=spacer_image, compound="center", bd=0, height=th )
		add_btn.grid( row=0, column=0, sticky="w" )

		root.grid_columnconfigure(0, weight=1)
		root.grid_rowconfigure(1, weight=1)
		# tab_frame.grid_columnconfigure(0, weight=1)
		
		listener_thread = threading.Thread( target=self.start_listener )
		listener_thread.daemon = True

		self.label1 = label1
		self.listener_thread = listener_thread
		self.tab_frame = tab_frame
		self.info_frame = info_frame
		self.add_btn = add_btn
		self.spacer_image = spacer_image
		# self.default_font = default_font

		root.protocol("WM_DELETE_WINDOW", self.exit_cb )

		h = Config.start_height
		w = Config.start_width
		root.geometry( str(h)+"x"+str(w) ) 

		listener_thread.start()
		root.mainloop()

		return

	def render_gui( self ):
		root = self.root
		window_handler = self.window_handler
		
		tab_buttons = self.tab_buttons
		tab_frame = self.tab_frame
		captured_windows = self.captured_windows
		add_btn = self.add_btn
		spacer_image = self.spacer_image

		info_frame = self.info_frame
		active_window = self.active_window

		winh = Config.start_height
		winw = Config.start_width
		th = Config.tab_height

		new_pos = (
			root.winfo_x()-8, 
			root.winfo_y()+th,
			root.winfo_x()+root.winfo_width()+8,
			root.winfo_y()+root.winfo_height()
		)

		if( len( captured_windows ) == 0 ):
			root.overrideredirect( 0 )
		elif( len( captured_windows ) == 1 ):
			root.overrideredirect( 1 )
			root.attributes("-transparentcolor", "red")
			root.attributes('-topmost', True)
			root.geometry( str( winw ) + "x" + str( th+4 )  )
			window_handler.set_size( active_window, new_pos )
			self.start_tracking()
		else:
			1==1


		for tab_btn in tab_buttons:
			tab_btn.destroy()

		tab_buttons = []

		for hwnd in captured_windows:
			title = captured_windows[hwnd]
			if( hwnd == active_window ):
				bg = None
			else:
				bg = "#b0b0b0"
			new_btn = tk.Button( tab_frame, text=title, image=spacer_image, compound="center", bd=0, height=th, bg=bg, command=lambda hwnd=hwnd: self.tab_click_tb(hwnd) )
			tab_buttons.append( new_btn )

		for i in range( 0, len( tab_buttons ) ):
			tab_buttons[i].grid( row=0, column=i, sticky="w", padx=(0,1) )

		add_btn.grid( row=0, column=i+1, sticky="w" )

		return

	def start_tracking( self ):
		self.tracking_enabled = True
		self.mover_thread = threading.Thread( target=self.move_to_active )
		self.mover_thread.daemon = True
		self.mover_thread.start()
		

	def move_to_active( self ):
		root = self.root
		window_handler = self.window_handler
		idle_start = 0
		is_idle = False

		sleep_time = 0

		while self.tracking_enabled:
			active_window = self.active_window
			active_rect = window_handler.get_size( active_window )
			now_tick = time.time()

			new_x = active_rect[0]+7
			new_y = active_rect[1]-Config.tab_height-4
			new_w = active_rect[2]-active_rect[0]-14
			new_h = Config.tab_height+4

			current_geo = self.root.winfo_geometry()
			new_geostring = "%sx%s+%s+%s" % (new_w, new_h, new_x, new_y)

			if( new_geostring == current_geo ):
				delta = now_tick-idle_start
				if( idle_start == 0 ):
					idle_start = now_tick
					print( "idle start" )
				elif( not is_idle and idle_start > 0 and delta > 10 ):
					is_idle = True
					sleep_time = 0.1
					print( "idle" )
			elif( is_idle and idle_start > 0 ):
					is_idle = False
					idle_start = 0
					sleep_time = 0
					print( "not idle" )
			else:
				is_idle = False

			time.sleep( sleep_time )
	
			if( not is_idle ):
				root.geometry( new_geostring )

			# print('.')

			self.pre_geo = current_geo

	def start_listener( self ):
		global SUB_PROCESS

		listener_process = subprocess.Popen([r"D:\script\pywintabber\stdout_test.exe"], stdout=subprocess.PIPE)

		SUB_PROCESS = listener_process

		while self.run_daemon:
			output = listener_process.stdout.readline()
			if output == '' and listener_process.poll() is not None:
				break
			
			self.blinking_cb( output.strip().decode('utf-8') )

		listener_process.kill()
		return

	def listener_cb( self, hwnd ):
		self.label2["text"] = str( hwnd )

		return

	def exit_cb( self ):
		for hwnd in self.captured_windows:
			self.window_handler.show( hwnd )

			if( hwnd in self.captured_pre_geo ):
				self.window_handler.set_size( hwnd, self.captured_pre_geo[hwnd] )

		self.run_daemon = False
		self.root.destroy()
		self.root.quit()

		return

	def add_btn_cb( self ):
		if( len( self.captured_windows ) == 0 ):
			main_win = int( self.root.frame(), 16 )
		else:
			main_win = self.active_window

		pre_active = self.active_window
		if( pre_active != None ):
			pre_rect = self.window_handler.get_size( pre_active )

		hwnd = self.window_handler.find_capture_target( main_win )

		if( hwnd == None ):
			return

		self.captured_pre_geo[hwnd] = self.window_handler.get_size( hwnd )

		self.active_window = hwnd
		overlapping_title = self.window_handler.get_title( hwnd )
		
		self.captured_windows[hwnd] = overlapping_title

		if( pre_active != None ):
			self.window_handler.set_size( hwnd, pre_rect )
		

		self.render_gui()
		self.show_only_active_window()
		return
		
	def blinking_cb( self, hwnd ):
		self.label1["text"] = str( hwnd )
		return

	def show_only_active_window( self ):
		for hwnd in self.captured_windows:
			if( hwnd == self.active_window ):
				self.window_handler.show( hwnd )
			else:
				self.window_handler.hide( hwnd )

		return

	def tab_click_tb( self, hwnd ):
		pre_active = self.active_window
		pre_rect = self.window_handler.get_size( pre_active )

		if( pre_active == hwnd ):
			return

		self.window_handler.set_size( hwnd, pre_rect )
		
		self.active_window = hwnd
		self.render_gui()
		self.show_only_active_window()

		

		# self.window_handler.make_active( hwnd )

if( __name__ == "__main__" ):
	Gui()
	os.kill(SUB_PROCESS.pid, signal.CTRL_C_EVENT)
	print( "quit" )
