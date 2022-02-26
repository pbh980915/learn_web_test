
from flask import Flask
from flask import request
from flask import render_template
from flask import abort
from flask import redirect
from flask import url_for
from flask import flash
from flask import session
from flask_pymongo import PyMongo
from bson.objectid import ObjectId
from datetime import datetime
from datetime import timedelta
import time
import math
from functools import wraps

app = Flask(__name__)

# mongodb connect
app.config["MONGO_URI"] = "mongodb://localhost:27017/myweb"
app.config["SECRET_KEY"] = "!"
# session 유지 시간
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(seconds=10)
mongo = PyMongo(app)


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("id") is None or session.get("id") == "":
            return redirect(url_for("member_login", next_url=request.url))
        return f(*args, **kwargs)
    return decorated_function


@app.template_filter("formdatetime")
def format_datetime(value):
    if value is None:
        return ""

    now_timestamp = time.time()
    offset = datetime.fromtimestamp(now_timestamp) - \
        datetime.utcfromtimestamp(now_timestamp)
    value = datetime.fromtimestamp(int(value) / 1000) + offset
    return value.strftime('%Y-%m-%d %H:%M:%S')


@app.route("/list")
def lists():
    # 페이지 값 (값이 없는 경우 기본값은 1)
    page = request.args.get("page", default=1, type=int)
    # 한페이지당 게시물 출력 개수
    limit = request.args.get("limit", 5, type=int)
    search = request.args.get("search", -1, type=int)
    keyword = request.args.get("keyword", type=str)
    query = {}
    # 검색어 상태 추가 리스트
    search_list = []
    if search == 0:
        # regex 검색어에 포함되는 단어를 가진 것을 찾는다.
        search_list.append({"title": {"$regex": keyword}})
    elif search == 1:
        search_list.append({"contents": {"$regex": keyword}})
    elif search == 2:
        search_list.append({"title": {"$regex": keyword}})
        search_list.append({"contents": {"$regex": keyword}})
    elif search == 3:
        search_list.append({"name": {"$regex": keyword}})

    if len(search_list) > 0:
        query = {"$or": search_list}
    print(query)
    """
    {"$or": [
        {"title": {"$regex": "파이"}},
        {"title": {"$regex": "자바"}},
        {"title": {"$regex": "안드"}},
    ]}
    """
    board = mongo.db.board
    datas = board.find(query).skip((page-1) * limit).limit(limit)

    # 개시물의 총개수
    tot_count = len(list(board.find({})))
    # 마지막 페이지의 수
    last_page_num = math.ceil(tot_count/limit)
    # 페이지 블럭을 5개
    block_size = 5
    # 현재 블럭 위치
    block_num = int((page-1)/block_size)
    # 블럭 시작 위치
    block_start = int((block_size*block_num)+1)
    # 블럭 끝 위치
    block_last = math.ceil(block_start + (block_size - 1))

    # 1-1번 부터 10개출력 page navigation
    return render_template(
        "list.html",
        datas=list(datas),
        limit=limit,
        page=page,
        block_start=block_start,
        block_last=block_last,
        last_page_num=last_page_num,
        search=search,
        keyword=keyword)


@app.route("/view")
def board_view():
    idx = request.args.get("idx")
    if idx is not None:
        page = request.args.get("page")
        search = request.args.get("search")
        keyword = request.args.get("keyword")
        board = mongo.db.board
        data = board.find_one({"_id": ObjectId(idx)})
        if data is not None:
            result = {
                "id": data.get("_id"),
                "name": data.get("name"),
                "title": data.get("title"),
                "contents": data.get("contents"),
                "pubdate": data.get("pubdate"),
                "view": data.get("view"),
                "writeid": data.get("writeid", "")
            }
            return render_template(
                "view.html",
                result=result,
                keyword=keyword,
                search=search,
                page=page)
    return abort(404)


@app.route("/write", methods=["GET", "POST"])
@login_required
def board_write():
    if request.method == "POST":
        name = request.form.get("name")
        title = request.form.get("title")
        contents = request.form.get("contents")
        pubdate = round(datetime.utcnow().timestamp() * 1000)
        # insert to dbMongo
        board = mongo.db.board
        post = {
            "name": name,
            "title": title,
            "contents": contents,
            "pubdate": pubdate,
            "writeid": session.get("id"),
            "view": 0,
        }
        x = board.insert_one(post)
        print(name, title, contents)
        print(x.inserted_id)
        return redirect(url_for("board_view", idx=x.inserted_id))
    else:
        return render_template("write.html")


@app.route("/join", methods=["GET", "POST"])
def member_join():
    if request.method == "POST":
        name = request.form.get("name", type=str)
        email = request.form.get("email", type=str)
        pass1 = request.form.get("pass1", type=str)
        pass2 = request.form.get("pass2", type=str)

        if name == "" or email == "" or pass1 == "" or pass2 == "":
            flash("입력되지 않은 값이 있습니다.")
            return render_template("join.html")

        if pass1 != pass2:
            flash("비밀번호가 일치하지 않습니다.")
            return render_template("join.html")

        members = mongo.db.members
        cnt = len(list(members.find({"email": email})))
        if cnt > 0:
            flash("중복된 이메일 주소입니다.")
            return render_template("join.html")

        current_utc_time = round(datetime.utcnow().timestamp() * 1000)
        post = {
            "name": name,
            "email": email,
            "pass": pass1,
            "joindate": current_utc_time,
            "logintime": "",
            "logincount": 0,
        }

        members.insert_one(post)

        return ""
    else:
        return render_template("join.html")


@app.route("/login", methods=["GET", "POST"])
def member_login():
    # 로그인 정보를 세션에 저장, 보안 증가, 서버 부담 증가
    # 쿠키에 저장, 보안 감소, 부담 감소
    print("a")
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("pass")
        next_url = request.form.get("next_url")

        members = mongo.db.members
        data = members.find_one({"email": email})
        print(data)
        if data is None:
            flash("회원 정보가 없습니다.")
            # get 접속이므로 로그인창이 다시 열린다.
            return redirect(url_for("member_login"))
        else:
            if data.get("pass") == password:
                session["email"] = email
                session["name"] = data.get("name")
                session["id"] = str(data.get("_id"))
                session.permanent = True
                # 세션은 자원관리를 위하여 유지시간을 할당한다.
                if next_url is not None:
                    return redirect(next_url)
                else:
                    return redirect(url_for("lists"))
            else:
                flash("비밀번호가 일치하지 않습니다.")
                return redirect(url_for("member_login"))
        return ""
    else:
        next_url = request.args.get("next_url", type=str)
        if next_url is not None:
            return render_template("login.html", next_url=next_url)
        else:
            return render_template("login.html")


@app.route("/edge", methods=["GET", "POST"])
def board_edit():
    idx = request.args.get("idx")
    return ""


@app.route("/delete", methods=["GET", "POST"])
def board_delete():
    idx = request.args.get("idx")
    return ""


if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True, port=1234)
