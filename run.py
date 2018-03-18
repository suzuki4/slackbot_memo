# coding: utf-8

import os
import random
import re
import pandas as pd
from slackbot.bot import Bot
from slackbot.dispatcher import MessageDispatcher
from slackbot import settings
from slackbot.bot import listen_to

class ExMessageDispatcher(MessageDispatcher):
    def __init__(self, slackclient, plugins, errors_to):
        super().__init__(slackclient, plugins, errors_to)

        alias_regex = ''
        if getattr(settings, 'ALIASES', None):
            alias_regex = '|(?P<alias>{})'.format('|'.join([re.escape(s) for s in settings.ALIASES.split(',')]))
        
        self.AT_MESSAGE_MATCHER = re.compile(r'^(?:\<@(?P<atuser>\w+)\>:?|(?P<username>\w+):{}) ?(?P<text>[\s\S]*)$'.format(alias_regex))

    def _on_new_message(self, msg):
        # ignore edits
        subtype = msg.get('subtype', '')
        if subtype == u'message_changed':
            return


        botname = self._client.login_data['self']['name']
        try:
            msguser = self._client.users.get(msg['user'])
            username = msguser['name']
        except (KeyError, TypeError):
            if 'username' in msg:
                username = msg['username']
            else:
                return

        #if username == botname or username == u'slackbot':
        #    return
        if re.match(r"^Reminder: .*\.$", msg["text"]):
            msg["text"] = msg["text"][10:len(msg["text"])-1]
            
        msg_respond_to = self.filter_text(msg)
        if msg_respond_to:
            self._pool.add_task(('respond_to', msg_respond_to))
        else:
            self._pool.add_task(('listen_to', msg))


class ExBot(Bot):
    def __init__(self):
        super().__init__()
        self._dispatcher = ExMessageDispatcher(self._client, self._plugins,
                                             settings.ERRORS_TO)

DATA_PATH = "./data.csv"
COLUMNS = ["no","text"]

@listen_to('¥help')
def help(message):
    text = """
¥register: 文章登録\n
¥list: 登録文章一覧\n
¥show: 登録文章ランダム表示\n
¥show 1: 1番目の登録文章表示\n
¥delete 1: 1番目の登録文章削除\n
¥search <text>: 引っかかった登録文章表示(ランダム3個まで)
    """
    message.reply(text)


@listen_to('¥register ([\s\S]*)')
def register(message, something):
    
    text = process_url(something)
    
    df = pd.read_csv(DATA_PATH)
    no = len(df)+1
    add_df = pd.DataFrame({COLUMNS[0]:no, COLUMNS[1]:text}, index=[len(df)])
    
    df = df.append(add_df)
    df = df.loc[:,COLUMNS]
    
    df.to_csv(DATA_PATH, index=False)
    
    message.reply('Registered as No.{}: {}'.format(no, text))


@listen_to('^¥list')
def _list(message):
    
    df = pd.read_csv(DATA_PATH)
    if process_no_data(df, message):
        return
    
    msgs = []
    for i, row in df.iterrows():
        msg = "{}: ".format(row[0])
        msg += adjust_msg(str(row[1]).replace("\n", " "))
        msgs.append(msg)
        
    message.reply("\n" + "\n".join(msgs))
   
   
@listen_to('^¥show(.*)')
def show_random(message, something):
    
    if something != "":
        return
    
    df = pd.read_csv(DATA_PATH)
    if process_no_data(df, message):
        return
        
    idx = random.randrange(0, len(df))
    
    msg = str(df.loc[idx, "text"])
        
    message.reply("\n{}".format(msg))
    

@listen_to('^¥show (\d+)')
def show(message, no):
    
    no = int(no)
    
    df = pd.read_csv(DATA_PATH)
    if process_no_data(df, message):
        return
        
    if process_not_registered(df, no, message):
        return
        
    idx = no - 1
    
    msg = str(df.loc[idx, "text"])
        
    message.reply("\n{}".format(msg))


@listen_to('¥^delete (\d+)')
def delete(message, no):
    
    no = int(no)
    
    df = pd.read_csv(DATA_PATH)
    if process_no_data(df, message):
        return
        
    if process_not_registered(df, no, message):
        return
        
    idx = no - 1
    
    msg = str(df.loc[idx, "text"])
    
    df = df.drop(idx).reset_index(drop=True)
    df["no"] = df.index + 1

    df.to_csv(DATA_PATH, index=False)
    
    message.reply('Deleted No.{}: {}'.format(no, msg))


@listen_to('^¥search (.*)')
def search(message, text):
    
    df = pd.read_csv(DATA_PATH)
    if process_no_data(df, message):
        return
                
    df = df[df["text"].apply(lambda x:str(text) in str(x))]
    if len(df) == 0:
        message.reply("Following search word is not registered: {}".format(text))
        return

    selection = df["text"].tolist()[:3]
    random.shuffle(selection)
        
    message.reply("\n{}".format("\n".join(selection)))



def adjust_msg(msg):
    
    return msg[:40] + ("…" if len(msg) > 40 else "")


def process_not_registered(df, no, message):
    
    if no not in df["no"].tolist():
        message.reply("No.{} is not registered.".format(no))
        return True
    return False
    

def process_no_data(df, message):

    if len(df) == 0:
        message.reply('Nothing. ¥register first.')
        return True
    return False
    

def process_url(url):
    
    if re.match(r"^<http.*>$" , url):
        return url[1:len(url)-1]
    return url


def initialize():    
    if not os.path.exists(DATA_PATH):
        df = pd.DataFrame(columns=COLUMNS)
        df.to_csv(DATA_PATH, index=False)

def main():
    bot = ExBot()
    bot.run()


if __name__ == "__main__":
    
    initialize()
    
    print('start slackbot')
    main()