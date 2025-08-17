# coding: UTF-8

# 警告: README.md を必ず読んでください
# WARNING: Be sure to read README.md


import os
from pathlib import Path
from bs4 import BeautifulSoup
import requests
import time
import re
import regex

from ebooklib import epub

import sys

args = sys.argv

# 現在のファイルのディレクトリに移動
this_file = Path(os.path.abspath(__file__))
os.chdir(this_file.parent)

narou_login_data = {
    "narouid" : "****",
    "pass" : "****"
}

# /works/<num> からChapterのURLを取得
def kakuyomu_get_base_info(url):
    data = requests.get(url)
    soup = BeautifulSoup(data.text, "html.parser")

    # タイトルを抽出
    og_title = soup.find("meta",property="og:title").attrs["content"]
    
    match = re.match(r"(.+)（(.+)） - カクヨム", og_title)

    if match:
        title = match.group(1) 
        author = match.group(2)

    first_episode_url = f"https://kakuyomu.jp{soup.select('a.WorkTocSection_link__ocg9K')[0].get('href')}"

    return (title, author, first_episode_url)


# get_chapter_urlsで取得したChapterにアクセスしてテキストを取ってきてPDFに変換
def kakuyomu_get_episode_contents(url):
    print(f"get {url} ......")
    data = requests.get(url)
    soup = BeautifulSoup(data.text, "html.parser")
    episodeTitle = soup.find("p", class_="widget-episodeTitle").text
    contents_list = soup.find("div", class_="widget-episodeBody").contents
    content_list_fillter = list(filter(lambda s: s != "\n", contents_list))

    # content = re.sub("[\'\\n\']+","<br/>",content)
    content = str(content_list_fillter)[1:-1]
    content = content.replace(">,", ">")
    print("OK \n")
    
    next_episode_element = soup.select("a#contentMain-readNextEpisode")
    if (len(next_episode_element) == 1) :
        next_url = f"https://kakuyomu.jp{soup.select('a#contentMain-readNextEpisode')[0].get('href')}"
    else :
        next_url = None
    return (episodeTitle, content, next_url)

def main_kakuyomu(url) :
        # 新しいEPUBブックを作成
    book = epub.EpubBook()
    (title, author, first_episode_url) = kakuyomu_get_base_info(url)

    print("Create EPUB\n")
    # メタデータをセット
    book.set_identifier(f"{title}_{author}")
    book.set_title(title)
    book.set_language("jp")
    book.set_direction("rtl")
    # 作者情報
    book.add_author(author)

    # CSSスタイルを定義し、ブックに追加

    style = open("default.css", "r",encoding="utf8")
    defualt_css = epub.EpubItem(
        uid="style_default",
        file_name="style/default.css",
        media_type="text/css",
        content=style.read(),
    )
    style.close()

    book.add_item(defualt_css)

    print("Set Metadata ...... OK\n")

    book_items = []

    (episodeTitle, content, next_url) = kakuyomu_get_episode_contents(first_episode_url)
    idx = 0

    while next_url is not None :
        name_initial = str(idx).zfill(3)
        page = epub.EpubHtml(
            title=episodeTitle, file_name=f"chap_{name_initial}.xhtml", lang="ja"
        )
        formatContetns = f"<h1>{episodeTitle}</h1>{content}"
        page.content = formatContetns
        page.add_item(defualt_css)
        book_items.append(page)

        idx += 1
        (episodeTitle, content, next_url) = kakuyomu_get_episode_contents(next_url)

        # 連続してアクセスしないように3s間とる
        if idx % 10 == 0:
            time.sleep(3)

    # 章をブックに追加
    for item in book_items:
        book.add_item(item)

    print("Set Contents ...... OK\n")
    # 目次を作成
    book.toc = tuple(book_items)

    # ナビゲーションファイルを作成し、ブックに追加
    book.add_item(epub.EpubNcx())
    nav = epub.EpubNav()
    nav.add_item(defualt_css)
    book.add_item(nav)

    print("Set TOC ...... OK\n")
    # スピンドルのオプション
    book.spine = ["nav"]
    book.spine += book_items

    # EPUBファイルを保存
    print("Finish Create EPUB\n")
    print(f"Export to  {title}-{author}.epub ...... ")

    epub.write_epub(name = f"{title}-{author}.epub",book =  book)
    print("OK\n")

def main_narou(url):
    # 新しいEPUBブックを作成
    book = epub.EpubBook()
    headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.0.0 Safari/537.36"
    }

    session = requests.Session()
    login_url = "https://syosetu.com/login/login/"

    req = session.post(login_url,data=narou_login_data,headers=headers)

    data = session.get(url,headers=headers)
    soup = BeautifulSoup(data.text, "html.parser")

    # タイトルを抽出
    title = soup.find("h1", class_="p-novel__title").text
    author = soup.find("div","p-novel__author").next.next.text

    links = soup.find_all("a", class_="c-under-nav__item")
    if links[1].text != "TXTダウンロード" :
        raise ValueError("TXTダウンロードが見つかりません")
    txt_link = soup.find_all("a", class_="c-under-nav__item")[1].attrs["href"]

    data = session.get(txt_link, headers=headers)
    soup = BeautifulSoup(data.text, "html.parser")

    titles = [op.text for op in soup.find("select").find_all("option")]

    ncode = match = re.search(r"ncode/(\d+)/", txt_link).group(1)
    download_url = f"https://ncode.syosetu.com/txtdownload/dlstart/ncode/{ncode}/?no=1&hankaku=0&code=utf-8&kaigyo=crlf"


    print("Create EPUB\n")
    # メタデータをセット
    book.set_identifier(f"{title}_{author}")
    book.set_title(title)
    book.set_language("jp")
    book.set_direction("rtl")
    # 作者情報
    book.add_author(author)

    # CSSスタイルを定義し、ブックに追加

    style = open("default.css", "r",encoding="utf8")
    defualt_css = epub.EpubItem(
        uid="style_default",
        file_name="style/default.css",
        media_type="text/css",
        content=style.read(),
    )
    style.close()

    book.add_item(defualt_css)

    print("Set Metadata ...... OK\n")

    book_items = []
    maegaki_separater = "********************************************"
    atogaki_separater = "************************************************"
    #re.split(r'\*{44,48}', data.text)


    #splitlines()
    for idx, episodeTitle in enumerate(titles,1) :
        contents = session.get(f"https://ncode.syosetu.com/txtdownload/dlstart/ncode/{ncode}/?no={idx}&hankaku=0&code=utf-8&kaigyo=crlf",headers=headers).text
        print(f"get Chapter {idx} ... OK")
        
            # 明示的ルビ（｜漢字《読み》）
        contents = regex.sub(r'[｜|](\S+?)《(.*?)》', r'<ruby>\1<rt>\2</rt></ruby>', contents)

        # 暗黙的ルビ（漢字《読み》）
        contents = regex.sub(r'(\p{Han}+?)《(.*?)》', r'<ruby>\1<rt>\2</rt></ruby>', contents)

        # 簡易ルビ（漢字(読み)） ※｜(読み) は除外
        contents = regex.sub(r'(?<![｜|])(\p{Han}+?)（(.+?)）', r'<ruby>\1<rt>\2</rt></ruby>', contents)

        # ルビ除外(｜（）)のパイプを削除
        contents = regex.sub(r'｜（', r'（', contents)

        #　挿絵の削除
        contents = regex.sub(r'<i.*?\|.*?>.*\n', '', contents)

        maegaki = ""
        atogaki = ""

        if atogaki_separater in contents :
            (contents, atogaki) = contents.split(atogaki_separater)
            atogaki = '<div class="maegaki">' + "".join(f"<p>{item}</p>" for item in atogaki.splitlines()) + '</div>'

        if maegaki_separater in contents :
            (maegaki,contents) = contents.split(maegaki_separater)      
            maegaki = '<div class="maegaki">' + "".join(f"<p>{item}</p>" for item in maegaki.splitlines()) + '</div>'
            
        contents = "".join(f"<p>{item}</p>" for item in contents.splitlines())
        
        page = epub.EpubHtml(
            title=episodeTitle, file_name=f"chap_{str(idx).zfill(3)}.xhtml", lang="ja"
        )
        page.content = f"<h1>{episodeTitle}</h1>{maegaki}{contents}{atogaki}"
        page.add_item(defualt_css)
        book_items.append(page)

        # 連続してアクセスしないように3s間とる
        if idx % 10 == 0:
            time.sleep(3)

    # 章をブックに追加
    for item in book_items:
        book.add_item(item)

    print("Set Contents ...... OK\n")
    # 目次を作成
    book.toc = tuple(book_items)

    # ナビゲーションファイルを作成し、ブックに追加
    book.add_item(epub.EpubNcx())
    nav = epub.EpubNav()
    nav.add_item(defualt_css)
    book.add_item(nav)

    print("Set TOC ...... OK\n")
    # スピンドルのオプション
    book.spine = ["nav"]
    book.spine += book_items

    # EPUBファイルを保存
    print("Finish Create EPUB\n")
    print(f"Export to  {title}-{author}.epub ...... ")

    epub.write_epub(name = f"{title}-{author}.epub",book =  book)
    print("OK\n")


def main():
    url = input("URL >> ")
    if url.startswith("https://kakuyomu.jp") :
        main_kakuyomu(url)
    else :
        main_narou(url)



main()