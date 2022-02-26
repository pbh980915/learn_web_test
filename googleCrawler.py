import requests
from bs4 import BeautifulSoup
from pymongo import MongoClient
from datetime import datetime
import random

# 몽고DB
client = MongoClient(host="localhost", port=27017)
# myweb 데이터베이스
db = client.myweb
# board 컬렉션
col = db.board

# 구글 검색시 헤더값을 설저하지 않으면 브라우저에서 보이는것과 다른 결과가 나옴
header = {"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/97.0.4692.99 Safari/537.36"}
# 검색 결과의 5페이지까지만 수집
for i in range(6):
    url = "https://www.google.com/search?q={}&start={}".format("ㅎㅂ", i+1)
    print(url)
    r = requests.get(url, headers=header)
    bs = BeautifulSoup(r.text, "lxml")
    lists = bs.select("div.jtfYYd")

    for sample in lists:
        current_utc_time = round(datetime.utcnow().timestamp() * 1000)
        title = sample.select_one("h3.LC20lb").text
        contents = sample.select_one("div.VwiC3b").text
        col.insert_one({
                "name": "테스터",
                "writer_id": "",
                "title": title,
                "contents": contents,
                "view": random.randrange(30, 777),
                "pubdate": current_utc_time
        })
        