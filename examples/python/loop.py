import os
from os import path
from datetime import datetime, timedelta

from feedplatform import db
from feedplatform.conf import config
from feedplatform import parse

dbfile = path.join(path.dirname(__file__), 'test.db')
urls = [
    u'http://www.heise.de/newsticker/heise-atom.xml',
    u'http://www.obviouslyinvalid.com/feed',
    u'http://feeds.feedburner.com/TechCrunch',
    u'http://www.escapistmagazine.com/rss/news',
    u'http://steve-yegge.blogspot.com/feeds/posts/default',
    u'http://nick.typepad.com/blog/index.rss',
    u'http://feeds.feedburner.com/GamasutraFeatureArticles/',
    u'http://dailybedpost.com/atom.xml',
    u'http://feeds.feedburner.com/codinghorror/',
    u'http://www.destructoid.com/elephant/index.phtml?mode=atom',
    u'http://de.wikipedia.org/w/index.php?title=Spezial:Letzte_%C3%84nderungen&feed=atom',
]

def init_config():
    config.DATABASE = 'sqlite:%s' % dbfile

def init_db():
    # if the database is new, create the tables
    if not os.path.exists(dbfile):
        db.store.execute("CREATE TABLE feed (id INTEGER PRIMARY KEY, url VARCHAR)")
        db.store.execute("CREATE TABLE item (id INTEGER PRIMARY KEY, feed_id INTEGER, guid VARCHAR)")
        db.store.commit()

    # create feeds that are currently missing
    for url in urls:
        if not db.store.find(db.Feed, db.Feed.url == url).count():
            print "Adding ", url
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