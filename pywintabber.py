import tkinter as tk
from tkinter import ttk
from tkinter import font as tkfont

import os
import signal
import threading
import subprocess
import time
import inspect
import win32api, win32gui, win32con
import pywintypes

from windowhandler import *

THREADS = {}
CAPTURED_WINDOWS = []
SUB_PROCESS = None

def CubicEaseInOut(p):
    if (p < 0.5):
        return 4 * p * p * p
    else:
        f = ((2 * p) - 2)
        return 0.5 * f * f * f + 1

def BounceEaseIn(p):
    return 1 - BounceEaseOut(1 - p)

def BounceEaseOut(p):
    if(p < 4/11.0):
        return (121 * p * p)/16.0
    
    elif(p < 8/11.0):
        return (363/40.0 * p * p) - (99/10.0 * p) + 17/5.0
    
    elif(p < 9/10.0):
        return (4356/361.0 * p * p) - (35442/1805.0 * p) + 16061/1805.0
    
    else:
        return (54/5.0 * p * p) - (513/25.0 * p) + 268/25.0

def BounceEaseInOut(p):
    if(p < 0.5):
        return 0.5 * BounceEaseIn(p*2)
    else:
        return 0.5 * BounceEaseOut(p * 2 - 1) + 0.5

def animation_wrapper(p):
	return CubicEaseInOut(p)

class Config():
	tab_height = 30
	button_margin = 2
	start_width = 600
	start_height = 600
	btn_font_size = 12
	idle_threshold = 2
	max_tabs = 10
	renames = {" | Microsoft Teams": " (MT)"}
	active_bg = "#f0f0f0"
	inactive_bg = "#a0a0a0"
	active_flashing_bg = "#CC7529"
	inactive_flashing_bg = "#ab8360"
	fudge_x = 8
	fudge_y = 8
	idle_sleep_timer = 0.1
	active_sleep_timer = 0
	tab_scroll_action = "scroll only" # "scroll only" or "scroll and switch"
	mouseover_idle_cancel = True

class Gui():
	root = None
	captured_windows = []
	blinking_windows = set()
	captured_pre_geo = {}
	threads = {}
	pause_tracking = False
	tab_buttons = []
	active_window = None
	_pre_render_cache = None
	last_blinked_hwnd = None
	tab_number_increasing = True
	active_rect = (0,0,0,0)

	def __init__( self ):
		global CAPTURED_WINDOWS
		global THREADS 

		self.root = tk.Tk()

		# Use persistant containers for captured windows and threads in order	
		# to handle them after gui is destroyed.
		self.captured_windows = CAPTURED_WINDOWS
		self.threads = THREADS
	
		self.set_gui_defaults()
		return

	# This method sets the default font and creates a 
	def set_gui_defaults( self ):
		# This is the base64-representation of gif file containing a single transparent pixel.
		spacer_image = tk.PhotoImage(data = b'R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7')

		# Setting the default font size.
		self.default_font = tkfont.nametofont( "TkDefaultFont" )
		self.default_font.configure( size=Config.btn_font_size )

		# Add, remove, left and right buttons are considered square buttons.
		# the spacer image is used to force the button size to be set in pixels.
		self.square_btn_data = {
			"width": Config.tab_height-4, 
			"height": Config.tab_height-4, 
			"image": spacer_image, 
			"bg": Config.inactive_bg,
			"compound": "center", 
			"bd": 0
		}
		
		self.tab_btn_data = {
			"height": Config.tab_height-4, 
			"image": spacer_image, 
			"compound": "center", 
			"bd": 0,
			"activebackground": Config.inactive_bg
		}

		return

	# This is the main method for displaying and layouting the GUI.
	def show( self ):
		# SHORTHANDS
		root = self.root
		addsub_w = Config.tab_height*4+Config.button_margin+5
		tab_btn_data = self.tab_btn_data
		tab_buttons = self.tab_buttons

		# ===========
		# DEFINITIONS
		# ===========
		# The GUI uses a canvas in order to crop and animate the frame containing the tabs.
		canvas = tk.Canvas( root, height=Config.tab_height, bd=0, highlightthickness=0, relief='ridge' )
		# Frames
		tab_frame = tk.Frame( canvas, height=Config.tab_height )
		addsub_frame = tk.Frame( root, height=Config.tab_height, width=addsub_w )
		info_frame = tk.Frame( root )

		# --------------------
		# Widgets in tab_frame
		# --------------------
		# Tab buttons
		tab_buttons.clear()
		for i in range( 0, Config.max_tabs ):
			# A lambda function is used to add an argument to the command called. 
			new_btn = tk.Button( tab_frame, tab_btn_data, text=".", command=lambda i=i: self._tab_click_cb(i) )
			tab_buttons.append( new_btn )

		# -----------------------
		# Widgets in addsub_frame
		# -----------------------
		left_btn = tk.Button( addsub_frame, self.square_btn_data, text="<", command=lambda: self._scroll_tabs_cb_threaded(1) )
		right_btn = tk.Button( addsub_frame, self.square_btn_data, text=">", command=lambda: self._scroll_tabs_cb_threaded(-1) )
		add_btn = tk.Button( addsub_frame, self.square_btn_data, text="+", command=self._add_btn_cb_threaded )
		sub_btn = tk.Button( addsub_frame, self.square_btn_data, text="-", command=self._sub_btn_cb )
		
		# ---------------------
		# Widgets in info_frame
		# ---------------------
		infotext = tk.Label( info_frame, text="Drag window here and press +", height=1 )

		# This is the reference to the tab frame inside the canvas.
		tab_frame_canvas_id = canvas.create_window((0, 0), window=tab_frame, anchor="nw")

		# ======
		# LAYOUT
		# ======
		canvas.grid( row=0, column=0, sticky="ew" )
		addsub_frame.grid( row=0, column=1 )
		info_frame.grid( row=1, column=0, columnspan=2, sticky="nsew" ) 
		infotext.grid( row=0, column=0 )

		left_btn.grid( row=0, column=0, padx=(Config.button_margin, 0) )
		right_btn.grid( row=0, column=1, padx=(Config.button_margin, 0) )
		add_btn.grid( row=0, column=2, padx=(Config.button_margin, 0) )
		sub_btn.grid( row=0, column=3, padx=(Config.button_margin, 0) )

		info_frame.grid_columnconfigure( 0, weight=1 )
		info_frame.grid_rowconfigure( 0, weight=1 )

		root.grid_columnconfigure( 0, weight=1 )
		root.grid_rowconfigure( 1, weight=2 )

		root.geometry( "%sx%s" % (Config.start_width, Config.start_height) )
		root.winfo_toplevel().title( "pywintabber" )

		self.canvas = canvas
		self.tab_frame = tab_frame
		self.canvas = canvas
		self.tab_frame_canvas_id = tab_frame_canvas_id
		self.addsub_frame = addsub_frame
		self.add_btn = add_btn
		self.default_bg = info_frame.cget( "bg" )
		
		root.protocol( "WM_DELETE_WINDOW", self._exit_cb )

		root.mainloop()

	# This method handles changing between the normal window and the tabs-only-style.
	def _change_win_style( self ):
		# SHORTHANDS
		root = self.root
		sw = Config.start_width
		sh = Config.start_height
		th = Config.tab_height
		tab_frame = self.tab_frame
		addsub_frame = self.addsub_frame
		canvas = self.canvas
		add_btn = self.add_btn
		default_bg = self.default_bg
		no_captures = len( self.captured_windows )

		# We calculate if the number of captured windows are increasing or decreasing 
		# by checking the value of this value and the number of captured windows.
		tab_number_increasing = self.tab_number_increasing		

		# If the number of captured windows is 0, the GUI style should be normal.
		if( no_captures == 0 ):
			root.overrideredirect( 0 )	
			root.geometry( "%sx%s" % (sw, sh) )
	
			# The background colors of the canvas and top frames must be explicitly 
			# reset to the default color since they are set when changing to tabs-mode.
			tab_frame["bg"] = default_bg
			canvas["bg"] = default_bg
			addsub_frame["bg"] = default_bg
			self._render_tabs()

		# This should run when going from 0 to 1 captured windows. This enables tabs-only
		# style.
		elif( no_captures == 1 and tab_number_increasing ):
			guihwnd = self.__get_gui_hwnd()
			
			# When changing to the tabs-only style, the borders and window padding is set
			# to 0. This means that the button positions will change relative to the 
			# position and size of the window. We solve this by offsetting the window 
			# position and size so that the buttons stay in place.

			# Get a list of the coordinates for the current location.
			pre_rect = WindowHandler.get_size( guihwnd )
			
			# Get the current position of the add-button.
			pre_btn_x = add_btn.winfo_rootx()
			pre_btn_y = add_btn.winfo_rooty()
		
			# Remove title bar and window borders.
			root.overrideredirect( 1 )
		
			# Change the window height to the same as the tabs.
			root.geometry( "%sx%s" % (sw, th) )

			# Set the frame- and canvas backgrounds to red and make red the transparent color
			# so that the frames become transparent.
			tab_frame["bg"] = "red"
			canvas["bg"] = "red"
			addsub_frame["bg"] = "red"
			root.attributes("-transparentcolor", "red")

			# When changing to overrideredirect( 1 ), it seems like the gui gets a new hwnd.
			new_guihwnd = self.__get_gui_hwnd()

			# Calculate the offset values.
			x_delta = pre_btn_x - add_btn.winfo_rootx()
			y_delta = pre_btn_y - add_btn.winfo_rooty()

			# Calculate the new window rect.
			new_rect = list( pre_rect )
			new_rect[0] += x_delta
			new_rect[1] += y_delta
			new_rect[2] -= x_delta
			new_rect[3] -= Config.fudge_y

			# Set the flag so that this does not trigger when going from 2 to 1 tabs.
			tab_number_increasing = False

			# Set the new size of the GUI.
			WindowHandler.set_size( new_guihwnd, new_rect )

		return

	def _render_tabs( self ):
		# SHORTHANDS 
		tab_frame = self.tab_frame
		captured_windows = self.captured_windows
		tab_buttons = self.tab_buttons
		active_window = self.active_window
		captured_windows = self.captured_windows
		_pre_render_cache = self._pre_render_cache
		blinking_windows = self.blinking_windows

		threads = self.threads

		# Get the current method name
		fname = inspect.currentframe().f_code.co_name

		# Save the method name and if it's currently running in a dictionary in order
		# to enforce that only 1 thread with this method runs at the same time.
		if( fname in threads and threads[fname] == True ):
			return

		# Set the running-flag of this method to true.
		threads[fname] = True

		# In order to only actually refresh the tabs when needed, we check if any of
		# the following data has changed sins last time this method was run:
		# * The names of the captured windows.
		# * Which windows that have been blinking.
		# * Which captured window is the actuve one.
		render_cache = []

		for i in range( 0, len( captured_windows ) ):
			hwnd = captured_windows[i]
			render_cache.append( WindowHandler.get_title( hwnd ) )

		render_cache.extend( list( blinking_windows ) )
		render_cache.append( active_window )

		# If any of this data has been changed, we re-render the tab area.
		if( render_cache != _pre_render_cache ):
			
			# The tabs are rendered by "forgetting" and re-layouting them.
			for i in range( 0, Config.max_tabs ):
				tab_buttons[i].grid_forget()

			for i in range( 0, len( captured_windows ) ):
				hwnd = captured_windows[i]
				name = self._rename_title( WindowHandler.get_title( hwnd ) )

				tab_buttons[i].grid(row=0, column=i, padx=(0,Config.button_margin) )
				tab_buttons[i]["text"] = name
		
			# After creating the buttons, set the bgcolors.
			for i in range( 0, len( captured_windows ) ): 
				hwnd = captured_windows[i]

				if( hwnd in blinking_windows and hwnd == active_window ):
					bg = Config.active_flashing_bg
				elif( hwnd in blinking_windows and hwnd != active_window ):
					bg = Config.inactive_flashing_bg
				elif( not hwnd in blinking_windows and hwnd == active_window ):
					bg = Config.active_bg
				elif( not hwnd in blinking_windows and hwnd != active_window ):
					bg = Config.inactive_bg

				tab_buttons[i]["bg"] = bg

		# Save the data for this loop in order to compare next time this is run.
		self._pre_render_cache = render_cache
		
		# Sat the running-flag to false so this method can run again.
		threads[fname] = False
		return

	# Thread wrapper for the scroll_tabs_cb-method.
	def _scroll_tabs_cb_threaded( self, dir ):
		threading.Thread( target=lambda: self._scroll_tabs_cb(dir), name="_scroll_tabs_cb" ).start()
		return

	# This method handles the animation 
	def _scroll_tabs_cb( self, dir=-1 ):
		# SHORTHANDS 
		captured_windows = self.captured_windows
		active_window = self.active_window
		canvas = self.canvas
		tab_frame = self.tab_frame
		tab_buttons = self.tab_buttons
		tab_frame_canvas_id = self.tab_frame_canvas_id
		threads = self.threads

		# Get the current method name
		fname = inspect.currentframe().f_code.co_name

		# If there is only one tab, there is nothing to do.
		if( len( self.captured_windows ) == 0 ):
			return

		# If this method is already running, exit pls.
		if( fname in threads and threads[fname] == True ):
			return

		# Set the running-flag to true.
		threads[fname] = True

		# Start by getting widget sizes and stuff.
		addsub_frame_x0 = self.addsub_frame.winfo_x()

		tab_frame_x0 = tab_frame.winfo_x()
		tab_frame_x1 = tab_frame_x0 + tab_frame.winfo_width()

		tab_frame_w = tab_frame.winfo_width()
		canvas_w = canvas.winfo_width()

		btn_i = -1

		# There are two possible actions for the scroll-buttons: either scroll the tabs only 
		# or scroll and select the next tab. The directions between these modes are shifted.
		if( Config.tab_scroll_action == "scroll only" ):
			dir = -dir

		# Search for the leftmost visible button.
		for i in range( 0, len( tab_buttons ) ): 
			this_btn_x0 = tab_buttons[i].winfo_rootx() - canvas.winfo_rootx()
			this_btn_x1 = this_btn_x0 + tab_buttons[i].winfo_width()+Config.button_margin

			if( this_btn_x0 == 0 or ( this_btn_x0 < 0 and this_btn_x1 > 1 ) ):
				btn_i = i
				break

		# Get relative coords by comparing absolute coordinates of canvas and buttons
		this_btn_x = tab_buttons[btn_i].winfo_rootx() - canvas.winfo_rootx()
		pre_btn_x = 0 if btn_i == 0 else tab_buttons[btn_i-1].winfo_rootx() - canvas.winfo_rootx()
		next_btn_x = 0 if btn_i == len( tab_buttons )-1 else tab_buttons[btn_i+1].winfo_rootx() - canvas.winfo_rootx()

		# If we want to move tabs to the left, all tabs are visible and there is empty space;
		# dont move.
		if( canvas_w > tab_frame_w and ( tab_frame_x0 <= 0 and dir < 0 ) ):
			delta = 0
		# If a button is aligned to the left, the delta is the relative position of the
		# previous button.
		elif( this_btn_x == 0 and dir > 0 ):
			delta = -pre_btn_x
		# If a button is aligned to the left, the delta is the relative position of the
		# next button.
		elif( this_btn_x == 0 and dir < 0 ):
			delta = -next_btn_x
		# If we are in the middle of a button and we want to move right, the delta is the
		# relative positon of the same button.
		elif( this_btn_x < 0 and next_btn_x > 1 and dir > 0 ):
			delta = -this_btn_x
		# if we are in the middle of a button and want to move to the left, the delta is the
		# relative position of the next button.
		elif( this_btn_x < 0 and next_btn_x > 1 and dir < 0 ):
			delta = -next_btn_x

		# This is for keeping the left side of the tab frame to the right of the addsub frame
		# if the tab frame is larger than the canvas.
		if( canvas_w < tab_frame_w and ( tab_frame_x1 + delta <= addsub_frame_x0 and dir < 0 ) ):
			delta = addsub_frame_x0-tab_frame_x1

		total_move = 0.0
		steps = 30

		# THERE WILL BE FLOATING POINT ERROOOORS!

		# Animate the transition between tabs
		for i in range( 1, steps+1 ):
			if( abs( delta ) < 0.1 ):
				break

			tmp = ( animation_wrapper( i/steps )-animation_wrapper( (i-1)/steps ) )*delta
			total_move += tmp
			canvas.move( tab_frame_canvas_id, tmp, 0 )
			time.sleep( 0.01 )

		# If the mode is set to switch, check if it's possible and change tab.
		if( Config.tab_scroll_action == "scroll and switch" ):
			next_i = captured_windows.index( active_window )-dir
			if( next_i >= 0 and next_i < len( captured_windows ) ):
				self._tab_click_cb_threaded( next_i )

		# Set the thread information to done
		threads[fname] = False

	# This method move the gui-window to the current active window and calls on the 
	# render tab-method.
	def _render_loop( self ):
		# Shorthands 
		root = self.root
		threads = self.threads
		idle_sleep_timer = Config.idle_sleep_timer
		active_sleep_timer = Config.active_sleep_timer
		idle_threshold = Config.idle_threshold
		captured_windows = self.captured_windows

		# Get the current method name
		fname = inspect.currentframe().f_code.co_name

		# If this method is already running, exit pls.
		if( fname in threads and threads[fname] == True ):
			return

		# If it's not already running, set the flag and continue onward brave sir.
		threads[fname] = True

		gui_hwnd = self.__get_gui_hwnd()

		pre_geo = (-1,-1,-1,-1)
		pre_cursor = (-1,-1)
		
		# There are three idle-modes:
		# 0: Active
		# 1: Not active
		# 2. Sleeping
		#
		# In order to not use too much CPU, the waiting time between each iteration
		# is increased if the active window does not move for a while.
		idle_mode = 0
		idle_start = 0

		active_cursor = False

		first_it = True

		# Use the thread status in the threads dict as a loop terminator.
		while threads[fname]:
			# The loop can be paused as well.
			if( self.pause_tracking ):
				continue

			if( not WindowHandler.exists( self.active_window ) ): 
				self._sub_btn_cb()
				if( len( captured_windows ) == 0 ):
					break

			# If there is no active window, exit the method.
			if( self.active_window == None ):
				break

			now_tick = time.time()

			# Get the current size of the active window.
			active_rect = WindowHandler.get_size( self.active_window )
			self.active_rect = active_rect

			# Calculate the rectangle for the GUI window.
			new_x = active_rect[0]+Config.fudge_x
			new_y = active_rect[1]-Config.tab_height
			new_w = active_rect[2]-active_rect[0]-Config.fudge_x*2
			new_h = Config.tab_height

			current_geo = (new_x, new_y, new_w, new_h)

			# If we allow the option below, moving the cursor around the window title bar ends the
			# sleep mode.
			if( Config.mouseover_idle_cancel ):
				active_zone = (new_x, new_y, new_x+new_w, new_y+new_h+50)

				current_cursor = win32gui.GetCursorPos()
				if( current_cursor != pre_cursor and 
						WindowHandler.corner_intersecting( active_zone, current_cursor ) ):

					active_cursor = True
				else:
					active_cursor = False

			# if the previous GUI rectangle is the same as this one, and has not moved for 
			# the time defined in the threshold, set the mode to sleep.
			if( pre_geo == current_geo and not active_cursor ):
				if( idle_mode == 0 ):
					idle_mode = 1
					idle_start = now_tick
				elif( now_tick - idle_start > idle_threshold ):
					idle_mode = 2
			else:
				idle_mode = 0

			# Set the position to the new rectangle and move it below the active window. This is to make sure
			# that the tab seems connected to the active window.
			if( not WindowHandler.exists( gui_hwnd ) ):
				gui_hwnd = self.__get_gui_hwnd()

			win32gui.SetWindowPos( gui_hwnd, self.active_window, new_x, new_y, new_w, new_h, win32con.SWP_NOACTIVATE )

			# Run the tab-rendering routine.
			self._render_tabs()

			# Sleep the appropriate time depending on idle mode.
			sleep_time = active_sleep_timer if( idle_mode < 2 ) else idle_sleep_timer
			time.sleep( sleep_time )

			# Save this gui size to the next iteration in order to compare later on.
			pre_geo = current_geo

		# Flag this method as finished.
		threads[fname] = False

		return

	# Callback that runs when the program recieves information that a window is blinking.
	def _blinking_cb( self, hwnd ):
		# Shorthands 
		threads = self.threads
		last_blinked_hwnd = self.last_blinked_hwnd
		captured_windows = self.captured_windows
		blinking_windows = self.blinking_windows

		# Get the current method name
		fname = inspect.currentframe().f_code.co_name

		# If this method is already running, exit pls.
		if( fname in threads and threads[fname] == True ):
			return

		threads[fname] = True

		# If we already blinked this window or the blinking window 
		# is not captured, exit pls.
		if( hwnd == last_blinked_hwnd or not hwnd in captured_windows ):
			threads[fname] = False
			return

		i = captured_windows.index( hwnd )
	
		# Blink by setting and unsettnig the blinking window data and letting 
		# the tab render method handle the changing of the button backgrounds.
		blinking_windows.add( hwnd )
		time.sleep(1)
		blinking_windows.discard( hwnd )
		time.sleep(1)
		blinking_windows.add( hwnd )

		last_blinked_hwnd = hwnd

		# Dis boi is DONE.
		threads[fname] = False

		return	

	# Threaded version of the blinking-callback.
	def _blinking_cb_threaded( self, hwnd ):
		threading.Thread( target=lambda: self._blinking_cb( hwnd ), name="_blinking_cb" ).start()

		return

	# Tab clicking callback
	def _tab_click_cb( self, hwnd_index ):
		blinking_windows = self.blinking_windows

		# hwnd of the to-be active window.
		hwnd = self.captured_windows[hwnd_index]

		# Get the window size and position for the current active window.
		# pre_rect = WindowHandler.get_size( self.active_window )
		pre_rect = self.active_rect

		# If the to-be active window is blinking, remove blinking status
		if( hwnd in blinking_windows ):
			blinking_windows.discard( hwnd )

		# Set the size of the new active window to the same as the last one.
		WindowHandler.set_size( hwnd, pre_rect )
		
		# Set the active window-property to the new active window.
		self.active_window = hwnd
		
		# Show new active window and hide all others.
		WindowHandler.show_only_active_window( hwnd, self.captured_windows )

		return	

	# Threaded version of tab clicking callback
	def _tab_click_cb_threaded( self, hwnd_index ):
		threading.Thread( target=lambda: self._tab_click_cb( hwnd_index ), name="_tab_click_cb" ).start()

		return

	def _add_btn_cb( self ):
		# Shorthands
		allwins = WindowHandler.get_all()
		this_win = self.__get_gui_hwnd()
		threads = self.threads
		captured_windows = self.captured_windows
		captured_pre_geo = self.captured_pre_geo
		active_window = self.active_window

		captured_geo = ()

		# The win32api-method for getting all windows conveniently gets them in z-order.
		# If we slice the list of all windows like below ge only get windows above the GUI.
		# OR DOES IT?!
		windows_above_me = allwins[0:allwins.index(this_win)+2]

		# Check if this is the first window added or not,
		# If it is, we use the gui window as reference when trying to find overlapping windows.
		first_window = False
		if( len( captured_windows ) == 0 ):
			main_win = self.__get_gui_hwnd()
			first_window = True
		else:
			main_win = self.active_window

		# Ask for the bottommost window that has its top-left corner inside the active/gui 
		# window.
		hwnd = WindowHandler.find_capture_target( main_win, windows_above_me )

		# If nothing was found, there is nothing more here to do.
		if( hwnd == None or hwnd in captured_windows ):
			return

		captured_geo = WindowHandler.get_size( hwnd )

		try:
			WindowHandler.set_size( hwnd, captured_geo )
		except pywintypes.error:
			print( "Cannot access window." )
			return
			

		# If we found a window, add it to the list of captured windows.
		captured_windows.append( hwnd )
		# Add the geometry of the caught window to a dictionary in order to restore it
		# when releasing it.
		captured_pre_geo[hwnd] = WindowHandler.get_size( hwnd )
		# Set the caught window as the new active window.
		self.active_window = hwnd
		# If this was the first caught window, we have to change to tabs-only-mode.
		# The _change_win_style method decides if it's time to redraw the window or 
		# not so we call it everytime.
		self._change_win_style()

		# Since we do a overrideredirect(1) in _change_win_style we have to reaquire the
		# hwnd of the gui.
		if( first_window ):
			main_win = self.__get_gui_hwnd()

		# Get the size of the main (active window or gui).
		pre_rect = WindowHandler.get_size( main_win )
	
		# If this is the first window, we have to recalculate the new geometry.
		if( first_window ):
			pre_rect = list( pre_rect )
			pre_rect[0] -= Config.fudge_x
			pre_rect[1] += Config.tab_height-1
			pre_rect[2] += Config.fudge_x
			pre_rect[3] += Config.fudge_y
			self.active_rect = pre_rect

		# Run the tab-click callback in order to hide all other windows and showing the
		self._tab_click_cb_threaded( len( captured_windows )-1 )
	
		# Pause the tracking in order to not have a race condition between this window
		# relocation and the one in the tracking thread.
		#
		# I think we still have a conflict sometimes though.
		self.pause_tracking = True
		WindowHandler.set_size( hwnd, pre_rect )
		self.pause_tracking = False

		# Start the window tracking/rendering and the program polling for flashing windows.
		if( first_window ):
			threading.Thread( target=self._render_loop, name="_render_loop" ).start()
			threading.Thread( target=self._start_listener, name="_start_listener", daemon=True ).start()

		return

	# Threaded version of the add-button callback.
	def _add_btn_cb_threaded( self ):
		threading.Thread( target=self._add_btn_cb, name="_add_btn_cb" ).start()
		return

	# Callback that runs when clicking the remove-window button.
	def _sub_btn_cb( self ):
		hwnd = self.active_window
		
		# Remove the active window from the list of captured windows.
		self.captured_windows.remove( hwnd )

		# Set the next window to the previous captured one.
		last_win_index = len( self.captured_windows )-1
	
		# If this was the last window, the active window is set to None,
		if( len( self.captured_windows  ) == 0 ):
			self.active_window = None
		# Otherwise the tab click callback is run to only show the previous captured one.
		else:
			self._tab_click_cb( last_win_index )

		# Restore the location of the released window and enforce that it is shown.
		if( hwnd in self.captured_pre_geo and WindowHandler.exists( hwnd ) ):
			WindowHandler.set_size( hwnd, self.captured_pre_geo[hwnd] )
			WindowHandler.show( hwnd )

		# Run the style chaning routine in the case we need to switch between tabs-only mode and gui-mode.
		self._change_win_style()

		return

	# Threaded version of the sub-button callback.
	def _sub_btn_cb_threaded( self ):
		threding.Thread( target=self._sub_btn_cb, name="_sub_btn_cb" ).start()

		return

	# Callback that runs when the GUI is closed.
	def _exit_cb( self ):
		print( "quitting" )
		
		# Show all captured windows in the case the program is prematurely quit.
		for hwnd in self.captured_windows:
			WindowHandler.show( hwnd )

		self.root.destroy()
		self.root.quit()

		return

	def _rename_title( self, title ):
		renames = Config.renames
		for rn in renames:
			if( not rn in title ):
				continue
			
			pattern = rn
			replacement = renames[rn]
			
			title = title.replace( pattern, replacement )
			
		return title

	# Returns the hwnd of the GUI.
	def __get_gui_hwnd( self ):
		return int( self.root.frame(), 16 )

	def _start_listener( self ):
		global SUB_PROCESS

		threads = self.threads

		this_dir = os.path.dirname( os.path.abspath( __file__ ) )
		external_process_path = os.path.join( this_dir, "test_2.exe" )

		fname = inspect.currentframe().f_code.co_name
		if( fname in threads and threads[fname] == True ):
			return

		threads[fname] = True

		listener_process = subprocess.Popen([external_process_path], stdout=subprocess.PIPE)

		SUB_PROCESS = listener_process

		while threads[fname]:
			output = listener_process.stdout.readline()
			if output == '' and listener_process.poll() is not None:
				break
			
			message = output.strip().decode('utf-8')

			try:
				hwnd = int( message )
			except ValueError:
				continue

			self._blinking_cb_threaded( hwnd )

		listener_process.kill()
		threads[fname] = False

		return



if( __name__ == "__main__" ):
	thegui = Gui()
	

	try:
		thegui.show()
	except KeyboardInterrupt:
		print( "Recieved crtl+c, exiting" )

	for hwnd in CAPTURED_WINDOWS:
		WindowHandler.show( hwnd )

	for fname in THREADS:
		THREADS[fname] = False

	if( not SUB_PROCESS is None ):
		os.kill(SUB_PROCESS.pid, signal.CTRL_C_EVENT)

