import base64
import re
import requests
import time

def grab_and_base64(url, retry=10):
    """
    !assume python3!
    input:  str, the url of a post, e.g. https://username.lofter.com/post/1f1f1f1f_f1f1f1f1
    return: image encoded as string (base64) and a flag
    """
    ret = []
    flag = 1
    pattern1 = re.compile('bigimgsrc="http://imglf[0-9].nosdn[0-9]*.126.net/img/[0-9a-zA-Z]+.png')
    pattern2 = re.compile('bigimgsrc="http://imglf[0-9].nosdn[0-9]*.126.net/img/[0-9a-zA-Z]+.jpg')
    html = requests.get(url)
    for i in range(retry):
        if html.ok: break
        else: 
            print('[warning::grab_and_base64] failed to get html; [{0}]th try...'.format(i))
            time.sleep(3)
            html = requests.get(url)
    if not html.ok:
        print('[error::grab_and_base64] failed to get html for [{0}]'.format(url))
        return 1
    img_urls = re.findall(pattern1, html.content.decode()) + re.findall(pattern2, html.content.decode())
    if len(img_urls)==0:
        print('[warning::grab_and_base64] no image found for [{0}]? '.format(url))
        print('                           If there should be, please check the image urls and improve regex pattern.')
        return 1
    for img_url in img_urls:
        img = requests.get(img_url.split('bigimgsrc="')[1])
        for i in range(retry):
            if img.ok: break
            else:
                print('[warning::grab_and_base64] failed to download img, retry...')
                time.sleep(3)
                img = requests.get(img_url)
        if not img.ok:
            print('[FAILING] cant download {0}, skipping.'.format(img_url))
            continue
        img = base64.b64encode(img.content)
        ret.append(img.decode())
    if len(ret)==len(img_urls): flag = 0  # all clear
    return ret, flag

if __name__=='__main__':
    ret = grab_and_base64('https://buffycoat.lofter.com/post/31a777_12ab0f1d3')
    test, flag = ret
    with open('testfunc.html', 'w') as file:
        for base in test:
            file.write('<img src="data:image/jpeg;charset=utf-8;base64,  {0}"/>\n'.format(base))
