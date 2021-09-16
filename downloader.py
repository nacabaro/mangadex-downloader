#!/usr/bin/env python3
import requests, os, datetime

##
quality = "data" ## Can be either data or dataSaver
##

def getMangaInfo(search):
    result = {}
    result.clear()
    r = requests.get(f'''https://api.mangadex.org/manga?title={search}&limit=100''')

    data = r.json()

    if not data['total'] == 0:
        for i in range(len(data['data'])):
            ## Structure = Number: {[Title, ID]}
            result.update({i+1: [data['data'][i]['attributes']['title']['en'], data['data'][i]['id']]})
    else:
        return 0

    return result

def getGroupInfo(search):
    result = {}

    r = requests.get(f'''https://api.mangadex.org/group?name={search}&limit=100''')
    data = r.json()

    if not data['total'] == 0:
        for i in range(0, len(data['data'])):
            ## Structure = Number: { [Title, ID] }
            result.update({i+1: [data['data'][i]['attributes']['name'], data['data'][i]['id']]})
    else:
        return 0

    return result

def getChapterInfo(titleID, groupID, chapter):
    result = {}
    pages = []
    global quality

    r = requests.get(f'''https://api.mangadex.org/chapter?manga={titleID}&groups[]={groupID}&chapter={chapter}''')
    data = r.json()

    id = data['data'][0]['id']

    if not data['total'] == 0:
        for i in data['data'][0]['attributes'][quality]:
            pages.append(i)

        r = requests.get(f'''https://api.mangadex.org/chapter/{id}''')
        data = r.json()

        ##  Structure:
        #   result = {
        #       id: chapterID
        #       hash: chapterHash
        #       title: chapterTitle
        #       pages: chapterPages
        #   }

        result.update({"id": id, "hash": data['data']['attributes']['hash'], "title": data['data']['attributes']['title'], "pages": pages})

        return result
    else:
        return 0

def getMDaHServer(chapterID):
    r = requests.get(f'''https://api.mangadex.org/at-home/server/{chapterID}''')
    data = r.json()

    return data['baseUrl']

def createMangaFolder(mangaTitle):
    if not os.path.isdir(mangaTitle):
        os.mkdir(mangaTitle)

def createChapterFolder(mangaTitle, chapterTitle, chapterNumber):
    chapterTitle = chapterTitle.replace("?", '').replace("!", '').replace(".", '').replace("/", '-').replace('"','')
    format = f'{mangaTitle}/Chapter {chapterNumber} - {chapterTitle}'

    if not os.path.isdir(f'{format}'):
        os.mkdir(format)

    print(f'Created {chapterTitle}')

    return chapterTitle

def downloadChapter(mangaTitle, chapterTitle, chapterHash, chapterID, chapterNumber, chapterFolder, chapterPages, serverURL, quality):
    chapterPage = 0

    for page in chapterPages:
        chapterPage += 1
        attempt = 1

        filename=f'{mangaTitle}/Chapter {chapterNumber} - {chapterFolder}/{str(chapterPage).zfill(3)}.png'
        url = f'''{serverURL}/{quality}/{chapterHash}/{page}'''

        while not attempt == 0 and attempt < 10:
            r = requests.get(url)

            if r.ok:
                print(f'OK! {filename}')
                success = True
                attempt = 0

                open(f'{filename}', 'wb').write(r.content)
            else:
                print(f'FAIL! {filename} WITH {r.status_code}')
                print(f'Attempt {attempt}')
                success = False
                attempt += 1

        if r.status_code == 404 or r.status_code == 500:
            errorCode = r.status_code
            writeBrokenChapters(chapterID, chapterPage, errorCode)

        if not os.path.isfile(filename):
            size = 0
        else:
            size = os.stat(filename).st_size

        reportChapter(url, r.ok, size, r.elapsed.microseconds // 1000, success)

def reportChapter(serverURL, success, bytes, duration, cache):
    json = {
        "url": f'{serverURL}',
        "success": success,
        "bytes": bytes,
        "duration": duration,
        "cached": cache
    }

    r = requests.post(url="https://api.mangadex.network/report", json=json)

def writeBrokenChapters(chapterid, num, error):
    filename = "errors.txt"
    errors = open(filename, 'a')
    errors.write(f'id={chapterid}; page={num}; err={error}\n')
    errors.close()

def showResults(result):
    if not result == 0:
        for number, data in result.items():
            print(f'{number} -- {data[0]} -- {data[1]}')
    else:
        print("No mangas/groups with that name were found.")
        return 0

    return select(result)

def select(result):
    choice = input("Input the number of the manga to download> ")
    if int(choice) in result.keys():
        return result[int(choice)]
    else:
        return 0

def main():
    global quality

    search = input("Manga?> ")
    mangaInfo = showResults(getMangaInfo(search))
    if not mangaInfo == 0:
        print(f'{mangaInfo[0]} -- {mangaInfo[1]}')
    else:
        print("Couldn't find manga.")
        return 0

    search = input("Group?> ")
    groupInfo = showResults(getGroupInfo(search))
    if not groupInfo == 0:
        print(f'{groupInfo[0]} -- {groupInfo[1]}')
    else:
        print("Couldn't find group.")
        return 0

    createMangaFolder(mangaInfo[0])

    start = input("Start?> ")

    if not str(start).startswith("!"):
        end = int(input("End?> "))

        for chapterNumber in range(int(start), end):
            chapterInfo = getChapterInfo(mangaInfo[1], groupInfo[1], chapterNumber)
            MDaHServer = getMDaHServer(chapterInfo["id"])
            chapterFolder = createChapterFolder(mangaInfo[0], chapterInfo["title"], chapterNumber)
            downloadChapter(mangaInfo[0], chapterInfo["title"], chapterInfo["hash"], chapterInfo["id"], chapterNumber, chapterFolder, chapterInfo["pages"], MDaHServer, quality)
    else:
        chapterNumber = start.strip("!")
        chapterInfo = getChapterInfo(mangaInfo[1], groupInfo[1], int(chapterNumber))
        MDaHServer = getMDaHServer(chapterInfo["id"])
        chapterFolder = createChapterFolder(mangaInfo[0], chapterInfo["title"], int(chapterNumber))
        downloadChapter(mangaInfo[0], chapterInfo["title"], chapterInfo["hash"], chapterInfo["id"], int(chapterNumber), chapterFolder, chapterInfo["pages"], MDaHServer, quality)

main()
