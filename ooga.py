import requests
from bs4 import BeautifulSoup
from datetime import datetime as dt
import numpy as np
import pandas as pd
from collections import Counter

def getDate(html):
    date = html.find(class_="date_read_value")
    if date is not None:
        date = date.get_text()
        format = '%b %d, %Y'
        return dt.strptime(date, format)
    else:
        return None

def getId(html):
    titleTd = html.find(class_="title")
    linkText = titleTd.find("a").get('href').split('/')[3]
    splitLink = linkText.split('-')
    if splitLink.__len__() == 1:
        splitLink = linkText.split('.')
    if splitLink.__len__() > 0:
        return splitLink[0]
    else:
        return -1

def getTitle(html):
    title = html.find(class_="Text__title1")
    return title.get_text() if title is not None else "n/a"

def getAuthor(html):
    author = html.find(class_="ContributorLink__name")
    return author.get_text() if author is not None else "n/a"

def getGivenRating(html):
    rating = html.find(class_="staticStars").get("title")
    match rating:
        case 'did not like it':
            return 1
        case 'it was ok':
            return 2
        case 'liked it':
            return 3
        case 'really liked it':
            return 4
        case 'it was amazing':
            return 5
        case default:
            return np.NaN

def getAvgRating(html):
    rating = html.find(class_="RatingStatistics__rating")
    return rating.get_text()

def getGenres(html):
    genresListContainer = html.find(class_="BookPageMetadataSection__genres")
    genresHtml = genresListContainer.find_all(class_="Button__labelItem")
    genres = map(lambda obj: obj.get_text(), genresHtml)
    return list(genres)[slice(5)] # just get top 5 genres

def getInfo(html):
    bookDetails = html.find(class_="BookDetails")
    pagesHtml = bookDetails.find("p", {"data-testid" : "pagesFormat"})
    pages = pagesHtml.get_text().split()[0]
    pubInfo = bookDetails.find("p", {"data-testid" : "publicationInfo"})
    date = pubInfo.get_text().split()[-1]
    return pages, date

headers = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Max-Age': '3600',
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

year = 2023
minDate = dt(year, 1, 1)
maxDate = dt(year + 1, 1, 1)

# TODO: add in maxDate checking
uid = 105241766
page = 1

isFirstPage = False
while not isFirstPage:
    url = f'https://www.goodreads.com/review/list/{uid}?page={page}ref=nav_mybooks&shelf=read&sort=date_read'
    req = requests.get(url, headers)
    soup = BeautifulSoup(req.content, 'html.parser')
    pageBooks = soup.find_all(class_="bookalike")

    # TODO: figure out if this should be < or <=
    pageContainsMaxDate = [book for book in pageBooks if getDate(book) is not None and getDate(book) <= maxDate].__len__() > 0
    if pageContainsMaxDate:
        isFirstPage = True
    else:
        page += 1

print('Getting reading info...')
isLastPage = False
bookIds = []
bookDatesRead = []
bookGivenRatings = []
while not isLastPage:
    url = f'https://www.goodreads.com/review/list/{uid}?page={page}ref=nav_mybooks&shelf=read&sort=date_read'

    req = requests.get(url, headers)
    soup = BeautifulSoup(req.content, 'html.parser')
    pageBooks = soup.find_all(class_="bookalike")

    # check for completed books
    pageContainsMinDate = [book for book in pageBooks if getDate(book) is not None and getDate(book) < minDate].__len__() > 0
    if pageContainsMinDate:
        isLastPage = True
    
    # filter based on 
    pageBooks = [book for book in pageBooks if getDate(book) is not None and getDate(book) >= minDate and getDate(book) < maxDate]
    for book in pageBooks:
        bookIds.append(getId(book))
        bookDatesRead.append(getDate(book))
        bookGivenRatings.append(getGivenRating(book))
        # TODO: add null checking to all of these

    page += 1

print(f'{len(bookIds)} books found for {year}')

print('Getting info for each book...')
bookTitles = []
bookAuthors = []
bookAvgRatings = []
bookGenres = []
bookNumPages = []
bookPubYears = []
for id in bookIds:
    url = f'https://goodreads.com/book/show/{id}'
    req = requests.get(url, headers)
    soup = BeautifulSoup(req.content, 'html.parser')
    bookContent = soup.find(class_="BookPage__mainContent")
    if bookContent is None:
        print('\nsomething went wrong :(')
        print(id)
        print(url)
        print('\n')
        bookTitles.append("n/a")
        bookAuthors.append("n/a")
        bookAvgRatings.append(np.NaN)
        bookGenres.append(np.NaN)
        numPages, pubYear = np.NaN,np.NaN
        bookNumPages.append(np.NaN)
        bookPubYears.append(np.NaN)
        # print(soup.prettify())
        continue
    bookTitles.append(getTitle(bookContent))
    bookAuthors.append(getAuthor(bookContent))
    bookAvgRatings.append(getAvgRating(bookContent))
    bookGenres.append(getGenres(bookContent))
    numPages, pubYear = getInfo(bookContent)
    bookNumPages.append(numPages)
    bookPubYears.append(pubYear)

bookData = pd.DataFrame()
bookData['ID'] = bookIds
bookData['Titles'] = bookTitles
bookData['Author'] = bookAuthors
bookData['Date Read'] = bookDatesRead
bookData['User Rating'] = bookGivenRatings
bookData['Average Rating'] = bookAvgRatings
bookData['Genres'] = bookGenres
bookData['Number of Pages'] = bookNumPages
bookData['Year Published'] = bookPubYears

print(bookData)

pagesData = bookData["Number of Pages"].dropna()
print(f'Max pages: {pagesData.max()}')
print(f'Min pages: {pagesData.min()}')
#print(f'Avg pages: {pagesData.mean()}')
print('\n')

print(bookData["Number of Pages"])

mostCommonAuthor = Counter(bookData['Author']).most_common(1)
print(f'Most common author: {mostCommonAuthor}')

allGenresList = []
for genreList in pagesData['Genre']:
    allGenresList.extend(genreList)
topGenres = Counter(allGenresList).most_common(5)
print(f'Top 5 genres: {topGenres}')