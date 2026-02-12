"""
CHI 660F 窗口截图捕捉工具

在电化学测量期间，周期性捕获 chi660f.exe 窗口画面并转为 QPixmap，
在主界面工作站区域实时显示 CHI 软件的测量图形。

使用 Win32 API (PrintWindow / BitBlt) 实现窗口内容捕获。
支持捕获被遮挡的窗口，多种回退策略。
"""
import ctypes
import ctypes.wintypes as wintypes
from typing import Optional, List, Tuple

_user32 = ctypes.windll.user32
_gdi32 = ctypes.windll.gdi32

# Win32 常量
SRCCOPY = 0x00CC0020
PW_CLIENTONLY = 1
PW_RENDERFULLCONTENT = 2
DIB_RGB_COLORS = 0
BI_RGB = 0


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ('biSize', wintypes.DWORD),
        ('biWidth', wintypes.LONG),
        ('biHeight', wintypes.LONG),
        ('biPlanes', wintypes.WORD),
        ('biBitCount', wintypes.WORD),
        ('biCompression', wintypes.DWORD),
        ('biSizeImage', wintypes.DWORD),
        ('biXPelsPerMeter', wintypes.LONG),
        ('biYPelsPerMeter', wintypes.LONG),
        ('biClrUsed', wintypes.DWORD),
        ('biClrImportant', wintypes.DWORD),
    ]


class BITMAPINFO(ctypes.Structure):
    _fields_ = [
        ('bmiHeader', BITMAPINFOHEADER),
        ('bmiColors', wintypes.DWORD * 3),
    ]


def _enum_all_visible_windows() -> List[Tuple[int, str]]:
    """枚举所有可见窗口，返回 (hwnd, title) 列表"""
    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    windows = []
    
    @WNDENUMPROC
    def callback(hwnd, _):
        if _user32.IsWindowVisible(hwnd):
            buf = ctypes.create_unicode_buffer(512)
            _user32.GetWindowTextW(hwnd, buf, 512)
            title = buf.value
            if title:
                windows.append((hwnd, title))
        return True
    
    _user32.EnumWindows(callback, 0)
    return windows


def find_chi_window() -> Optional[int]:
    """查找 CHI660F 主窗口句柄
    
    搜索策略 (宽松匹配):
    - 标题包含 'CHI660' 或 'CHI 660' 或 'chi660' 或 'CHI1140'
    """
    windows = _enum_all_visible_windows()
    
    # 优先精确匹配
    for hwnd, title in windows:
        upper = title.upper()
        if 'CHI660' in upper or 'CHI 660' in upper or 'CHI1140' in upper:
            return hwnd
    
    # 备选: 匹配含 'CHI' 和数字的标题
    for hwnd, title in windows:
        upper = title.upper()
        if 'CHI' in upper and any(c.isdigit() for c in title):
            return hwnd
    
    return None


def capture_window_to_bytes(hwnd: int) -> Optional[tuple]:
    """捕获窗口内容为 BGRA 字节数据
    
    尝试多种捕获策略:
    1. PrintWindow + PW_RENDERFULLCONTENT (最佳，支持DWM合成)
    2. PrintWindow + PW_CLIENTONLY
    3. BitBlt 回退
    
    Returns:
        (width, height, bytes_data) 或 None
    """
    if not hwnd or not _user32.IsWindowVisible(hwnd):
        return None
    
    # 获取客户区尺寸
    rect = wintypes.RECT()
    _user32.GetClientRect(hwnd, ctypes.byref(rect))
    width = rect.right - rect.left
    height = rect.bottom - rect.top
    
    if width <= 0 or height <= 0:
        # 尝试 GetWindowRect
        _user32.GetWindowRect(hwnd, ctypes.byref(rect))
        width = rect.right - rect.left
        height = rect.bottom - rect.top
        if width <= 0 or height <= 0:
            return None
    
    # 创建兼容 DC 和位图 (使用屏幕DC以获得正确的色彩深度)
    screen_dc = _user32.GetDC(0)
    hwnd_dc = _user32.GetDC(hwnd)
    if not hwnd_dc:
        _user32.ReleaseDC(0, screen_dc)
        return None
    
    mem_dc = _gdi32.CreateCompatibleDC(screen_dc)
    bitmap = _gdi32.CreateCompatibleBitmap(screen_dc, width, height)
    old_bmp = _gdi32.SelectObject(mem_dc, bitmap)
    
    captured = False
    
    # 策略1: PrintWindow + PW_RENDERFULLCONTENT (Windows 8.1+, 最优)
    if not captured:
        ret = _user32.PrintWindow(hwnd, mem_dc, PW_CLIENTONLY | PW_RENDERFULLCONTENT)
        if ret:
            captured = True
    
    # 策略2: PrintWindow + PW_CLIENTONLY
    if not captured:
        ret = _user32.PrintWindow(hwnd, mem_dc, PW_CLIENTONLY)
        if ret:
            captured = True
    
    # 策略3: BitBlt (要求窗口不被遮挡)
    if not captured:
        _gdi32.BitBlt(mem_dc, 0, 0, width, height, hwnd_dc, 0, 0, SRCCOPY)
        captured = True
    
    # 读取位图为 DIB 数据
    bmi = BITMAPINFO()
    bmi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
    bmi.bmiHeader.biWidth = width
    bmi.bmiHeader.biHeight = -height  # 负值 = 自上而下
    bmi.bmiHeader.biPlanes = 1
    bmi.bmiHeader.biBitCount = 32
    bmi.bmiHeader.biCompression = BI_RGB
    
    buf_size = width * height * 4
    buf = ctypes.create_string_buffer(buf_size)
    
    rows_read = _gdi32.GetDIBits(mem_dc, bitmap, 0, height, buf, ctypes.byref(bmi), DIB_RGB_COLORS)
    
    # 清理
    _gdi32.SelectObject(mem_dc, old_bmp)
    _gdi32.DeleteObject(bitmap)
    _gdi32.DeleteDC(mem_dc)
    _user32.ReleaseDC(hwnd, hwnd_dc)
    _user32.ReleaseDC(0, screen_dc)
    
    if rows_read <= 0:
        return None
    
    return (width, height, bytes(buf))


def _bgra_to_rgba(data: bytes, width: int, height: int) -> bytes:
    """将 BGRA 字节序转为 RGBA (逐像素交换 B 和 R)"""
    arr = bytearray(data)
    for i in range(0, len(arr), 4):
        arr[i], arr[i + 2] = arr[i + 2], arr[i]  # swap B <-> R
    return bytes(arr)


def capture_chi_to_qpixmap():
    """捕获 CHI660F 窗口并转为 QPixmap
    
    Returns:
        QPixmap 或 None
    """
    hwnd = find_chi_window()
    if not hwnd:
        return None
    
    result = capture_window_to_bytes(hwnd)
    if not result:
        return None
    
    width, height, data = result
    
    # 检查数据是否全零 (空白)
    if all(b == 0 for b in data[:min(1000, len(data))]):
        return None
    
    try:
        from PySide6.QtGui import QImage, QPixmap
        
        # Win32 GetDIBits 返回 BGRA 格式，转为 RGBA
        rgba_data = _bgra_to_rgba(data, width, height)
        
        qimg = QImage(rgba_data, width, height, width * 4, QImage.Format_RGBA8888)
        # 必须 copy，因为原始 data 是临时的
        pixmap = QPixmap.fromImage(qimg.copy())
        
        if pixmap.isNull() or pixmap.width() == 0:
            return None
        
        return pixmap
    except Exception as e:
        print(f"[WindowCapture] QPixmap 转换失败: {e}")
        return None
