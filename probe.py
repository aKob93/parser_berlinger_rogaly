import os
import re
import time
import lxml
import shutil
import sys
import aiohttp
import asyncio
import aiofiles
import requests
from bs4 import BeautifulSoup
from aiohttp_retry import RetryClient, ExponentialRetry
from fake_useragent import UserAgent
from openpyxl import load_workbook
from tqdm import tqdm
import datetime
from PIL import Image, ImageFile

ua = UserAgent()
headers = {'user_agent': ua.random}

url2 = 'https://berlingerhaus.ru/catalog/?q=BH-1718&how=r'
response = requests.get(url2, headers=headers)
soup = BeautifulSoup(response.text, 'lxml')
print(response.text)
print(soup.find('div', class_='item-title'))

