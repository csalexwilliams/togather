from django.conf.urls import patterns, include, url
from django.contrib import admin

from GameSystem.views import *

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'togather.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),

    url(r'^admin/', include(admin.site.urls)),
    url(r'^$', 'GameSystem.views.home', name='home'),
    url(r'^login-register-user/', 'GameSystem.views.get_user', name='get_user'),
    url(r'^question/', 'GameSystem.views.answer_question', name='answer_question'),
    url(r'^(?P<gametype_id>\d*)/', 'GameSystem.views.load_game_session', name='load_game_session'),
    url(r'^game/add_label/', 'GameSystem.views.add_label', name='add_label'),
    url(r'^game/add_vote/', 'GameSystem.views.add_vote', name='add_vote'),
    url(r'^summary/(?P<game_id>\d*)/', 'GameSystem.views.game_summary', name='game_summary'),
    url(r'^logout/', 'GameSystem.views.user_logout', name='user_logout'),
    url(r'^get/peerid', 'GameSystem.views.get_peer_id', name='get_peer_id'),
)
