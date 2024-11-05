import os
import random
import re

import requests
import uvicorn

from gpt_api import gpt
import logging
import pymysql as sql
from fastapi import FastAPI
from datetime import datetime
app=FastAPI()
mysql = sql.connect(host='127.0.0.1', port=3306, password='xxxxxx', user='root', database='python')
def sql_list(userid)->list:     #获取数据库列表,返回一个现有数据，未加入新问题和回答
    mysql.ping(reconnect=True)
    cursor = mysql.cursor()
    # 可以正常连接到数据库时
    cursor.execute(f'SELECT count(1) FROM produce WHERE userid = {userid}')
    if_exists = cursor.fetchone()[0]  # 获取结果
    print(f'ID:{userid} 是否存在【0不存在；1存在】：', if_exists)
    result_list = []
    if if_exists == 1:
        cursor.execute(f'select result from produce where userid={userid}')
        result = cursor.fetchone()[0]
        # result = json.dumps(result).replace('\n', '')  # 去掉其中的换行
        # result = json.loads(result)
        try:
            result_ls = result.split('}')
            for i in result_ls:
                if "'role': 'user'" in i:
                    user_str = i.split("{'role': 'user', 'content':")[1]
                    result_list.append({'role': 'user', 'content': user_str.replace("'", '').strip()})
                if "'role': 'assistant'" in i:
                    assistant_str = i.split("{'role': 'assistant', 'content':")[1]
                    result_list.append({'role': 'assistant', 'content': assistant_str.replace("'", '').strip()})
        except:
            logging.warning(f'解析出错')
            result_list = []
    if if_exists == 0:
        cursor.execute(f'INSERT INTO produce (userid) VALUES ("{userid}")')
        mysql.commit()
        result_list=[]
    print('result_list', result_list)
    return result_list
async def update_sql(userid,question,ansewer)->list:  #更新数据库
    result_list =sql_list(userid)  #获取数据库列表，没有用户会返回一个空列表
    #将新问题与答案写入sql
    result_list.append({'role': 'user', 'content': question})
    result_list.append({'role': 'assistant', 'content': ansewer})
    prompt = result_list
    cursor = mysql.cursor()
    if len(prompt) > 100:
        prompt.pop(0)
        prompt.pop(0)  # 移除列表的前两个对话
    try:
        tm = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute(f'update produce set result= "{str(prompt)}",ask_date="{tm}" where userid={userid}')
        mysql.commit()
    except:
        logging.warning(f'更新出错')

    # # 查询every_question表里今天的数据
    try:
        time = datetime.now().strftime("%Y-%m-%d")
        cursor.execute(f'select date1,question from every_question where date1="{time}"')
        result = cursor.fetchall()
        print(result)
        # 判断date1是否存在
        if len(result) == 0:
            ans = str([{'问题': question, '回答': ansewer}]).replace('"', "'").strip()
            s = re.search(r'【(.*?)】', ans).group(1)
            ans = ans.replace(s, '').replace('————', '').replace('【', '').replace('】', '').strip()
            cursor.execute(f'insert into every_question set date1="{time}",question="{ans}"')
            mysql.commit()
        else:
            if result[0][1] is None:
                ans = str([{'问题': question, '回答': ansewer}]).replace('"', "'").strip()
                s = re.search(r'【(.*?)】', ans).group(1)
                ans = ans.replace(s, '').replace('————', '').replace('【', '').replace('】', '').strip()
                cursor.execute(f'update every_question set question="{ans}" where date1="{time}"')
                mysql.commit()
            else:
                ans = result[0][1]
                if '[' in ans or '}' in ans:
                    # 将'[{}]'进行列表化
                    ans = ans.replace('[', '').replace(']', '').replace('{', '').split('},')
                    all = []
                    for i in ans:
                        ls = i.split(", '回答':")
                        q = ls[0].replace("'问题':", "").replace("{", "").replace("'", "").replace(",", "").strip()
                        a = ls[1].replace("'", "").replace("}", "").strip()
                        all.append({'问题':q, '回答':a})
                    all.append({'问题':question, '回答':ansewer})
                    ans = str(all).replace('"', "'").strip()
                    print('ans1', ans)
                else:
                    ans = str([{'问题':question, '回答':ansewer}]).replace('"', "'").strip()
                    print('ans2', ans)
            # 获取【 xxc】中间的内容
            try:
                s = re.search(r'【(.*?)】', ans).group(1)
                ans = ans.replace(s, '').replace('————', '').replace('【', '').replace('】', '').strip()
                print(ans)
            except Exception as e:
                print(e)
            print(f'update  every_question set question="{ans}" where date1="{datetime.now().strftime("%Y-%m-%d")}"')
            cursor.execute(
                f'update  every_question set question="{ans}" where date1="{datetime.now().strftime("%Y-%m-%d")}"')
            mysql.commit()
    except Exception as e:
        print(e)

def keyword(question):   #判断是否有关键词
    if '逗币' in question:
        question=question.replace('逗币','豆币').replace('云币','豆币')
    try:
        mysql.ping(reconnect=True)
        cursor = mysql.cursor()
        cursor.execute(f'SELECT * FROM keyword')
        for i in cursor.fetchall():
            if '*' not in i[0]:
                if i[0] in question:
                    return i[0]
            else:
                ls=i[0].split('*')
                if all(j in question for j in ls):
                    return i[0]
        return '无关键词'
    except:
        return '查询失败'

def vector_search(question,key_word):
    try:
        # port=random.choice([5555,5566])
        content=requests.post(f'http://127.0.0.1:3301/question?question={question}&keyword={key_word}').text  #请求本地模型，返回检索内容
        print('模型返回查询结果：',content)
        return content
    except:
        print('模型查询失败')
        pass

@app.get('/nkai')
async def qa(question,userid):
    try:
        # 判断是否有关键词
        key_word=keyword(question)
        print('关键词:',key_word)
        if key_word not in '无关键词,查询失败':
            question = question.replace('逗币', '豆币').replace('逗比', '豆币').replace('豆比', '豆币').replace('云币', '豆币').replace('云豆', '豆币')
            # 调用本地模型
            # key_word=key_word.replace('存在关键词：','')
            content = vector_search(question,key_word)
            prompt = (
                f'假如你是一个客服助手，请根据下面"信息内容"回答用户问题。 如果问题与内容没有关联，则返回"NK不知道"；\n' 
                f'信息内容：{content}\n\n'            
                f'用户问题：{question}\n'
                f'最终答案：')
            #使用模型回答
            try:
                text=gpt.qianwen(prompt,0)
            except:
                text=gpt.baichaung(prompt,0)
            if 'NK不知道' in text:
                try:
                    text = gpt.xunfei(question, 0)
                except:
                    text = gpt.zhipu(question, 0)
            qq=random.choice(['856193750','839698968','637203971','925481546'])
            text=text+f"   ————【本回答由AI助手生成，有其他问题问题可加QQ群反馈：{qq}】"
            print(text)
        else:
            #进行上下文回答
            messages=sql_list(userid)  #获取sql列表最后一个对话
            messages=messages[-2:]
            messages.append({'role': 'user', 'content': question})
            try:
                text=gpt.xunfei(messages,1)
            except:
                text=gpt.qianwen(messages,1)
            finally:
                if len(text)==0:
                    text=gpt.wenxin(messages,1)
            text=text+f"   ————【本回答由AI生成】"
    except:
        try:
            text = gpt.qianwen(question, 0)
        except:
            text = gpt.baichaung(question, 0)
        finally:
            if len(text)==0:
                text=gpt.wenxin(question,0)
            else:
                pass
        text=text+f"   ————【本回答由AI生成】"

    # 写入sql
    text=text.replace('\n','').replace('"','').replace('\\','').replace("'","’")
    # await update_sql(userid, question, text)
    return text
# '例如：“啊哈哈123...”，“484到wda”,“0000021555”，都认为是错误的，返回“false”。'
@app.post("/judge")    #判断帖子是否为true
def judge(question):
    question=('判断下面语法是否正确，判断维度：[是否多处重复,是否乱码,语义是否明确]。如果语法正确请回答：“true”，如果不正确请回答：“false”，不需要做其他说明和扩展。'
              '需要判断的语句：'+question)
    answer = []
    answer1=gpt.qianwen(question,0)
    answer.append(answer1)
    answer2=gpt.zhipu(question,0)
    answer.append(answer2)
    answer3=gpt.xunfei(question,0)
    answer.append(answer3)
    print(answer)
    t,f=0,0
    for i in answer:
        if 'false' in i or 'FALSE' in i:
            f+=1
        elif 'true' in i or 'TRUE' in i:
            t+=1
        else:
            pass
    #统计列表里的true个数
    print(t,f)
    if t>f:
        return 'true'
    elif t<f:
        return 'false'
    else:
        return ''

if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=3303)