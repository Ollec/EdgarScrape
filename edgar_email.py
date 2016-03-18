#Import necessary modules
import smtplib
import datetime
from twilio.rest import TwilioRestClient
import feedparser
import openpyxl
import xml.etree.ElementTree as ET
import requests
import bs4
import time

#Initialize lists that we will record our data in
CompanyNameList = []
TickerList = []
ProcessedList = []
ReportingOwnerRelationshipList = []
TransactionSharesList = []
PricePerShareList = []
TotalValueList = []
transactionCodeList = []
DorIList = []
portfolio = []
bought_price = []
stocks_sent = []
checked = []


#----------------------------------------------------------------------------------#
#PULL FROM STOCK SCREEN EXCEL AND CURRENT PORTFOLIO

wb = openpyxl.load_workbook(filename = 'stock_screenv2.xlsx')
sheet = wb.active

print('Getting info from cells...')
for row in range(2, sheet.max_row + 1):
    company_name      = sheet['A' + str(row)].value
    ticker            = sheet['B' + str(row)].value
    CompanyNameList.append(company_name)
    TickerList.append(ticker)

wb.save('stock_screenv2.xlsx')

with open('portfolio.txt', 'r') as f:
    stocks = f.readlines()
    for item in stocks:
        item = item.strip()
        portfolio.append(item)

with open('bought_price.txt', 'r') as f:
    price = f.readlines()
    for item in price:
        item = item.strip()
        bought_price.append(item)

#----------------------------------------------------------------------------------#
#COMMUNICATION FUNCTIONS

def email(tradingSymbol, link):
    today = datetime.datetime.today()
    today = today.strftime('%m/%d/%Y %I:%M %p')
    smtpObj = smtplib.SMTP('smtp.gmail.com', 587)
    smtpObj.ehlo()
    smtpObj.starttls()
    smtpObj.login('***********************@gmail.com', '**********')
    print(smtpObj.sendmail('***************@gmail.com',\
                     '***************@gmail.com',\
                     'Subject: ' + str(today) + ' | Stock order: ' + str(tradingSymbol) + '.\nBuy this stock and heres the address + ' + str(link) + '\n'))
    smtpObj.quit()

def text_phone(tradingSymbol):
    accountSID = '***********************************'
    authToken = '***********************************'
    twilioCli = TwilioRestClient(accountSID, authToken)
    myTwilioNumber = '**************'
    myCellPhone = '*****************'
    message = twilioCli.messages.create(body='Yo, buy this stock: ' + str(tradingSymbol), from_=myTwilioNumber, to=myCellPhone)


#----------------------------------------------------------------------------------#
#SCAN EDGAR, SCRAPE XML, AND CHECK PRICES

#Gets the link to the XML of the relevant insider buy and looks for pre-defined characteristics on the Form 4
def scrape_xml(link):
    TotalValue = 0
    transactionCodeList = []
    DorIList = []
    today = datetime.datetime.today()
    today = today.strftime('%m/%d/%Y %I:%M %p')

    headers = {
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/48.0.2564.103 Safari/537.36",
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "accept-charset": "ISO-8859-1,utf-8;q=0.7,*;q=0.3",
    "accept-encoding": "gzip, deflate, sdch",
    "accept-language": "en-US,en;q=0.8",
    }
    res = requests.get(link, headers=headers)
    soup = bs4.BeautifulSoup(res.text, 'html.parser')
    try:
        for a in soup.find_all('a'):
            if 'Archives' in a['href'] and 'xml' in a.getText():
                address = 'http://www.sec.gov' + a['href']
                print ('Scraping XML on ' + str(today) + ' at ' + str(link))
                res = requests.get(address, headers=headers)
                tree = ET.fromstring(res.text)
                isOfficer = tree.find('reportingOwner/reportingOwnerRelationship/isOfficer')
                if isOfficer == None:
                    isOfficer = ''
                transactionCode = tree.findall('nonDerivativeTable/nonDerivativeTransaction/transactionCoding/transactionCode')
                if transactionCode == None:
                    transactionCode = []
                tradingSymbol = tree.find('issuer/issuerTradingSymbol')
                transactionShares = tree.findall('nonDerivativeTable/nonDerivativeTransaction/transactionAmounts/transactionShares/value')
                if transactionShares == None:
                    transactionShares = []
                transactionPricePerShare = tree.findall('nonDerivativeTable/nonDerivativeTransaction/transactionAmounts/transactionPricePerShare/value')
                if transactionShares == None:
                    transactionShares = []
                DorI = tree.findall('nonDerivativeTable/nonDerivativeTransaction/ownershipNature/directOrIndirectOwnership/value')
                if DorI == None:
                    DorI = []
                for price, shares, direct, code in zip(transactionPricePerShare, transactionShares, DorI, transactionCode):
                    if direct.text == 'D' and code.text == 'P':
                        TotalValue = TotalValue + float(shares.text)*float(price.text)
                for code in transactionCode:
                    transactionCodeList.append(code.text)
                for item in DorI:
                    DorIList.append(item.text)
                print (isOfficer.text)
                print(transactionCodeList)
                print (TotalValue)
                print (DorIList)
                print (tradingSymbol.text)  
                if isOfficer != None:
                    if isOfficer.text == str(1) and 'P' in transactionCodeList and TotalValue > 10000 and 'D' in DorIList and tradingSymbol.text not in portfolio:
                        print ('Stock found.')
                        print (today)
                        print (tradingSymbol.text)
                        with open('portfolio.txt', 'a') as f:
                            f.write(tradingSymbol.text + '\n')
                        ticker = tradingSymbol.text.lower()
                        res = requests.get('http://finance.yahoo.com/q?s=' + ticker)
                        soup = bs4.BeautifulSoup(res.text, 'html.parser')
                        elems = soup.select('#yfs_l84_'+str(ticker))
                        current_price = elems[0].getText()
                        with open('bought_price.txt', 'a') as f:
                            f.write(current_price + '\n')
                        email (tradingSymbol.text, link)
                        text_phone (tradingSymbol.text)
                        text_scott (tradingSymbol.text)
                        print ('~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')
    except Exception as e:
        print (address)
        print (e)
        print (datetime.datetime.today())
        pass

#Scrapes every entry on the RSS feed of the SEC's "Lastest Filings"
def edgar_feed(url):
    try:
        d = feedparser.parse(url)
        lower = [x.lower() for x in CompanyNameList]
        for entry in range(0,100):
            company_name = d.entries[entry].title.lower()
            company_name = company_name.split('- ')
            company_name = company_name[1].split(' (')
            company_name = company_name[0]
            if company_name in lower and d.entries[entry].title[0:1:] == '4':
                link = d.entries[entry].link
                stocks_sent.append(link)
                if link not in stocks_sent:
                    scrape_xml(link)
            else:
                pass
    except Exception as e:
        print (e)
        print (datetime.datetime.today())
        pass

#Checks prices in current portfolio and notifies to sell if +2% or -5%
def check_price():
    for stock, price in zip(portfolio, bought_price):
        ticker = stock.lower()
        res = requests.get('http://finance.yahoo.com/q?s=' + ticker)
        soup = bs4.BeautifulSoup(res.text, 'html.parser')
        elems = soup.select('#yfs_l84_'+str(ticker))
        current_price = elems[0].getText()
        ticker = stock.upper()
        if float(current_price) > 1.02*float(price) and stock not in checked:
        #Email
            today = datetime.datetime.today()
            today = today.strftime('%m/%d/%Y %I:%M %p')
            smtpObj = smtplib.SMTP('smtp.gmail.com', 587)
            smtpObj.ehlo()
            smtpObj.starttls()
            smtpObj.login('**************@gmail.com', 'password')
            print(smtpObj.sendmail('*****************@gmail.com',\
                             '*********************@gmail.com',\
                             'Subject: ' + str(today) + ' | Stock to sell after 2% gains: ' + str(ticker) + '.\nSell this stock' + '\n'))
            smtpObj.quit()
            #Text me
            accountSID = '*******************************'
            authToken = '*******************************'
            twilioCli = TwilioRestClient(accountSID, authToken)
            myTwilioNumber = '***************'
            myCellPhone = '**************'
            message = twilioCli.messages.create(body='Yo, sell this stock (2% gain): ' + str(ticker), from_=myTwilioNumber, to=myCellPhone)
            portfolio.remove(stock)
            bought_price.remove(price)
            checked.append(stock)
            f = open("portfolio.txt","r+")
            d = f.readlines()
            f.seek(0)
            for i in d:
                if i != str(stock + '\n'):
                    f.write(i)
            f.truncate()
            f.close()
            f = open("bought_price.txt","r+")
            d = f.readlines()
            f.seek(0)
            for i in d:
                if i != str(price + '\n'):
                    f.write(i)
            f.truncate()
            f.close()
            checked.append(stock)
        elif float(current_price) < .95*float(price) and stock not in checked:
        #Email
            today = datetime.datetime.today()
            today = today.strftime('%m/%d/%Y %I:%M %p')
            smtpObj = smtplib.SMTP('smtp.gmail.com', 587)
            smtpObj.ehlo()
            smtpObj.starttls()
            smtpObj.login('*****************@gmail.com', '*****************')
            print(smtpObj.sendmail('***********@gmail.com',\
                             '**************@gmail.com',\
                             'Subject: ' + str(today) + ' | Stock to sell after 5% losses: ' + str(ticker) + '.\nSell this stock' + '\n'))
            smtpObj.quit()
        #Text me
            accountSID = '**********************'
            authToken = '**********************'
            twilioCli = TwilioRestClient(accountSID, authToken)
            myTwilioNumber = '+13607270127'
            myCellPhone = '+13605626329'
            message = twilioCli.messages.create(body='Yo, sell this stock (5% losses): ' + str(ticker), from_=myTwilioNumber, to=myCellPhone)
        #Remove from portfolio
            portfolio.remove(stock)
            bought_price.remove(price)
            stock = stock.upper()
            f = open("portfolio.txt","r+")
            d = f.readlines()
            f.seek(0)
            for i in d:
                if i != str(stock + '\n'):
                    f.write(i)
            f.truncate()
            f.close()
            f = open("bought_price.txt","r+")
            d = f.readlines()
            f.seek(0)
            for i in d:
                if i != str(price + '\n'):
                    f.write(i)
            f.truncate()
            f.close()
            checked.append(stock)
        else:
            pass

#-------------------------------------------------------------------------------------#
#SCRIPT BODY

#Has a "while True" to make sure both functions (edgar_feed and check_price) run constantly    
url = 'http://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=&company=&dateb=&owner=only&start=0&count=100&output=atom'
print ('monitoring feed...')
run_counter = 0
def job():
    global run_counter
    time.sleep(10)
    run_counter += 1
    if run_counter % 100 == 0:
        print ('Completed ' + str(run_counter) + ' passes.')
    edgar_feed(url)
    check_price()

while True:
    job()


