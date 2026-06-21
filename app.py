import json
import os
from datetime import datetime
from pathlib import Path

import streamlit as st


BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"

INTERACTIVE_PATH = DATA_DIR / "copland_interactive_content.json"
LOGS_PATH = DATA_DIR / "listening_logs.jsonl"

DATA_DIR.mkdir(exist_ok=True)


st.set_page_config(
    page_title="What to Listen for in Music",
    page_icon="🎧",
    layout="wide"
)


def read_json(path, default):
    if not path.exists():
        return default
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


@st.cache_data
def load_interactive_content():
    return read_json(INTERACTIVE_PATH, {})


def load_logs():
    if not LOGS_PATH.exists():
        return []

    logs = []
    with open(LOGS_PATH, "r", encoding="utf-8-sig") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                logs.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return logs


def save_log(record):
    with open(LOGS_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def flatten_cards(chapters):
    rows = []
    for chapter in chapters:
        for card in chapter.get("listening_cards", []):
            row = dict(card)
            row["chapter_id"] = chapter.get("chapter_id", "")
            row["chapter_title"] = chapter.get("source_title", "")
            row["chapter_core_argument"] = chapter.get("core_argument", "")
            row["chapter_role"] = chapter.get("chapter_role", "")
            rows.append(row)
    return rows


def flatten_ideas(chapters):
    rows = []
    for chapter_index, chapter in enumerate(chapters, start=1):
        for idea in chapter.get("key_ideas", []):
            rows.append({
                "chapter_index": chapter_index,
                "chapter_id": chapter.get("chapter_id", ""),
                "chapter_title": chapter.get("source_title", ""),
                "idea_id": idea.get("idea_id", ""),
                "title": idea.get("title", ""),
                "summary": idea.get("summary", ""),
                "why": idea.get("why_it_matters_for_listening", ""),
                "misunderstanding": idea.get("common_misunderstanding", "")
            })
    return rows


def local_feedback(text):
    if not text.strip():
        return "还没有写观察。先写下你听到了什么。"

    dimension_words = [
        "旋律", "节奏", "和声", "音色", "织体", "曲式", "段落", "重复", "变化",
        "发展", "回归", "对比", "紧张", "释放", "音量", "速度", "密度",
        "主题", "动机", "配器", "层次", "前景", "背景", "低音", "鼓", "乐器",
        "音区", "重音", "停顿", "高潮", "尾声"
    ]

    vague_words = [
        "好听", "难听", "高级", "震撼", "舒服", "无聊", "有感觉", "牛", "神", "绝了"
    ]

    position_words = [
        "开头", "前半", "中间", "后半", "结尾", "主歌", "副歌", "高潮",
        "尾声", "之后", "再次", "回到", "进入", "第一段", "第二段"
    ]

    dimension_count = sum(word in text for word in dimension_words)
    vague_count = sum(word in text for word in vague_words)
    position_count = sum(word in text for word in position_words)

    if dimension_count >= 2 and position_count >= 1 and len(text) >= 90:
        return "这段观察已经比较具体：你写到了音乐维度，也写到了位置或变化。下一步可以进一步说明这些声音现象如何服务于当前章节的听赏思想。"

    if dimension_count >= 1 and position_count >= 1:
        return "你已经抓到具体音乐维度和位置了。下一步可以补充：这个现象前后有什么变化？它带来了什么期待、紧张、释放或结构感？"

    if dimension_count >= 1:
        return "你已经开始使用音乐维度了。下一步请补充位置：这个现象出现在开头、中段、高潮还是结尾？"

    if vague_count > 0:
        return "这段观察目前偏感受化。请把“好听 / 震撼 / 高级”改写成具体声音现象，例如旋律、节奏、音色、织体、段落变化。"

    return "请加入至少一个音乐维度，例如旋律、节奏、和声、音色、织体、曲式、重复或变化。"


def ai_feedback(chapter, card, music_title, observation):
    api_key = os.getenv("OPENAI_API_KEY")

    try:
        import streamlit as st_local
        if "OPENAI_API_KEY" in st_local.secrets:
            api_key = st_local.secrets["OPENAI_API_KEY"]
    except Exception:
        pass

    if not api_key:
        return "没有检测到 OPENAI_API_KEY。请先在 PowerShell 设置：$env:OPENAI_API_KEY=\"你的真实 API key\"。"

    try:
        from openai import OpenAI
    except ImportError:
        return "没有安装 openai。请运行：pip install openai"

    client = OpenAI(api_key=api_key)

    prompt = f"""
你是《What to Listen for in Music》中文互动作品里的 AI 听赏导师。

你不能听音频，只能根据用户写下的观察进行反馈。
不要假装你分析了音频。
你的任务是根据当前章节思想和听赏卡，评价用户的听赏观察是否具体、是否符合 Copland 式主动听赏。

当前章节标题：
{chapter.get("source_title", "")}

本章核心观点：
{chapter.get("core_argument", "")}

本章在全书中的作用：
{chapter.get("chapter_role", "")}

当前听赏卡：
{card.get("title", "")}

卡片概念：
{card.get("concept_summary", "")}

反馈标准：
{json.dumps(card.get("feedback_rubric", {}), ensure_ascii=False)}

用户听的作品：
{music_title}

用户观察：
{observation}

请用中文反馈，结构如下：

1. 这段观察已经做得好的地方
2. 还不够具体或不够贴合本章思想的地方
3. 如何把它改写得更像 Copland 式主动听赏
4. 给出一个改写示范
5. 下一次听同类音乐时应该注意什么

要求：
- 不要编造音频内容。
- 不要说“我听到这首歌如何如何”。
- 只评价用户写下的观察。
- 语言要像老师指导学生，不要太机械。
"""

    response = client.responses.create(
        model="gpt-5-mini",
        input=prompt
    )

    return response.output_text


def render_chapter_summary(chapter, chapter_number):
    with st.container(border=True):
        st.caption(f"Chapter {chapter_number}")
        st.subheader(chapter.get("source_title", "未命名章节"))

        st.markdown("**本章在全书中的作用**")
        st.write(chapter.get("chapter_role", ""))

        st.markdown("**本章核心观点**")
        st.write(chapter.get("core_argument", ""))

        if chapter.get("final_takeaway"):
            st.info(chapter["final_takeaway"])


def render_visual_structure(chapter):
    visual = chapter.get("visual_structure", {})
    nodes = visual.get("nodes", [])
    edges = visual.get("edges", [])

    st.markdown("## 本章可视化结构")

    if visual.get("visual_metaphor"):
        st.info(f"视觉隐喻：{visual['visual_metaphor']}")

    if nodes:
        st.markdown("### 概念节点")
        cols = st.columns(2)
        for i, node in enumerate(nodes):
            with cols[i % 2]:
                with st.container(border=True):
                    st.markdown(f"**{node.get('label', '')}**")
                    if node.get("type"):
                        st.caption(node.get("type", ""))
                    st.write(node.get("description", ""))

    if edges:
        st.markdown("### 节点关系")
        for edge in edges:
            st.markdown(
                f"- **{edge.get('source', '')}** → **{edge.get('target', '')}**：{edge.get('relation', '')}"
            )


def render_scene(scene):
    with st.container(border=True):
        st.subheader(scene.get("scene_title", "互动场景"))
        st.write(scene.get("scene_description", ""))

        if scene.get("user_action"):
            st.markdown("**你要做什么：**")
            st.write(scene["user_action"])

        if scene.get("reflection_prompt"):
            st.markdown("**反思问题：**")
            st.info(scene["reflection_prompt"])


def render_card(card, show_examples=True):
    with st.container(border=True):
        st.caption(card.get("chapter_title", ""))
        st.subheader(card.get("title", ""))

        if card.get("listening_dimension"):
            st.caption(f"听赏维度：{card.get('listening_dimension', '')}")

        st.markdown("**概念说明**")
        st.write(card.get("concept_summary", ""))

        notice = card.get("what_to_notice", [])
        if notice:
            st.markdown("**听的时候注意：**")
            for item in notice:
                st.markdown(f"- {item}")

        if card.get("guided_task"):
            st.markdown("**听赏任务：**")
            st.info(card.get("guided_task", ""))

        if show_examples:
            with st.expander("弱观察 / 强观察示例"):
                if card.get("weak_observation"):
                    st.markdown("**弱观察：**")
                    st.warning(card.get("weak_observation", ""))
                if card.get("strong_observation"):
                    st.markdown("**强观察：**")
                    st.success(card.get("strong_observation", ""))


content = load_interactive_content()

if not content:
    st.title("What to Listen for in Music")
    st.error("没有找到最终互动内容文件：data/copland_interactive_content.json")
    st.code("python .\\tools\\10_build_copland_interactive_content.py", language="powershell")
    st.stop()


chapters = content.get("chapters", [])
cards = flatten_cards(chapters)
ideas = flatten_ideas(chapters)
logs = load_logs()

chapter_by_id = {chapter.get("chapter_id", ""): chapter for chapter in chapters}

st.sidebar.title("What to Listen for in Music")
st.sidebar.caption("Aaron Copland 中文互动听赏作品")

page = st.sidebar.radio(
    "页面",
    [
        "首页",
        "章节展厅",
        "概念地图",
        "互动场景",
        "听赏工作台",
        "听赏日志",
        "AI 导师反馈说明"
    ]
)


if page == "首页":
    metadata = content.get("book_metadata", {})

    st.title("What to Listen for in Music")
    st.caption("Aaron Copland 音乐听赏思想中文互动作品")

    st.markdown("""
    这个项目把 Aaron Copland《What to Listen for in Music》转化为一个中文互动听赏作品。

    它不是电子书复刻，也不是乐理考试系统，而是把原书中的听赏思想做成：
    **章节展厅、概念地图、互动场景、听赏任务和反馈工作台**。
    """)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("章节", len(chapters))
    col2.metric("关键概念", len(ideas))
    col3.metric("听赏卡", len(cards))
    col4.metric("听赏日志", len(logs))

    st.markdown("## 书籍信息")
    st.write(f"**书名：** {metadata.get('title', '')}")
    st.write(f"**作者：** {metadata.get('creator', '')}")

    st.warning("本项目不展示 EPUB 原文全文，只展示基于原书内容改写生成的中文互动学习内容。")

    st.markdown("## 推荐使用方式")
    st.markdown("""
    1. 先进入 **章节展厅**，理解某一章的核心思想。
    2. 再进入 **互动场景**，看这一章可以怎样转化成听赏动作。
    3. 然后进入 **听赏工作台**，选择一张听赏卡，自己听一首音乐并写观察。
    4. 最后保存到 **听赏日志**，形成自己的听赏记录。
    """)


elif page == "章节展厅":
    st.title("章节展厅")

    if not chapters:
        st.info("没有章节内容。")
    else:
        options = [
            f"{i + 1}. {chapter.get('source_title', '未命名章节')}"
            for i, chapter in enumerate(chapters)
        ]

        selected = st.selectbox("选择章节", options)
        chapter_index = options.index(selected)
        chapter = chapters[chapter_index]

        render_chapter_summary(chapter, chapter_index + 1)

        st.divider()

        st.markdown("## 本章关键思想")
        ideas_in_chapter = chapter.get("key_ideas", [])

        if not ideas_in_chapter:
            st.info("本章没有生成关键思想。")
        else:
            for idea in ideas_in_chapter:
                with st.container(border=True):
                    st.subheader(idea.get("title", ""))
                    st.write(idea.get("summary", ""))

                    if idea.get("why_it_matters_for_listening"):
                        st.markdown("**它如何改变听法：**")
                        st.write(idea.get("why_it_matters_for_listening", ""))

                    if idea.get("common_misunderstanding"):
                        st.markdown("**常见误解：**")
                        st.warning(idea.get("common_misunderstanding", ""))

        st.divider()
        render_visual_structure(chapter)

        questions = chapter.get("reflection_questions", [])
        if questions:
            st.divider()
            st.markdown("## 本章反思问题")
            for question in questions:
                st.markdown(f"- {question}")


elif page == "概念地图":
    st.title("概念地图")

    st.markdown("""
    这里把整本书的关键概念按章节展开。它不是严格学术图谱，而是一个帮助你浏览 Copland 听赏思想的地图。
    """)

    if not ideas:
        st.info("没有概念数据。")
    else:
        try:
            import pandas as pd
            import plotly.express as px

            df = pd.DataFrame(ideas)
            df["概念序号"] = list(range(1, len(df) + 1))
            df["y"] = 1

            fig = px.scatter(
                df,
                x="chapter_index",
                y="y",
                hover_name="title",
                hover_data={
                    "chapter_title": True,
                    "summary": True,
                    "y": False,
                    "chapter_index": True,
                    "概念序号": False
                },
                title="全书概念沿章节展开的地图"
            )
            fig.update_yaxes(visible=False)
            fig.update_layout(height=420)
            st.plotly_chart(fig, use_container_width=True)
        except Exception as e:
            st.warning(f"概念图暂时无法显示：{e}")

        st.markdown("## 概念列表")
        for idea in ideas:
            with st.container(border=True):
                st.subheader(idea.get("title", ""))
                st.caption(idea.get("chapter_title", ""))
                st.write(idea.get("summary", ""))

                if idea.get("why"):
                    st.markdown("**它如何改变听法：**")
                    st.write(idea.get("why", ""))

                if idea.get("misunderstanding"):
                    st.markdown("**常见误解：**")
                    st.warning(idea.get("misunderstanding", ""))


elif page == "互动场景":
    st.title("互动场景")

    if not chapters:
        st.info("没有章节内容。")
    else:
        options = [
            f"{i + 1}. {chapter.get('source_title', '未命名章节')}"
            for i, chapter in enumerate(chapters)
        ]

        selected = st.selectbox("选择章节", options)
        chapter_index = options.index(selected)
        chapter = chapters[chapter_index]

        st.markdown("## 本章互动场景")
        scenes = chapter.get("interactive_scenes", [])

        if not scenes:
            st.info("本章没有生成互动场景。")
        else:
            for scene in scenes:
                render_scene(scene)


elif page == "听赏工作台":
    st.title("听赏工作台")

    if not cards:
        st.info("没有听赏卡。")
    else:
        card_options = [
            f"{card.get('chapter_title', '')} ｜ {card.get('title', '')}"
            for card in cards
        ]

        selected = st.selectbox("选择一张来自本书的听赏卡", card_options)
        card_index = card_options.index(selected)
        card = cards[card_index]
        chapter = chapter_by_id.get(card.get("chapter_id", ""), {})

        render_card(card, show_examples=True)

        st.divider()

        st.markdown("## 写下你的听赏观察")

        music_title = st.text_input("你听的作品")
        artist_or_composer = st.text_input("作曲家 / 乐队 / 歌手，可选")

        observation = st.text_area(
            "你的听赏观察",
            height=240,
            placeholder="请根据当前听赏卡写下具体观察。不要只写“好听”“震撼”“高级”。"
        )

        st.markdown("### 本地即时反馈")
        local_result = local_feedback(observation)
        st.info(local_result)

        use_ai = st.checkbox("使用 AI 导师反馈。会调用 OpenAI API，会花钱。", value=False)

        ai_result = ""

        if use_ai and st.button("生成 AI 导师反馈"):
            if not observation.strip():
                st.error("请先写观察。")
            else:
                with st.spinner("AI 导师正在根据本章思想反馈……"):
                    ai_result = ai_feedback(chapter, card, music_title, observation)
                    st.markdown(ai_result)

        if st.button("保存到听赏日志"):
            if not music_title.strip():
                st.error("请填写作品名。")
            elif not observation.strip():
                st.error("请填写听赏观察。")
            else:
                record = {
                    "timestamp": datetime.now().isoformat(timespec="seconds"),
                    "music_title": music_title.strip(),
                    "artist_or_composer": artist_or_composer.strip(),
                    "chapter_id": card.get("chapter_id", ""),
                    "chapter_title": card.get("chapter_title", ""),
                    "card_id": card.get("card_id", ""),
                    "card_title": card.get("title", ""),
                    "observation": observation.strip(),
                    "local_feedback": local_result,
                    "ai_feedback": ai_result
                }
                save_log(record)
                st.success("已保存到听赏日志。")


elif page == "听赏日志":
    st.title("听赏日志")

    logs = load_logs()

    if not logs:
        st.info("还没有日志。去“听赏工作台”完成一次听赏记录后，这里会显示。")
    else:
        st.write(f"共有 **{len(logs)}** 条听赏记录。")

        filter_options = ["全部章节"] + sorted({
            log.get("chapter_title", "")
            for log in logs
            if log.get("chapter_title")
        })

        selected_filter = st.selectbox("按章节筛选", filter_options)

        filtered_logs = logs
        if selected_filter != "全部章节":
            filtered_logs = [
                log for log in logs
                if log.get("chapter_title") == selected_filter
            ]

        for i, log in enumerate(reversed(filtered_logs), start=1):
            with st.container(border=True):
                st.subheader(f"{i}. {log.get('music_title', '未命名作品')}")

                if log.get("artist_or_composer"):
                    st.caption(log.get("artist_or_composer", ""))

                st.caption(log.get("timestamp", ""))
                st.write(f"**章节：** {log.get('chapter_title', '')}")
                st.write(f"**听赏卡：** {log.get('card_title', '')}")

                st.markdown("**你的观察：**")
                st.write(log.get("observation", ""))

                if log.get("local_feedback"):
                    st.markdown("**本地反馈：**")
                    st.info(log.get("local_feedback", ""))

                if log.get("ai_feedback"):
                    with st.expander("查看 AI 导师反馈"):
                        st.markdown(log.get("ai_feedback", ""))


elif page == "AI 导师反馈说明":
    st.title("AI 导师反馈说明")

    st.markdown("""
    这个项目的 AI 使用分成两种：

    ## 1. 生成整本书互动内容

    这是你已经运行过的步骤：

    ```powershell
    python .\\tools\\10_build_copland_interactive_content.py
    ```

    它会读取你本地 EPUB，按章节提取内容，并生成：

    ```text
    data/copland_interactive_content.json
    ```

    ## 2. 听赏工作台里的 AI 导师反馈

    AI 不听音频。

    它只根据：

    - 当前章节的核心思想
    - 当前听赏卡
    - 用户写下的听赏观察

    来判断这段观察是否具体、是否符合本章的听赏方法。

    只有你在“听赏工作台”里勾选并点击 **生成 AI 导师反馈** 时，才会调用 API。

    ## 注意

    本项目不会把 EPUB 原文全文展示在网页里。
    """)
