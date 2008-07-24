from tests import feedev

PASSES = 2

class TestFeed(feedev.Feed):
    content = """
    <rss>
  <channel>
    <title>Chaosradio Express</title>
    <item>
      <title>CRE062 Monochrom</title>
      <enclosure type="audio/mpeg" url="http://chaosradio.ccc.de/archive/chaosradio_express_062.mp3" length="86522496"/>
      <guid isPermaLink="false">http://chaosradio.ccc.de/cre062.html-001</guid>
    </item>
    {% =2 %}
    <item>
      <title>CRE062 Monochrom</title>
      <enclosure type="audio/mpeg" url="http://chaosradio.ccc.de/archive/chaosradio_express_062.mp3" length="86522496"/>
      <guid isPermaLink="false">http://chaosradio.ccc.de/cre062.html-001</guid>
    </item>
    {% end %}
  </channel>
</rss>
    """

def test():
    feedev.testmod()