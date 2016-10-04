# EdgarScrape

This script scrapes the Edgar database (by the Security Exchange Commission) and looks for "insider buys" by officers of public companies.
This includes CEOs, COOs, etc. If they make a purchase big enough through the direct market (i.e. not a vesting of stock or something),
the script texts and emails you an alert to buy the stock.

The script also maintains a portfolio in text files and constantly checks for prices using Yahoo Finance. If the stock has gained 2% or 
lost 5%, the script emails and texts and alert for you to sell that stock.

Posted here: https://hofdata.com/2016/03/18/investing-with-python/
