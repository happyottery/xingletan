#!/usr/bin/env python
# coding: utf-8

# In[3]:


import streamlit as st
from streamlit_chat import message


# In[4]:


import pandas as pd
import numpy as np
import jieba
import jieba.analyse as ana
# 加载未登录词 
jieba.load_userdict('D:/学习/学习资料/毕业设计/未登录词.txt')
import re
import pickle


# In[ ]:


from openai import OpenAI


# In[ ]:


import lightfm
from lightfm import LightFM


# In[ ]:


# 读取普通excel
@st.cache_data  # 添加缓存装饰
def load_data(file_path):
    df = pd.read_excel(file_path, engine='openpyxl')
    return df


# In[ ]:


# 网页标签
st.set_page_config(
    page_title="小星Chat音乐推荐",
    page_icon="⭐",
    layout="wide",
)


# In[3]:


song_label_df = load_data('D:/学习/学习资料/毕业设计/userBehavior(去1歌曲标签补充版).xlsx')


# In[ ]:


# 读取模型
@st.cache_data  # 添加缓存装饰
def load_model(file_path):
    with open(file_path, "rb") as f:
        model_hybrid_test = pickle.load(f)
    return model_hybrid_test


# In[ ]:


# 加载模型
model_hybrid_test = load_model("D:/学习/学习资料/毕业设计/lightfm_model.pkl")


# In[4]:


# 用户登录/注册


# In[5]:


# Read users data
#@st.cache_data
def read_users_data(file_path):
    df = pd.read_excel(file_path, dtype={'user': str, 'password': str, 'blacklist': str})
    return df

# Write users data
@st.cache_data
def write_users_data(file_path, df):
    df.to_excel(file_path, index=False)

@st.cache_data
def get_user_id(users_df, username, password):
    matching_user = users_df[(users_df['user'] == username) & (users_df['password'] == password)]
    if not matching_user.empty:
        match_user_id = matching_user['user_id'].values[0]
        return match_user_id
    else:
        return None
    
# 用户注册
def user_register(users_df, user_id_df, username, password):
    last_user_id = users_df['user_id'].max() if not users_df.empty else 0
    user_id = last_user_id + 1
    new_user = {'user_id': user_id, 'user': username, 'password': password}
    users_df = users_df._append(new_user, ignore_index=True)
    write_users_data("D:/学习/学习资料/毕业设计/用户登录.xlsx", users_df)
    user_id_df.iat[0, 0] = new_user['user_id']
    write_users_data("D:/学习/学习资料/毕业设计/用户id临时存储.xlsx", user_id_df)
    st.success(f"注册成功，欢迎 {username} 登录！")
    return users_df

# 用户登录
def user_login(users_df, user_id_df, username, password):
    match_user_id = get_user_id(users_df, username, password)
    if match_user_id is not None:
        user_id_df.iat[0, 0] = match_user_id
        st.success(f"登录成功，欢迎 {username}！")
        write_users_data("D:/学习/学习资料/毕业设计/用户id临时存储.xlsx", user_id_df)
        return True
    else:
        st.error("昵称或密码错误，请重新输入。")
        return False

# 用户登录页面
def user_login_page(users_df, user_id_df):
    st.title("用户登录/注册")
    action = st.radio("请选择操作", ["登录", "注册", "游客模式"])

    # 初始化 submit_button
    submit_button = None

    # 显示输入昵称和密码的字段只有在登录和注册模式下才显示
    with st.form(key="user_form"):
        if action in ["登录", "注册"]:
            username = st.text_input("请输入您的昵称:")
            password = st.text_input("请输入您的密码:", type="password")

            # 创建一个提交按钮
            submit_button = st.form_submit_button("提交")

    # 在按钮被点击后执行
    if action == "游客模式" and st.button("进入游客模式"):
        st.session_state.logged_in = True
        st.session_state.logged_in_as_guest = True
        st.experimental_rerun()
    elif submit_button:
        if action == "注册":
            users_df = user_register(users_df, user_id_df, username, password)
        if user_login(users_df, user_id_df, username, password):
            st.session_state.logged_in = True
            st.experimental_rerun()


# In[6]:
# 计算流行度
def get_top_10_songs(song_df1, song_df2):
    popularity = song_df1['song_mid'].value_counts()
    top_10_song_mids = popularity.head(10).index

    # 在song_df2中找到这些song_mid对应的行
    top_songs_df = song_df2[song_df2['song_mid'].isin(top_10_song_mids)]

    # 按照song_mid的流行度对top_songs_df进行排序
    top_songs_df = top_songs_df.sort_values('song_mid', key=lambda x: popularity[x], ascending=False)
    top_songs_df['排名'] = range(1, 11)
    return top_songs_df.reset_index(drop=True)


# 页面1: 排行榜（游客模式）
def display_rankings_guest(song_df, title):
    st.subheader(title)
    song_df = song_df.sort_values(song_df.columns[-1], ascending=False).head(10)
    song_df['排名'] = range(1, 11)

    for index, row in song_df.iterrows():
        song_info = f"{row['排名']}. {row['song']} - 演唱者: {row['singer']}"
        song_link = 'https://y.qq.com/n/ryqq/songDetail/' + f"{row['song_mid']}"
        # 播放链接
        st.markdown(f"{song_info} - [点击播放]({song_link})🎧", unsafe_allow_html=True)

def display_rankings_popularity_guest(ranking_df):
    st.subheader("流行度榜单")
    for index, row in ranking_df.iterrows():
        song_info = f"{row['排名']}. {row['song']} - 演唱者: {row['singer']}"
        song_link = 'https://y.qq.com/n/ryqq/songDetail/' + f"{row['song_mid']}"

        # 显示歌曲信息和播放链接
        st.markdown(f"{song_info} - [点击播放]({song_link})🎧", unsafe_allow_html=True)


# In[ ]:


# 页面1: 排行榜（用户登录模式）
def display_rankings(user_id, users_df, user_behaviour, song_df, title):
    st.subheader(title)
    song_df = song_df.sort_values(song_df.columns[-1], ascending=False).head(10)
    song_df['排名'] = range(1, 11)

    for index, row in song_df.iterrows():
        song_info = f"{row['排名']}. {row['song']} - 演唱者: {row['singer']}"
        song_link = 'https://y.qq.com/n/ryqq/songDetail/' + f"{row['song_mid']}"
        # 播放链接
        st.markdown(f"{song_info} - [点击播放]({song_link})🎧", unsafe_allow_html=True)
        match_song_mid_without_prefix = song_link.replace('https://y.qq.com/n/ryqq/songDetail/', '')
        # 喜欢按钮
        play_button_clicked = st.button("喜欢♥", key=f"play_{title}_{match_song_mid_without_prefix}", 
                             on_click=play_click_button, args=[users_df, user_id, match_song_mid_without_prefix, user_behaviour])
        
def display_rankings_popularity(user_id, users_df, user_behaviour,ranking_df):
    st.subheader("流行度榜单")
    for index, row in ranking_df.iterrows():
        song_info = f"{row['排名']}. {row['song']} - 演唱者: {row['singer']}"
        song_link = 'https://y.qq.com/n/ryqq/songDetail/' + f"{row['song_mid']}"
        match_song_mid_without_prefix = song_link.replace('https://y.qq.com/n/ryqq/songDetail/', '')

        # 显示歌曲信息和播放链接
        st.markdown(f"{song_info} - [点击播放]({song_link})🎧", unsafe_allow_html=True)
        play_button_clicked = st.button("喜欢♥", key=f"play_流行度_{match_song_mid_without_prefix}", 
                             on_click=play_click_button, args=[users_df, user_id, match_song_mid_without_prefix, user_behaviour])


# In[7]:


greetings_keywords = ["你好", "hi", "Hi", "早上好", "晚上好", "中午好", "下午好", "哈喽", "嗨", "在吗", "在不", "早生蚝", "晚生蚝", "你是", "自我介绍"]
gratitude_keywords = ['谢', '哈哈', '嘿嘿', '嗯', '棒', '不错', '好的']
search_keywords = ['推荐', '歌', '首', '有关', '关于', '音乐', '相关', '想听']


# In[8]:


# 页面2: 用户交互（游客模式）
def user_interaction_guest():
    st.title("你好😉我是音乐推荐机器人小星！")

    # 在侧边栏悬浮窗显示常见问题，用户点击选择的项目自动填充到对话框中
    with st.sidebar:
        st.title("常见问题")
        # 添加样式和布局
        # 常见问题列表
        faq = ["来一首摇滚乐", "想听周杰伦的歌", "分手神曲疗愈心伤"]
        # 显示常见问题
        selected=""
        for question in faq:
            if st.button(question):
                selected=question
       
    # user_input接收用户的输入
    if user_input:= st.chat_input("输入文字开启音乐推荐吧～") or selected:
        # 在页面上显示用户的输入
        with st.chat_message("user"):
            st.markdown(user_input)
            
        # 判断用户输入，如果包含打招呼相关的关键词，输出专属音乐推荐机器人的欢迎语
        if any(keyword in user_input for keyword in greetings_keywords):
            with st.chat_message("assistant"):
                st.markdown("Hi！我是音乐推荐机器人小星😊你可以跟我说说你想听什么样的歌，把我当树洞也可以～<br>我会为你推荐一首歌，希望音乐能带给你快乐！", unsafe_allow_html=True)
        
        # 如果不包含打招呼相关的关键词，按照标签推荐        
        else:
            # 检查是否包含感谢开心或认可的关键词，或字数是否小于3
            if any(keyword in user_input for keyword in gratitude_keywords) or len(user_input) < 3:
                with st.chat_message("assistant"):
                    st.markdown("希望你会喜欢我推荐的音乐\(￣︶￣*\))祝你天天开心，身体健康，万事胜意～")
            
            else:
                keyword_list = build_keyword_list(user_input)
                match_song, match_singer, match_song_mid = find_best_match(keyword_list, song_label_df)

                # 不包含检索相关词汇，进行额外输出+歌手歌名歌曲链接
                if not any(keyword in user_input for keyword in search_keywords):
                    messages = [{'role': 'user', 'content':  user_input},]
                    answer = gpt_35_api(messages)
                    with st.chat_message("assistant"):
                        st.markdown(f"{answer}<br>为你推荐： {match_song} - {match_singer}<br>歌曲链接： {match_song_mid}", unsafe_allow_html=True)
                # 包含检索相关词汇，只输出歌名歌手歌曲链接
                else:
                    # 输出匹配度最高的歌曲信息
                    with st.chat_message("assistant"):
                        st.markdown(f"为你推荐： {match_song} - {match_singer}<br>歌曲链接： {match_song_mid}", unsafe_allow_html=True)

    


# In[ ]:


# 页面2: 用户交互（用户登录模式）
def user_interaction(users_df, user_id, user_behaviour):
    st.markdown("## 你好😉我是小星，你的专属音乐推荐机器人\n对推荐结果进行评价，我会为你带来专属推荐歌曲～")

    # 在侧边栏悬浮窗显示常见问题，用户点击选择的项目自动填充到对话框中
    with st.sidebar:
        st.title("常见问题")
        # 添加样式和布局
        # 常见问题列表
        faq = ["来一首摇滚乐", "想听周杰伦的歌", "分手神曲疗愈心伤"]
        # 显示常见问题
        selected=""
        for question in faq:
            if st.button(question):
                selected=question
       
    # user_input接收用户的输入
    if user_input:= st.chat_input("输入文字开启音乐推荐吧～") or selected:
        # 在页面上显示用户的输入
        with st.chat_message("user"):
            st.markdown(user_input)
            
        # 判断用户输入，如果包含打招呼相关的关键词，输出专属音乐推荐机器人的欢迎语
        if any(keyword in user_input for keyword in greetings_keywords):
            with st.chat_message("assistant"):
                st.markdown("Hi！我是你的专属音乐推荐机器人小星😊你可以跟我说说你想听什么样的歌，把我当树洞也可以～<br>我会为你推荐一首歌，希望音乐能带给你快乐！", unsafe_allow_html=True)
        
        # 检查是否包含感谢开心或认可的关键词，或字数是否小于3，输出祝福语
        elif any(keyword in user_input for keyword in gratitude_keywords) or len(user_input) < 3:
            with st.chat_message("assistant"):
                st.markdown("希望你会喜欢我推荐的音乐\(￣︶￣*\))祝你天天开心，身体健康，万事胜意～")

        else:
            keyword_list = build_keyword_list(user_input)
            match_song, match_singer, match_song_mid = find_best_match_vip(keyword_list,song_label_df,users_df,user_behaviour,user_id,model_hybrid_test)
            # 如果曲库中没有匹配的歌曲，输出抱歉语录
            if match_song is None:
                with st.chat_message("assistant"):
                    st.markdown("非常抱歉😔🥀小星的曲库里暂时没有符合您要求的歌")
            
            # 不包含检索相关词汇，更新user_behaviour，进行额外输出+歌手歌名歌曲链接
            elif not any(keyword in user_input for keyword in search_keywords):
                match_song_mid_without_prefix = match_song_mid.replace('https://y.qq.com/n/ryqq/songDetail/', '')
                user_behaviour2 = update_user_behaviour(users_df, user_behaviour, user_id, match_song_mid_without_prefix)
                write_users_data("D:/学习/学习资料/毕业设计/userBehavior(去1播放版).xlsx", user_behaviour2)
                
                messages = [{'role': 'user', 'content':  user_input},]
                answer = gpt_35_api(messages)
                with st.chat_message("assistant"):
                    st.markdown(f"{answer}<br>为你推荐： {match_song} - {match_singer}<br>歌曲链接： {match_song_mid}", unsafe_allow_html=True)

                    dislike_button_clicked = st.button("👎不喜欢", key=f"dislike_button_{match_song_mid}", on_click=dislike_click_button,
                                                       args=[users_df, user_id, match_song_mid_without_prefix, user_behaviour2])

            # 包含检索相关词汇，更新user_behaviour，只输出歌名歌手歌曲链接
            else:
                match_song_mid_without_prefix = match_song_mid.replace('https://y.qq.com/n/ryqq/songDetail/', '')
                user_behaviour2 = update_user_behaviour(users_df, user_behaviour, user_id, match_song_mid_without_prefix)
                write_users_data("D:/学习/学习资料/毕业设计/userBehavior(去1播放版).xlsx", user_behaviour2)
                # 输出匹配度最高的歌曲信息
                with st.chat_message("assistant"):
                    st.markdown(f"为你推荐： {match_song} - {match_singer}<br>歌曲链接： {match_song_mid}", unsafe_allow_html=True)
                    # 创建不喜欢按钮
                    dislike_button_clicked = st.button("👎不喜欢", key=f"dislike_button_{match_song_mid}", on_click=dislike_click_button,
                                                       args=[users_df, user_id, match_song_mid_without_prefix, user_behaviour2])


# In[ ]:


# 个性化推荐


# In[ ]:


# 更新user_behaviour
def update_user_behaviour(users_df, user_behaviour, user_id, match_song_mid_without_prefix):
    new_row = pd.Series()

    # 设置"user_id"和"song_mid"列的值
    new_row['user_id'] = user_id
    new_row['song_mid'] = match_song_mid_without_prefix

    # 找到users_df中user_id为user_id的行，并获取对应的user值
    user = users_df.loc[users_df['user_id'] == user_id, 'user'].values[0]

    # 将user值填入"user"列中
    new_row['user'] = user

    # 查找user_behaviour中song_mid相同的第一个数据
    song_data = user_behaviour[user_behaviour['song_mid'] == match_song_mid_without_prefix].iloc[0]

    # 将song_data的指定列的值填入new_row的相应列中
    columns_to_update = ['song_id', 'song', 'singer', 'singer_id', 'album', 'year', 'QQ音乐评论数', '评论数_level', '流派', '语言']
    for column in columns_to_update:
        new_row[column] = song_data[column]

    # 将counts_level列的值设为1
    new_row['counts_level'] = 1

    # 将新的一行插入到DataFrame中
    user_behaviour = user_behaviour._append(new_row, ignore_index=True)

    return user_behaviour


# In[ ]:


# 模糊匹配标签，匹配度高的排名前（用户登录模式）
def find_best_match_vip(lst, df, blacklist_df, user_behaviour, user_id, model):
    # 将列表元素组合成正则表达式模式
    pattern = re.compile('|'.join(lst), flags=re.IGNORECASE)
    
    # 使用正则表达式进行模糊匹配
    matches = df['标签'].str.contains(pattern, regex=True)
    
    # 去除黑名单中的数据
    blacklist = set()
    for s in blacklist_df.loc[blacklist_df['user_id'] == user_id, 'blacklist'].values:
        if ',' in str(s):
            blacklist = set(s.split(','))
        else:
            blacklist.add(s)
    
    matched_df = df[matches]
    filtered_df = matched_df[~matched_df['song_mid'].isin(blacklist)]
    
    if filtered_df.empty:
        return None, None, None

    num_users, num_items = model.user_embeddings.shape[0], model.item_embeddings.shape[0]
    
    if not lst:  # 检查lst是否为空
        if num_users >= (user_id + 1): # 判断为老用户
            scores = model.predict(int(user_id), np.arange(num_items)) # predict函数会将已知的正反馈项排除在推荐结果之外
            top_songs_index = np.argsort(-scores)
            top_songs = user_behaviour['song_mid'][top_songs_index].tolist()
            # 找到 top_songs 中第一个值在 filtered_df 的 'song_mid' 列中对应的序号
            for song_mid in top_songs:
                if song_mid in filtered_df['song_mid'].values:
                    best_match_index = filtered_df[filtered_df['song_mid'] == song_mid].index[0]
                    break
        else: # 新用户，推荐交互表里没有的、播放量最高的那首
            best_match_index = filtered_df['歌曲总counts'].idxmax()
            while True:
                if not user_behaviour[(user_behaviour['user_id'] == user_id) & (user_behaviour['song_mid'] == filtered_df.loc[best_match_index, 'song_mid'])].empty:
                    # 如果用户行为中已存在该首歌，则换下一首播放量最高的歌曲
                    filtered_df.drop(best_match_index, inplace=True)
                    best_match_index = filtered_df['歌曲总counts'].idxmax()
                else:
                    break
                    
    else:
        # 计算每行匹配上的元素数量
        match_counts = filtered_df['标签'].apply(lambda x: len(re.findall(pattern, x)))

        # 找到匹配度最高的行的索引，匹配度=列表词语匹配上的数量
        max_match_count = match_counts.max()
        best_matches = filtered_df[match_counts == max_match_count]

        # 如果有多个并列的行，调用训练好的混合推荐模型，用模型计算各项得分，推荐分数最高的那首
        if len(best_matches) > 1:
            if num_users >= (user_id + 1): # 判断是老用户
                scores = model.predict(int(user_id), np.arange(num_items)) # predict函数会将已知的正反馈项排除在推荐结果之外
                top_songs_index = np.argsort(-scores)
                top_songs = user_behaviour['song_mid'][top_songs_index].tolist()
                # 找到 top_songs 中第一个值在 best_matches 的 'song_mid' 列中对应的序号
                for song_mid in top_songs:
                    if song_mid in best_matches['song_mid'].values:
                        best_match_index = best_matches[best_matches['song_mid'] == song_mid].index[0]
                        break
            else: # 新用户，冷启动，直接推荐匹配度最高的行中播放数最高的
                best_match_index = best_matches['歌曲总counts'].idxmax()
        else:
            best_match_index = best_matches.index[0]
    
    best_match_row = filtered_df.loc[best_match_index]
    
    # 获取匹配度最高的行的 "song" 列和 "song_mid" 列内容
    song = best_match_row['song']
    singer = best_match_row['singer']
    song_mid = 'https://y.qq.com/n/ryqq/songDetail/'+ best_match_row['song_mid']
    
    return song, singer, song_mid


# In[ ]:


# 接入大模型生成用户语句主题词情绪词+标签匹配


# In[ ]:


# GPT-3.5 API密钥
client = OpenAI(
    api_key="sk-MZTG8t3SkL4l5G9d5nkMcvQHS2kihSBL2R0gK1kIoMGUBqZp", #替换api key
    base_url="https://api.chatanywhere.tech/v1"
)


# In[ ]:


# 非流式响应模板
def gpt_35_api(messages: list):
    """为提供的对话消息创建新的回答

    Args:
        messages (list): 完整的对话消息
    """
    completion = client.chat.completions.create(model="gpt-3.5-turbo", messages=messages)
    return completion.choices[0].message.content


# In[ ]:


# 去除非中英文字符及各别停用词
def preprocess_text(text):
    # 使用正则表达式匹配中英文字符
    pattern = re.compile(r'[\u4e00-\u9fa5a-zA-Z]+')
    result = pattern.findall(text)
    text = ''.join(result)
    
    # 分词
    tokens = jieba.lcut(text)
    
    # 过滤掉"主题"和"情绪词汇"
    filtered_tokens = [token for token in tokens if token not in ['主题词','情绪词','主题','情绪','词汇','词']]
    
    return filtered_tokens


# In[ ]:


# GPT生成用户语句的主题词和情绪词+tf-idf
def build_keyword_list(message):
    # 判断message中是否含有指定关键词，如果含有则不使用gpt，直接分词检索
    if any(word in message for word in search_keywords):
        # 对message进行分词
        seg_list = jieba.lcut(message)
        # 提取关键词及其对应的tf-idf值
        tfidf_keywords = ana.extract_tags(' '.join(seg_list), topK=12, withWeight=True)
        # 获取tf-idf高的前5个词
        top_keywords = [keyword for keyword, tfidf in tfidf_keywords if keyword not in ['推荐','歌','首','有关','关于','一首','一首歌','什么']]
        keyword_list = top_keywords[:5]  # 取tf-idf值前5的词
        
    # 不含有指定关键词，判定为树洞类语句，使用GPT生成主题词情绪词+tf-idf前5去重
    else:
        messages = [{'role': 'user','content': '请生成以下这段话的主题词情绪词，词与词之间用逗号分隔：'+ message},]
        answer = gpt_35_api(messages)
        keyword_list = preprocess_text(answer)
        
        seg_list = jieba.lcut(message)
        tfidf_keywords = ana.extract_tags(' '.join(seg_list), topK=5, withWeight=True)
        top_keywords = [keyword for keyword, tfidf in tfidf_keywords]
        keyword_list.extend(top_keywords)
        # 去除重复项
        keyword_list = list(set(keyword_list))

    return keyword_list


# In[ ]:


# 模糊匹配标签，匹配度高的排名前（游客模式）
def find_best_match(lst, df):
    if not lst:  # 检查lst是否为空
        best_match_index = df['歌曲总counts'].idxmax()
    else:
        # 将列表元素组合成正则表达式模式
        pattern = re.compile('|'.join(lst), flags=re.IGNORECASE)

        # 使用正则表达式进行模糊匹配
        matches = df['标签'].str.contains(pattern, regex=True)

        # 计算每行匹配上的元素数量
        match_counts = df[matches]['标签'].apply(lambda x: len(re.findall(pattern, x)))

        # 找到匹配度最高的行的索引，匹配度=列表词语匹配上的数量
        max_match_count = match_counts.max()
        best_matches = df[matches & (match_counts == max_match_count)]

        # 如果有多个并列的行，选取其中"歌曲总counts"列值最大的
        if len(best_matches) > 1:
            best_match_index = best_matches['歌曲总counts'].idxmax()
        else:
            best_match_index = best_matches.index[0]

    best_match_row = df.loc[best_match_index]
    
    # 获取匹配度最高的行的 "song" 列和 "song_mid" 列内容
    song = best_match_row['song']
    singer = best_match_row['singer']
    song_mid = 'https://y.qq.com/n/ryqq/songDetail/'+ best_match_row['song_mid']
    
    return song, singer, song_mid


# In[ ]:


# 播放按钮点击触发事件
def play_click_button(users_df, user_id, match_song_mid_without_prefix, user_behaviour):
    if ((user_behaviour['user_id'] == user_id) & (user_behaviour['song_mid'] == match_song_mid_without_prefix)).any():
        st.warning("已喜欢，不需重复点击按钮~")
    else:
        # 将这首歌加入该用户的behaviour里
        user_behaviour2 = update_user_behaviour(users_df, user_behaviour, user_id, match_song_mid_without_prefix)
        write_users_data("D:/学习/学习资料/毕业设计/userBehavior(去1播放版).xlsx", user_behaviour2)
        st.success("已更新喜欢列表")


# In[ ]:


# 不喜欢按钮点击触发事件
def dislike_click_button(users_df, user_id, match_song_mid_without_prefix, user_behaviour2):
    # 将这首歌的match_song_mid_without_prefix加入该用户的黑名单里
    existing_value = users_df.loc[users_df['user_id'] == user_id, 'blacklist'].values[0]
    if pd.notna(existing_value):
        updated_value = f"{existing_value},{match_song_mid_without_prefix}"
    else:
        updated_value = match_song_mid_without_prefix
    users_df.loc[users_df['user_id'] == user_id, 'blacklist'] = updated_value
    # st.success(f"歌曲 {match_song} 已加入黑名单！")
    write_users_data("D:/学习/学习资料/毕业设计/用户登录.xlsx", users_df)

    user_behaviour2 = user_behaviour2.drop(user_behaviour2.index[-1])
    write_users_data("D:/学习/学习资料/毕业设计/userBehavior(去1播放版).xlsx", user_behaviour2)

    st.success("感谢反馈~我会努力变得更好ヾ(•ω•`)o")


# In[ ]:


# 主应用程序
def main():
    users_df = read_users_data("D:/学习/学习资料/毕业设计/用户登录.xlsx")
    user_id_df = pd.read_excel('D:/学习/学习资料/毕业设计/用户id临时存储.xlsx', engine='openpyxl')
    user_behaviour = pd.read_excel('D:/学习/学习资料/毕业设计/userBehavior(去1播放版).xlsx', engine='openpyxl')
    user_id = user_id_df.iat[0, 0] # 获取第一行第一列的单元格值
    
    # 进入网页后先检查用户是否登录
    # 初始化 logged_in session state
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
        
    # 初始化 logged_in_as_guest session state
    if 'logged_in_as_guest' not in st.session_state:
        st.session_state.logged_in_as_guest = False
        
    # Check if the user is logged in
    if not st.session_state.logged_in:
        user_login_page(users_df, user_id_df)
    else:
        # 登录成功后才展示其他页面
        st.sidebar.title("导航菜单")
        page = st.sidebar.selectbox("选择页面", ["音乐排行榜", "聊天界面"])  # 创建导航栏

        if page == "音乐排行榜":
            # 游客模式
            if st.session_state.logged_in_as_guest: 
                display_rankings_guest(song_label_df, "总排行榜")
                popularity_ranking = get_top_10_songs(user_behaviour, song_label_df)
                display_rankings_popularity_guest(popularity_ranking)
                pop_songs = song_label_df[song_label_df['流派'] == 'Pop']
                display_rankings_guest(pop_songs, "流行音乐排行榜")
                rock_songs = song_label_df[song_label_df['流派'] == 'Rock']
                display_rankings_guest(rock_songs, "摇滚音乐排行榜")
                Folk_songs = song_label_df[song_label_df['流派'] == 'Folk']
                display_rankings_guest(Folk_songs, "民谣音乐排行榜")
            else:
                display_rankings(user_id, users_df, user_behaviour, song_label_df, "总排行榜")
                popularity_ranking = get_top_10_songs(user_behaviour, song_label_df)
                display_rankings_popularity(user_id, users_df, user_behaviour,popularity_ranking)
                pop_songs = song_label_df[song_label_df['流派'] == 'Pop']
                display_rankings(user_id, users_df, user_behaviour, pop_songs, "流行音乐排行榜")
                rock_songs = song_label_df[song_label_df['流派'] == 'Rock']
                display_rankings(user_id, users_df, user_behaviour, rock_songs, "摇滚音乐排行榜")
                Folk_songs = song_label_df[song_label_df['流派'] == 'Folk']
                display_rankings(user_id, users_df, user_behaviour, Folk_songs, "民谣音乐排行榜")
                
        elif page == "聊天界面":
            # 如果是游客模式，则运行user_interaction_guest函数
            if st.session_state.logged_in_as_guest:
                user_interaction_guest()
            else:
                user_interaction(users_df, user_id, user_behaviour)

if __name__ == "__main__":
    main()


# In[ ]:




# In[ ]:




