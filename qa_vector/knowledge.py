import datetime
import os
import shutil
import fastapi
from  fastapi import FastAPI,Request
import pymysql as sql
import uvicorn
from langchain.embeddings import HuggingFaceBgeEmbeddings
from langchain.text_splitter import CharacterTextSplitter
from langchain.vectorstores.chroma import Chroma

#embedding模型加载
model_name = os.path.join(os.path.dirname(os.getcwd()),'BAAI_bge-large-zh-v1.5')
model_kwargs = {'device': 'cuda'}
encode_kwargs = {'normalize_embeddings': True}  # set True to compute cosine similarity
embedding = HuggingFaceBgeEmbeddings(
    model_name=model_name,
    model_kwargs=model_kwargs,
    encode_kwargs=encode_kwargs,
    query_instruction="为这个句子生成表示以用于检索相关文章：")
embedding.query_instruction = "为这个句子生成表示以用于检索相关文章："

#数据库加载
mysql = sql.connect(host='127.0.0.1', port=3306, password='xxxxxxx', user='root', database='python')
mysql.ping(reconnect=True)
cursor = mysql.cursor()
cursor.execute("select * from qadb")
data=cursor.fetchall()
text=""
for i in data:
    id,a,b = i[0],i[1],i[2]
    s = str([{a:b}])+"\n\n"
    text += s

#字符拆分
text_splitter = CharacterTextSplitter(
    separator="\n\n",
    chunk_size=70,
    chunk_overlap=10,
    length_function=len,
    is_separator_regex=False,
)
doc = text_splitter.create_documents([text])
print(doc)
#语义拆分
# text_splitter1 = SemanticChunker(embedding)
# docs = text_splitter1.create_documents([text])
# print(docs[0].page_content)

vector_path=os.path.join(os.path.dirname(os.getcwd()),'vector_store')
vectordb = Chroma.from_documents(doc, embedding, persist_directory=vector_path)
vectordb.persist()

app=fastapi.FastAPI()
def vectordata(prompt)->list:
    # 构建检索方式
    retriever = vectordb.similarity_search(prompt)
    data = retriever[0].page_content # 召回相似文本
    print('date:',datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    print('question:',prompt,'data:',data)
    return str(data).strip().split('\n\n')

def sql_keyword(keyword)->list:   #获取关键词的内容
    cursor = mysql.cursor()
    all_txt=[]
    if '*' not in keyword:
        cursor.execute(f"select question,answer from qadb where question like '%{keyword}%'")
        print(f"select question,answer from qadb where question like '%{keyword}%'")
        txt=cursor.fetchall()
        for i in txt:
            s=str({i[0]:i[1]})
            all_txt.append(s)
    if '*' in keyword:
        keyword=keyword.split('*')
        cursor.execute(f"select question,answer from qadb where question like '%{keyword[0]}%' or question like '%{keyword[1]}%'")
        print(f"select question,answer from qadb where question like '%{keyword[0]}%' or question like '%{keyword[1]}%'")
        txt=cursor.fetchall()
        for i in txt:
            s=str({i[0]:i[1]})
            all_txt.append(s)
    print('all_txt:',all_txt)
    return all_txt

@app.post('/question')
def chat(request: Request):
    ls=[]
    question=request.query_params.get('question')
    # keyword=request.query_params.get('keyword')   #数据库里关键信息
    content1 =vectordata(question)  # 向量库中获取的相似文本
    # try:
    #     content2=sql_keyword(keyword)  #获取数据库中文本
    # except:
    #     content2=[]
    question_list = ['NKAI不知道这个问题，不过可以换个问题！', '我不是很清楚，可以在描述清晰一点吗？',
                     'NKAI目前不知道，后续我们会更新这个问题。', '抱歉，作为一个客服助手，目前还不知道这个问题。']
    # teampt = f"根据下面内容回答问题，没有就说“{random.choice(question_list)}”，不要进行其他信息的扩展。'问题：{prompt}'；'内容：{content}'。"
    # teampt = (
    #     f'根据下面内容回答问题， 如果问题与内容没有关联或者相似性，则返回"NK不知道"；\n'  # 则返回"{random.choice(question_list)}
    #     f'内容信息：{content}\n'
    #     f'用户问题：{question}\n'
    #     f'最终答案：')
    # print(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")+'\n',teampt)

    #判断没有重复的内容
    # for x in content1:
    #     if x not in ls:
    #         ls.append(x)
    # print(ls)
    # if len(content2)>0:
    #     for j in content2:
    #         if j not in ls:
    #             ls.append(j)
    # print(ls)
    print(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")+'\n',content1)
    return str(content1)

@app.post('/insert')
#插入数据
def insert_data(request: Request):
    cursor = mysql.cursor()
    question = request.query_params.get('question')
    answer=request.query_params.get('answer')
    time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute(f'INSERT INTO qadb (question,answer,qa_date) values ("{question}","{answer}","{time}")')
    mysql.commit()
    update_data()
    return '数据插入成功'

@app.post('/delete')
def delete_data(request: Request):
    id=request.query_params.get('id')
    cursor = mysql.cursor()
    cursor.execute(f"delete from qadb where id='{id}'")
    mysql.commit()
    # 更新向量库
    update_data()
    return '删除成功'

def update_data():
    # 获取所有数据
    cursor.execute("select * from qadb")
    data = cursor.fetchall()
    text = ""
    for i in data:
        id, a, b = i[0], i[1], i[2]
        s = str([{a: b}]) + "\n\n"
        text += s

    # 字符拆分
    text_splitter = CharacterTextSplitter(
        separator="\n\n",
        chunk_size=100,
        chunk_overlap=0,
        length_function=len,
        is_separator_regex=False,
    )
    doc = text_splitter.create_documents([text])
    # 初始化
    global vectordb
    if vectordb is not None:
        vectordb.delete_collection()
    vectordb = Chroma.from_documents(doc, embedding, persist_directory=vector_path)
    # 保存数据库
    vectordb.persist()
    try:
        remove_file(vector_path)
    except:
        pass
    print('向量库更新完成')
@app.post('/search')
def search_data(request: Request):
    keyword=request.query_params.get('keyword')
    cursor.execute(f"SELECT * FROM qadb q where question LIKE '%{keyword}%' or answer like '%{keyword}%';")
    data=cursor.fetchall()
    return data

async def remove_file(folder_path):
    import os
    import time
    dic = {}
    while True:
        if os.path.exists(folder_path) and os.path.isdir(folder_path):
            for filename in os.listdir(folder_path):
                if os.path.isdir(os.path.join(folder_path, filename)):
                    file_path = os.path.join(folder_path, filename)
                    creation_time =  os.path.getctime(file_path)
                    # 将时间戳转换为日期
                    creation_time = time.localtime(creation_time)
                    formatted_time = time.strftime("%Y-%m-%d %H:%M:%S", creation_time)
                    dic[formatted_time] = file_path
        sorted_dict = dict(sorted(dic.items(), key=lambda item: item[0]))
        print(sorted_dict)
        keys = list(sorted_dict.keys())[:-1]
        path = [sorted_dict[key] for key in keys]
        print(path)
        for i in path:
            shutil.rmtree(i)
            time.sleep(1)
        if len(path) == 0:
            break
if __name__ == '__main__':
    uvicorn.run(app, host="0.0.0.0", port=3301)