from django.shortcuts import render
from django.http import HttpResponseRedirect,HttpResponse
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from GameSystem.models import *
from django.db.models import Q, F
import random


def home(request):
    '''
    Two Scenarios:
    User is anonymous: Serves login form.
    User is logged in: Serves the homepage of our application.
    :param request:
    :return:
    '''
    if request.user.is_authenticated():
        # get a list of available games
        games = AvailableGames.objects.all()

        return render(request, 'lobby.html', {'available_games': games})
    else:
        return render(request, 'login.html', {})


def user_logout(request):
    logout(request)

    # redirect to the homepage
    return HttpResponseRedirect("/")


def get_user(request):
    '''
    Logs in the user. Creates user if the username doesn't exist already.
    :param request:
    :return:
    '''
    if request.method == "POST":
        username = request.POST["username"]
        password = request.POST["password"]

        new_user = 0
        # if the username doesnt exist already, make it
        if not User.objects.filter(username=username).exists():
            new_user = 1
            user = User.objects.create_user(username=username,
                                            email='burr@ismyBFF.com',
                                            password=password)

        # authenticate and login the user programmatically
        user = authenticate(username=request.POST['username'],
                            password=request.POST['password'])
        login(request, user)

        if(new_user):
            return render(request,'question.html',{})
        else:
            # redirect to the homepage for both types of requests
            return HttpResponseRedirect('/')

def answer_question(request):
    if request.method == "POST":
        expert = int(request.POST["expert"])

    user=User.objects.get(id=request.user.id)
    player=Player.objects.create(user=user,expert=expert)

    return HttpResponseRedirect('/')

def load_game_session(request, gametype_id):
    '''
    Serves the Game UI to users. Automatically assigns a user to a game based on players waiting in the player queue.
    :param request: the HTTP request object
    :param gametype_id: ID of the type of game (e.g. Papyrology, Music, etc)
    :return:
    '''
    round = ''


    # get the available game with the id
    game_type = AvailableGames.objects.get(id=gametype_id)

    # get pre-existing game with this user
    games = Game.objects.filter(Q(user1=request.user.id, complete=0) | Q(user2=request.user.id, complete=0))

    # create the game if necessary
    if len(games) == 0:   # User is not currently in a game
        # look at the player queue
        pq = PlayerQueue.objects.all()

        if len(pq) == 0: # if the player queue is empty, create a new game instance
            # Create a list of subjects for each user with some percentage of identity
            NUM_CLIPS = 20
            NUM_ROUNDS = 10
            NUM_SAME = 4

            clips = range(1, NUM_CLIPS)
            user1 = random.sample(range(1, NUM_CLIPS), 10)
            user2 = random.sample(range(1, NUM_CLIPS), 10)

            # Generate two list where user1[index] != user2[index]
            for index in range(len(user2)):
                if (user1[index] == user2[index]):
                    # Figure out what song we can replace in user2
                    # so they do not listen to the same song twice
                    canAdd = list(set(clips) - set(user2))
                    # Grab a random song from this list
                    replace = random.choice(canAdd)
                    # Replace it in the user2
                    user2[index] = replace


            # Create a list of random indexes (determining where
            # to serve the same clips to both)
            sameIndex = random.sample(range(0, NUM_ROUNDS-1), NUM_SAME)

            for index in range(len(sameIndex)):
                item1 = user1[sameIndex[index]]
                item2 = user2[sameIndex[index]]
                if item1 not in user2:
                    user2[sameIndex[index]] = item1
                elif item2 not in user1:
                    user1[sameIndex[index]] = item2
                else:
                    # Generate a single list of random IDs not currently
                    # in both lists
                    randomID = list(set(clips) - set(user1) - set(user2))
                    item = random.choice(randomID)
                    user1[sameIndex[index]] = item
                    user2[sameIndex[index]] = item

            # convert the lists
            user1 = ','.join(map(str, user1))
            user2 = ','.join(map(str, user2))

            # Create the Game instance
            game = Game.objects.create(user1=request.user.id,
                                           user1_subjects=user1,
                                           user2_subjects=user2)
            game.save()

            round = RoundResponses.objects.create()
            game.rounds.add(round)

            # Add the user to the PlayerQueue
            new_player = PlayerQueue.objects.create(user_id=request.user.id, api_key="")
            new_player.save()

            # Serve the first subject to the user
            subject_id = int(user1.split(",")[0])
            
            subject = Subject.objects.get(explicit_id=subject_id)


        else: # Player Queue isn't empty; Find the game with the player in the queue and add this user to the game.
            # get the first player in the queue
            existing_player = pq[0]
            PlayerQueue.objects.get(id=existing_player.id).delete()

            # get the game the existing player belongs to
            game = Game.objects.filter(Q(user1=existing_player.user_id, complete=0) | Q(user2=existing_player.user_id, complete=0))[0]

            # add the requesting user to the game as player 2
            game.user2 = request.user.id
            game.save()

            # serve the first subject in the user2_subjects to the user
            subject_id = int(game.user2_subjects.split(",")[0])
            subject = Subject.objects.get(explicit_id=subject_id)


    elif len(games) == 1:   # User is currently in a game.

        # get the user's game
        game = games[0]

                # check if they're user 1 or 2
        subject_set = ''
        if int(game.user1) == int(request.user.id):
            subject_set = game.user1_subjects
        elif int(game.user2) == int(request.user.id):
            subject_set = game.user2_subjects

        # get the subject at the round index.
        round_index = int(game.round_index)
        subject_id = int(subject_set.split(",")[int(round_index)-1])
        subject = Subject.objects.get(explicit_id=subject_id)

        # do we need to add a new round object?
        if round_index > int(game.rounds.count()):
            round = RoundResponses.objects.create()
            game.rounds.add(round)


    # get the round
    round = game.rounds.all().order_by('created')[int(game.round_index)-1]

    # is this the final subject for the round?
    final_round = 0
    if int(game.round_index) == 10:
        final_round = 1

    # determine if request.user is user1 or user2
    peer_id =''
    my_labels = []
    peer_labels = []
    if int(game.user1) == int(request.user.id):
        peer_id = 'togather'+str(game.user2)
        my_labels = str(round.user1_tags).split(',')
        peer_labels = str(round.user2_tags).split(',')

    elif int(game.user2) == int(request.user.id):
        peer_id = 'togather'+str(game.user1)
        my_labels = str(round.user2_tags).split(',')
        peer_labels = str(round.user1_tags).split(',')

    # determine if the two users are looking at the same content
    correct_answer = 0
    if str(game.user1_subjects).split(',')[int(game.round_index)-1] == str(game.user2_subjects).split(',')[int(game.round_index)-1]:
        correct_answer = 1

    return render(request, 'game_interface.html', {'game_type': game_type, 'game': game, 'my_labels': my_labels, 'peer_labels' : peer_labels,
                                                   'peer_id': peer_id,'subject': subject, 'subject_id': subject_id, 'final_round': final_round,
                                                   'correct_answer': correct_answer})


def add_label(request):
    # extract the values
    new_label = request.POST['label']
    game_id = request.POST['game_id']
    user_id = request.POST['user_id']
    round_index = request.POST['round']
    subject_id = int(request.POST['subject_id'])

    # get the game by id
    game = Game.objects.get(id=game_id)

    # check that the round is in the game already
    if int(game.rounds.count()) < int(round_index):
        # create the game round
        round = RoundResponses.objects.create()
        game.rounds.add(round)

        # save the label to the correct set of labels
        if int(user_id) == int(game.user1):
            round.user1_tags = str(new_label)
        elif int(user_id) == int(game.user2):
            round.user2_tags = str(new_label)

        # save the round
        round.save()

    else:
        # get the round at the relevant index
        round = game.rounds.all().order_by('created')[int(round_index)-1]

        # save the label to the correct set of labels
        if int(user_id) == int(game.user1):
            # set the user1 subject if necessary
            round.user1_subject = subject_id

            # add the label
            if round.user1_tags == '':
                round.user1_tags = new_label
            else:
                round.user1_tags = round.user1_tags+","+str(new_label)
        elif int(user_id) == int(game.user2):
            # set the user1 subject if necessary
            round.user2_subject = subject_id

            # add the label
            if round.user2_tags == '':
                round.user2_tags = str(new_label)
            else:
                round.user2_tags = round.user2_tags+","+str(new_label)

        # save the round
        round.save()

    print new_label + " " + game_id + " " + user_id
    return HttpResponse(200)


def add_vote(request):
    #extract values
    vote = request.POST['vote']
    game_id = request.POST['game_id']
    user_id = request.POST['user_id']
    round_index = request.POST['round']

    # get the game by id
    game = Game.objects.get(id=game_id)

    # get the round at the relevant index
    round = game.rounds.all().order_by('created')[int(round_index)-1]

    # save the label to the correct set of labels
    if int(user_id) == int(game.user1):
        if round.user1_vote == -1:
            round.user1_vote = int(vote)
    elif int(user_id) == int(game.user2):
        if round.user2_vote == -1:
            round.user2_vote = int(vote)

    # save the round
    round.save()

    # return a variable for round completeness
    round_complete = 0
    round_win = 0
    if int(round.user2_vote) != -1 and int(round.user1_vote) != -1:
        # mark the round as complete
        round_complete = 1

        # were the two users served the same subject?
        correct_result = 0
        if int(round.user1_subject) == int(round.user2_subject):
            correct_result = 1

        # were the two users right?
        if int(round.user2_vote) == correct_result and int(round.user1_vote) == correct_result:
            # mark the round as won
            round_win = 1
            round.result = 1
            game.score = F('score') + 10
        else:
            round.result = 0
        round.save()

        # increment the round and save the game
        # NOTE: It seems like the F() function doesn't evaluate
        # until saved to the db. Hence the extra save + get calls
        game.round_index = int(game.rounds.count()) + 1
        game.save()

        # check if game is complete
        if game.round_index == 11:
            game.complete = 1

        game.save()

    return HttpResponse(round_complete)


def game_summary(request, game_id):
    # get the game by ID
    game = Game.objects.get(id=game_id)

    # get the users' usernames
    user1 = User.objects.get(id=game.user1)
    user2 = User.objects.get(id=game.user2)

    return render(request, 'summary.html', {'game': game, 'user1': user1, 'user2': user2})


def get_peer_id(request):
    # extract the game_id
    game_id = request.GET['game_id']
    user_id = request.GET['user_id']
    print game_id
    print user_id

    # get the game by id
    game = Game.objects.get(id=game_id)

    data = -1
    # get the partner's id
    if int(user_id) == game.user1:
        data = game.user2
    elif int(user_id) == game.user2:
        data = game.user1

    peer_id = "togather"+str(data)
    print peer_id
    return HttpResponse(peer_id)