import pickle, os, time, json, requests, bs4,sys, math
from copy import deepcopy
from requests import Session
from urllib.request import Request, urlopen
from functools import lru_cache

gameurl = 'https://byroredux-metacritic.p.mashape.com/search/game'
key = "clcFDDQWvcmshavNiBerDhWS2mPbp1VzntCjsnLyj1W2ZiKb97"
hdr = {'User-Agent': 'Chrome/37.0.2049.0'}

gamelist = {}

#http://www.metacritic.com/search/all/cod/results

global userlist

class User:
    def __init__(self, username, gamesReviewed):
        self.username = username
        self.gamesReviewed = gamesReviewed
        self.updateAvgRating()
        self.updateNumReviews()
        self.updateAvgWordCt() #
        self.goodReviews = [] #review scores from 7 - 10
        self.badReviews = [] #review scores from 0-6
        self.all_tfidf_list= []
        self.good_tfidf_list = []
        self.bad_tfidf_list = []
        self.filterReviews()

    def filterReviews(self):
        for review in self.gamesReviewed:
            if int(review[1]) >= 7:
                self.goodReviews.append(review)
            else:
                self.badReviews.append(review)

    def updateUser(self, newReviews):
        for review in newReviews not in self.gamesReviewed:
            if review[1] >= 7:
                self.goodReviews.append(review)
            else:
                self.badReviews.append(review)
            self.gamesReviewed += review
        self.updateAvgRating()
        self.updateNumReviews()
        self.updateAvgWordCt()
        self.updateReviews()

    def updateAvgRating(self):
        if len(self.gamesReviewed) > 0:
            self.avgRating = sum(int(n[1]) for n in self.gamesReviewed)/len(self.gamesReviewed) #location of review score per game
        else :
            self.avgRating = 0

    def updateAvgWordCt(self):
        self.avgWordCt = sum(len(n[2]) for n in self.gamesReviewed)/len(self.gamesReviewed)
    
    def updateNumReviews(self):
        self.numReviews = len(self.gamesReviewed)

#u = User("a", [("blah", "0", "this is a a sample"), ("meh", "1", "this is another another example example example")])

def tfidf(user, mode):
    print(user.username)
    totalDocuments = user.numReviews
    numDocWithTerm = {}
    termFrequencyList = {}
    TFIDFList = {}
    reviewList = None
    appendList = []
    LOG_BASE = 10

    if mode == "goodReviews":
        reviewList = user.goodReviews
    elif mode == "badReviews":
        reviewList = user.badReviews
    else:
        reviewList = user.gamesReviewed

    def termFrequencyUserReview(review, numDocWithTerm):
        idFDict = {}
        wordDictionary = {}
        wordList = []
        termCount = len(review.split())
        for word in review.split():
            #check if word is already found for idf calculation
            if not word in wordList: 
                if not word in numDocWithTerm:
                    numDocWithTerm[word] = 1
                else:
                    numDocWithTerm[word] += 1
                wordList.append(word)
            
            #for TF calculation
            if not word in wordDictionary:
                wordDictionary[word] = 1
            else:
                wordDictionary[word] += 1
        for term in wordDictionary:
            wordDictionary[term] = wordDictionary[term] #CHANGE tf to whatever specified -- currently raw

        return wordDictionary

    #Updates TermFrequency and the IDF counter
    for review in reviewList:
        termFrequencyList[review] = termFrequencyUserReview(review[2], numDocWithTerm)
    #Calculate IDF for each term in each review
    for review in reviewList:
        TFIDFList[review] = []
        for term in set(review[2].split()):
            tf = termFrequencyList[review][term]
            TFIDFList[review].append((term, tf * math.log(totalDocuments/numDocWithTerm[term], LOG_BASE)))
    
    for review, tfidfReview in TFIDFList.items():
        reversed(sorted(tfidfReview, key=lambda tup: tup[1]))
        appendList.append((review, tfidfReview))

    if mode == "goodReviews":
        user.good_tfidf_list = appendList 
    elif mode == "badReviews":
        user.bad_tfidf_list = appendList 
    else:
        user.all_tfidf_list = appendList 
            


# Suggest items based on difference between user and the item
#A) Similarity based. You make four groups of reviews. 
#1) Review texts of things the user has liked, (do tfidf on all good reviews)
#2) Review texts of things the user has disliked. (do tfidf on all bad review, gather up all words they have in common);
#3) Review texts of things everyone who liked the for each item (i) has said about,
# 4) review text of things everyone who disliked for each item  item (i) has said.
# Is the distance between |(1) - (3)| less than |(2) - (4)| ? if it is, then possible good item

def similarityBased(user):
    global userlist
    
    similarList = {}
    for username, temp_user in userlist.items():
        tfidf(temp_user, "goodReviews")
        tfidf(temp_user, "badReviews")
        tfidf(temp_user, "all")
    

    def cosineSimilarity(userReviewTFIDF, otherReviewTFIDF):
        Scores = {}
        Magnitude = {}
        userVector = dict(deepcopy(userReviewTFIDF))
        otherVector = dict(deepcopy(otherReviewTFIDF))
        dotproduct = 0
        d1 = 0
        d2 = 0

        for term in userReviewTFIDF:
            query_term = term[0]
            if query_term not in otherVector:
                otherVector[query_term] = 0
        for term in otherReviewTFIDF:
            query_term = term[0]
            if query_term not in userVector:
                otherVector[query_term] = 0

        for term, value in userVector.items():
            dotproduct += (userVector[term] * otherVector[term])
            d1 += math.pow(userVector[term], 2)
            d2 += math.pow(otherVector[term], 2)
        print(d1, d2)
        if d1 == 0 or d2 == 0:
            return 0
        cosSimilarity = dotproduct / (math.sqrt(d1) * math.sqrt(d2))
        return cosSimilarity
    #print(len(user.good_tfidf_list), user.good_tfidf_list, user.username)

    print(cosineSimilarity(user.good_tfidf_list[0][1], user.good_tfidf_list[1][1]))
    print(user.good_tfidf_list[0][0][0], user.good_tfidf_list[1][0][0])

#Checks the Metacritic Search page and gets the top 5 games

def findGame(gamename):
    global userlist
    global hdr

    def parseGameName(gamename):
        return gamename.replace(' ', '%20')

    req = Request('http://www.metacritic.com/search/game/' + parseGameName(gamename) + '/results', headers = hdr)
    page = urlopen(req)
    soup = bs4.BeautifulSoup(page)
    game_list_soup = soup.findAll("li", {"class" : "result"})
    queriedRes = []
    #gameTitles = game_list_soup.findAll("a", href=True)
    for game in game_list_soup:
        queriedRes.append({'url': 'http://www.metacritic.com/' + game.findAll("a", href=True)[0].attrs.get('href'), 'name': game.findAll("a", href=True)[0].get_text(), 'platform': game.findAll("span", {"class" : "platform"})[0].get_text()})
    if len(queriedRes) > 0:
        print("Found the following games: ")
        for idx in range(0, 5 if len(queriedRes) > 5 else len(queriedRes)):
            query = queriedRes[idx] 
            print((str(idx + 1) + "."), query['name'], "for the", query['platform'])
        while True:
            selected = int(input("Select a game number: ")) - 1
            if selected < 0 or selected > 5:
                raise Exception() 
            print("Searching for user reviews for %s for the %s" % (queriedRes[selected]['name'], queriedRes[selected]['platform']))
            url = queriedRes[selected]['url']
            return beginGameSearch(url)
    else:
        print("No games found similar to %s" % gamename)

@lru_cache(maxsize=32)
def beginGameSearch(gameurl):
    global userlist
    global hdr
       
    game_req = Request(gameurl, headers = hdr)
    game_soup = bs4.BeautifulSoup(urlopen(game_req))
    usernames = [b.attrs.get('href') for b in (game_soup.select("div.name a[href^=/user]"))]
    for name in usernames:
        name = name.split('/')[2] #split out the /user/ part
        if name in userlist:
            userlist[name].updateUser(beginUserSearch(name))
        else:
            games = beginUserSearch(name) 
            if games != "Bad User":
                new_user = User(name, games)
                userlist[name] = new_user
            
    return userlist

def beginUserSearch(username):
    start_time = time.time();
    game_users = getUserReviews(username + "?myscore-filter=Game", [])
    end_time = time.time();
    print('Getting username %s\'s data took %0.3f ms' % (username, ((end_time - start_time)*1000.0)))
    return game_users
    
    
def getPlatform(link):
    global hdr
    platform_req = Request('http://www.metacritic.com/' + link, headers = hdr)
    platform_soup = bs4.BeautifulSoup(urlopen(platform_req))
    platformString = platform_soup.find_all ("span", { "class" : "platform" })[0].get_text().strip()
    return platformString


"""
    TODO: Don't know how to accept foreign characters in review text so collapse.get_text() + expand.get_text() are encoded in utf-8 for now.
"""
def getUserReviews(user, games): 
    global hdr
    try:
        req = Request('http://www.metacritic.com/user/' + user, headers = hdr)
        page = urlopen(req)
        soup = bs4.BeautifulSoup(page)
        next_check_soup = soup.findAll("span", {"class" : "flipper next"})
        if next_check_soup:
           next_check_soup = next_check_soup[0].find_all("a", href=True)
        splitsoup = soup.select('div.user_profile_reviews')[0]
        platformLink = [a.attrs.get('href') for a in soup.select('div.review_content a[href^=/game]')]
        games.extend(list(zip([productName.get_text() for productName in splitsoup.find_all ("div", { "class" : "product_title" })],
                              #[getPlatform((link.attrs.get('href'))) for platformLink in soup.select('div.review_content a[href^=/game]')],
                              [userScore.get_text() for userScore in splitsoup.find_all ("div", { "class" : "metascore_w" })],
                              [collapse.get_text().encode('utf-8') + expand.get_text().encode('utf-8') for collapse,expand in zip(splitsoup.find_all("span", { "class" : "blurb_collapsed" }), splitsoup.find_all("span", { "class" : "blurb_expanded" }))])))
        if not next_check_soup:
            return games
        else:
            return getUserReviews(next_check_soup[0]['href'].split('/')[2], games)
    except Exception as e: 
        print("Could not get %s profile page -- %s " % (user, str(e)))
        return "Bad User"

def reloadUsrList(userlist):
    if os.path.isfile('userlist.txt'):
        with open("userlist.txt", 'rb') as infile:       
            while True:
                try:
                    c = pickle.load(infile)
                    userlist[c.username] = c 
                except EOFError:
                    break
             
def main():
    global userlist
    userlist = {}
    reloadUsrList(userlist)

    similarityBased(userlist["Woulong"])
    #for review in userlist["Woulong"].tfidf_list:
        #print(review[1])

    #for user,value in userlist.items():
        #tfidf(value)
    gamename = ""
    while True:
        gamename = input('Enter a gamename: ')
        if gamename == 'Quit':
            break
        findGame(gamename)
    with open("userlist.txt", 'wb') as outfile:
        print(userlist)
        for user in userlist:
            pickle.dump(userlist[user], outfile, pickle.HIGHEST_PROTOCOL)

main()

