import datetime
import hashlib
import json
import random
import time
from http import HTTPStatus
import dashscope
import pyperclip
import requests
import streamlit as st
import openai
import flask
from dashscope import Generation
import zhipuai
import logging

# logging.basicConfig(filename='./gpt_web.log',level=logging.INFO,format='%(asctime)s %(levelname)s %(name)s %(message)s',datefmt='%Y-%m-%d %H:%M:%S')   #日志记录
def gpt(question,n):
    # userip = str(request.headers.get('X-Forwarded-For') or request.remote_addr)
    if n==0:
        messages = [{'role': 'user', "content": question}]
    else:
        messages = question
    openai.api_key = 'xxxxxxx'
    try:
        print('连接OPENAI')
        rsp = openai.ChatCompletion.create(
            model="gpt-3.5-turbo-1106",
            messages=messages,  # 只带入一次的问话，不做上下文
            temperature=0.95,
            top_p=0.75,
            max_tokens=2048,
            stream=True
        )
    except:
        print('连接OPENAI失败')
    def get_text():
        final_text = ''
        for info in rsp:
            if info['choices'][0]['finish_reason'] != 'stop':
                final_text += info['choices'][0]['delta']['content']
                # print(final_text)
            else:
                final_text = final_text.replace('"', "").replace("'",'’')
            # yield " %s\n\n" % final_text
        print('【提问时间】：', datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),'\n')
        print('【用户问题】：', question, '\n')
        print('【gpt回答】：', final_text, '\n')
        return final_text
    # return flask.Response(get_text(), mimetype='text/event-stream')
    return get_text()

def baichaung(question,n):
    # question=request.args.get("question")
    # userid=request.args.get("userid")
    url = "https://api.baichuan-ai.com/v1/chat/completions"
    api_key = 'sk-5axxxxxxx'
    if n==0:
        messages=[{"role": "user","content": question}]
    else:
        messages=question
    data = {
        "model": "Baichuan2-Turbo",
        "messages": messages
    }

    json_data = json.dumps(data)

    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer " + api_key,
    }

    def data():
        answer = ''
        try:
            response = requests.post(url, data=json_data, headers=headers,stream=True)

            for line in response.iter_lines():
                content=line.decode('utf-8')
                content=json.loads(content)
                message = content['choices'][0]["message"]['content']
                # stop=content['data']['messages'][0]['finish_reason']
                answer=answer+message
                # yield answer

        except:
            print('百川调用异常')
            return '发生了一点问题，稍后重试！'
            # yield "data: %s\n\n" % answer.replace('\n', '<br />')
            # await asyncio.sleep(0.7)
        print('【提问时间】：', datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),'\n')
        print('【用户问题】：',question,'\n')
        print('【百川回答】：',answer,'\n')
        return answer
    # return flask.Response(data(), mimetype="text/event-stream; charset=utf-8")
    return data()

def qianwen(question,n):
    # #获取dict的key,value值
    # model_type=list(model_dic.keys())[0]
    # dashscope.api_key=list(model_dic.values())[0]
    dashscope.api_key='xxxxxb'
    #
    # if 'turbo'in model_type:
    #     model=Generation.Models.qwen_turbo
    # elif 'plus'in model_type:
    #     model=Generation.Models.qwen_plus
    # else:
    #     model=Generation.Models.qwen_max
    # model=Generation.Models.qwen_turbo
    def data():
        full_content = ''
        if n==0:
            messages = [
                {'role': 'user', 'content': question}]
        else:
            messages=question

        responses = Generation.call(
            model='qwen-turbo',
            messages=messages,
            result_format='message',  # set the result to be "message" format.
            stream=True,
            incremental_output=True  # get streaming output incrementally
        )
         # with incrementally we need to merge output.
        for response in responses:
            if response.status_code == HTTPStatus.OK:
                full_content += response.output.choices[0]['message']['content']
                # yield full_content

            else:
                print('Request id: %s, Status code: %s, error code: %s, error message: %s' % (
                    response.request_id, response.status_code,
                    response.code, response.message
                    ))
        print('【提问时间】：', datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),'\n')
        print('【用户问题】：', question, '\n')
        print('【千问回答】：', full_content, '\n')
        return full_content
    # return flask.Response(data(), mimetype="text/event-stream; charset=utf-8")
    return data()

def zhipu(question,n):
    zhipuai.api_key = "xxxxxXET"
    #userid = request.args.get('userid','1')  # 获取用户的唯一标识符
    #question = request.args.get('question')  # 获取用户的对话消息

    def data():
        content = ""
        response = zhipuai.model_api.sse_invoke(
        model="chatglm_turbo",
        prompt=question,
        temperature=0.9,
        top_p=0.7,
        incremental=True
    )
        data = ""
        for event in response.events():
            data += event.data
            # yield data
    # logger.info(data)
        print('【提问时间】：', datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),'\n')
        print('【用户问题】：', question, '\n')
        print('【智谱回答】：', data, '\n')
        return data
    # return flask.Response(data(), mimetype="text/event-stream; charset=utf-8")
    return data()

def get_access_token():
    url = "https://aip.baidubce.com/oauth/2.0/token?grant_type=client_credentials&client_id=xxxxQ&client_secret=xxxxxgELCSO"
    payload = json.dumps("")
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    response = requests.request("POST", url, headers=headers, data=payload)
    # print(response.json().get("access_token"))
    return response.json().get("access_token")
def wenxin(question,n):
    url = "https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/completions_pro?access_token=" + get_access_token()
    if n==0:
        messages = [
            {
                "role": "user",
                "content": question
            }
        ]
    else:
        messages=question
    payload = json.dumps({
        "messages": messages,
        "stream": True
    })
    headers = {
        'Content-Type': 'application/json'
    }

    response = requests.request("POST", url, headers=headers, data=payload, stream=True)
    def data():
        text=''
        for line in response.iter_lines():
            if line:
                line=line.decode('utf-8').replace('data: ','')
                line=json.loads(line)['result']
                text += line
                # yield text.replace('\n','')
        print('【提问时间】：', datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),'\n')
        print('【用户问题】：', question, '\n')
        print('【文心回答】：', text, '\n')
        return text
    # return flask.Response(data(), mimetype='text/event-stream; charset=utf-8')
    return data()

#科大讯飞
from qa_gpt import SparkApi
text = []
# def getText(role, content):
#     jsoncon = {}
#     jsoncon["role"] = role
#     jsoncon["content"] = content
#     text.append(jsoncon)
#     return text
def xunfei(question,n):
    if n==0:
        messages =[{'role': 'user', 'content': question}]
    else:
        messages=question
    domain = 'generalv3'
    Spark_url = "ws://spark-api.xf-yun.com/v3.1/chat"
    appid = "b3767005"
    api_key = 'xxxxxxxxxx'
    api_secret = 'xxxxxx'
    SparkApi.answer = ""
    def txt():
        SparkApi.main(appid, api_key, api_secret, Spark_url, domain,messages)
        # yield SparkApi.answer
        return SparkApi.answer
    # return flask.Response(txt(), mimetype="text/event-stream; charset=utf-8")
    print('【提问时间】：', datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),'\n')
    print('【用户问题】：', messages, '\n')
    print('【讯飞回答】：', SparkApi.answer, '\n')
    return txt()

from openai import OpenAI
def  moonshot(question,n):
    if n==0:
        messages = [{"role": "user", "content": question}]
    else:
        messages = question
    client = OpenAI(
        api_key="xxxxxoboe",
        base_url="https://api.moonshot.cn/v1",
    )

    response = client.chat.completions.create(
        model="moonshot-v1-8k",
        messages=messages,
        temperature=0.3,
        stream=True,
    )
    collected_messages = []
    def answer():
        for idx, chunk in enumerate(response):
            # print("Chunk received, value: ", chunk)
            chunk_message = chunk.choices[0].delta
            if not chunk_message.content:
                continue
            collected_messages.append(chunk_message)  # save the message
            ans=''.join([m.content for m in collected_messages])
            yield ans
    # print(f"Full conversation received: {''.join([m.content for m in collected_messages])}")
    return flask.Response(answer(), mimetype="text/event-stream")

def skywork(question,n):
    if n==0:
        messages = [{"role": "user", "content": question}]
    else:
        messages = question
    url = 'https://api-maas.singularity-ai.com/sky-work/api/v1/chat'
    app_key = 'xxxxxxx'        # 这里需要替换你的APIKey
    app_secret = 'xxxxxxxx'  # 这里需要替换你的APISecret
    timestamp = str(int(time.time()))
    sign_content = app_key + app_secret + timestamp
    sign_result = hashlib.md5(sign_content.encode('utf-8')).hexdigest()

    # 设置请求头，请求的数据格式为json
    headers={
       "app_key": app_key,
       "timestamp": timestamp,
       "sign": sign_result,
       "Content-Type": "application/json",
    }

    # 设置请求URL和参数
    data = {
       "messages": messages,
       "intent": "" # 用于强制指定意图，默认为空将进行意图识别判定是否搜索增强，取值 'chat'则不走搜索增强

}
    # 发起请求并获取响应
    response = requests.post(url, headers=headers, json=data, stream=True)

    # 处理响应流
    ans=''
    for line in response.iter_lines():
        if line:
            # 处理接收到的数据
            ans+=line.decode('utf-8')
    print(ans)
    return ans
