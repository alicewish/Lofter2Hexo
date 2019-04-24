import base64
import html
import json
import re
from collections import OrderedDict
from datetime import datetime
from pathlib import Path

import html2text
import xmltodict
from markdownify import markdownify as md

p_server = re.compile(r'(imglf\d?)', re.I)

p_img = re.compile(r'<img src="([^"]+?)"([^>]*)>', re.I)


def list2str(some_list):
    some_string = ''
    if isinstance(some_list, list):
        some_string = "[" + ", ".join(some_list) + "]"
    elif isinstance(some_list, str):
        some_string = some_list
    return some_string


def format_hugo_title(title):
    if "'" in title or "#" in title or "@" in title or "[" in title or "]" in title or "+" in title or "!" in title or ":" in title:  # or "：" in title or "（" in title or "）" in title
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
    f = open(file_path, 'w')
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


def head_matter_hexo(title, publishTime, modifyTime, author, categories, tags, permalink, description='', layout='post',
                     mathjax=False):
    # ================构造头部================
    content = '---'
    title_info = format_hugo_title(title)

    permalink_lower = permalink.lower()
    slug = '"' + permalink_lower + '"'
    content += '\nlayout: ' + layout
    content += '\ntitle: ' + title_info
    content += '\ndate: ' + publishTime
    content += '\nupdated: ' + modifyTime
    content += '\ncomments: true'
    content += '\ncategories: ' + list2str(categories)
    content += '\ntags: ' + list2str(tags)
    if not title.isdigit():
        content += '\npermalink: ' + slug
    content += '\nauthor: "' + author + '"'
    content += '\ndescription: "' + description + '"'
    content += '\ntoc: true'

    if mathjax:
        content += '\nmathjax: ' + str(mathjax).lower()

    content += '\n---'
    return content


def get_https_url(jpg_url):
    m_server = re.search(p_server, jpg_url)
    jpg_url_https = jpg_url.replace('http://', 'https://', 1)

    jpg_name = Path(jpg_url).name
    if m_server and not Path(jpg_url).stem.isdigit():
        jpg_name = 'img_' + jpg_name

    jpg_path = jpg_dir / jpg_name

    if jpg_path.exists():
        jpg_url_https = 'https://' + str(gh_prefix / owner / repo_name / 'master' / jpg_name)
    return jpg_url_https


def markdown_pic(match):
    jpg_url = match.group(1)
    jpg_url = jpg_url.split('?')[0]
    jpg_url_https = get_https_url(jpg_url)
    string = '\n![](' + jpg_url_https + ')\n'
    return string


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
            decodedpublisherUserId = base64.b64decode(publisherUserId)  # 然而还是乱码……
            decodedreplyToUserId = base64.b64decode(replyToUserId)  # 然而还是乱码……

            publisherContentMD = html2text.html2text(publisherContent).strip('\r\n\t ')
            publisherContentMD = md(publisherContent).strip('\r\n\t ')
            publisherContentText = html.unescape(publisherContent)

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


def process():
    id2name_dict = {}
    with open(file_path) as fd:
        doc = xmltodict.parse(fd.read())
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

    with open(file_path) as fd:
        doc = xmltodict.parse(fd.read())
        posts = doc['lofterBlogExport']['PostItem']
        posts.reverse()

        for i in range(len(posts)):
            post = posts[i]
            title = post['title']
            if not title:
                title = str(i + 1)

            md_file_name = safe(title) + '.md'
            md_file_path = md_dir / md_file_name

            publishTime = post['publishTime']
            modifyTime = publishTime
            if 'modifyTime' in post:
                modifyTime = post['modifyTime']

            publishTime = int2time(publishTime)
            modifyTime = int2time(modifyTime)

            tag = ''
            if 'tag' in post:
                tag = post['tag']

            post_type = post['type']
            permalink = post['permalink']

            categories = [post_type]
            tags = tag.split(',')

            head_matter = head_matter_hexo(title, publishTime, modifyTime, author, categories, tags, permalink)

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
                content = re.sub(p_img, markdown_pic, content)
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
                        print(photoLink)

                    if jpg_url != '':
                        jpg_url_https = get_https_url(jpg_url)
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
            write_text(md_file_path, text)


if __name__ == '__main__':
    GitHub = Path('你的GitHub文件夹路径')
    gh_prefix = Path(r'raw.githubusercontent.com')

    display_comments = True  # 是否在博文中显示历史评论
    file_path = '你的xml文件路径'
    author = '你的lofter昵称'
    md_dir = Path('你的Hexo博客的/source/_posts文件夹路径')
    repo_name = '你的存放图片的GitHub库名称'
    owner = '你的GitHub账号名'

    jpg_dir = GitHub / repo_name

    process()
