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

def pause_tracker( myfunction ):
	def inner(self, *arg, **kw):
		self.do_pause_tracking()
		myfunction(self, *arg, **kw)
		self.do_unpause_tracking()
	return inner

class Config():
	tab_height = 20
	start_width = 600
	start_height = 600
	btn_font_size = 12
	idle_threshold = 5
	max_tabs = 10
	renames = {" | Microsoft Teams": " (MT)"}

class WindowHandler():
	def get_all():

		top_windows = []
		win32gui.EnumWindows(WindowHandler._win_enum_handler, top_windows)

		return top_windows		

	def _win_enum_handler( hwnd, top_windows ):
		if( win32gui.IsWindowVisible( hwnd ) == 1 ):
			top_windows.append( hwnd )
		return

	def set_size( hwnd, rect, activate=False ):
		x = rect[0]
		y = rect[1]
		w = rect[2]-x
		h = rect[3]-y

		win32gui.MoveWindow( hwnd, x, y, w, h, True )
		if( activate ):
			WindowHandler.make_active( hwnd )
		return
	
	def get_size( hwnd ):
		rect = win32gui.GetWindowRect( hwnd )
		return rect

	def get_title( hwnd ):
		name = win32gui.GetWindowText( hwnd )
		return name

	def hide( hwnd ):
		win32gui.ShowWindow( hwnd, win32con.SW_HIDE )
		return

	def show( hwnd ):
		win32gui.ShowWindow( hwnd, win32con.SW_SHOW )
		return

	def make_active( hwnd ):
		win32gui.SetActiveWindow( hwnd )
		return

	def corner_inside( main_win_rect, test_win_rect ):
		a = main_win_rect
		b = test_win_rect

		# Use g.e and l.e to not capture the same window...
		if( a[0] >= b[0] or a[1] >= b[1] or a[2] <= b[0] or a[3] <= b[1] ):
			return False
		else:
			return True

	def find_capture_target( main_win, window_list = [] ):
		main_geo = WindowHandler.get_size( main_win )

		if( window_list == [] ):
			window_list = WindowHandler.get_all()

		for hwnd in window_list:

			other_geo = win32gui.GetWindowRect( hwnd )
			title = WindowHandler.get_title( hwnd )

			if( WindowHandler.corner_inside( main_geo, other_geo ) ):
				return hwnd

		return None

	def show_only_active_window( active_window, captured_windows ):
		for hwnd in captured_windows:
			if( hwnd == active_window ):
				WindowHandler.show( hwnd )
			else:
				WindowHandler.hide( hwnd )

		return


class Gui():
	counter = 0
	run_daemon = True
	daemon_has_quit = False
	WindowHandler = None
	tab_buttons = []
	default_font = None
	active_window = None
	pre_geo = None
	captured_pre_geo = {}
	tracking_enabled = False
	pause_tracking = False
	tracking_has_stopped = True

	# self.btn_data = {}

	def __init__( self, captured_windows_container ):
		self.captured_windows = captured_windows_container
		self.show()
		return

	def set_gui_defaults( self ):
		spacer_image = tk.PhotoImage(data = b'R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7')

		self.default_font = tkfont.nametofont( "TkDefaultFont" )
		self.default_font.configure( size=Config.btn_font_size )

		self.square_btn_data = {
			"width": Config.tab_height, 
			"height": Config.tab_height, 
			"image": spacer_image, 
			"compound": "center", 
			"bd": 0
		}

		self.tab_btn_data = {
			"height": Config.tab_height, 
			"image": spacer_image, 
			"compound": "center", 
			"bd": 0
		}

		return

	def show( self ):	
		root = tk.Tk()
		self.root = root

		self.set_gui_defaults()

		btn_data = self.square_btn_data
		tab_btn_data = self.tab_btn_data

		self.tab_frame = tk.Frame( root, height=Config.tab_height, bg="green" )
		info_frame = tk.Frame( root, bg="blue" )

		self.tab_frame.grid( row=0, column=0, sticky="ew" )
		info_frame.grid( row=1, column=0, sticky="nsew" )

		tk.Label( info_frame, text="Drag window here and press +" ).grid( row=0, column=0 )

		self.tab_buttons = []

		for i in range( 0, Config.max_tabs ):
			new_btn = tk.Button( self.tab_frame, tab_btn_data, text=".", command=lambda i=i: self.tab_click_cb(i) )
			self.tab_buttons.append( new_btn )
			# new_btn.grid( row=0, column=i, sticky="w", padx=(0,1) )

		add_btn = tk.Button( self.tab_frame, btn_data, text="+", command=self.add_btn_cb )
		sub_btn = tk.Button( self.tab_frame, btn_data, text="-", command=self.sub_btn_cb )

		add_btn.grid( row=0, column=Config.max_tabs, sticky="w", padx=(0,1) )
		sub_btn.grid( row=0, column=Config.max_tabs+1, sticky="w", padx=(0,1) )
		sub_btn.grid_forget()

		root.grid_columnconfigure( 0, weight=1 )
		root.grid_rowconfigure( 1, weight=1 )

		self.add_btn = add_btn
		self.sub_btn = sub_btn

		root.protocol( "WM_DELETE_WINDOW", self.exit_cb )

		self.listener_thread = threading.Thread( target=self.start_listener )
		self.listener_thread.daemon = True
		self.listener_thread.start()

		root.resizable( height = 0, width = 0 )
		root.attributes("-transparentcolor", "red")
		
		self.render_gui()
		root.mainloop()
		return


	def render_gui( self ):
		threading.Thread( target=self.render_gui_threaded() ).start()
		return

	def render_gui_threaded( self ):
		root = self.root
		
		tab_buttons = self.tab_buttons
		tab_frame = self.tab_frame
		captured_windows = self.captured_windows
		sub_btn = self.sub_btn

		active_window = self.active_window

		winh = Config.start_height
		winw = Config.start_width
		th = Config.tab_height

		tab_btn_data = self.tab_btn_data

		for i in range( 0, Config.max_tabs ):
			this_btn = self.tab_buttons[i]
			this_btn.grid_forget()
		
		self.sub_btn.grid_forget()
		
		for i in range( 0, Config.max_tabs ):
			this_btn = self.tab_buttons[i]

			if( i < len( captured_windows ) ):
				hwnd = self.captured_windows[i]
				title = WindowHandler.get_title( hwnd )

				bg = "#f0f0f0" if( hwnd == active_window ) else "#a0a0a0"

				for rep in Config.renames:
					if rep in title:
						title = title.replace( rep, Config.renames[rep] )

				this_btn["text"] = title
				this_btn["bg"] = bg
				this_btn.grid(row=0, column=i, sticky="w", padx=(0,1))

			else:
				this_btn.grid_forget()

		if( len( captured_windows ) > 0 ):
			sub_btn.grid( row=0, column=Config.max_tabs+2, sticky="w", padx=(0,1) )

		if( len( captured_windows ) == 0 ):
			self.from_empty = True
			self.stop_tracking()

			# if( not self.tracking_has_stopped ):
				# self.mover_thread.join()

			root.overrideredirect( 0 )
			self.tab_frame["bg"] = "pink"
			time.sleep( 1 )
			root.geometry( "%sx%s" % ( Config.start_width, Config.start_height ) )
			
		elif( len( captured_windows ) == 1 and self.from_empty ):
			self.from_empty = False

			self.start_tracking()

			self.tab_frame["bg"] = "red"

			root.geometry( "%sx%s" % ( winw, th+4 )  )
			root.overrideredirect( 1 )

			new_pos = (
				root.winfo_x()-8, 
				root.winfo_y()+th,
				root.winfo_x()+root.winfo_width()+8,
				root.winfo_y()+root.winfo_height()
			)

			WindowHandler.set_size( active_window, new_pos )
				
		else:
			1==1

		return

	def start_tracking( self ):
		if( self.tracking_enabled == True ):
			return

		self.tracking_enabled = True
		self.mover_thread = threading.Thread( target=self.move_to_active )
		# self.mover_thread.daemon = True
		self.mover_thread.start()
		return

	def stop_tracking( self ):
		self.tracking_enabled = False
		return

	def do_pause_tracking( self ):
		self.pause_tracking = True
		return

	def do_unpause_tracking( self ):
		self.pause_tracking = False
		return

	def move_to_active( self ):
		root = self.root
		idle_start = 0
		is_idle = False
		self.tracking_has_stopped = False

		sleep_time = 0

		while self.tracking_enabled:
			if( self.pause_tracking ):
				continue

			active_window = self.active_window
			active_rect = WindowHandler.get_size( active_window )
			now_tick = time.time()
			new_x = active_rect[0]+37
			new_y = active_rect[1]-Config.tab_height-4
			new_w = active_rect[2]-active_rect[0]-14
			new_h = Config.tab_height+4

			current_geo = self.root.winfo_geometry()
			new_geostring = "%sx%s+%s+%s" % (new_w, new_h, new_x, new_y)

			if( new_geostring == current_geo ):
				root.attributes("-topmost", False)
				delta = now_tick-idle_start
				if( idle_start == 0 ):
					idle_start = now_tick
				elif( not is_idle and idle_start > 0 and delta > 1 ):
					is_idle = True
					sleep_time = 0.1
			elif( is_idle and idle_start > 0 ):
					is_idle = False
					idle_start = 0
					sleep_time = 0
			else:
				root.attributes("-topmost", True)
				is_idle = False

			time.sleep( sleep_time )
	
			if( not is_idle ):
				root.geometry( new_geostring )

			# print('.')

			self.pre_geo = current_geo

		self.tracking_has_stopped = True
		return

	def start_listener( self ):
		global SUB_PROCESS

		listener_process = subprocess.Popen([r"D:\script\pywintabber\test_2.exe"], stdout=subprocess.PIPE)

		SUB_PROCESS = listener_process

		while self.run_daemon:
			output = listener_process.stdout.readline()
			if output == '' and listener_process.poll() is not None:
				break
			
			self.blinking_cb( output.strip().decode('utf-8') )

		listener_process.kill()

		return

	def blink_thread( self, hwnd ):
		if( not hwnd in self.captured_windows ):
			return

		i = self.captured_windows.index( hwnd )

		precolor = self.tab_buttons[i]["bg"]

		self.tab_buttons[i]["bg"] = "#CC7529"
		time.sleep(1)
		self.tab_buttons[i]["bg"] = precolor

		return	

	def listener_cb( self, hwnd ):
		self.label2["text"] = str( hwnd )
		return

	def exit_cb( self ):
		for hwnd in self.captured_windows:
			WindowHandler.show( hwnd )

			if( hwnd in self.captured_pre_geo ):
				WindowHandler.set_size( hwnd, self.captured_pre_geo[hwnd] )

		self.run_daemon = False
		self.root.destroy()
		self.root.quit()

		return

	@pause_tracker
	def add_btn_cb( self ):
		threading.Thread( self.add_btn_cb_threaded() ).start()
		return

	def add_btn_cb_threaded( self ):
		allwins = WindowHandler.get_all()
		this_win = int( self.root.frame(), 16 )
		windows_above_me = allwins[0:allwins.index(this_win)+2]

		if( len( self.captured_windows ) == 0 ):
			main_win = int( self.root.frame(), 16 )
		else:
			main_win = self.active_window

		pre_active = self.active_window
		if( pre_active != None ):
			pre_rect = WindowHandler.get_size( pre_active )

		hwnd = WindowHandler.find_capture_target( main_win, windows_above_me )

		if( hwnd == None ):
			return

		self.captured_windows.append( hwnd )
		self.captured_pre_geo[hwnd] = WindowHandler.get_size( hwnd )

		self.active_window = hwnd
	
		if( pre_active != None ):
			WindowHandler.set_size( hwnd, pre_rect )

		self.render_gui()
		WindowHandler.show_only_active_window( self.active_window, self.captured_windows )

		return

	@pause_tracker
	def sub_btn_cb( self ):
		threading.Thread( target=self.sub_btn_cb_threaded ).start()
		return
	
	def sub_btn_cb_threaded( self ):

		hwnd = self.active_window
		self.captured_windows.remove( hwnd )

		last_win_index = len( self.captured_windows )-1
	
		if( len( self.captured_windows  ) == 0 ):
			self.active_window = None
		else:
			self.tab_click_cb( last_win_index )
			
		self.render_gui()
		return
	
	def blinking_cb( self, hwnd_str ):
		try:
			hwnd = int( hwnd_str )
		except ValueError:
			return

		blinker = threading.Thread( target=self.blink_thread( hwnd ) )
		blinker.start()

		return

	@pause_tracker
	def tab_click_cb( self, hwnd_index ):
		threading.Thread( target=self.tab_click_cb_threaded( hwnd_index ) ).start()

	def tab_click_cb_threaded( self, hwnd_index ):
		hwnd = self.captured_windows[hwnd_index]

		pre_active = self.active_window
		pre_rect = WindowHandler.get_size( pre_active )

		if( pre_active == hwnd ):
			return

		WindowHandler.set_size( hwnd, pre_rect )
		
		self.active_window = hwnd
		self.render_gui()
		WindowHandler.show_only_active_window( hwnd, self.captured_windows )

		return

if( __name__ == "__main__" ):
	captured_windows = []

	try:
		Gui( captured_windows )
	except KeyboardInterrupt:
		print( "Recieved crtl+c, exiting" )

	for hwnd in captured_windows:
		win32gui.ShowWindow( hwnd, win32con.SW_SHOW )

	os.kill(SUB_PROCESS.pid, signal.CTRL_C_EVENT)

	print( "quit" )
