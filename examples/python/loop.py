import os
from os import path
from datetime import datetime, timedelta

from feedplatform import db
from feedplatform.conf import config
from feedplatform import parse

dbfile = path.join(path.dirname(__file__), 'test.db')
urls = [
    u'http://www.heise.de/newsticker/heise-atom.xml',
    u'http://www.haise.de/newsticker/heise-atom.xml',
    u'http://gamingxp.com/rss-news.xml'
]

def init_config():
    config.DATABASE = 'sqlite:%s' % dbfile

def init_db():
    # if the database is new, create the tables
    if not os.path.exists(dbfile):
        db.store.execute("CREATE TABLE feed (id INTEGER PRIMARY KEY, url VARCHAR)")
        db.store.execute("CREATE TABLE item (id INTEGER PRIMARY KEY, feed_id INTEGER, guid VARCHAR)")

    # create feeds that are currently missing
    for url in urls:
        if not db.store.find(db.Feed, db.Feed.url == url):
            feed = db.Feed()
            feed.url = url
            db.store.add(feed)
    db.store.flush()
    db.store.commit()

if __name__ == '__main__':
    init_config()
    init_db()

    print "Let me look at my finds for the next 10 seconds..."
    started = datetime.now()
    parse.simple_loop(callback=lambda c: datetime.now() > started + timedelta(seconds=10))