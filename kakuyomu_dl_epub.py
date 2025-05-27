# coding: UTF-8

# 警告: README.md を必ず読んでください
# WARNING: Be sure to read README.md


import os
from pathlib import Path
from bs4 import BeautifulSoup
import requests
import time
import re

from ebooklib import epub

import sys

args = sys.argv

# 現在のファイルのディレクトリに移動
this_file = Path(os.path.abspath(__file__))
os.chdir(this_file.parent)


# /works/<num> からChapterのURLを取得
def get_base_info(url):
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
def get_episode_contents(url):
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


def main():
    # 新しいEPUBブックを作成
    book = epub.EpubBook()
    (title, author, first_episode_url) = get_base_info(input("URL >> "))

    print("Create EPUB\n")
    # メタデータをセット
    book.set_identifier(f"{title}_{author}")
    book.set_title(title)
    book.set_language("jp")

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

    (episodeTitle, content, next_url) = get_episode_contents(first_episode_url)
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
        (episodeTitle, content, next_url) = get_episode_contents(next_url)

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
    book.spine = ["toc:ncx,page-progression-direction:rtl","nav"]
    book.spine += book_items

    # EPUBファイルを保存
    print("Finish Create EPUB\n")
    print(f"Export to  {title}-{author}.epub ...... ")

    epub.write_epub(name = f"{title}-{author}.epub",book =  book)
    print("OK\n")


main()