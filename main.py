import itchat
import time
import config
import random
from apscheduler.schedulers.background import BackgroundScheduler
from itchat.content import *

# 群聊们
crdata = {}                 # chatroom data, 为dict{id, group_server}

reply_turn = 0              # 轮转回复

# 一个对象管理一个群
class group_server:
    def __init__(self, id):
        self.chatroom_id = id           # 群聊id
        self.msgqueue = []              # 待发送消息
        self.status = 0                 # 状态，0-通常状态，1-成语接龙中

    def cyjl_start(self):
        self.cyjl = cyjl_server()       # 管理者
        self.status = 1


# 成语接龙的管理者
class cyjl_server:
    data = []               # 成语们，简单粗暴

    def __init__(self):   
        self.now = ''       # 当前成语
        self.index = 0      # 第几个词
        self.scores = {}    # 大家的分数，字典，key为username，value是list，第一个是分数，第二个是昵称
        self.result = []    # 可以接的词
        self.start()

    # 开始
    def start(self):
        while True:
            word = random.sample(cyjl_server.data, 1)[0]
            print(word[-1])
            result = self.get_start_with(word[-1])
            if result:       # 后继有人
                self.result = result
                self.now = word
                print(self.now)
                self.index = 1
                return True

    # 以某个字开头的成语们
    def get_start_with(self, last_word):
        result = [word for word in cyjl_server.data if word[0]==last_word]
        return result

    # 某人发了个开头正确的消息，接受正义的审判吧
    def judge(self, answer, username, nickname):
        if answer in self.result:    # 这该死的群友，数理基础竟然如此扎实
            self.index += 1
            self.now = answer
            if username in self.scores:   # 已经有了，+1，没有则增加
                self.scores[username][0] += 1
            else:
                self.scores[username] = [1,nickname]
            self.result = self.get_start_with(answer[-1])
            return True
        return False

    # 游戏结束
    def end_game(self):
        # 成绩排序
        items=self.scores.items()
        backitems=[v[1] for v in items]      # 分数，昵称
        backitems.sort()

        reply = '本次共接龙了%s轮，大家的成绩为：\n' % (self.index-1)
        for backitem in backitems:
            reply += '%s:%s分\n' % (backitem[1], backitem[0])
        return reply


### 收到群聊消息调用它
@itchat.msg_register([TEXT, SHARING], isGroupChat=True)
def group_reply_text(msg):
    # 发送者的信息
    usernick = msg['ActualNickName']        # 用户昵称
    userid = msg['ActualUserName']          # 用户id
    groupid = msg['FromUserName']           # 群聊id

    #print(msg)

    # 消息是否来自于需要服务的群
    chatroom_id = msg['FromUserName']
    if not (chatroom_id in crdata.keys()):
        return

    gs = crdata[groupid]                    # group server

    # 是否是文本消息
    if msg['Type'] != TEXT:
        return
    
    # 内容
    content = msg['Text']
    if content[-1] == '。':                  # 私人定制
        content = content[:-1]
    print(content)

    # 成语接龙
    if '结束成语接龙' in content:             # 结束
        if 1 == gs.status:
            gs.msgqueue.append(gs.cyjl.end_game())
            gs.status = 0
            del gs.cyjl

    elif '成语接龙' in content:               # 成语接龙
        if 1 == gs.status:                     # 已经在接龙了
            gs.msgqueue.append('@%s\n你是不是沙雕，我们已经在玩成语接龙了！当前是第%s个成语：\n%s' % (usernick, gs.cyjl.index, gs.cyjl.now))
            print('@%s\n你是不是沙雕，我们已经在玩成语接龙了！当前是第%s个成语：\n%s' % (usernick, gs.cyjl.index, gs.cyjl.now))
        else:                               # 没在接，就进入接的状态
            gs.cyjl_start()
            gs.msgqueue.append('成语接龙开始！当前是第%s个成语：\n%s' % (gs.cyjl.index, gs.cyjl.now))
            print('成语接龙开始！当前是第%s个成语：\n%s' % (gs.cyjl.index, gs.cyjl.now))

    elif '点歌' in content:
        content = content.replace('点歌','')

    elif 1 == gs.status and content[0] == gs.cyjl.now[-1]:          # 第一个字对
        if gs.cyjl.judge(content, userid, usernick):             # 还真接上了
            gs.msgqueue.append('@%s\n恭喜您接龙成功！当前是第%s个成语：\n%s' % (usernick, gs.cyjl.index, gs.cyjl.now))
            print('@%s\n恭喜您接龙成功！当前是第%s个成语：\n%s' % (usernick, gs.cyjl.index, gs.cyjl.now))
            if 0 == len(gs.cyjl.result):                 # 后面没法接
                gs.msgqueue.append('这成语没法接，算了，就玩到这吧')
                print('这成语没法接，算了，就玩到这吧')
                gs.msgqueue.append(gs.cyjl.end_game())
                gs.status = 0
                del gs.cyjl
        else:   # 没接上
            gs.msgqueue.append('@%s\n不对不对！你说的什么玩意，【%s】不是成语！' % (usernick, content))


### 检查是否需要处理这条消息
def check(msg):
    gs = crdata[chatroom_id]
    # 是否是成语接龙
    if 1 == gs.status:
        return True

    content = msg['Content']
    # 有我的名字
    if not any(keyword in content for keyword in config.keywords):
        return False
    
    return True

### 发送消息
def send_msg():
    global reply_turn
    long_str = ''
    #print('我来了')
    gs = list(crdata.values())[reply_turn % len(crdata)]   # 这大概不是个好的写法
    for msg in gs.msgqueue:
        msg = msg.replace('二狗','敏感词')
        long_str += '--------\n%s\n' % msg
        #print(gs.chatroom_id)
    #print(long_str)
    gs.msgqueue = []
    itchat.send(long_str, toUserName=gs.chatroom_id)
    reply_turn += 1


if __name__ == '__main__':
    # 初始化成语接龙
    print('正在初始化成语接龙...')
    with open("data.txt", "r") as f:
        counter = 0
        for line in f:
            content = line.split("\t")
            #word = content[0]
            #pinyin = content[1].split("'")
            #meaning = content[2].replace("\n", "")
            cyjl_server.data.append(content[0])
            counter += 1
        print("Init finished! [%d] words." % (counter))

    # 扫二维码登录
    itchat.auto_login(hotReload=True, enableCmdQR=2)

    # 获取所有通讯录中的群聊
    # 需要在微信中将需要同步的群聊都保存至通讯录
    global crdata
    chatrooms = itchat.search_chatrooms(name=config.group)
    for chatroom in chatrooms:
        crdata[chatroom['UserName']] = group_server(chatroom['UserName'])
    print('正在监测的群聊：', len(chatrooms), '个')
    print(' '.join([item['NickName'] for item in chatrooms]))

    # 初始化调度任务
    # 创建后台执行的 schedulers
    scheduler = BackgroundScheduler()  
    # 添加调度任务
    # 调度方法为 timedTask，触发器选择 interval(间隔性)，间隔时长为 5 秒
    scheduler.add_job(send_msg, 'interval', seconds=config.tick)
    # 启动调度任务
    scheduler.start()

    # 开始监测
    itchat.run()
