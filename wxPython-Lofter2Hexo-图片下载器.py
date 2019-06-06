import json
import os
import random
import re
import sys
import threading
import time
from collections import OrderedDict
from pathlib import Path

import pyautogui
import wx
import xmltodict
from selenium import webdriver

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.1

p_server = re.compile(r'(imglf\d?)', re.I)
p_img = re.compile(r'<img src="([^"]+?)"[^>]*>', re.I)

# gh_prefix = Path(r'raw.githubusercontent.com')


# script_text = """
# global frontApp, frontAppName, windowTitle
#
# set windowTitle to ""
# tell application "System Events"
# 	set frontApp to first application process whose frontmost is true
# 	set frontAppName to name of frontApp
# 	tell process frontAppName
# 		tell (1st window whose value of attribute "AXMain" is true)
# 			set windowTitle to value of attribute "AXTitle"
# 		end tell
# 	end tell
# end tell
#
# return {frontAppName & "\r" & windowTitle}
# """


# def get_front_app():
#     code, out, err = osascript.run(script_text)
#     return code, out, err


if os.name == 'nt':
    import ctypes
    from ctypes import windll, wintypes
    from uuid import UUID


    # ctypes GUID copied from MSDN sample code
    class GUID(ctypes.Structure):
        _fields_ = [
            ("Data1", wintypes.DWORD),
            ("Data2", wintypes.WORD),
            ("Data3", wintypes.WORD),
            ("Data4", wintypes.BYTE * 8)
        ]

        def __init__(self, uuidstr):
            uuid = UUID(uuidstr)
            ctypes.Structure.__init__(self)
            self.Data1, self.Data2, self.Data3, \
            self.Data4[0], self.Data4[1], rest = uuid.fields
            for i in range(2, 8):
                self.Data4[i] = rest >> (8 - i - 1) * 8 & 0xff


    SHGetKnownFolderPath = windll.shell32.SHGetKnownFolderPath
    SHGetKnownFolderPath.argtypes = [
        ctypes.POINTER(GUID), wintypes.DWORD,
        wintypes.HANDLE, ctypes.POINTER(ctypes.c_wchar_p)
    ]


    def _get_known_folder_path(uuidstr):
        pathptr = ctypes.c_wchar_p()
        guid = GUID(uuidstr)
        if SHGetKnownFolderPath(ctypes.byref(guid), 0, 0, ctypes.byref(pathptr)):
            raise ctypes.WinError()
        return pathptr.value


    FOLDERID_Download = '{374DE290-123F-4565-9164-39C4925E467B}'


    def get_download_folder():
        return _get_known_folder_path(FOLDERID_Download)
else:
    def get_download_folder():
        home = os.path.expanduser("~")
        return os.path.join(home, "Downloads")


def get_platform():
    platforms = {
        'linux1': 'Linux',
        'linux2': 'Linux',
        'darwin': 'OS X',
        'win32': 'Windows'
    }
    if sys.platform not in platforms:
        return sys.platform
    return platforms[sys.platform]


def get_di_files_w_suffix(rootdir, suffixes):
    file_paths = []
    files = os.listdir(rootdir)
    if isinstance(suffixes, str):
        suffixes = (suffixes,)
    for file in files:
        file_path = Path(rootdir) / file
        if file_path.suffix.lower() in suffixes and file_path.is_file():
            file_paths.append(file_path)
    file_paths.sort()
    return file_paths


def get_di_xml(rootdir):
    suffixes = ".xml"
    return get_di_files_w_suffix(rootdir, suffixes)


# ================创建目录================
def make_dir(file_path):
    if not os.path.exists(file_path):
        try:
            os.mkdir(file_path)
        except:
            pass


# ================运行时间计时================
def run_time(start_time):
    '''
    :param start_time:
    :return: 运行时间
    '''
    run_time = time.time() - start_time
    if run_time < 60:  # 两位小数的秒
        show_run_time = '{:.2f}秒'.format(run_time)
    elif run_time < 3600:  # 分秒取整
        show_run_time = '{:.0f}分{:.0f}秒'.format(run_time // 60, run_time % 60)
    else:  # 时分秒取整
        show_run_time = '{:.0f}时{:.0f}分{:.0f}秒'.format(run_time // 3600, run_time % 3600 // 60, run_time % 60)
    return show_run_time


def deduce_list(input_list):
    output_list = list(OrderedDict.fromkeys(input_list))
    return output_list


class HelloFrame(wx.Frame):
    def __init__(self, *args, **kw):
        # ensure the parent's __init__ is called
        super(HelloFrame, self).__init__(*args, **kw)

        # self.SetBackgroundColour(wx.Colour(224, 224, 224))

        dsize = wx.DisplaySize()
        self.SetSize(ratioX * dsize[0], ratioY * dsize[1])

        self.Center()

        self.SetToolTip(wx.ToolTip('这是一个框架！'))
        # self.SetCursor(wx.StockCursor(wx.CURSOR_MAGNIFIER))  # 改变鼠标样式

        self.pnl = wx.Panel(self)

        self.PicDirStr = '你的图片库文件夹路径'
        self.PicDirStr = str(current_dir)
        self.PicDir = Path(self.PicDirStr)

        self.DownDirStr = '你的下载库文件夹'
        self.DownDirStr = get_download_folder()
        self.DownDir = Path(self.DownDirStr)

        if os_info == 'Windows':
            chromedriverName = 'chromedriver.exe'
        else:
            chromedriverName = 'chromedriver'

        self.chromedriverPathStr = str(current_dir / chromedriverName)
        # self.chromedriver = Path(self.chromedriverPathStr)

        self.ratio = 3

        # ================框架================
        self.button1 = wx.Button(self.pnl, wx.ID_ANY, '执行任务')

        self.st11 = wx.StaticText(self.pnl, label='图片库文件夹：')
        self.tc11 = wx.TextCtrl(self.pnl, wx.ID_ANY, value=self.PicDirStr)

        self.st12 = wx.StaticText(self.pnl, label='下载库文件夹：')
        self.tc12 = wx.TextCtrl(self.pnl, wx.ID_ANY, value=self.DownDirStr)

        self.st13 = wx.StaticText(self.pnl, label='chromedriver路径：')
        self.tc13 = wx.TextCtrl(self.pnl, wx.ID_ANY, value=self.chromedriverPathStr)

        self.st0 = wx.StaticText(self.pnl, label='当前文件夹：')
        # line = str(__file__) + '|' + str(current_dir) + '|' + str(dirpath)
        line = str(current_dir)
        self.tc0 = wx.TextCtrl(self.pnl, wx.ID_ANY, value=line, style=wx.TE_READONLY)

        self.st1 = wx.StaticText(self.pnl, label='读取自：')
        self.tc1 = wx.TextCtrl(self.pnl, wx.ID_ANY, style=wx.TE_READONLY)

        self.st2 = wx.StaticText(self.pnl, label='保存到文件夹：')
        self.tc2 = wx.TextCtrl(self.pnl, wx.ID_ANY, style=wx.TE_READONLY)

        self.st3 = wx.StaticText(self.pnl, label='调试信息：')
        self.tc3 = wx.TextCtrl(self.pnl, wx.ID_ANY, style=wx.TE_READONLY)

        self.st4 = wx.StaticText(self.pnl, label='调试日志：')
        self.tc4 = wx.TextCtrl(self.pnl, wx.ID_ANY, style=wx.TE_MULTILINE | wx.TE_READONLY)

        self.st_progress = wx.StaticText(self.pnl, label='进度：')
        # self.tc5 = wx.TextCtrl(self.pnl, wx.ID_ANY, style=wx.TE_READONLY)
        self.gauge = wx.Gauge(self.pnl, range=100, )  # ,  size=(250, -1)

        # ================尺寸器================

        self.vBox = wx.BoxSizer(wx.VERTICAL)  # 垂直尺寸器

        # 给尺寸器添加组件，从左往右，从上到下

        self.vBox.Add(self.button1, proportion=1, flag=wx.EXPAND | wx.ALL, border=pad)

        self.sBox11 = wx.BoxSizer()  # 水平尺寸器，不带参数则为默认的水平尺寸器
        self.sBox11.Add(self.st11, proportion=1, flag=wx.EXPAND | wx.ALL, border=pad)
        self.sBox11.Add(self.tc11, proportion=self.ratio, flag=wx.EXPAND | wx.ALL, border=pad)
        self.vBox.Add(self.sBox11, proportion=1, flag=wx.EXPAND | wx.ALL, border=pad)

        self.sBox12 = wx.BoxSizer()  # 水平尺寸器，不带参数则为默认的水平尺寸器
        self.sBox12.Add(self.st12, proportion=1, flag=wx.EXPAND | wx.ALL, border=pad)
        self.sBox12.Add(self.tc12, proportion=self.ratio, flag=wx.EXPAND | wx.ALL, border=pad)
        self.vBox.Add(self.sBox12, proportion=1, flag=wx.EXPAND | wx.ALL, border=pad)

        self.sBox13 = wx.BoxSizer()  # 水平尺寸器，不带参数则为默认的水平尺寸器
        self.sBox13.Add(self.st13, proportion=1, flag=wx.EXPAND | wx.ALL, border=pad)
        self.sBox13.Add(self.tc13, proportion=self.ratio, flag=wx.EXPAND | wx.ALL, border=pad)
        self.vBox.Add(self.sBox13, proportion=1, flag=wx.EXPAND | wx.ALL, border=pad)

        self.sBox0 = wx.BoxSizer()  # 水平尺寸器，不带参数则为默认的水平尺寸器
        self.sBox0.Add(self.st0, proportion=1, flag=wx.EXPAND | wx.ALL, border=pad)
        self.sBox0.Add(self.tc0, proportion=self.ratio, flag=wx.EXPAND | wx.ALL, border=pad)
        self.vBox.Add(self.sBox0, proportion=1, flag=wx.EXPAND | wx.ALL, border=pad)

        self.sBox1 = wx.BoxSizer()  # 水平尺寸器，不带参数则为默认的水平尺寸器
        self.sBox1.Add(self.st1, proportion=1, flag=wx.EXPAND | wx.ALL, border=pad)
        self.sBox1.Add(self.tc1, proportion=self.ratio, flag=wx.EXPAND | wx.ALL, border=pad)
        self.vBox.Add(self.sBox1, proportion=1, flag=wx.EXPAND | wx.ALL, border=pad)

        self.sBox2 = wx.BoxSizer()  # 水平尺寸器，不带参数则为默认的水平尺寸器
        self.sBox2.Add(self.st2, proportion=1, flag=wx.EXPAND | wx.ALL, border=pad)
        self.sBox2.Add(self.tc2, proportion=self.ratio, flag=wx.EXPAND | wx.ALL, border=pad)
        self.vBox.Add(self.sBox2, proportion=1, flag=wx.EXPAND | wx.ALL, border=pad)

        self.sBox3 = wx.BoxSizer()  # 水平尺寸器，不带参数则为默认的水平尺寸器
        self.sBox3.Add(self.st3, proportion=1, flag=wx.EXPAND | wx.ALL, border=pad)
        self.sBox3.Add(self.tc3, proportion=self.ratio, flag=wx.EXPAND | wx.ALL, border=pad)
        self.vBox.Add(self.sBox3, proportion=1, flag=wx.EXPAND | wx.ALL, border=pad)

        self.vBox.Add(self.st4, proportion=1, flag=wx.EXPAND | wx.ALL, border=pad)
        self.vBox.Add(self.tc4, proportion=self.ratio, flag=wx.EXPAND | wx.ALL, border=pad)

        self.vBox.Add(self.st_progress, proportion=1, flag=wx.EXPAND | wx.ALL, border=pad)

        self.vBox.Add(self.gauge, proportion=1, flag=wx.EXPAND | wx.ALL, border=pad)

        # 设置主尺寸
        self.pnl.SetSizer(self.vBox)  # 因为sBox被嵌套在vBox上，所以以vBox为主尺寸

        # ================绑定================
        self.button1.Bind(wx.EVT_BUTTON, self.onStartButton)

        # ================状态栏================
        self.CreateStatusBar()
        self.SetStatusText('准备就绪')

        # ================菜单栏================
        self.fileMenu = wx.Menu()  # 文件菜单

        self.helloItem = self.fileMenu.Append(-1, '你好\tCtrl-H', '程序帮助')
        self.fileMenu.AppendSeparator()
        self.exitItem = self.fileMenu.Append(wx.ID_EXIT, '退出\tCtrl-Q', '退出程序')

        self.helpMenu = wx.Menu()  # 帮助菜单

        self.aboutItem = self.helpMenu.Append(wx.ID_ABOUT, '关于\tCtrl-G', '关于程序')

        self.menuBar = wx.MenuBar()  # 菜单栏
        self.menuBar.Append(self.fileMenu, '文件')
        self.menuBar.Append(self.helpMenu, '其他')

        self.SetMenuBar(self.menuBar)

        # ================绑定================
        self.Bind(wx.EVT_MENU, self.OnHello, self.helloItem)
        self.Bind(wx.EVT_MENU, self.OnExit, self.exitItem)
        self.Bind(wx.EVT_MENU, self.OnAbout, self.aboutItem)

    def correct(self, jpg_url):
        m_server = re.search(p_server, jpg_url)
        jpg_url_https = jpg_url.replace('http://', 'https://', 1)
        jpg_name = Path(jpg_url).name

        if m_server and 'netease.com' in jpg_url:
            server = m_server.group(1)
            # jpg_url = 'http://' + server + '.nosdn.127.net/img/' + jpg_name
            jpg_url_https = 'https://' + server + '.nosdn.127.net/img/' + jpg_name

        return jpg_url_https

    def get_jpg_urls(self, xml_text):
        doc = xmltodict.parse(xml_text)
        posts = doc['lofterBlogExport']['PostItem']
        posts.reverse()

        jpg_urls = []

        for i in range(len(posts)):
            post = posts[i]
            post_type = post['type']
            if post_type == 'Photo':
                photoLinks = ''
                if 'photoLinks' in post:
                    photoLinks = post['photoLinks']

                photoLinks = json.loads(photoLinks)  # 将json字符串转换成python对象
                for photoLink in photoLinks:
                    if 'raw' in photoLink and isinstance(photoLink['raw'], str):
                        jpg_url = photoLink['raw']
                    elif 'orign' in photoLink and isinstance(photoLink['orign'], str):
                        jpg_url = photoLink['orign']
                    else:
                        jpg_url = ''

                    if jpg_url != '':
                        jpg_urls.append(jpg_url)

            elif post_type == 'Text' and 'content' in post:
                content = post['content']
                # print(content)
                sub_jpg_url = p_img.findall(content)
                if sub_jpg_url:
                    sub_jpg_url = [x.split('?')[0] for x in sub_jpg_url]
                    # print(sub_jpg_url)

                    jpg_urls.extend(sub_jpg_url)

            gau = 100 * (i + 1) / len(posts)
            wx.CallAfter(self.gauge.SetValue, gau)
        return jpg_urls

    def check_on_disk(self, jpg_url):
        on_disk = False
        m_server = re.search(p_server, jpg_url)
        jpg_name = Path(jpg_url).name
        if m_server and not Path(jpg_url).stem.isdigit():
            jpg_name = 'img_' + jpg_name

        jpg_path = self.PicDir / jpg_name
        down_jpg_path = self.DownDir / jpg_name

        if jpg_path.exists() or down_jpg_path.exists():
            on_disk = True
        return on_disk

    def process(self, jpg_urls):
        browser = webdriver.Chrome(self.chromedriverPathStr)
        for i in range(len(jpg_urls)):
            jpg_url = jpg_urls[i]
            jpg_name = Path(jpg_url).name

            m_server = re.search(p_server, jpg_url)
            if m_server and 'netease.com' in jpg_url:
                server = m_server.group(1)
                jpg_url = 'http://' + server + '.nosdn.127.net/img/' + jpg_name

            self.show_label_str(self.tc3, jpg_url)

            # print(jpg_url)

            browser.get(jpg_url)
            page_source = browser.page_source

            # print(page_source)

            if '<center><h1>403 Forbidden</h1></center>' in page_source:
                pass

            elif jpg_url in page_source or '<meta name="viewport"' in page_source:
                # code, app_meta, err = get_front_app()
                # print(code, app_meta, err)
                #
                # lines = app_meta.splitlines()
                # app_name, page_name = '', ''
                #
                # if len(lines) >= 2:
                #     app_name = lines[0]
                #     page_name = lines[1]
                #
                # if app_name != 'Google Chrome':
                #     break
                #
                # print(app_name)
                # print(page_name)

                time.sleep(random.randint(2000, 3000) / 1000)
                if os_info == 'Windows':
                    pyautogui.hotkey('ctrl', 's')
                else:
                    pyautogui.hotkey('command', 's')

                time.sleep(random.randint(1000, 2000) / 1000)
                pyautogui.press('enter')

    def process_xmls(self, xmls, event_obj):
        wx.CallAfter(event_obj.Disable)
        start_time = time.time()  # 初始时间戳
        xml_jpg_urls = []
        for x in range(len(xmls)):
            xml_file_path = xmls[x]
            with open(xml_file_path, mode="r", encoding="utf-8") as fp:
                xml_text = fp.read()
            xml_text = re.sub(u"[\x00-\x08\x0b-\x0c\x0e-\x1f]+", u"", xml_text)

            self.show_label_str(self.tc1, str(xml_file_path))
            jpg_urls = self.get_jpg_urls(xml_text)
            xml_jpg_urls.extend(jpg_urls)

        xml_jpg_urls = [self.correct(jpg_url) for jpg_url in xml_jpg_urls]
        xml_jpg_urls = [jpg_url for jpg_url in xml_jpg_urls if not self.check_on_disk(jpg_url)]
        xml_jpg_urls = deduce_list(xml_jpg_urls)
        xml_jpg_urls.reverse()
        if xml_jpg_urls:
            self.process(xml_jpg_urls)

        # ================运行时间计时================
        show_run_time = run_time(start_time)
        label_str = '程序结束！' + show_run_time
        self.show_label_str(self.tc3, label_str)
        wx.CallAfter(event_obj.Enable)

    def onStartButton(self, event):
        event_obj = event.GetEventObject()
        self.PicDirStr = self.tc11.GetValue()
        self.DownDirStr = self.tc12.GetValue()
        self.chromedriverPathStr = self.tc13.GetValue()

        self.PicDir = Path(self.PicDirStr)
        self.DownDir = Path(self.DownDirStr)
        # self.chromedriver = Path(self.chromedriverPathStr)

        self.thread_it(self.process_xmls, xmls, event_obj)
        # event.GetEventObject().Enable()

    def OnExit(self, event):
        self.Close(True)

    def OnHello(self, event):
        wx.MessageBox('来自 wxPython', '你好')

    def OnAbout(self, event):
        wx.MessageBox(message=about_me,
                      caption='关于' + app_name,
                      style=wx.OK | wx.ICON_INFORMATION)

    def show_label_str(self, bar, label_str):
        # print(label_str)

        wx.CallAfter(bar.Clear)
        wx.CallAfter(bar.AppendText, label_str)

        if not label_str.endswith('\n\r'):
            label_str += '\n'

        wx.CallAfter(self.tc4.AppendText, label_str)

    @staticmethod
    def thread_it(func, *args):
        t = threading.Thread(target=func, args=args)
        t.setDaemon(True)  # 守护--就算主界面关闭，线程也会留守后台运行（不对!）
        t.start()  # 启动
        # t.join()          # 阻塞--会卡死界面！


if __name__ == '__main__':
    os_info = get_platform()

    current_dir = os.path.dirname(os.path.abspath(__file__))
    current_dir = Path(current_dir)

    dirpath = os.getcwd()

    xmls = get_di_xml(current_dir)
    xmls = [x for x in xmls if x.stem.startswith('LOFTER-')]

    app_name = 'Lofter2Hexo配套图片下载器 v1.2 by 墨问非名'
    about_me = '这是Lofter图片下载器。'

    ratioX = 0.5
    ratioY = 0.7

    pad = 5

    icon_size = (16, 16)

    app = wx.App()

    frm = HelloFrame(None, title=app_name)
    frm.Show()

    ppi_tup = wx.ScreenDC().GetPPI()
    # print(ppi_tup)

    app.MainLoop()
