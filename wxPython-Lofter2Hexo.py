import json
import os
import re
import threading
import time
from collections import OrderedDict
from datetime import datetime
from pathlib import Path

import wx
import xmltodict
from markdownify import markdownify as md

p_server = re.compile(r'(imglf\d?)', re.I)

p_img = re.compile(r'<img src="([^"]+?)"([^>]*)>', re.I)

gh_prefix = Path(r'raw.githubusercontent.com')

# LOFTER-墨问非名-2019.03.29.xml
p_lofter = re.compile(r'^LOFTER-(.*)-(\d{4}\.\d{2}\.\d{2})')


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


def list2str(some_list):
    some_string = ''
    if isinstance(some_list, list):
        some_string = "[" + ", ".join(some_list) + "]"
    elif isinstance(some_list, str):
        some_string = some_list
    return some_string


def format_hugo_title(title):
    if "'" in title or "#" in title or "@" in title or "[" in title or "]" in title or "+" in title or "!" in title or ":" in title or title.isdigit():  # or "：" in title or "（" in title or "）" in title
        title_info = '"' + title + '"'
    else:
        title_info = title
    return title_info


def safe(title):
    keys = '<>'
    for key in keys:
        title = title.replace(key, ' ')
    title = title.replace(':', '：')
    title = title.replace('/', '／')
    title = title.replace('\\', '＼')
    return title


# ================写入文件================
def write_text(file_path, text):
    f = open(file_path, mode='w', encoding="utf-8")
    try:
        f.write(text)
    finally:
        f.close()


def deduce_list(input_list):
    output_list = list(OrderedDict.fromkeys(input_list))
    return output_list


def int2time(timestamp, formatter='%Y-%m-%d %H:%M:%S'):
    timestamp = int(timestamp)
    timestamp = timestamp / 1000
    time_str = datetime.utcfromtimestamp(timestamp).strftime(formatter)

    return time_str


def get_head_matter(export_type, title, publishTime, modifyTime, author, categories, tags, permalink, description=''):
    # ================构造头部================
    content = '---'
    title_info = format_hugo_title(title)

    permalink_lower = permalink.lower()
    slug = '"' + permalink_lower + '"'

    if export_type == 'Hugo':
        publishTime = publishTime.replace(' ', 'T') + '+08:00'
        modifyTime = modifyTime.replace(' ', 'T') + '+08:00'

    content += '\ntitle: ' + title_info
    content += '\ndate: ' + publishTime
    content += '\ntags: ' + list2str(tags)

    if export_type == 'Hexo':
        content += '\ncategories: ' + list2str(categories)
        content += '\nupdated: ' + modifyTime
        content += '\npermalink: ' + permalink
        content += '\nauthor: "' + author + '"'
        content += '\ndescription: "' + description + '"'

    elif export_type == 'Hugo':
        content += '\ncategories: ' + list2str(categories)
        content += '\nlastmod: ' + modifyTime
        content += '\nslug: ' + permalink
        content += '\nauthor: "' + author + '"'
        content += '\ndescription: "' + description + '"'

    elif export_type == 'Jekyll':
        content += '\ncategories: ' + list2str(categories)

    elif export_type == 'Gridea':
        content += '\npublished: true'
        content += '\nhideInList: false'
        content += '\nfeature: '

    content += '\n---'
    return content


def get_comments(post, content, id2name_dict):
    commentList = post['commentList']
    comments = commentList['comment']
    if not isinstance(comments, list):
        comments = [comments]
    if comments:
        comments.reverse()
        content += '\n\n---\n'
        for j in range(len(comments)):
            comment = comments[j]
            publisherUserId = comment['publisherUserId']
            publisherNick = comment['publisherNick']
            publisherContent = comment['content']
            commentPublishTime = comment['publishTime']
            commentPublishTime = int2time(commentPublishTime)
            replyToUserId = comment['replyToUserId']
            # decodedpublisherUserId = base64.b64decode(publisherUserId)  # 然而还是乱码……
            # decodedreplyToUserId = base64.b64decode(replyToUserId)  # 然而还是乱码……
            # publisherContentMD = html2text.html2text(publisherContent).strip('\r\n\t ')
            # publisherContentMD = md(publisherContent).strip('\r\n\t ')
            # publisherContentText = html.unescape(publisherContent)

            replyToStr = ''
            if replyToUserId in id2name_dict:
                Nicks = id2name_dict[replyToUserId]
                Nicks_only = [x[0] for x in Nicks]
                Nicks_only = deduce_list(Nicks_only)
                if len(Nicks_only) >= 2:
                    print(Nicks)
                Nicks.sort(key=lambda x: x[-1])
                Nick = Nicks[-1][0]
                replyToStr = ' 回复【' + md(Nick) + '】'

            line = '\n`' + commentPublishTime + '` 【' + md(publisherNick) + '】'
            line += replyToStr + ' ' + md(publisherContent) + '\n'

            content += line
    return content


def get_id2name_dict(xml_text):
    id2name_dict = {}
    doc = xmltodict.parse(xml_text)
    posts = doc['lofterBlogExport']['PostItem']
    posts.reverse()
    for i in range(len(posts)):
        post = posts[i]
        if 'commentList' in post:
            commentList = post['commentList']
            comments = commentList['comment']
            if not isinstance(comments, list):
                comments = [comments]
            for j in range(len(comments)):
                comment = comments[j]
                publisherUserId = comment['publisherUserId']
                publisherNick = comment['publisherNick']
                commentPublishTime = comment['publishTime']
                commentPublishTime = int2time(commentPublishTime)
                if publisherUserId not in id2name_dict:
                    id2name_dict[publisherUserId] = []
                tup = (publisherNick, commentPublishTime)
                id2name_dict[publisherUserId].append(tup)
    return id2name_dict


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

        self.export_type = 'Hexo'
        self.display_comments = True  # 是否在博文中显示历史评论

        self.GitHubPathStr = '你的GitHub主文件夹路径'
        self.owner = '你的GitHub账号名'
        self.repo_name = '你存放图片的GitHub库名称'

        self.ratio = 3

        # ================框架================
        self.button1 = wx.Button(self.pnl, wx.ID_ANY, '执行任务')

        self.st11 = wx.StaticText(self.pnl, label='GitHub主文件夹：')
        self.tc11 = wx.TextCtrl(self.pnl, wx.ID_ANY, value=self.GitHubPathStr)

        self.st12 = wx.StaticText(self.pnl, label='GitHub账号名：')
        self.tc12 = wx.TextCtrl(self.pnl, wx.ID_ANY, value=self.owner)

        self.st13 = wx.StaticText(self.pnl, label='GitHub库名称：')
        self.tc13 = wx.TextCtrl(self.pnl, wx.ID_ANY, value=self.repo_name)

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

        self.cb = wx.CheckBox(self.pnl, label='在输出文件中包含评论')
        self.cb.SetValue(self.display_comments)

        self.sampleList = ['Hexo', 'Hugo', 'Jekyll', 'Gridea']
        self.rbox = wx.RadioBox(self.pnl, -1, "迁移到", (0, 0), wx.DefaultSize,
                                self.sampleList, 4, wx.RA_SPECIFY_COLS)

        # ================尺寸器================
        # self.sBox = wx.BoxSizer()  # 水平尺寸器，不带参数则为默认的水平尺寸器

        self.vBox = wx.BoxSizer(wx.VERTICAL)  # 垂直尺寸器

        # 给尺寸器添加组件，从左往右，从上到下

        self.vBox.Add(self.button1, proportion=1, flag=wx.EXPAND | wx.ALL, border=pad)

        self.vBox.Add(self.rbox, proportion=1, flag=wx.EXPAND | wx.ALL, border=pad)

        self.vBox.Add(self.cb, proportion=1, flag=wx.EXPAND | wx.ALL, border=pad)

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

        # self.vBox.Add(self.st0, proportion=1, flag=wx.EXPAND | wx.ALL, border=pad)
        # self.vBox.Add(self.tc0, proportion=1, flag=wx.EXPAND | wx.ALL, border=pad)

        self.sBox0 = wx.BoxSizer()  # 水平尺寸器，不带参数则为默认的水平尺寸器
        self.sBox0.Add(self.st0, proportion=1, flag=wx.EXPAND | wx.ALL, border=pad)
        self.sBox0.Add(self.tc0, proportion=self.ratio, flag=wx.EXPAND | wx.ALL, border=pad)
        self.vBox.Add(self.sBox0, proportion=1, flag=wx.EXPAND | wx.ALL, border=pad)

        # self.vBox.Add(self.st1, proportion=1, flag=wx.EXPAND | wx.ALL, border=pad)
        # self.vBox.Add(self.tc1, proportion=1, flag=wx.EXPAND | wx.ALL, border=pad)

        self.sBox1 = wx.BoxSizer()  # 水平尺寸器，不带参数则为默认的水平尺寸器
        self.sBox1.Add(self.st1, proportion=1, flag=wx.EXPAND | wx.ALL, border=pad)
        self.sBox1.Add(self.tc1, proportion=self.ratio, flag=wx.EXPAND | wx.ALL, border=pad)
        self.vBox.Add(self.sBox1, proportion=1, flag=wx.EXPAND | wx.ALL, border=pad)

        # self.vBox.Add(self.st2, proportion=1, flag=wx.EXPAND | wx.ALL, border=pad)
        # self.vBox.Add(self.tc2, proportion=1, flag=wx.EXPAND | wx.ALL, border=pad)

        self.sBox2 = wx.BoxSizer()  # 水平尺寸器，不带参数则为默认的水平尺寸器
        self.sBox2.Add(self.st2, proportion=1, flag=wx.EXPAND | wx.ALL, border=pad)
        self.sBox2.Add(self.tc2, proportion=self.ratio, flag=wx.EXPAND | wx.ALL, border=pad)
        self.vBox.Add(self.sBox2, proportion=1, flag=wx.EXPAND | wx.ALL, border=pad)

        # self.vBox.Add(self.st3, proportion=1, flag=wx.EXPAND | wx.ALL, border=pad)
        # self.vBox.Add(self.tc3, proportion=1, flag=wx.EXPAND | wx.ALL, border=pad)

        self.sBox3 = wx.BoxSizer()  # 水平尺寸器，不带参数则为默认的水平尺寸器
        self.sBox3.Add(self.st3, proportion=1, flag=wx.EXPAND | wx.ALL, border=pad)
        self.sBox3.Add(self.tc3, proportion=self.ratio, flag=wx.EXPAND | wx.ALL, border=pad)
        self.vBox.Add(self.sBox3, proportion=1, flag=wx.EXPAND | wx.ALL, border=pad)

        # self.vBox.Add(self.st4, proportion=1, flag=wx.EXPAND | wx.ALL, border=pad)
        # self.vBox.Add(self.tc4, proportion=self.ratio, flag=wx.EXPAND | wx.ALL, border=pad)

        self.sBox4 = wx.BoxSizer()  # 水平尺寸器，不带参数则为默认的水平尺寸器
        self.sBox4.Add(self.st4, proportion=1, flag=wx.EXPAND | wx.ALL, border=pad)
        self.sBox4.Add(self.tc4, proportion=self.ratio, flag=wx.EXPAND | wx.ALL, border=pad)
        self.vBox.Add(self.sBox4, proportion=self.ratio, flag=wx.EXPAND | wx.ALL, border=pad)

        # self.vBox.Add((0, 30))

        self.sBox5 = wx.BoxSizer()  # 水平尺寸器，不带参数则为默认的水平尺寸器
        self.sBox5.Add(self.st_progress, proportion=1, flag=wx.EXPAND | wx.ALL, border=pad)
        self.sBox5.Add(self.gauge, proportion=self.ratio, flag=wx.EXPAND | wx.ALL, border=pad)
        self.vBox.Add(self.sBox5, proportion=1, flag=wx.EXPAND | wx.ALL, border=pad)

        # self.vBox.Add(self.st_progress, proportion=1, flag=wx.EXPAND | wx.ALL, border=pad)
        # self.vBox.Add(self.gauge, proportion=1, flag=wx.EXPAND | wx.ALL, border=pad)

        # 设置主尺寸
        self.pnl.SetSizer(self.vBox)  # 因为sBox被嵌套在vBox上，所以以vBox为主尺寸

        # ================绑定================
        self.button1.Bind(wx.EVT_BUTTON, self.onStartButton)
        self.rbox.Bind(wx.EVT_RADIOBOX, self.onRadioBox)
        self.cb.Bind(wx.EVT_CHECKBOX, self.onCheck)

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

        # # ================工具栏================
        # self.toolbar = self.CreateToolBar()
        #
        # save_ico = wx.ArtProvider.GetBitmap(wx.ART_FILE_SAVE, wx.ART_TOOLBAR, icon_size)
        # self.saveTool = self.toolbar.AddTool(wx.ID_ANY, '保存', save_ico, '保存')
        #
        # self.toolbar.AddSeparator()
        #
        # print_ico = wx.ArtProvider.GetBitmap(wx.ART_PRINT, wx.ART_TOOLBAR, icon_size)
        # self.printTool = self.toolbar.AddTool(wx.ID_ANY, '打印', print_ico, '打印')
        #
        # delete_ico = wx.ArtProvider.GetBitmap(wx.ART_DELETE, wx.ART_TOOLBAR, icon_size)
        # self.deleteTool = self.toolbar.AddTool(wx.ID_ANY, '删除', delete_ico, '删除')
        #
        # self.toolbar.AddSeparator()
        #
        # previous_ico = wx.ArtProvider.GetBitmap(wx.ART_GOTO_FIRST, wx.ART_TOOLBAR, icon_size)
        # self.previousTool = self.toolbar.AddTool(wx.ID_ANY, '向前', previous_ico, '向前')
        #
        # next_ico = wx.ArtProvider.GetBitmap(wx.ART_GOTO_LAST, wx.ART_TOOLBAR, icon_size)
        # self.nextTool = self.toolbar.AddTool(wx.ID_ANY, '向后', next_ico, '向后')
        #
        # self.toolbar.AddSeparator()
        #
        # undo_ico = wx.ArtProvider.GetBitmap(wx.ART_UNDO, wx.ART_TOOLBAR, icon_size)
        # self.undoTool = self.toolbar.AddTool(wx.ID_UNDO, '撤销', undo_ico, '撤销')
        # self.toolbar.EnableTool(wx.ID_UNDO, False)
        #
        # redo_ico = wx.ArtProvider.GetBitmap(wx.ART_REDO, wx.ART_TOOLBAR, icon_size)
        # self.redoTool = self.toolbar.AddTool(wx.ID_REDO, '重做', redo_ico, '重做')
        # self.toolbar.EnableTool(wx.ID_REDO, False)
        #
        # # ================绑定================
        # self.Bind(wx.EVT_MENU, self.onSave, self.saveTool)
        # self.Bind(wx.EVT_MENU, self.onPrint, self.printTool)
        # self.Bind(wx.EVT_MENU, self.onDelete, self.deleteTool)
        # self.Bind(wx.EVT_TOOL, self.onUndo, self.undoTool)
        # self.Bind(wx.EVT_TOOL, self.onRedo, self.redoTool)
        #
        # self.toolbar.Realize()  # 准备显示

    def get_https_url(self, jpg_url):
        m_server = re.search(p_server, jpg_url)
        jpg_url_https = jpg_url.replace('http://', 'https://', 1)
        jpg_name = Path(jpg_url).name

        if m_server and 'netease.com' in jpg_url:
            server = m_server.group(1)
            # jpg_url = 'http://' + server + '.nosdn.127.net/img/' + jpg_name
            jpg_url_https = 'https://' + server + '.nosdn.127.net/img/' + jpg_name

        # ================图床迁移-GitHub================
        down_jpg_name = jpg_name
        if m_server and not Path(jpg_url).stem.isdigit():
            down_jpg_name = 'img_' + jpg_name
            # print(down_jpg_name)

        self.GitHub = Path(self.GitHubPathStr)
        self.jpg_dir = self.GitHub / self.repo_name
        jpg_path = self.jpg_dir / down_jpg_name
        # print(jpg_path)

        if jpg_path.exists():
            jpg_url_https = 'https://' + str(gh_prefix / self.owner / self.repo_name / 'master' / down_jpg_name)

        return jpg_url_https

    def markdown_pic(self, match):
        jpg_url = match.group(1)
        jpg_url = jpg_url.split('?')[0]
        jpg_url_https = self.get_https_url(jpg_url)
        string = '\n![](' + jpg_url_https + ')\n'
        return string

    def generate(self, xml_text, id2name_dict, author, md_dir, export_type, display_comments):
        doc = xmltodict.parse(xml_text)
        posts = doc['lofterBlogExport']['PostItem']
        posts.reverse()

        for i in range(len(posts)):
            post = posts[i]
            raw_title = post['title']
            if raw_title:
                title = raw_title
            else:
                title = str(i + 1)

            publishTime = post['publishTime']
            modifyTime = publishTime
            if 'modifyTime' in post:
                modifyTime = post['modifyTime']

            publishDate = int2time(publishTime, formatter='%Y-%m-%d')
            publishTime = int2time(publishTime)
            modifyTime = int2time(modifyTime)

            tag = ''
            if 'tag' in post:
                tag = post['tag']

            post_type = post['type']
            permalink = post['permalink']

            categories = [post_type]
            tags = tag.split(',')

            head_matter = get_head_matter(export_type, title, publishTime, modifyTime, author, categories, tags,
                                          permalink)

            caption = ''
            if 'caption' in post:
                caption = post['caption']

            embed = {}
            if 'embed' in post:
                embed = post['embed']
            if embed != {}:
                embed = json.loads(embed)

            if post_type == 'Text':
                content = ''
                if 'content' in post:
                    content = post['content']
                content = re.sub(p_img, self.markdown_pic, content)

            elif post_type == 'Photo':
                photoLinks = ''
                if 'photoLinks' in post:
                    photoLinks = post['photoLinks']
                photoLinks = json.loads(photoLinks)  # 将json字符串转换成python对象

                content = ''
                if isinstance(caption, str):
                    content += caption

                for photoLink in photoLinks:
                    if 'raw' in photoLink and isinstance(photoLink['raw'], str):
                        jpg_url = photoLink['raw']
                    elif 'orign' in photoLink and isinstance(photoLink['orign'], str):
                        jpg_url = photoLink['orign']
                    else:
                        jpg_url = ''
                        # print(photoLink)

                    if jpg_url != '':
                        jpg_url_https = self.get_https_url(jpg_url)
                        content += '\n\n![](' + jpg_url_https + ')'

            elif post_type == 'Video':
                originUrl = embed['originUrl']
                content = caption
                content += '\n\n[' + originUrl + '](' + originUrl + ')'

            else:  # type == 'Music'
                listenUrl = embed['listenUrl']

                song_name = ''
                if 'song_name' in embed:
                    song_name = embed['song_name']

                song_name = song_name.replace('%20', ' ')

                content = caption
                content += '\n\n[' + song_name + '](' + listenUrl + ')'

            if 'commentList' in post and display_comments:
                content = get_comments(post, content, id2name_dict)

            text = head_matter + '\n\n' + content

            num_prefix = str(i + 1).zfill(len(str(len(posts)))) + ' '

            if export_type == 'Jekyll':
                md_file_stem = publishDate + '-' + safe(title)
            elif export_type == 'Gridea':
                md_file_stem = safe(permalink)
            else:  # if export_type in ['Hexo','Hugo']:
                if raw_title:
                    md_file_stem = num_prefix + safe(raw_title)
                else:
                    md_file_stem = num_prefix + publishTime.replace(':', '-')

            md_file_path = md_dir / (md_file_stem + '.md')

            write_text(md_file_path, text)

            # self.show_label_str(self.tc3, str(md_file_path))

            wx.CallAfter(self.tc3.Clear)
            wx.CallAfter(self.tc3.AppendText, str(md_file_path))

            gau = 100 * (i + 1) / len(posts)
            wx.CallAfter(self.gauge.SetValue, gau)

    def process_xmls(self, xmls, export_type, display_comments, event_obj):
        wx.CallAfter(event_obj.Disable)
        start_time = time.time()  # 初始时间戳

        for x in range(len(xmls)):
            xml_file_path = xmls[x]

            # xml_text = open(xml_file_path).read()
            with open(xml_file_path, mode="r", encoding="utf-8") as fp:
                xml_text = fp.read()
            xml_text = re.sub(u"[\x00-\x08\x0b-\x0c\x0e-\x1f]+", u"", xml_text)

            author = '你的lofter昵称'
            m_lofter = re.search(p_lofter, xml_file_path.stem)
            if m_lofter:
                author = m_lofter.group(1)

            md_dir_name = 'markdown-' + export_type + '-' + author
            md_dir = current_dir / md_dir_name
            make_dir(md_dir)

            self.show_label_str(self.tc1, str(xml_file_path))
            self.show_label_str(self.tc2, str(md_dir))

            id2name_dict = get_id2name_dict(xml_text)
            self.generate(xml_text, id2name_dict, author, md_dir, export_type, display_comments)

            # gau = 100 * (x + 1) / len(xmls)
            # wx.CallAfter(self.gauge.SetValue, gau)
        # ================运行时间计时================
        show_run_time = run_time(start_time)
        label_str = '程序结束！' + show_run_time

        self.show_label_str(self.tc3, label_str)

        wx.CallAfter(event_obj.Enable)

    def onStartButton(self, event):
        event_obj = event.GetEventObject()

        self.GitHubPathStr = self.tc11.GetValue()
        self.owner = self.tc12.GetValue()
        self.repo_name = self.tc13.GetValue()

        self.thread_it(self.process_xmls, xmls, self.export_type, self.display_comments, event_obj)
        # event.GetEventObject().Enable()

    def OnExit(self, event):
        self.Close(True)

    def OnHello(self, event):
        wx.MessageBox('来自 wxPython', '你好')

    # def onSave(self, event):
    #     wx.MessageBox('保存自 wxPython')
    #
    # def onPrint(self, event):
    #     wx.MessageBox('打印自 wxPython')
    #
    # def onDelete(self, event):
    #     wx.MessageBox('删除自 wxPython')
    #
    # def onUndo(self, event):
    #     wx.MessageBox('撤销自 wxPython')
    #
    # def onRedo(self, event):
    #     wx.MessageBox('重做自 wxPython')

    def OnAbout(self, event):
        wx.MessageBox(message=about_me,
                      caption='关于' + app_name,
                      style=wx.OK | wx.ICON_INFORMATION)

    def onRadioBox(self, event):
        self.export_type = self.rbox.GetStringSelection()

    def onCheck(self, event):
        sender = event.GetEventObject()
        isChecked = sender.GetValue()
        self.display_comments = isChecked

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
    current_dir = os.path.dirname(os.path.abspath(__file__))
    current_dir = Path(current_dir)

    dirpath = os.getcwd()

    xmls = get_di_xml(current_dir)
    xmls = [x for x in xmls if x.stem.startswith('LOFTER-')]

    app_name = 'Lofter2Hexo v1.2 by 墨问非名'
    about_me = '这是将Lofter导出的xml转换成给静态博客使用的markdown的软件。'

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
