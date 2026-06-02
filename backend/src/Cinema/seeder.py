from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

import bcrypt
from sqlalchemy import delete, insert, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.Auth.models import Base, User
from src.Cinema.models import CinemaRoom, Movie, Seat, Showtime, TicketOrder


async def run_reset_and_seed(session: AsyncSession) -> None:
    """
    执行数据库完全清表重置，并播种符合高并发压测的豆瓣Top100微型选座票仓数据
    """
    # ==================== Step 0: 物理删表与自愈建表 (支持表结构扩展) ====================
    connection = await session.connection()
    await connection.run_sync(Base.metadata.drop_all)
    await connection.run_sync(Base.metadata.create_all)
    await session.flush()

    # ==================== Step 1: 物理清表 (双重防线) ====================
    await session.execute(delete(TicketOrder))
    await session.execute(delete(Seat))
    await session.execute(delete(Showtime))
    await session.execute(delete(CinemaRoom))
    await session.execute(delete(Movie))
    await session.execute(delete(User))
    await session.flush()

    # ==================== Step 2: 播种 1,000 名压测虚拟用户 (Raw SQL 极速注入) ====================
    hashed_passwd = "$2b$12$Jl9VH.0D4vj7.oPVzGfkW.PK8.9BNxpNqY0dui0g0ro7ju8uSSXFm"
    now_time = datetime.now(timezone.utc)

    user_list = []

    # 额外播种 1 个特权管理员用户
    user_list.append(
        {
            "uid": uuid4().hex,
            "email": "admin@cinema.com",
            "password": bcrypt.hashpw(b"admin12345", bcrypt.gensalt()).decode("utf-8"),
            "admin": 1,
            "first_name": "Cinema",
            "last_name": "Admin",
            "gender": 1,
            "birthday": None,
            "user_status": 0,
            "avatar": None,
            "current_session_id": None,
            "created_at": now_time,
            "updated_at": now_time,
            "is_deleted": 0,
        }
    )

    for i in range(1, 1001):
        user_list.append(
            {
                "uid": uuid4().hex,
                "email": f"user_{i}@test.com",
                "password": hashed_passwd,
                "admin": 0,
                "first_name": f"user_{i}",
                "last_name": "test",
                "gender": 2,
                "birthday": None,
                "user_status": 0,
                "avatar": None,
                "current_session_id": None,
                "created_at": now_time,
                "updated_at": now_time,
                "is_deleted": 0,
            }
        )

    sql_insert_user = text("""
        INSERT INTO users (uid, email, passwd, admin, first_name, last_name, gender, birthday, user_status, avatar, current_session_id, created_at, updated_at, is_deleted)
        VALUES (:uid, :email, :password, :admin, :first_name, :last_name, :gender, :birthday, :user_status, :avatar, :current_session_id, :created_at, :updated_at, :is_deleted)
    """)
    await session.execute(sql_insert_user, user_list)

    # ==================== Step 3: 播种 100 部豆瓣 Top100 殿堂级经典大片 ====================
    raw_movies = [
        ("肖申克的救赎", 142, "9.7", "剧情 / 犯罪", "希望让人自由。"),
        ("霸王别姬", 171, "9.6", "剧情 / 爱情 / 同性", "风华绝代，人戏不分。"),
        ("阿甘正传", 142, "9.5", "剧情 / 爱情", "一部美国近现代史，跑出奇迹。"),
        ("泰坦尼克号", 194, "9.5", "剧情 / 爱情 / 灾难", "失去的才是永恒的，海枯石烂。"),
        ("美丽人生", 116, "9.5", "剧情 / 喜剧 / 爱情", "最美的谎言，伟大的父爱。"),
        ("千与千寻", 125, "9.4", "动画 / 奇幻", "最好的宫崎骏，最好的久石让。"),
        ("辛德勒的名单", 195, "9.5", "剧情 / 历史 / 战争", "拯救一个人，就是拯救整个世界。"),
        ("盗梦空间", 148, "9.4", "剧情 / 科幻 / 冒险", "诺兰给了我们一场无法盗取的深海之梦。"),
        ("星际穿越", 169, "9.4", "剧情 / 科幻 / 冒险", "爱是一种力量，让我们超越时空。"),
        ("这个杀手不太冷", 110, "9.4", "剧情 / 动作 / 犯罪", "怪蜀黍和小萝莉不得不说的纯真救赎。"),
        ("楚门的世界", 103, "9.4", "剧情 / 科幻", "如果再也不能见到你，祝你早安、午安和晚安。"),
        ("忠犬八公的故事", 93, "9.4", "剧情", "永远都不能忘记你所爱的人，十年一瞬。"),
        ("三傻大闹宝莱坞", 171, "9.2", "剧情 / 喜剧 / 爱情", "做你热爱的事，成功就会不期而遇。"),
        ("海上钢琴师", 165, "9.3", "剧情 / 音乐", "每个人都要走一条自己坚定了的路。"),
        ("放牛班的春天", 97, "9.3", "剧情 / 音乐", "天籁歌声洗涤孤儿心灵，充满阳光。"),
        ("机器人总动员", 98, "9.3", "动画 / 科幻 / 冒险", "小瓦力，大人生，跨越星系只为你。"),
        ("大话西游之大圣娶亲", 95, "9.2", "喜剧 / 爱情 / 奇幻", "一生所爱，苦海无涯。"),
        ("熔炉", 125, "9.3", "剧情", "我们奋战不是为了改变世界，而是不让世界改变我们。"),
        ("疯狂动物城", 108, "9.2", "动画 / 喜剧 / 冒险", "迪士尼乌托邦，勇敢追梦，无所畏惧。"),
        ("无间道", 101, "9.3", "剧情 / 惊悚 / 犯罪", "我想做一个好人，华语警匪片的终极巅峰。"),
        ("教父", 175, "9.3", "剧情 / 犯罪", "开创黑帮史诗的旷世巨作。"),
        ("当幸福来敲门", 117, "9.2", "剧情 / 传记 / 家庭", "只要有梦想，就要去捍卫它。"),
        ("触不可及", 112, "9.3", "剧情 / 喜剧", "最真挚的友情，跨越阶级的灵魂碰撞。"),
        ("控方证人", 116, "9.6", "剧情 / 悬疑 / 犯罪", "法庭推理电影的里程碑，结局惊天逆转。"),
        ("龙猫", 86, "9.2", "动画 / 奇幻", "人人心中都有一个温暖的大龙猫。"),
        ("寻梦环游记", 105, "9.1", "动画 / 奇幻 / 音乐", "死亡不是终点，遗忘才是。"),
        ("末代皇帝", 163, "9.3", "剧情 / 传记 / 历史", "尊严与历史纠葛下的世纪绝唱。"),
        ("活着", 132, "9.3", "剧情 / 历史 / 家庭", "张艺谋巅峰代表作，生命力的最强回响。"),
        ("哈尔的移动城堡", 119, "9.1", "动画 / 奇幻 / 冒险", "宫崎骏式的浪漫，爱能治愈一切。"),
        ("天堂电影院", 124, "9.2", "剧情 / 爱情", "老电影放映员与小少年的电影人生。"),
        ("蝙蝠侠：黑暗骑士", 152, "9.2", "剧情 / 动作 / 科幻", "希斯·莱杰之后，世间再无小丑。"),
        ("指环王：王者归来", 201, "9.3", "剧情 / 动作 / 奇幻", "中土世界史诗战役的完美终章。"),
        ("乱世佳人", 238, "9.3", "剧情 / 历史 / 爱情", "Tomorrow is another day!"),
        ("罗马假日", 118, "9.1", "喜剧 / 爱情", "奥黛丽·赫本的盛世美颜，经典永恒。"),
        ("搏击俱乐部", 139, "9.0", "剧情 / 动作 / 悬疑", "打破规则，释放内心隐藏的野兽。"),
        ("闻香识女人", 156, "9.1", "剧情", "阿尔·帕西诺演绎盲眼军官的灵魂探戈。"),
        ("少年派的奇幻漂流", 127, "9.1", "剧情 / 奇幻 / 冒险", "李安视听美学巅峰，人与自我的海上修行。"),
        ("死亡诗社", 128, "9.1", "剧情", "及时行乐，噢，船长，我的船长！"),
        ("天空之城", 124, "9.2", "动画 / 冒险 / 奇幻", "拉普达的飞翔，纯真童年的永恒歌谣。"),
        ("大闹天宫", 114, "9.4", "动画 / 奇幻", "中国动画影史的旷世神作，齐天大圣。"),
        ("海蒂和爷爷", 111, "9.3", "剧情 / 儿童", "阿尔卑斯山风光下的极致治愈。"),
        ("钢琴家", 150, "9.3", "剧情 / 传记 / 历史 / 战争", "在断壁残垣间为生命奏响的悠扬肖邦。"),
        ("狮子王", 89, "9.1", "动画 / 冒险 / 歌舞", "哈库呐玛塔塔，生生不息的荣耀王国。"),
        ("本杰明·巴顿奇事", 166, "9.0", "剧情 / 爱情 / 奇幻", "逆行时光中的爱与生老病死。"),
        ("美丽心灵", 135, "9.1", "剧情 / 传记", "博弈论大师纳什与精神分裂的终生对抗。"),
        ("黑客帝国", 136, "9.1", "动作 / 科幻", "红药丸还是蓝药丸？网络科幻里程碑。"),
        ("让子弹飞", 132, "9.0", "剧情 / 喜剧 / 动作", "站着把钱挣了！姜文黑色幽默巅峰。"),
        ("拯救大兵瑞恩", 169, "9.1", "剧情 / 历史 / 战争", "最真实的诺曼底登陆，生命的价值拷问。"),
        ("大话西游之月光宝盒", 87, "9.0", "喜剧 / 爱情 / 奇幻", "曾经有一份真挚的爱情摆在我的面前。"),
        ("西西里的美丽传说", 109, "8.9", "剧情 / 爱情", "美丽是罪吗？莫妮卡·贝鲁奇的性感与哀愁。"),
        ("致命魔术", 130, "8.9", "剧情 / 悬疑 / 惊悚", "两个魔术师的终生博弈与自我吞噬。"),
        ("音乐之声", 174, "9.1", "剧情 / 爱情 / 歌舞", "雪绒花，歌声充满阿尔卑斯山。"),
        ("绿皮书", 130, "8.9", "剧情 / 喜剧 / 传记", "跨越偏见与阶级的温暖公路之旅。"),
        ("剪刀手爱德华", 105, "8.7", "剧情 / 奇幻 / 爱情", "如果我没有刀，我无法保护你。"),
        ("哈利·波特与魔法石", 152, "9.2", "奇幻 / 冒险", "欢迎来到霍格沃茨！魔法梦的开始。"),
        ("情书", 117, "8.9", "剧情 / 爱情", "你好吗？我很好。岩井俊二的唯美极致。"),
        ("蝴蝶效应", 113, "8.8", "剧情 / 科幻 / 悬疑", "微小的变化，引发人生的惊天改写。"),
        ("沉默的羔羊", 118, "8.9", "剧情 / 惊悚 / 犯罪", "汉尼拔教授与 Clarice 的高智商博弈。"),
        ("心灵捕手", 126, "8.9", "剧情", "这不是你的错。天才数学少年的心路蜕变。"),
        ("春光乍泄", 96, "9.0", "剧情 / 爱情 / 同性", "不如我们重新来过。"),
        ("红辣椒", 90, "9.0", "动画 / 科幻 / 悬疑", "今敏奇幻梦境，前所未有的视听风暴。"),
        ("幽灵公主", 134, "8.9", "动画 / 奇幻 / 冒险", "人与自然的终极对抗与共生思索。"),
        ("低俗小说", 154, "8.9", "剧情 / 喜剧 / 犯罪", "昆汀的非线性叙事神作，舞蹈极具张力。"),
        ("布达佩斯大饭店", 100, "8.9", "剧情 / 喜剧", "韦斯·安德森极致对称与粉色美学。"),
        ("加勒比海盗", 143, "8.8", "动作 / 奇幻 / 冒险", "杰克船长的黑珍珠号，扬帆启航！"),
        ("超脱", 97, "8.9", "剧情", "我们都需要被拯救，极致孤独的教育悲歌。"),
        ("断背山", 134, "8.8", "剧情 / 爱情 / 同性", "每个人心中都有座断背山。"),
        ("阳光灿烂的日子", 138, "8.8", "剧情", "姜文处女作，青春的荷尔蒙在夏日飞扬。"),
        ("爱在黎明破晓前", 101, "8.8", "剧情 / 爱情", "维也纳一日，话痨情侣的灵魂交流。"),
        ("爱在日落黄昏时", 80, "8.9", "剧情 / 爱情", "巴黎九年重逢，夕阳落山前的浪漫对话。"),
        ("重庆森林", 102, "8.8", "剧情 / 爱情", "凤梨罐头会过期，但王家卫的重庆森林不会。"),
        ("大鱼", 125, "8.8", "剧情 / 家庭 / 奇幻", "父亲的那些荒诞故事，原来全都是爱。"),
        ("傲慢与偏见", 129, "8.7", "剧情 / 爱情", "达西先生在雨中的深情表白。"),
        ("七宗罪", 127, "8.8", "剧情 / 惊悚 / 犯罪", "暴食、贪婪、懒惰、嫉妒、骄傲、淫欲、愤怒。"),
        ("摩登时代", 87, "9.3", "剧情 / 喜剧 / 爱情", "卓别林对机械工业时代最辛辣的嘲讽。"),
        ("消失的爱人", 149, "8.7", "剧情 / 悬疑 / 惊悚", "大卫·芬奇的婚姻惊悚片，相爱相杀。"),
        ("甜蜜蜜", 118, "8.9", "剧情 / 爱情", "黎小军同志，黎小军与李翘的时代浮沉。"),
        ("猫鼠游戏", 141, "9.1", "传记 / 犯罪", "小李子与汤姆·汉克斯的智勇交锋。"),
        ("记忆碎片", 113, "8.7", "悬疑 / 惊悚", "诺兰倒叙神作，碎片时间里的真凶。"),
        ("侧耳倾听", 111, "8.9", "动画 / 爱情", "因为你，我想成为一个更好的人。"),
        ("完美陌生人", 97, "8.5", "剧情 / 喜剧", "手机是潘多拉魔盒，千万别玩这个游戏。"),
        ("告白", 106, "8.8", "剧情 / 悬疑", "女教师的复仇，纯黑色的校园悲剧。"),
        ("杀人回忆", 131, "8.9", "剧情 / 悬疑 / 犯罪", "韩国影史犯罪题材的无上巅峰，那个深邃的回眸。"),
        ("射雕英雄传", 110, "9.1", "武侠 / 古装", "铁血丹心，华语武侠的黄金时代。"),
        ("素媛", 122, "9.3", "剧情", "最深痛的社会题材，最温情的守护自愈。"),
        ("幸福终点站", 128, "8.8", "剧情 / 喜剧 / 爱情", "在机场里建立属于自己的幸福绿洲。"),
        ("阿凡达", 162, "8.8", "动作 / 科幻", "詹姆斯·卡梅隆的潘多拉星球，开启3D时代。"),
        ("疯狂原始人", 98, "8.7", "动画 / 喜剧", "咕噜家族的追光之旅，合家欢巅峰。"),
        ("喜剧之王", 85, "8.8", "剧情 / 喜剧", "我养你啊！周星驰的龙套辛酸史。"),
        ("小森林 夏秋篇", 111, "9.0", "剧情", "美食与四季，在大自然中找回内心的宁静。"),
        ("无人知晓", 141, "9.1", "剧情", "是枝裕和代表作，四个孩子被抛弃后的残酷成长。"),
        ("教父2", 202, "9.3", "剧情 / 犯罪", "黑帮史诗的延续，两代教父的隔空对话。"),
        ("黑客帝国3", 129, "8.8", "动作 / 科幻", "尼奥的终极奉献，机器帝国的和平契约。"),
        ("指环王：双塔奇兵", 179, "9.2", "动作 / 奇幻", "圣盔谷之战，史诗级的魔幻巨制。"),
        ("飞越疯人院", 133, "9.1", "剧情", "不自由，毋宁死，对体制最强烈的控诉。"),
        ("末路狂花", 130, "8.9", "剧情 / 犯罪", "两个女人的公路逃亡，女权的终极觉醒。"),
        ("哈利·波特与阿兹卡班的囚徒", 142, "8.9", "奇幻 / 冒险", "阿方索执导的哈利波特巅峰黑暗风。"),
        ("一一", 173, "9.1", "剧情", "杨德昌家庭叙事史诗，人生其实很简单。"),
        ("看不见的客人", 106, "8.8", "悬疑 / 惊悚", "西班牙悬疑反转神作，细节决定成败。"),
        ("海街日记", 127, "8.8", "剧情", "四姐妹的镰仓四季，温柔淡雅的生活流。"),
    ]

    movie_list = []
    for title, duration, rating, genres, summary in raw_movies:
        movie_list.append(
            {"uid": uuid4(), "title": title, "duration": duration, "rating": Decimal(rating), "genres": genres, "summary": summary, "is_deleted": 0}
        )

    await session.execute(insert(Movie), movie_list)
    await session.flush()

    # ==================== Step 4: 播种 4 个精品小型特色影厅 (缩减座位至 5排x8列=40座，控制在50座以内) ====================
    room_list = [
        {"uid": uuid4(), "name": "🚀 穹顶VIP尊享·银河厅", "total_seats": 40, "is_deleted": 0},
        {"uid": uuid4(), "name": "🌀 织女星IMAX·激光立体厅", "total_seats": 40, "is_deleted": 0},
        {"uid": uuid4(), "name": "🎧 幽浮声场·杜比全景声厅", "total_seats": 40, "is_deleted": 0},
        {"uid": uuid4(), "name": "📼 猎户座经典·胶片情怀厅", "total_seats": 40, "is_deleted": 0},
    ]
    await session.execute(insert(CinemaRoom), room_list)
    await session.flush()

    # ==================== Step 5: 播种 2,160 场高频、高均匀轮播的豆瓣百佳排片场次 ====================
    now = datetime.now()
    m_uids = [m["uid"] for m in movie_list]
    r_uids = [r["uid"] for r in room_list]

    showtime_list = []

    # 制定 4 个影厅的交叉排片时段分布：每个影厅每天排 18 场高频排片
    # 每天 4 厅共 18 * 4 = 72 场；30 天一共高频排片 72 * 30 = 2,160 场！
    # 完美满足深度分页与高并发压测，总售票库达 2,160 * 40 = 86,400 张！
    schedule_templates = []
    for h in range(6, 24):  # 早上 6:00 到晚上 23:00
        # 每个小时段为不同影厅均匀交叉排片
        schedule_templates.append({"hour": h, "minute": 0, "room_idx": 0, "price": Decimal("35.00")})
        schedule_templates.append({"hour": h, "minute": 15, "room_idx": 1, "price": Decimal("45.00")})
        schedule_templates.append({"hour": h, "minute": 30, "room_idx": 2, "price": Decimal("40.00")})
        schedule_templates.append({"hour": h, "minute": 45, "room_idx": 3, "price": Decimal("50.00")})

    # 只取前 72 个时段模板，保证每天排满 72 场
    schedule_templates = schedule_templates[:72]

    showtime_index = 0
    for day_offset in range(30):
        target_date = now.date() + timedelta(days=day_offset)

        for temp in schedule_templates:
            # 100部电影顺序且均匀循环轮播播种
            movie_idx = showtime_index % len(m_uids)

            st_datetime = datetime(
                year=target_date.year,
                month=target_date.month,
                day=target_date.day,
                hour=temp["hour"],
                minute=temp["minute"],
            )

            # 防阻断：避免排出的今天场次由于时间早于当前时间 + 3小时偏移导致被售票拦截
            if st_datetime <= now + timedelta(hours=3):
                st_datetime = st_datetime + timedelta(days=1)

            showtime_list.append(
                {
                    "uid": uuid4(),
                    "movie_id": m_uids[movie_idx],
                    "room_id": r_uids[temp["room_idx"]],
                    "start_time": st_datetime,
                    "price": temp["price"],
                    "remaining_inventory": 40,
                    "version": 1,
                    "is_deleted": 0,
                }
            )
            showtime_index += 1

    await session.execute(insert(Showtime), showtime_list)
    await session.flush()

    # ==================== Step 6: 播种各场次对应的全部物理可选座位 (精致小型 5排x8列=40座) ====================
    seat_list = []
    # 物理座位网格为 5 排 x 8 列 = 40 座 (控制在 50座以内，网页渲染极其美观大方)
    rows = 5
    cols = 8

    for st in showtime_list:
        for r in range(1, rows + 1):
            for c in range(1, cols + 1):
                seat_list.append(
                    {
                        "uid": uuid4(),
                        "showtime_id": st["uid"],
                        "row_num": r,
                        "col_num": c,
                        "status": 0,
                        "sold_to_user": None,
                        "is_deleted": 0,
                    }
                )

    await session.execute(insert(Seat), seat_list)
    await session.commit()


if __name__ == "__main__":
    import asyncio
    from contextlib import asynccontextmanager

    async def main() -> None:
        from src.common.dependencies import get_async_engine, get_async_session

        engine = await get_async_engine()
        async with asynccontextmanager(get_async_session)(engine) as session:
            print("🚀 正在全面清洗库表，并注入高并发高密度种子数据...")
            await run_reset_and_seed(session)
            print("✨ 选座票仓数据播种成功！")

    asyncio.run(main())
