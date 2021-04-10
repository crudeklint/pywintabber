import win32gui, win32con

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
	
	def exists( hwnd ):
		return win32gui.IsWindow( hwnd )

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

	def corner_intersecting( main_win_rect, test_win_rect ):
		a = main_win_rect
		b = test_win_rect

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

			if( WindowHandler.corner_intersecting( main_geo, other_geo ) ):
				return hwnd

		return None

	def show_only_active_window( active_window, captured_windows ):
		for hwnd in captured_windows:
			if( hwnd == active_window ):
				WindowHandler.show( hwnd )
				WindowHandler.make_active( hwnd )
			else:
				WindowHandler.hide( hwnd )

		return