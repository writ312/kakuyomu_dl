# coding: UTF-8

# 警告: README.md を必ず読んでください
# WARNING: Be sure to read README.md

login_data = {
    "narouid" : "****",
    "pass" : "****"
}

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

def main():
    # 新しいEPUBブックを作成
    book = epub.EpubBook()
    headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.0.0 Safari/537.36"
    }

    session = requests.Session()
    login_url = "https://syosetu.com/login/login/"

    req = session.post(login_url,data=login_data,headers=headers)

    data = session.get(input("URL >> "),headers=headers)
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

    separater = "************************************************"
    for idx, episodeTitle in enumerate(titles,1) :
        data = session.get(f"https://ncode.syosetu.com/txtdownload/dlstart/ncode/{ncode}/?no={idx}&hankaku=0&code=utf-8&kaigyo=crlf",headers=headers)
        print(f"get Chapter {idx} ... OK")
        
        content = "<p>" + data.text.replace("\r\n\r\n","</p><br/><br/><p>")
        
        matches = [match.start() for match in re.finditer(separater.replace("*","\*"), content)]
        if len(matches) == 2 :
            content = '<div class="maegaki">' + content.replace(separater,'</div>',1)
            content = content.replace(separater,'<div class="maegaki">') + '</div>'
        elif len(matches) == 1 :
            if matches[0] < (len(content) // 2) : 
                content = '<div class="maegaki">' + content.replace(separater,'</div>')
            else :
                content = content.replace(separater,'<div class="maegaki">') + '</div>'
        
        name_initial = str(idx).zfill(3)
        page = epub.EpubHtml(
            title=episodeTitle, file_name=f"chap_{name_initial}.xhtml", lang="ja"
        )
        formatContetns = f"<h1>{episodeTitle}</h1>{content}"
        page.content = formatContetns
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
    book.spine = ["toc:ncx,page-progression-direction:rtl","nav"]
    book.spine += book_items

    # EPUBファイルを保存
    print("Finish Create EPUB\n")
    print(f"Export to  {title}-{author}.epub ...... ")

    epub.write_epub(name = f"{title}-{author}.epub",book =  book)
    print("OK\n")

main()