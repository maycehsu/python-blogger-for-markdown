# -*- coding: utf-8 -*-

import pprint
import httplib2
import sys
import argparse
import ConfigParser
import os
from apiclient.discovery import build
from oauth2client import tools
from oauth2client.file import Storage
from oauth2client.client import AccessTokenRefreshError
from oauth2client.client import OAuth2WebServerFlow
import json
import sqlite3 as lite
import md5
import markdown
from datetime import datetime,timedelta

#########config file###############################
config = ConfigParser.ConfigParser()
config.read(os.path.join(os.path.dirname(sys.argv[0]), "blogger.ini"))


#########global variable in config file##################
CLIENT_KEY_FILE=eval(config.get('Config', 'CLIENT_KEY_FILE'))
API_KEY_FILE=eval(config.get('Config', 'API_KEY_FILE'))
BLOG_ID=eval(config.get('Config', 'BLOG_ID'))
DB_PATH=eval(config.get('Config', 'DB_PATH'))
ARTICLE_PATH=eval(config.get('Config', 'ARTICLE_PATH'))


#########const global variable###################
TBL_POSTS_FIELDS=['id', 'title', 'filename', 'checksum', 'published', 'updated']

#########helper functions################
err_flag=1
dbg_flag=0
class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def pgreen(*args):
    return pcolor(bcolors.OKGREEN, *args)

def pfail(*args):
    return pcolor(bcolors.FAIL, *args)

def pcolor(asni_escape, *args):
    string=asni_escape
    for arg in args:
        string = string+" "+str(arg)
    string = string + bcolors.ENDC
    return string
    
def perror(*args):
    if err_flag:
        func=sys._getframe().f_back.f_code.co_name
        string=pfail("[Error],%s(),"%(func))
        for arg in args:
            if type(arg) is unicode:
                string = string+' '+arg
            else:
                string = string+" "+str(arg)
        
    
        print string
        string = string+"\n"
    #with open(error_file, 'a') as outfile:
    #    outfile.write(string)
    
def pdebug(*args):
    if dbg_flag:
        func=sys._getframe().f_back.f_code.co_name
        string="[Debug],%s(),"%(func)
        for arg in args:
            if type(arg) is unicode:
                string = string+' '+arg
            else:
                string = string+" "+str(arg)
    
        print string
        string = string+"\n"

#from datetime import datetime,timedelta
def dt_parse(t, GMT_offset=8):
    ret = datetime.strptime(t[0:19],'%Y-%m-%dT%H:%M:%S')
    if t[19]=='-':
        ret+=timedelta(hours=int(t[20:22]),minutes=int(t[23:]))
    elif t[19]=='+':
        ret-=timedelta(hours=int(t[20:22]),minutes=int(t[23:]))
    else:
        perror('wrong format')
    
    if GMT_offset>0:
        ret+=timedelta(hours=GMT_offset)
    elif GMT_offset<0:
        ret-=timedelta(hours=GMT_offset)
    return ret
    
#########class blogger###################
class blogger(object):
    def __init__(self):
        self.service=None
        self.posts=[]
        self.articles=[] 
        with open(API_KEY_FILE, 'r') as reader:
            self.api_key=reader.read()
            
            
        with open(CLIENT_KEY_FILE, 'r') as fd:
            data=json.load(fd)
            self.client_data=data['installed']
        
        self.setupDB()
        print 'connect db',DB_PATH
        self.dbcon=lite.connect(DB_PATH)
        print 'connected'
            #pprint.pprint(self.client_data)
        #service = build('blogger', 'v3', developerKey=self.api_key)
    
    
    ###########blogger Client Authorize######
    def client_authorize(self):
        client_id=self.client_data['client_id']
        client_secret=self.client_data['client_secret']
        scope = 'https://www.googleapis.com/auth/blogger'
        # Create a flow object. This object holds the client_id, client_secret, and
        # scope. It assists with OAuth 2.0 steps to get user authorization and
        # credentials.
        flow = OAuth2WebServerFlow(client_id, client_secret, scope)
        
        # Create a Storage object. This object holds the credentials that your
        # application needs to authorize access to the user's data. The name of the
        # credentials file is provided. If the file does not exist, it is
        # created. This object can only hold credentials for a single user, so
        # as-written, this script can only handle a single user.
        storage = Storage('credentials.dat')

        # The get() function returns the credentials for the Storage object. If no
        # credentials were found, None is returned.
        credentials = storage.get()

        # If no credentials are found or the credentials are invalid due to
        # expiration, new credentials need to be obtained from the authorization
        # server. The oauth2client.tools.run_flow() function attempts to open an
        # authorization server page in your default web browser. The server
        # asks the user to grant your application access to the user's data.
        # If the user grants access, the run_flow() function returns new credentials.
        # The new credentials are also stored in the supplied Storage object,
        # which updates the credentials.dat file.
        print 'check credentials'
        if credentials is None or credentials.invalid:
            print 'credentials is None or Invalid, re-run flow'
            credentials = tools.run_flow(flow, storage, tools.argparser.parse_args())

        # Create an httplib2.Http object to handle our HTTP requests, and authorize it
        # using the credentials.authorize() function.
        print 'authorize'
        http = httplib2.Http(cache=".cache")
        http = credentials.authorize(http)
        print 'authorize done'
        
        print 'build blogger v3 service'
        self.service = build('blogger', 'v3', http=http)
        print 'build blogger v3 service done'
    
    ###########blogger API#################
    """
    blogger blogs API:
    https://developers.google.com/resources/api-libraries/documentation/blogger/v3/python/latest/blogger_v3.blogs.html
    """
    def blogs_listByUser(self):
        service=self.service
        blogs=service.blogs()
        thisuserblogs=blogs.listByUser(userId='self').execute()
        pprint.pprint(thisuserblogs)
    
    
    """
    blogger posts API:
    https://developers.google.com/resources/api-libraries/documentation/blogger/v3/python/latest/blogger_v3.posts.html
    """
    def posts_list(self):
        service=self.service
        posts=service.posts()
        post_list=posts.list(blogId=BLOG_ID).execute()
        for post in post_list['items']:
            print '#', post['id']
            print 'Title:', post['title']
            print 'URL:', post['url']
            checksum=md5.new(post['content'].encode('utf-8')).hexdigest()
            print 'Content checksum:', checksum
            print
        return post_list
            
    def post_update(self, blogId, postId, title, content):
        service=self.service
        posts=service.posts()
        post={'title':title, 'content':content}
        r=posts.update(blogId=blogId, postId=postId, body=post).execute()
        return r
    
    def post_insert(self, blogId, title, content):
        service=self.service
        posts=service.posts()
        post={'title':title, 'content':content}
        r=posts.insert(blogId=blogId, body=post).execute()
        return r
    
    
    ####################
    @staticmethod
    def get_db_empty_record():
        #db_record={'id': '', 'title': '', 'filename':'', 'checksum':'', 'published':'', 'updated':''}
        db_record={k:'' for k in TBL_POSTS_FIELDS}
        return db_record
    
    def get_posts_and_sync_to_db(self):
        
        service=self.service
        posts=service.posts()
        post_list=posts.list(blogId=BLOG_ID).execute()
        print '============posts sync to db=============='
        for post in post_list['items']:
            #print '#', post['id']
            
            content=post['content'].encode('utf-8')
            record=self.get_db_empty_record()
            record['id']=post['id']
            record['title']=post['title']
            content=post['content'].encode('utf-8')
            record['checksum']=md5.new(content).hexdigest()
            record['published']=post['published']
            record['updated']=post['updated']
            conditions={'id=':record['id']}
            print 'Title:', post['title'], ', len=', len(content),',Checksum=', record['checksum'], ',Updated=',dt_parse(record['updated'])
            DBUtil.db_update_or_insert(self.dbcon, 'posts', record, conditions)
            #conditions_for_update={'id=':record['id'], 'checksum!=':record['checksum']}
            #DBUtil.db_update_or_insert(self.dbcon, 'posts', record, conditions, conditions_for_update=conditions_for_update)
    
    def show_posts_from_db(self):
        print '=========show from db============'
        fields=TBL_POSTS_FIELDS
        r=DBUtil.db_fetch_data(self.dbcon, 'posts', fields, None)
        for row in r:
            #pprint.pprint(r)
            if len(row)==len(TBL_POSTS_FIELDS):
                data=dict(zip(TBL_POSTS_FIELDS, row))
                print 'title=', data['title'], '[%d]'%(len(data['title']))
                print 'updated=', dt_parse(data['updated'], GMT_offset=8)
                
                    
            
        
    def scan_local_articles(self, mypath=ARTICLE_PATH, force_regenerate_html=False):
        
        files_info=[]
        files = [f for f in os.listdir(mypath) if os.path.isfile(os.path.join(mypath, f))]
        print '===========scan files=========='
        print 'Path=', mypath
        for f in files:
            if f.endswith('.md'):
                path=os.path.join(mypath, f)
                #print 'path:',path
                with open(path, 'r') as fd:
                    title = fd.readline()
                    title = title[1:len(title)-1]
                    
                    if not title.startswith('[draft]'):
                       
                        content=fd.read().decode('utf-8')
                    
                        #compare html modified time < md modified time to re-generate html
                        html_path=path[:-3]+'.html'
                        html_mtime=os.path.getmtime(html_path)
                        md_mtime=os.path.getmtime(path)
                        
                        if force_regenerate_html or not os.path.isfile(html_path) or html_mtime < md_mtime:
                            print 'generate html file for ', title, '...'
                            with open(html_path, 'w') as f_out:
                                html = markdown.markdown(content, extensions=['markdown.extensions.extra'])
                                html = html.encode('utf-8')
                                f_out.write(html)
                                            
                        if os.path.isfile(html_path):
                            with open(html_path, 'r') as reader:
                                content=reader.read()
                                checksum = md5.new(content).hexdigest()
                                content_len =  len(content)
                                mtime = datetime.fromtimestamp(os.path.getmtime(path))
                                file_info={'title':title.decode('utf-8'), 'path':path, 'html_path':html_path, 'checksum':checksum, 'len':content_len, 'mtime':mtime}
                                files_info.append(file_info)
                                print '[ready]', title, 'len=', content_len, 'checksum=', checksum, ', modified=',mtime
                        else:
                            perror('[not ready]', title)
                            pass
                    else:
                        print '[draft]', title
                        #ignore draft
                        pass
        if files_info:
            self.articles=files_info
            print 'Total ', len(files_info), 'files are ready'
            #record information local html files: title, file-path, modified time, checksum
                    
    def publish_or_update(self, dry_run=False):
        #if scan complete, do publish or update
        #if no title found and no [draft] found in title, publish
        #if title found, checksum is different, check html modified timestamp > update timestamp -> update
        print '=======publish or update===='
        for file_info in self.articles:
            conditions={u'title=':file_info['title']}
            fields=[u'id', u'title', u'checksum', u'updated']
            
            r=DBUtil.db_fetch_data(self.dbcon, 'posts', fields, conditions)
            if r and len(r)==1:
                #print 'title found', file_info['title']
                post=dict(zip(fields, r[0]))
                post_updated = dt_parse(post['updated'])
                print 'checking...', file_info['title'], 'checksum:', file_info['checksum'], post['checksum'] 
                if post['checksum']!=file_info['checksum'] and post_updated<file_info['mtime']:
                    #update
                    print '[update]#%s '%(post['id']), file_info['title'], ', modified:', file_info['mtime'], 'checksum:', file_info['checksum']
                    if not dry_run:
                        with open(file_info['html_path'], 'r') as reader:
                            content=reader.read()
                            r=self.post_update(BLOG_ID, post['id'], file_info['title'], content)
                            if r:
                                print 'update success'
                elif post['checksum']==file_info['checksum']:
                    print '[content no change]',file_info['title'], ', checksum=',file_info['checksum']
                elif  post_updated>file_info['mtime']:
                    print '[file no update]', file_info['title'], ', post update=', post_updated, ', file mtime=', file_info['mtime']
                   
                
            else:
                if len(r)>1:
                    perror('more than one article found with same title, conflict')
                else:
                    #no title found, new article, publish
                    print '[publish]', file_info['title'], ', modified:', file_info['mtime'], 'checksum:', file_info['checksum']
                    if not dry_run:
                        with open(file_info['html_path'], 'r') as reader:
                            content=reader.read()
                            r=self.post_insert(BLOG_ID, file_info['title'], content)
                            if r:
                                print 'publish success'
                        
    
    def setupDB(self):
        print("Setting up the database: " + DB_PATH)
        con = None
        try:
            con = lite.connect(DB_PATH)
            #con.text_factory = str
            cur = con.cursor()
            cur.execute('CREATE TABLE IF NOT EXISTS posts (id TEXT, title TEXT, filename INT, checksum INT, published TEXT, updated TEXT)')
            #cur.execute('CREATE TABLE IF NOT EXISTS sets (set_id INT, name TEXT, primary_photo_id INTEGER)')
            cur.execute('CREATE UNIQUE INDEX IF NOT EXISTS post_id ON posts (id)')
            #cur.execute('CREATE INDEX IF NOT EXISTS setsindex ON sets (name)')
            con.commit()
            '''
            cur = con.cursor()
            cur.execute('PRAGMA user_version')
            row = cur.fetchone()
            if (row[0] == 0):
                print('Adding last_modified column to database');
                cur = con.cursor()
                cur.execute('PRAGMA user_version="1"')
                cur.execute('ALTER TABLE files ADD COLUMN last_modified REAL');
                con.commit()
            '''
            con.close()
        except lite.Error, e:
            print("Error: %s" % e.args[0])
            if con != None:
                con.close()
            sys.exit(1)
        finally:
            print("Completed database setup")
            
class DBUtil(object):
    @staticmethod
    def db_fetch_data(con, tbl_name, fields, conditions):
        with con:
            c= con.cursor()
            select_fields=''
            for i, field in enumerate(fields):
                select_fields+=field
                if i!=len(fields)-1:
                    select_fields+=','
            
            cond = ''
            t= []
            if conditions:
                for i, key_op in enumerate(conditions.keys()):
                    cond+='%s?'%(key_op)
                    if i!=len(conditions)-1:
                        cond+=' and '
                    t.append(conditions[key_op])
            
            
            if cond:
                query='SELECT %s from %s where %s'%(select_fields, tbl_name, cond)
                pdebug('query=',query)
                pdebug('t=', t)
                c.execute(query, tuple(t))
            else:
                query='SELECT %s from %s'%(select_fields, tbl_name)
                c.execute(query)
            r=c.fetchall()
            #pdebug('r=',r)
            return r
    
    
    @classmethod
    def db_update_or_insert(cls, con, tbl_name, record, conditions, conditions_for_update=None):
        #perror('enter')
        with con:
            fields=['*']
            r=cls.db_fetch_data(con, tbl_name, fields, conditions)
            if not r:
                cls.db_insert(con, tbl_name, record)
            else:
                if conditions_for_update:
                    fields=['*']
                    r=cls.db_fetch_data(con, tbl_name, fields, conditions_for_update)
                    if r:
                        cls.db_update(con, tbl_name, record, conditions_for_update)
                else:
                    cls.db_update(con, tbl_name, record, conditions)
    
    @classmethod
    def db_insert_new(cls, con, tbl_name, record, key):
        with con:
            fields=['*']
            r=cls.db_fetch_data(con, tbl_name, fields, key)
            if not r:
                cls.db_insert(con, tbl_name, record)
                return True
            
    @staticmethod
    def db_insert(con, tbl_name, record):
        with con:
            c = con.cursor()
            fields=''
            fieldsq=''
            t=[]
            for i, key in enumerate(record.keys()):
                fields+=key
                fieldsq+='?'
                if i!=len(record)-1:
                    fields+=','
                    fieldsq+=','
                t.append(record[key])    
        
            query=u'INSERT INTO %s (%s) VALUES (%s)'%(tbl_name, fields, fieldsq)
            pdebug('query=', query)
            pdebug('t=', *t)
            c.execute(query, tuple(t))
            con.commit()
        
    @staticmethod
    def db_update(con, tbl_name, record, conditions):
        with con:
            c = con.cursor()
            fields=''
            cond=''
            t=[]
            for i, key in enumerate(record.keys()):
                fields+=u'{}=?'.format(key)
                if i!=len(record)-1:
                    fields+=', '
                #t.append(key)
                t.append(record[key])
            if conditions:
                for i, key in enumerate(conditions.keys()):
                    cond+=u'{}?'.format(key)
                    if i!=len(conditions)-1:
                        cond+=' and '
                    #t.append(key)
                    t.append(conditions[key])
            
                query='UPDATE %s set %s where %s'%(tbl_name, fields, cond)
                pdebug('query=', query)
                pdebug('t=', *t)
                c.execute(query, tuple(t))
                con.commit()
                return True
            else:
                perror('no conditions')
            
if __name__ == '__main__':
    
    parser = argparse.ArgumentParser(description='Blogger publish/update.')
    parser.add_argument('-s', '--sync-db', action='store_true',
                        help='Sync blogger to local db')
    parser.add_argument('-f', '--scan-files', action='store_true',
                        help='scan local files')
    
    parser.add_argument('-b', '--show-db', action='store_true',
                        help='show posts from db')
    parser.add_argument('-r', '--run', action='store_true',
                        help='run scan files and update/create posts')
    parser.add_argument('-d', '--dry-run', action='store_true',
                        help='dry run to show ready to update/create articles')
    #parser.add_argument('-i', '--title', action='store',
    #                    help='Title for uploaded files')
    #parser.add_argument('-e', '--description', action='store',
    #                    help='Description for uploaded files')
    
    args = parser.parse_args()
    
    blogger=blogger()
    blogger.client_authorize()
    if args.run:
        blogger.get_posts_and_sync_to_db()
        blogger.scan_local_articles()
        blogger.publish_or_update()
    elif args.dry_run:
        blogger.get_posts_and_sync_to_db()
        blogger.scan_local_articles()
        blogger.publish_or_update(dry_run=True)
    else:
        if args.sync_db:
            print 'sync from blogger...'
            blogger.get_posts_and_sync_to_db()
        if args.scan_files:
            print 'scan files....'
            blogger.scan_local_articles()
        if args.show_db:
            print 'show posts in db...'
            blogger.show_posts_from_db()
        else:
            print 'Invalid argument'
    
    
    