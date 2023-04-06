# -*- coding: utf8 -*-
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


class Parser:

    def __init__(self):
        ua = UserAgent()
        self.headers = {'user_agent': ua.random}
        self.token = ''
        self.secret_key = ''
        self.active_token = ''
        self.active_secret_key = ''
        self.base_url = 'https://berlinger-haus-shop.ru'
        self.article_numbers = []
        self.links_products = {}
        self.article_imgs = {}
        self.article_save_imgs = {}
        self.read_data_file = ''

    def open_token_file(self):
        try:
            with open('token.txt', 'r') as file:
                for i, line in enumerate(file):
                    if i == 0:
                        self.token = line.split('=')[1].strip().split(', ')
                    elif i == 1:
                        self.secret_key = line.split('=')[1].strip().split(', ')
        except Exception:
            print('Не удалось прочитать token или secret_key')
            raise IndexError

    def read_file(self):
        try:
            for file in os.listdir():
                if file[:6] == 'data1.':
                    self.read_data_file = file
        except Exception:
            print('Нет файла с именем data.')
            raise IndexError

    def get_article_number(self):
        try:
            wb = load_workbook(filename=self.read_data_file)
            sheets = wb.sheetnames
            ws = wb[sheets[0]]

            for row in ws.iter_cols(min_col=2, max_col=2, min_row=9):
                for cell in row:
                    if cell.value is None:
                        continue
                    # есть ли числа в строке
                    if re.search('\d+', cell.value.strip().split(' ')[0]):
                        self.article_numbers.append(cell.value.strip().split(' ')[0])

            self.article_numbers = list(dict.fromkeys(self.article_numbers))
        except Exception as exc:
            print(f'Ошибка {exc} в чтении табличного документа data.xlsx')
            with open('error.txt', 'a', encoding='utf-8') as file:

                file.write(f'{datetime.datetime.now().strftime("%d-%m-%y %H:%M")} '
                           f'Ошибка {exc} в чтении табличного документа data.xlsm, функция - get_article_number()\n')
            raise IndexError

    def get_link_prodicts(self):
        # self.article_numbers = ['BH-9093']
        for art in self.article_numbers:
            if len(art) == 1:
                continue
            response = requests.get(f'{self.base_url}/search?q={art[3:]}', headers=self.headers)
            soup = BeautifulSoup(response.text, features='lxml')

            product_not_found = soup.find('p', class_='warning')
            if bool(product_not_found) is False:

                # TODO обработать когда на странице несколько товаров
                if f'{self.base_url}/search?q={art[3:]}' == response.url:
                    found_links_some_product = soup.find_all('div', class_='item-img')
                    self.links_products[art] = found_links_some_product[0].find('a')['href']
                # когда ссылка на новую страницу с продуктом
                else:
                    article_on_page = soup.find('div', class_='goodsDataMainModificationArtNumber').find(
                        'span').text.strip()
                    print(art, article_on_page)
                    # при совпадении искомого артикула с артикулом на странице
                    if art[3:] in article_on_page:
                        some_links_imgs = soup.find('div', class_='thumblist-box').find_all('li')
                        # при нескольких изображениях
                        if len(some_links_imgs) > 1:
                            self.article_imgs.setdefault(art, [img.find('a')['href'] for img in some_links_imgs])
                        elif len(some_links_imgs) == 1:
                            link_img_found = soup.find('div', class_='product-img-box col-md-5 col-sm-12 col-sms-12')
                            link_img = link_img_found.find_all('a')
                            self.article_imgs.setdefault(art, [link['href'] for link in link_img])

                        # при одном изображении
                        else:
                            link_img_found = soup.find('div', class_='general-img popup-gallery')
                            if link_img_found.find('a') == None:
                                continue
                            else:
                                link_img = link_img_found.find_all('a')
                                self.article_imgs.setdefault(art, [link['href'] for link in link_img])
                    # если на странице артикул не совпадает с искомым
                    else:
                        continue

            else:
                print(product_not_found.text)
        print(self.links_products)
        print(self.article_imgs)

    # TODO проход по ссылкам и сбор недостающих изображений
    def get_link_img(self):
        self.links_products = {
            'BH-7061': 'https://berlinger-haus-shop.ru/goods/Nabor-kastryul-s-mramornym-pokrytiem-Royalty-Line-RL-BS1010M-Cooper?mod_id=285547898',
            'BH-7072': 'https://berlinger-haus-shop.ru/goods/Nabor-kontejnerov-Blaumann-BL-3363-5-pr?mod_id=240768142',
            'BH-7081': 'https://berlinger-haus-shop.ru/goods/Nabor-posudy-10pr-BerlingerHaus-VN-7081-Monaco?mod_id=300601317',
            'BH-7082': 'https://berlinger-haus-shop.ru/goods/BH-7082-Monaco-Collection-Skovoroda-20sm-Berlinger-Haus?mod_id=300595273',
            'BH-7083': 'https://berlinger-haus-shop.ru/goods/Skovoroda-24sm-BerlingerHaus-VN-7083-Monaco?mod_id=300595836',
            'BH-7088': 'https://berlinger-haus-shop.ru/goods/VN-7088-Monaco-Collection-Kastryulya-so-steklyannoj-kryshkoj-28sm-6?mod_id=300600221',
            'BH-6625': 'https://berlinger-haus-shop.ru/goods/Skovoroda-24-sm-Berlinger-Haus-BH-6625-Royal-Purple-Metallic-Line?mod_id=266521357',
            'BH-6627': 'https://berlinger-haus-shop.ru/goods/BH-6627-Purple-Eclips-Kovsh-16sm-Berlinger-Haus?mod_id=272547246',
            'BH-6628': 'https://berlinger-haus-shop.ru/goods/Kastryulya-s-kryshkoj-20sm-Berlinger-Haus-VN-6628-Purple-Eclips-Collection-2?mod_id=261759814',
            'BH-6630': 'https://berlinger-haus-shop.ru/goods/Kastryulya-s-kryshkoj-28sm-Berlinger-Haus-VN-6630-Purple-Eclips-Collection?mod_id=274789997',
            'BH-6632': 'https://berlinger-haus-shop.ru/goods/Sotejnik-s-kryshkoj-28sm-Berlinger-Haus-VN-6632-Royal-Purple-Metallic-Line?mod_id=265063575',
            'BH-7026': 'https://berlinger-haus-shop.ru/goods/Flip-skovoroda-26sm-Berlinger-Haus-VN-7026-Purple-Eclips-Collection?mod_id=300592632',
            'BH-7102': 'https://berlinger-haus-shop.ru/goods/BH-7102-Purple-Eclips-Nabor-posudy-4-pr?mod_id=300594691',
            'BH-7103': 'https://berlinger-haus-shop.ru/goods/BH-7103-Purple-Eclips-Collection-Nabor-posudy-3-pr?mod_id=300591208',
            'BH-7104': 'https://berlinger-haus-shop.ru/goods/BH-7104-Purple-Eclips-Nabor-posudy-3-pr?mod_id=302601142',
            'BH-7105': 'https://berlinger-haus-shop.ru/goods/BH-7105-Purple-Eclips-Gril-skovoroda-s-kryshkoj?mod_id=300594857',
            'BH-7107': 'https://berlinger-haus-shop.ru/goods/NABOR-STALNYH-NOZheJ-NA-PODSTAVKe-BERLINGER-HAUS-2528-BH?mod_id=285546608',
            'BH-7138': 'https://berlinger-haus-shop.ru/goods/Kovsh-16sm-BerlingerHaus-BH-7138-Purple-Eclips-Collection?mod_id=300591937',
            'BH-7145': 'https://berlinger-haus-shop.ru/goods/BH-7036-Purple-Eclips-Line-Nabor-posudy-2?mod_id=300586185',
            'BH-1884': 'https://berlinger-haus-shop.ru/goods/NABOR-POSUDY-12-PReDMeTOV-BERLINGER-HAUS-I-ROSE-EDITION-VN?mod_id=285546877',
            'BH-6143': 'https://berlinger-haus-shop.ru/goods/BH-6143-Aquamarine-Edition-Nabor-posudy-10-pr-BerlingerHaus?mod_id=285546386',
            'BH-6152': 'https://berlinger-haus-shop.ru/goods/BH-6152-Aquamarine-Edition-Nabor-posudy-10-pr?mod_id=285546387',
            'BH-6165': 'https://berlinger-haus-shop.ru/goods/BH-6165-Aquamarine-Metallic-Line-Sotejnik-s-kryshkoj?mod_id=285546394',
            'BH-1626N': 'https://berlinger-haus-shop.ru/goods/Sotejnik-s-kryshkoj-28sm-BerlingerHaus-VN-1626N-Black-burgundy-Metallic-Line?mod_id=285546578',
            'BH-1251': 'https://berlinger-haus-shop.ru/goods/Skovoroda-20sm-Berlinger-Haus-VN-1251-Burgundy-Metallic-Line?mod_id=285546480',
            'BH-1253': 'https://berlinger-haus-shop.ru/goods/Skovoroda-28sm-Berlinger-Haus-VN-1253-Burgundy-Metallic-Line?mod_id=285546477',
            'BH-1254': 'https://berlinger-haus-shop.ru/goods/%D0%A1%D0%BA%D0%BE%D0%B2%D0%BE%D1%80%D0%BE%D0%B4%D0%B0-30%D1%81%D0%BC-Berlinger-Haus-%D0%92%D0%9D-1254-Burgundy-Metallic-Line?mod_id=285548339',
            'BH-1255': 'https://berlinger-haus-shop.ru/goods/%D0%9A%D0%BE%D0%B2%D1%88-1-3%D0%BB-16%D1%81%D0%BC-Berlinger-Haus-%D0%92%D0%9D-1255-Burgundy-Metallic-Line?mod_id=285546471',
            'BH-1257': 'https://berlinger-haus-shop.ru/goods/SKOVORODA-GRIL-ALyuMINIeVAya-BLAUMANN-BL?mod_id=285547832',
            'BH-1258': 'https://berlinger-haus-shop.ru/goods/Kastryulya-6l-28sm-Berlinger-Haus-VN-1258-Burgundy-Metallic-Line?mod_id=285546455',
            'BH-1260': 'https://berlinger-haus-shop.ru/goods/Skovoroda-s-kryshkoj-28sm-Berlinger-Haus-VN-1260-Burgundy-Metallic-Line?mod_id=285546467',
            'BH-1261': 'https://berlinger-haus-shop.ru/goods/Skovoroda-s-kryshkoj-32sm-Berlinger-Haus-VN-1261-Burgundy-Metallic-Line?mod_id=285546466',
            'BH-1264': 'https://berlinger-haus-shop.ru/goods/%D0%A1%D0%BE%D1%82%D0%B5%D0%B9%D0%BD%D0%B8%D0%BA-%D1%81-%D0%BA%D1%80%D1%8B%D1%88%D0%BA%D0%BE%D0%B9-32%D1%81%D0%BC-Berlinger-Haus-%D0%92%D0%9D-1264-Burgundy-Metallic-Line?mod_id=285546462',
            'BH-1267': 'https://berlinger-haus-shop.ru/goods/%D0%A1%D0%BA%D0%BE%D0%B2%D0%BE%D1%80%D0%BE%D0%B4%D0%B0-%D0%B2%D0%BE%D0%BA-28%D1%81%D0%BC-Berlinger-Haus-%D0%92%D0%9D-1267-Burgundy-Metallic-Line?mod_id=285546475',
            'BH-1613N': 'https://berlinger-haus-shop.ru/goods/Gril-skovoroda-s-kryshkoj-28sm-BerlingerHaus-BH-1613N-Burgundy-Metallic-Line-2?mod_id=285546483',
            'BH-1674': 'https://berlinger-haus-shop.ru/goods/Nabor-posudy-12-pr-Berlinger-Haus-Metallic-Line-Burgundy-Edition-VN-3?mod_id=285548132',
            'BH-1946': 'https://berlinger-haus-shop.ru/goods/SOTeJNIK-S-KRYShKOJ-ROYALTY-LINE-RL-BR28M-3?mod_id=285547162',
            'BH-6166': 'https://berlinger-haus-shop.ru/goods/Skovoroda-vok-30sm-Berlinger-Haus-s-Burgundy-Metallic-Line?mod_id=222189163',
            'BH-7035': 'https://berlinger-haus-shop.ru/goods/BH-7035-Burgundy-Metallic-Line-Nabor-posudy?mod_id=285543349',
            'BH-7110': 'https://berlinger-haus-shop.ru/goods/Skovoroda-Vok-s-kryshkoj-30sm-Berlinger-Haus-BH-7110-Burgundy-Metallic-Line?mod_id=301854771',
            'BH-6918': 'https://berlinger-haus-shop.ru/goods/Kontejner-d-syp-prod-WR-6918-1?mod_id=285547219',
            'BH-6051': 'https://berlinger-haus-shop.ru/goods/BH-6051-Emerald-Collection-Metallic-Line-Gril-skovoroda-so-steklyannoj-kryshkoj?mod_id=285546792',
            'BH-6052': 'https://berlinger-haus-shop.ru/goods/BH-2501-Nabor-nozhej-7-pr?mod_id=285546539',
            'BH-6087': 'https://berlinger-haus-shop.ru/goods/BH-6087-Skovoroda-24sm-Berlinger-Haus-Emerald-Collection?mod_id=285545099',
            'BH-6167F': 'https://berlinger-haus-shop.ru/goods/BH-1883F-Aquamarine-Edition-Metallic-Line-Nabor-iz-2-h-skovorod?mod_id=285546391',
            'BH-6024': 'https://berlinger-haus-shop.ru/goods/4?mod_id=285546890',
            'BH-6104': 'https://berlinger-haus-shop.ru/goods/NABOR-POSUDY-12-PReDMeTOV-BERLINGER-HAUS-I-ROSE-EDITION-VN?mod_id=285546877',
            'BH-1991': 'https://berlinger-haus-shop.ru/goods/BH-9162-Black-Rose-Collection-Izmelchitel-mehanieskij?mod_id=285547264',
            'BH-1992': 'https://berlinger-haus-shop.ru/goods/BH-2525-Nabor-nozhej-7-pr-2?mod_id=285546800',
            'BH-6012': 'https://berlinger-haus-shop.ru/goods/KASTRyuLya-24-SM-BERLINGER-HAUS-MOONLIGHT-EDITION-6012-VN?mod_id=285546927',
            'BH-6169': 'https://berlinger-haus-shop.ru/goods/VN-6169-Moonlight-Edition-Nabor-posudy-3-pr?mod_id=285546923',
            'BH-1518N': 'https://berlinger-haus-shop.ru/goods/Skovoroda-s-kryshkoj-28-sm-Berlinger-Haus-BH-1518N-Rosegold-Line?mod_id=285547004',
            'BH-6142': 'https://berlinger-haus-shop.ru/goods/BH-6142-Rosegold-Line-Nabor-posudy-10-pr-BerlingerHaus?mod_id=285546985',
            'BH-1894': 'https://berlinger-haus-shop.ru/goods/NABOR-POSUDY-15-PR-BERLINGER-HAUS-MOONLIGHT-EDITION-VN-2?mod_id=285546929',
            'BH-1895': 'https://berlinger-haus-shop.ru/goods/BH-7107-Purple-Eclips-Nabor-posudy-6-pr?mod_id=300594852',
            'BH-1900': 'https://berlinger-haus-shop.ru/goods/Planetarnyj-mikser-KOMBAJN-TeSTOMeS-ROYALTY-LINE-1900V-RL-PKM1900-7-0?mod_id=285547447',
            'BH-6605': 'https://berlinger-haus-shop.ru/goods/BH-6605-Shiny-Black-Edition-Kastryulya-so-steklyannoj-kryshkoj?mod_id=285544765',
            'BH-6616': 'https://berlinger-haus-shop.ru/goods/BH-6616-Shiny-Black-Edition-Nabor-posudy?mod_id=285544066',
            'BH-1202': 'https://berlinger-haus-shop.ru/goods/Sotejnik-s-kryshkoj-32sm-Berlinger-Haus-BH-1202-Forest-Line?mod_id=285548105',
            'BH-1204': 'https://berlinger-haus-shop.ru/goods/Skovoroda-vok-28sm-Berlinger-Haus-BH-1204-Forest-Line?mod_id=285546769',
            'BH-1210': 'https://berlinger-haus-shop.ru/goods/Sotejnik-s-kryshkoj-24sm-Berlinger-Haus-BH-1210-Forest-Line?mod_id=285546768',
            'BH-1095': 'https://berlinger-haus-shop.ru/goods/%D0%9A%D0%B0%D1%81%D1%82%D1%80%D1%8E%D0%BB%D1%8F-%D1%81-%D0%BA%D1%80%D1%8B%D1%88%D0%BA%D0%BE%D0%B9-4-2%D0%BB-24%D1%81%D0%BC-Berlinger-Haus-BH-1095-Granit-Diamond-Line?mod_id=285546843',
            'BH-1096': 'https://berlinger-haus-shop.ru/goods/Kastryulya-s-kryshkoj-5-8l-28sm-Berlinger-Haus-BH-1096-Granit-Diamond-Line?mod_id=285546841',
            'BH-1101': 'https://berlinger-haus-shop.ru/goods/BC-2022-Nabor-posudy?mod_id=285547562',
            'BH-1107': 'https://berlinger-haus-shop.ru/goods/%D0%A1%D0%BA%D0%BE%D0%B2%D0%BE%D1%80%D0%BE%D0%B4%D0%B0-%D1%81%D0%BE-%D1%81%D1%8A%D0%B5%D0%BC%D0%BD%D0%BE%D0%B9-%D1%80%D1%83%D1%87%D0%BA%D0%BE%D0%B9-24%D1%81%D0%BC-Berlinger-Haus-BH-1107-Granit-Diamond-Line?mod_id=285546860',
            'BH-1446': 'https://berlinger-haus-shop.ru/goods/BH-1446-Granit-Diamond-Line-Tazhin-28-sm?mod_id=302600951',
            'BH-1634N': 'https://berlinger-haus-shop.ru/goods/Skovoroda-so-steklyannoj-kryshkoj-24sm-BerlingerHaus-VN-1643N-Black-Rose-2?mod_id=285546526',
            'BH-1645N': 'https://berlinger-haus-shop.ru/goods/Nabor-posudy-10pr-BerlingerHaus-VN-1645N-Black-Rose-2?mod_id=285546505',
            'BH-6149': 'https://berlinger-haus-shop.ru/goods/BH-6149-Black-Rose-Nabor-posudy-10-pr-BerlingerHaus?mod_id=285543434',
            'BH-6154': 'https://berlinger-haus-shop.ru/goods/BH-6154-Black-Rose-Nabor-posudy-10-pr?mod_id=285546507',
            'BH-6766': 'https://berlinger-haus-shop.ru/goods/Sotejnik-s-kryshkoj-28sm-Berlinger-Haus-VN?mod_id=285547374',
            'BH-7423': 'https://berlinger-haus-shop.ru/goods/BH-7423-Eternal-Collection-Skovoroda?mod_id=285546826',
            'BH-6072': 'https://berlinger-haus-shop.ru/goods/Skovoroda-20sm-BerlingerHaus-VN-6046-Emerald?mod_id=285546790',
            'BH-6074': 'https://berlinger-haus-shop.ru/goods/BH-6074-Primal-Gloss-Collection-Nabor-posudy-4-pr?mod_id=302601284',
            'BH-6567': 'https://berlinger-haus-shop.ru/goods/BH-6567-Primal-Gloss-Collection-Skovoroda?mod_id=285547071',
            'BH-6569': 'https://berlinger-haus-shop.ru/goods/Skovoroda-28sm-Berlinger-Haus-VN-6569-Prima-Gloss?mod_id=285547069',
            'BH-6571': 'https://berlinger-haus-shop.ru/goods/BH-6571-Primal-Gloss-Collection-Kastryulya-so-steklyannoj?mod_id=285547065',
            'BH-6572': 'https://berlinger-haus-shop.ru/goods/BH-6572-Primal-Gloss-Collection-Kastryulya-so-steklyannoj-kryshkoj-24-sm?mod_id=285547064',
            'BH-6576': 'https://berlinger-haus-shop.ru/goods/BH-6576-Primal-Gloss-Collection-Sotejnik?mod_id=285547067',
            'BH-6577': 'https://berlinger-haus-shop.ru/goods/Skovoroda-sotejnik-28sm-Berlinger-Haus-VN-6577-Prima-Gloss?mod_id=285547066',
            'BH-6579': 'https://berlinger-haus-shop.ru/goods/BH-6579-Primal-Gloss-Collection-Blinnica?mod_id=285547987',
            'BH-7144': 'https://berlinger-haus-shop.ru/goods/B?mod_id=302601231',
            'BH-9289': 'https://berlinger-haus-shop.ru/goods/BH-9289-Purple-Eclipse-Jelektricheskaya-percemolka-1?mod_id=272547380',
            'BH-2698': 'https://berlinger-haus-shop.ru/goods/%D0%A1%D0%BA%D0%BE%D0%B2%D0%BE%D1%80%D0%BE%D0%B4%D0%B0-%D0%92%D0%BE%D0%BA-28%D1%81%D0%BC-Berlinger-Haus-BH-1159-Grey-Stone-Touch-Line?mod_id=124974740',
            'LP-BH-047L': 'https://berlinger-haus-shop.ru/goods/BH-1965-Burgundy-Metallic-Line-Molochnik-1?mod_id=285546497'}
        for art in self.links_products:
            print(art)
            resp = requests.get(self.links_products[art])
            soup = BeautifulSoup(resp.text, features='lxml')
            article_on_page = soup.find('div', class_='goodsDataMainModificationArtNumber').find(
                        'span').text.strip()
            # если артикул на странице не совпадает с искомым
            if art[3:] not in article_on_page:
                continue
            else:
                some_links_imgs = soup.find('div', class_='thumblist-box').find_all('li')
                # при нескольких изображениях
                if len(some_links_imgs) > 1:
                    self.article_imgs.setdefault(art, [img.find('a')['href'] for img in some_links_imgs])
                elif len(some_links_imgs) == 1:
                    link_img_found = soup.find('div', class_='product-img-box col-md-5 col-sm-12 col-sms-12')
                    link_img = link_img_found.find_all('a')
                    self.article_imgs.setdefault(art, [link['href'] for link in link_img])

                # при одном изображении
                else:
                    link_img_found = soup.find('div', class_='general-img popup-gallery')
                    if link_img_found.find('a') == None:
                        continue
                    else:
                        link_img = link_img_found.find_all('a')
                        self.article_imgs.setdefault(art, [link['href'] for link in link_img])
        print(self.article_imgs)


    # async def get_link_product(self, session, article):
    #     # try:
    #
    #     retry_options = ExponentialRetry(attempts=5)
    #     retry_client = RetryClient(raise_for_status=False, retry_options=retry_options, client_session=session,
    #                                start_timeout=0.5)
    #     async with retry_client.get(
    #             url=f'{self.base_url}search?q={article}&spell=1&where=') as response:
    #         print(f'{self.base_url}search?q={article}&spell=1&where=')
    #         if response.ok:
    #
    #             # sys.stdout.write("\r")
    #             # sys.stdout.write(f'Получаю ссылку на товар {article}')
    #             # sys.stdout.flush()
    #
    #             resp = await response.text()
    #             soup = BeautifulSoup(resp, features='lxml')
    #             product_not_found = soup.find('div', class_='catalog_item main_item_wrapper item_wrap')
    #             print(product_not_found)
    #             # if bool(product_not_found) is False:
    #             #     # print(f'Получаю ссылку на товар {article}')
    #             #     print('True')
    #             #     link_found = soup.find_all('div', class_='item col-sm-4 col-sms-6 col-smb-12')
    #             #
    #             #     print(len(link_found), article)
    #             #     # links_imgs = soup.find('div', class_='thumblist-box')
    #             #     # some_links_imgs = links_imgs.find_all('a', class_='thumblisticon')
    #             #     # link_product = soup.find('div', class_='catalog-item__inner').find('a')
    #             #     # self.links_products[article] = link_product["href"]
    #             # else:
    #             #     print(f'{article} не найдено')
    #
    #     # except Exception as exc:
    #     #     print(f'Ошибка {exc} в получении ссылок на товары')
    #     #     with open('error.txt', 'a', encoding='utf-8') as file:
    #     #         file.write(f'{datetime.datetime.now().strftime("%d-%m-%y %H:%M")} '
    #     #                    f'Ошибка {exc} в получении ссылок на товары, функция - get_link_product()\n')
    #
    # async def get_link_product_run_async(self):
    #     connector = aiohttp.TCPConnector(force_close=True)
    #     async with aiohttp.ClientSession(headers=self.headers, connector=connector) as session:
    #         tasks = []
    #         i = 0
    #         for article in self.article_numbers:
    #             # i += 1
    #             # if i == 2:
    #             #
    #             #     break
    #             task = asyncio.create_task(self.get_link_product(session, article))
    #             tasks.append(task)
    #             if len(tasks) % 50 == 0:
    #                 await asyncio.gather(*tasks)
    #         await asyncio.gather(*tasks)

    # async def get_link_img(self, session, link):
    #     try:
    #
    #         retry_options = ExponentialRetry(attempts=5)
    #         retry_client = RetryClient(raise_for_status=False, retry_options=retry_options, client_session=session,
    #                                    start_timeout=0.5)
    #         async with retry_client.get(url=f'https://playtoday.ru{self.links_products[link].rstrip()}') as response:
    #             if response.ok:
    #
    #                 sys.stdout.write("\r")
    #                 sys.stdout.write(f'Получаю ссылку на изображение {link}')
    #                 sys.stdout.flush()
    #
    #                 resp = await response.text()
    #                 soup = BeautifulSoup(resp, features='lxml')
    #                 link_image = soup.find_all('picture', class_='product-gallery__full-img lazy')
    #                 if bool(link_image) is False:
    #                     self.article_imgs[link] = ''
    #                 else:
    #                     ff = [link.find('source')['srcset'] for link in link_image]
    #                     if len(ff) >= 3:
    #                         self.article_imgs[link] = [ff[0], ff[2]]
    #                     elif len(ff) == 2:
    #                         self.article_imgs[link] = [ff[0], ff[1]]
    #                     else:
    #                         self.article_imgs[link] = [ff[0]]
    #     except Exception as exc:
    #         print(f'Ошибка {exc} в получении ссылок на изображения товаров')
    #         with open('error.txt', 'a', encoding='utf-8') as file:
    #
    #             file.write(f'{datetime.datetime.now().strftime("%d-%m-%y %H:%M")} '
    #                        f'Ошибка {exc} в получении ссылок на изображения товаров, функция - get_link_img()\n')
    #
    # async def get_link_img_run_async(self):
    #     connector = aiohttp.TCPConnector(force_close=True)
    #     async with aiohttp.ClientSession(headers=self.headers, connector=connector) as session:
    #         tasks = []
    #         for link in self.links_products:
    #             task = asyncio.create_task(self.get_link_img(session, link))
    #             tasks.append(task)
    #             if len(tasks) % 50 == 0:
    #                 await asyncio.gather(*tasks)
    #         await asyncio.gather(*tasks)
    #     # print(self.article_imgs)
    #
    # async def save_images(self, session, urls, name_img):
    #     try:
    #         images = []
    #
    #         sys.stdout.write("\r")
    #         sys.stdout.write(f'Сохраняю изображение для {name_img}')
    #         sys.stdout.flush()
    #
    #         for a, url in enumerate(urls):
    #             date_now = datetime.datetime.now()
    #             async with aiofiles.open(f'./img/{name_img}_{date_now.strftime("%M%S%f")}_{a}.jpg', mode='wb') as f:
    #                 async with session.get(url) as response:
    #                     images.append(f'./img/{name_img}_{date_now.strftime("%M%S%f")}_{a}.jpg')
    #                     async for x in response.content.iter_chunked(1024):
    #                         await f.write(x)
    #
    #         self.article_imgs[name_img] = images
    #     except Exception as exc:
    #         print(f'Ошибка {exc} в сохранении изображений товаров')
    #         with open('error.txt', 'a', encoding='utf-8') as file:
    #
    #             file.write(f'{datetime.datetime.now().strftime("%d-%m-%y %H:%M")} '
    #                        f'Ошибка {exc} в сохранении изображений товаров, функция - save_images()\n')
    #
    # async def save_images_run_async(self):
    #     if not os.path.isdir('./img/'):
    #         os.mkdir('./img/')
    #     async with aiohttp.ClientSession() as session:
    #         tasks = []
    #         for link in self.article_imgs:
    #             task = asyncio.create_task(self.save_images(session, urls=self.article_imgs[link], name_img=link))
    #             tasks.append(task)
    #             await asyncio.gather(*tasks)
    #
    # def resize_img(self):
    #     try:
    #         ImageFile.LOAD_TRUNCATED_IMAGES = True
    #         fixed_height = 426
    #         for img_file in tqdm(os.listdir('./img/')):
    #             if img_file[-4:] == '.jpg':
    #                 img = Image.open(f'./img/{img_file}')
    #                 height_percent = (fixed_height / float(img.size[1]))
    #                 width_size = int((float(img.size[0]) * float(height_percent)))
    #                 new_image = img.resize((width_size, fixed_height))
    #                 new_image.save(f'./img/{img_file}')
    #     except Exception as exc:
    #         print(f'Ошибка {exc} в изменении разрешения изображений')
    #         with open('error.txt', 'a', encoding='utf-8') as file:
    #             file.write(f'{datetime.datetime.now().strftime("%d-%m-%y %H:%M")} '
    #                        f'Ошибка {exc} в изменении разрешения изображений, функция - resize_img()\n')
    #
    # def sending_to_fotohosting(self):
    #     self.active_token = self.token[0]
    #     self.active_secret_key = self.secret_key[0]
    #     headers = {
    #         'Authorization': f'TOKEN {self.active_token}',
    #     }
    #     for img_url in self.article_imgs:
    #
    #         img_short_link = []
    #
    #         sys.stdout.write("\r")
    #         sys.stdout.write(f'Загружаю изображение для - {img_url}')
    #         sys.stdout.flush()
    #
    #         img_links = self.article_imgs[img_url]
    #
    #         for img in img_links:
    #
    #             try:
    #                 files = {
    #                     'image': open(img, 'rb'),
    #                     'secret_key': (None, self.active_secret_key),
    #                 }
    #                 response = requests.post('https://api.imageban.ru/v1', headers=headers, files=files)
    #                 if response.json()['status'] == 200:
    #                     img_short_link.append(f"[URL=https://imageban.ru][IMG]{response.json()['data']['link']}"
    #                                           f"[/IMG][/URL]")
    #                 else:
    #                     print(f'Не удалось загрузить {img}')
    #                     continue
    #             except KeyError:
    #                 print(f'{img_url} ошибка загрузки изображения - {response.json()["error"]["message"]}\n')
    #                 with open('error.txt', 'a', encoding='utf-8') as file:
    #                     file.write(f'{datetime.datetime.now().strftime("%d-%m-%y %H:%M")} '
    #                                f'{img} ошибка загрузки изображения, функция - sending_to_fotohosting()\n')
    #                 if response.json()["error"]["message"] == 'File reception error':
    #                     continue
    #                 elif response.json()["error"]["message"] == \
    #                         'Exceeded the daily limit of uploaded images for your account':
    #                     print('Переключение на второй аккаунт')
    #
    #                     self.active_token = self.token[1]
    #                     self.active_secret_key = self.secret_key[1]
    #
    #                     files = {
    #                         'image': open(img, 'rb'),
    #                         'secret_key': (None, self.active_secret_key),
    #                     }
    #                     response = requests.post('https://api.imageban.ru/v1', headers=headers, files=files)
    #                     if response.json()['status'] == 200:
    #                         img_short_link.append(f"[URL=https://imageban.ru][IMG]{response.json()['data']['link']}"
    #                                               f"[/IMG][/URL]")
    #                     else:
    #                         print(f'Не удалось загрузить {img}')
    #                 continue
    #             except FileNotFoundError:
    #                 continue
    #             self.article_save_imgs[img_url] = img_short_link

    def write_final_file(self):
        self.article_save_imgs = {'BH-7081': [
            'https://i3.stat01.com/2/8491/184902464/afacdb/nabor-posudy-10pr-berlingerhaus-vn-1645n-black-rose.jpg',
            'https://i3.stat01.com/2/8491/184902466/afacdb/nabor-posudy-10pr-berlingerhaus-vn-1645n-black-rose.jpg',
            'https://i3.stat01.com/2/8491/184902467/afacdb/nabor-posudy-10pr-berlingerhaus-vn-1645n-black-rose.jpg',
            'https://i4.stat01.com/2/8491/184902468/afacdb/nabor-posudy-10pr-berlingerhaus-vn-1645n-black-rose.png',
            'https://i3.stat01.com/2/8491/184902469/afacdb/nabor-posudy-10pr-berlingerhaus-vn-1645n-black-rose.jpg'],
         'BH-7082': [
             'https://i3.stat01.com/2/8490/184895455/afacdb/skovoroda-20-sm-berlinger-haus-bh-6624-royal-purple-metallic-line.jpg',
             'https://i3.stat01.com/2/8490/184895456/afacdb/skovoroda-20-sm-berlinger-haus-bh-6624-royal-purple-metallic-line.jpg'],
         'BH-7083': [
             'https://i3.stat01.com/2/8490/184896031/afacdb/skovoroda-24sm-berlingerhaus-vn-1634n-black-rose.jpg',
             'https://i4.stat01.com/2/8490/184896032/afacdb/skovoroda-24sm-berlingerhaus-vn-1634n-black-rose.jpg'],
         'BH-7088': [
             'https://i2.stat01.com/2/8491/184901285/afacdb/vn-1931-black-rose-collection-kastryulya-so-steklyannoj-kryshkoj-28sm-6-1l.jpg',
             'https://i1.stat01.com/2/8491/184901287/afacdb/vn-1931-black-rose-collection-kastryulya-so-steklyannoj-kryshkoj-28sm-6-1l.jpg'],
         'BH-6625': [
             'https://i3.stat01.com/2/5417/154161236/afacdb/skovoroda-24-sm-berlinger-haus-bh-1857-royal-purple-metallic-line.jpg',
             'https://i4.stat01.com/2/5417/154161237/afacdb/skovoroda-24-sm-berlinger-haus-bh-1857-royal-purple-metallic-line.jpg'],
         'BH-6627': [
             'https://i3.stat01.com/2/5540/155391320/afacdb/kovsh-16-sm-berlinger-haus-bh-1874-aquamarine-metallic-line.png',
             'https://i4.stat01.com/2/5540/155391321/afacdb/kovsh-16-sm-berlinger-haus-bh-1874-aquamarine-metallic-line.png'],
         'BH-6628': [
             'https://i5.stat01.com/2/5094/150931582/afacdb/kastryulya-s-kryshkoj-20sm-berlinger-haus-vn-6628-purple-eclips-collection.jpg',
             'https://i4.stat01.com/2/5094/150931583/afacdb/kastryulya-s-kryshkoj-20sm-berlinger-haus-vn-6628-purple-eclips-collection.jpg'],
         'BH-6630': [
             'https://i5.stat01.com/2/5094/150931582/afacdb/kastryulya-s-kryshkoj-20sm-berlinger-haus-vn-6628-purple-eclips-collection.jpg',
             'https://i4.stat01.com/2/5094/150931583/afacdb/kastryulya-s-kryshkoj-20sm-berlinger-haus-vn-6628-purple-eclips-collection.jpg'],
         'BH-6632': [
             'https://i1.stat01.com/2/4930/149297960/afacdb/sotejnik-s-kryshkoj-24sm-berlinger-haus-vn-6631-royal-purple-metallic-line.png',
             'https://i2.stat01.com/2/4930/149297961/afacdb/sotejnik-s-kryshkoj-24sm-berlinger-haus-vn-6631-royal-purple-metallic-line.png'],
         'BH-7026': [
             'https://i1.stat01.com/2/8490/184891863/afacdb/flip-skovoroda-26sm-berlinger-haus-vn-7026-purple-eclips-collection.jpg',
             'https://i4.stat01.com/2/8490/184891865/afacdb/flip-skovoroda-26sm-berlinger-haus-vn-7026-purple-eclips-collection.jpg'],
         'BH-7102': [
             'https://i1.stat01.com/2/8490/184893593/afacdb/nabor-posudy-5-pr-berlinger-haus-vn-6790-black-rose.jpg',
             'https://i3.stat01.com/2/8490/184893594/afacdb/nabor-posudy-5-pr-berlinger-haus-vn-6790-black-rose.jpg',
             'https://i4.stat01.com/2/8490/184893595/afacdb/nabor-posudy-5-pr-berlinger-haus-vn-6790-black-rose.jpg',
             'https://i3.stat01.com/2/8490/184893596/afacdb/nabor-posudy-5-pr-berlinger-haus-vn-6790-black-rose.jpg',
             'https://i3.stat01.com/2/8490/184893597/afacdb/nabor-posudy-5-pr-berlinger-haus-vn-6790-black-rose.jpg',
             'https://i1.stat01.com/2/8490/184893598/afacdb/nabor-posudy-5-pr-berlinger-haus-vn-6790-black-rose.jpg',
             'https://i3.stat01.com/2/8490/184893599/afacdb/nabor-posudy-5-pr-berlinger-haus-vn-6790-black-rose.jpg'],
         'BH-7103': ['https://i3.stat01.com/2/8489/184888885/afacdb/bh-6177-aquamarine-edition-nabor-posudy-3-pr.jpg',
                     'https://i4.stat01.com/2/8489/184888883/afacdb/bh-6177-aquamarine-edition-nabor-posudy-3-pr.jpg',
                     'https://i4.stat01.com/2/8489/184888886/afacdb/bh-6177-aquamarine-edition-nabor-posudy-3-pr.jpg',
                     'https://i4.stat01.com/2/8489/184888887/afacdb/bh-6177-aquamarine-edition-nabor-posudy-3-pr.jpg',
                     'https://i3.stat01.com/2/8489/184888888/afacdb/bh-6177-aquamarine-edition-nabor-posudy-3-pr.jpg'],
         'BH-7104': ['https://i4.stat01.com/2/8726/187253719/afacdb/bh-7104-purple-eclips-nabor-posudy-3-pr.jpg',
                     'https://i1.stat01.com/2/8726/187253718/afacdb/bh-7104-purple-eclips-nabor-posudy-3-pr.jpg'],
         'BH-7105': [
             'https://i1.stat01.com/2/8490/184893617/afacdb/gril-skovoroda-s-kryshkoj-28sm-berlingerhaus-bh-1613n-burgundy-metallic-line.jpg',
             'https://i3.stat01.com/2/8514/185139235/afacdb/bh-7105-purple-eclips-gril-skovoroda-s-kryshkoj-28sm.jpg',
             'https://i2.stat01.com/2/8514/185139239/afacdb/bh-7105-purple-eclips-gril-skovoroda-s-kryshkoj-28sm.jpg'],
         'BH-7138': [
             'https://i4.stat01.com/2/8489/184889583/afacdb/kovsh-16sm-berlingerhaus-bh-1525n-burgundy-metallic-line.jpg',
             'https://i1.stat01.com/2/8489/184889584/afacdb/kovsh-16sm-berlingerhaus-bh-1525n-burgundy-metallic-line.jpg',
             'https://i3.stat01.com/2/8489/184889585/afacdb/kovsh-16sm-berlingerhaus-bh-1525n-burgundy-metallic-line.jpg',
             'https://i3.stat01.com/2/8489/184889586/afacdb/kovsh-16sm-berlingerhaus-bh-1525n-burgundy-metallic-line.png'],
         'BH-7145': ['https://i1.stat01.com/2/8489/184889234/afacdb/bh-7145-purple-eclips-nabor-posudy-18pr.jpg',
                     'https://i3.stat01.com/2/8489/184889235/afacdb/bh-7145-purple-eclips-nabor-posudy-18pr.jpg',
                     'https://i2.stat01.com/2/8489/184883712/afacdb/bh-7036-aquamarine-metallic-line-nabor-posudy-18pr.jpg',
                     'https://i1.stat01.com/2/8489/184883713/afacdb/bh-7036-aquamarine-metallic-line-nabor-posudy-18pr.png',
                     'https://i4.stat01.com/2/8489/184883784/afacdb/bh-7036-aquamarine-metallic-line-nabor-posudy-18pr.jpg',
                     'https://i3.stat01.com/2/8489/184883783/afacdb/bh-7036-aquamarine-metallic-line-nabor-posudy-18pr.jpg',
                     'https://i4.stat01.com/2/8489/184883782/afacdb/bh-7036-aquamarine-metallic-line-nabor-posudy-18pr.jpg',
                     'https://i4.stat01.com/2/8489/184883781/afacdb/bh-7036-aquamarine-metallic-line-nabor-posudy-18pr.jpg',
                     'https://i1.stat01.com/2/8489/184883780/afacdb/bh-7036-aquamarine-metallic-line-nabor-posudy-18pr.png',
                     'https://i1.stat01.com/2/8489/184883710/afacdb/bh-7036-aquamarine-metallic-line-nabor-posudy-18pr.jpg'],
         'BH-6143': [
             'https://i3.stat01.com/2/2852/128519417/afacdb/nabor-posudy-10-pr-berlingerhaus-vn-1884-aquamarine-metallic-line.jpg',
             'https://i5.stat01.com/2/2852/128519420/afacdb/nabor-posudy-10-pr-berlingerhaus-vn-1884-aquamarine-metallic-line.jpg',
             'https://i4.stat01.com/2/2852/128519480/afacdb/bh-6143-aquamarine-edition-nabor-posudy-10-pr-berlingerhaus.jpg',
             'https://i4.stat01.com/2/6157/161560350/afacdb/bh-6143-aquamarine-edition-nabor-posudy-10-pr-berlingerhaus.jpg',
             'https://i2.stat01.com/2/6157/161560351/afacdb/bh-6143-aquamarine-edition-nabor-posudy-10-pr-berlingerhaus.jpg'],
         'BH-6152': ['https://i4.stat01.com/2/3445/134446812/afacdb/bh-6151-rosegold-line-nabor-posudy-10-pr.jpg',
                     'https://i4.stat01.com/2/3445/134446811/afacdb/bh-6151-rosegold-line-nabor-posudy-10-pr.jpg',
                     'https://i5.stat01.com/2/3445/134446988/afacdb/bh-6151-rosegold-line-nabor-posudy-10-pr.png',
                     'https://i4.stat01.com/2/6157/161560355/afacdb/bh-6152-aquamarine-edition-nabor-posudy-10-pr.jpg'],
         'BH-6165': [
             'https://i5.stat01.com/2/200/101997723/afacdb/skovoroda-s-kryshkoj-28-sm-berlinger-haus-bh-1877-aquamarine-metallic-line.jpg',
             'https://i5.stat01.com/2/200/101997723/afacdb/skovoroda-s-kryshkoj-28-sm-berlinger-haus-bh-1877-aquamarine-metallic-line.jpg'],
         'BH-1626N': [
             'https://i4.stat01.com/2/5894/158931737/afacdb/sotejnik-s-kryshkoj-28sm-berlingerhaus-vn-1626n-black-burgundy-metallic-line.jpg',
             'https://i4.stat01.com/2/5894/158931738/afacdb/sotejnik-s-kryshkoj-28sm-berlingerhaus-vn-1626n-black-burgundy-metallic-line.jpg'],
         'BH-1251': [
             'https://i4.stat01.com/2/2022/120215439/afacdb/skovoroda-20sm-berlinger-haus-vn-1251-burgundy-metallic-line.jpg',
             'https://i4.stat01.com/2/2022/120215440/afacdb/skovoroda-20sm-berlinger-haus-vn-1251-burgundy-metallic-line.jpg'],
         'BH-1253': [
             'https://i4.stat01.com/2/2022/120215443/afacdb/skovoroda-28sm-berlinger-haus-vn-1253-burgundy-metallic-line.jpg',
             'https://i4.stat01.com/2/2022/120215444/afacdb/skovoroda-28sm-berlinger-haus-vn-1253-burgundy-metallic-line.jpg'],
         'BH-1254': [
             'https://i4.stat01.com/1/7279/72789955/afacdb/skovoroda-30sm-berlinger-haus-vn-1254-carbon-metallic-line.jpg',
             'https://i4.stat01.com/1/7279/72789954/afacdb/skovoroda-30sm-berlinger-haus-vn-1254-carbon-metallic-line.jpg'],
         'BH-1255': [
             'https://i3.stat01.com/1/7279/72784541/afacdb/kovsh-1-3l-16sm-berlinger-haus-vn-1255-carbon-metallic-line.jpg',
             'https://i4.stat01.com/1/7279/72784540/afacdb/kovsh-1-3l-16sm-berlinger-haus-vn-1255-carbon-metallic-line.jpg'],
         'BH-1257': ['https://i5.stat01.com/2/2147/121465965/afacdb/screenshot6-png.png',
                     'https://i4.stat01.com/2/2147/121465966/afacdb/screenshot7-png.png'], 'BH-1258': [
            'https://i4.stat01.com/2/2492/124915393/afacdb/kastryulya-28sm-berlinger-haus-vn-1258-burgundy-metallic-line.jpg',
            'https://i5.stat01.com/2/2492/124915394/afacdb/kastryulya-28sm-berlinger-haus-vn-1258-burgundy-metallic-line.jpg'],
         'BH-1260': [
             'https://i4.stat01.com/2/2022/120215457/afacdb/skovoroda-s-kryshkoj-28sm-berlinger-haus-vn-1260-burgundy-metallic-line.jpg',
             'https://i4.stat01.com/2/2022/120215458/afacdb/skovoroda-s-kryshkoj-28sm-berlinger-haus-vn-1260-burgundy-metallic-line.jpg'],
         'BH-1261': [
             'https://i5.stat01.com/2/2022/120215459/afacdb/skovoroda-s-kryshkoj-32sm-berlinger-haus-vn-1261-burgundy-metallic-line.jpg',
             'https://i5.stat01.com/2/2022/120215460/afacdb/skovoroda-s-kryshkoj-32sm-berlinger-haus-vn-1261-burgundy-metallic-line.jpg'],
         'BH-1264': [
             'https://i4.stat01.com/1/7280/72791304/afacdb/sotejnik-s-kryshkoj-32sm-berlinger-haus-vn-1264-carbon-metallic-line.jpg',
             'https://i3.stat01.com/1/7280/72791303/afacdb/sotejnik-s-kryshkoj-32sm-berlinger-haus-vn-1264-carbon-metallic-line.jpg'],
         'BH-1267': [
             'https://i4.stat01.com/1/7279/72789963/afacdb/skovoroda-vok-28sm-berlinger-haus-vn-1267-burgundy-metallic-line.jpg',
             'https://i3.stat01.com/1/7279/72789962/afacdb/skovoroda-vok-28sm-berlinger-haus-vn-1267-burgundy-metallic-line.jpg'],
         'BH-1613N': [
             'https://i5.stat01.com/2/2061/120601387/afacdb/gril-skovoroda-s-kryshkoj-28sm-berlingerhaus-bh-1613n-burgundy-metallic-line.jpg',
             'https://i2.stat01.com/2/2061/120601388/afacdb/gril-skovoroda-s-kryshkoj-28sm-berlingerhaus-bh-1613n-burgundy-metallic-line.jpg'],
         'BH-1674': [
             'https://i2.stat01.com/2/2492/124915802/afacdb/nabor-posudy-12-pr-berlinger-haus-metallic-line-burgundy-edition-vn-1674.png',
             'https://i4.stat01.com/2/2492/124915803/afacdb/nabor-posudy-12-pr-berlinger-haus-metallic-line-burgundy-edition-vn-1674.png'],
         'BH-6166': [
             'https://i2.stat01.com/2/2492/124916093/afacdb/skovoroda-vok-28sm-berlinger-haus-s-burgundy-metallic-line.jpg',
             'https://i4.stat01.com/2/2492/124916094/afacdb/skovoroda-vok-28sm-berlinger-haus-s-burgundy-metallic-line.jpg'],
         'BH-7035': [
             'https://i4.stat01.com/2/5595/155947600/afacdb/bh-7035-burgundy-metallic-line-nabor-posudy-18pr.jpg',
             'https://i3.stat01.com/2/5595/155947602/afacdb/bh-7035-burgundy-metallic-line-nabor-posudy-18pr.jpg',
             'https://i5.stat01.com/2/5595/155947603/afacdb/bh-7035-burgundy-metallic-line-nabor-posudy-18pr.jpg',
             'https://i3.stat01.com/2/5595/155947605/afacdb/bh-7035-burgundy-metallic-line-nabor-posudy-18pr.jpg',
             'https://i3.stat01.com/2/5595/155947606/afacdb/bh-7035-burgundy-metallic-line-nabor-posudy-18pr.jpg',
             'https://i3.stat01.com/2/5595/155947700/afacdb/bh-7035-burgundy-metallic-line-nabor-posudy-18pr.jpg',
             'https://i5.stat01.com/2/5595/155947701/afacdb/bh-7035-burgundy-metallic-line-nabor-posudy-18pr.jpg',
             'https://i2.stat01.com/2/5595/155947702/afacdb/bh-7035-burgundy-metallic-line-nabor-posudy-18pr.jpg'],
         'BH-7110': [
             'https://i4.stat01.com/2/8672/186713899/afacdb/skovoroda-vok-s-kryshkoj-30sm-berlinger-haus-vn-1266-burgundy-metallic-line.jpg'],
         'BH-6918': ['https://i4.stat01.com/2/6041/160403376/afacdb/kontejner-d-syp-prod-wr-6918-1-41l.png'],
         'BH-6051': [
             'https://i3.stat01.com/2/4780/147796855/afacdb/bh-6051-emerald-collection-metallic-line-gril-skovoroda-so-steklyannoj-kryshkoj-28sm.jpg',
             'https://i3.stat01.com/2/4780/147796856/afacdb/bh-6051-emerald-collection-metallic-line-gril-skovoroda-so-steklyannoj-kryshkoj-28sm.jpg',
             'https://i3.stat01.com/2/4780/147796857/afacdb/bh-6051-emerald-collection-metallic-line-gril-skovoroda-so-steklyannoj-kryshkoj-28sm.jpg'],
         'BH-6087': [
             'https://i4.stat01.com/2/6439/164385295/afacdb/bh-6087-skovoroda-24sm-berlinger-haus-emerald-collection.jpg',
             'https://i4.stat01.com/2/6439/164385296/afacdb/bh-6087-skovoroda-24sm-berlinger-haus-emerald-collection.jpg'],
         'BH-6024': [
             'https://i5.stat01.com/2/2202/122010750/afacdb/skovoroda-berlinger-haus-irose-s-antiprigarnym-pokrytiem-diametr-28-sm-6025-bh.png',
             'https://i2.stat01.com/2/2202/122010751/afacdb/skovoroda-berlinger-haus-irose-s-antiprigarnym-pokrytiem-diametr-28-sm-6025-bh.png'],
         'BH-6104': ['https://i4.stat01.com/2/2231/122300396/afacdb/screenshot7-png.png',
                     'https://i3.stat01.com/2/2231/122300398/afacdb/screenshot6-png.png'], 'BH-6012': [
            'https://i5.stat01.com/2/2492/124915392/afacdb/kastryulya-28sm-berlinger-haus-moonlight-edition-6013-vn.png',
            'https://i5.stat01.com/2/5519/155188494/afacdb/kastryulya-24-sm-berlinger-haus-moonlight-edition-6012-vn.png',
            'https://i4.stat01.com/2/5519/155188495/afacdb/kastryulya-24-sm-berlinger-haus-moonlight-edition-6012-vn.jpg',
            'https://i2.stat01.com/2/5519/155188499/afacdb/kastryulya-24-sm-berlinger-haus-moonlight-edition-6012-vn.jpg',
            'https://i4.stat01.com/2/5519/155188500/afacdb/kastryulya-24-sm-berlinger-haus-moonlight-edition-6012-vn.png',
            'https://i4.stat01.com/2/5519/155188549/afacdb/kastryulya-24-sm-berlinger-haus-moonlight-edition-6012-vn.jpg'],
         'BH-6169': ['https://i4.stat01.com/2/5519/155188407/afacdb/vn-6169-moonlight-edition-nabor-posudy-3-pr.jpg',
                     'https://i4.stat01.com/2/6543/165427579/afacdb/vn-6169-moonlight-edition-nabor-posudy-3-pr.jpg',
                     'https://i2.stat01.com/2/6543/165427578/afacdb/vn-6169-moonlight-edition-nabor-posudy-3-pr.jpg',
                     'https://i3.stat01.com/2/6543/165427576/afacdb/vn-6169-moonlight-edition-nabor-posudy-3-pr.jpg',
                     'https://i1.stat01.com/2/6543/165427577/afacdb/vn-6169-moonlight-edition-nabor-posudy-3-pr.jpg',
                     'https://i3.stat01.com/2/5519/155188429/afacdb/vn-6169-moonlight-edition-nabor-posudy-3-pr.png'],
         'BH-1518N': [
             'https://i4.stat01.com/2/5602/156011145/afacdb/skovoroda-s-kryshkoj-28-sm-berlinger-haus-bh-1518n-rosegold-line.jpg',
             'https://i1.stat01.com/2/5602/156011144/afacdb/skovoroda-s-kryshkoj-28-sm-berlinger-haus-bh-1518n-rosegold-line.jpg',
             'https://i5.stat01.com/2/5602/156011146/afacdb/skovoroda-s-kryshkoj-28-sm-berlinger-haus-bh-1518n-rosegold-line.jpg'],
         'BH-6142': [
             'https://i2.stat01.com/2/5601/156004778/afacdb/bh-6142-rosegold-line-nabor-posudy-10-pr-berlingerhaus.jpg',
             'https://i4.stat01.com/2/5601/156004780/afacdb/bh-6142-rosegold-line-nabor-posudy-10-pr-berlingerhaus.jpg',
             'https://i1.stat01.com/2/3887/138862631/afacdb/bh-6142-rosegold-line-nabor-posudy-10-pr-berlingerhaus.jpg',
             'https://i2.stat01.com/2/5601/156004781/afacdb/bh-6142-rosegold-line-nabor-posudy-10-pr-berlingerhaus.jpg'],
         'BH-1900': [
             'https://i4.stat01.com/2/2784/127834120/afacdb/kombajn-testomes-royalty-line-1900v-rl-pkm1900-7-0.jpg',
             'https://i1.stat01.com/2/2784/127834121/afacdb/kombajn-testomes-royalty-line-1900v-rl-pkm1900-7-0.jpg',
             'https://i3.stat01.com/2/2784/127834122/afacdb/kombajn-testomes-royalty-line-1900v-rl-pkm1900-7-0.jpg'],
         'BH-6605': [
             'https://i4.stat01.com/2/6440/164390026/afacdb/bh-6605-shiny-black-edition-kastryulya-so-steklyannoj-kryshkoj-24sm.jpg',
             'https://i4.stat01.com/2/6440/164390027/afacdb/bh-6605-shiny-black-edition-kastryulya-so-steklyannoj-kryshkoj-24sm.jpg',
             'https://i4.stat01.com/2/6440/164390028/afacdb/bh-6605-shiny-black-edition-kastryulya-so-steklyannoj-kryshkoj-24sm.jpg',
             'https://i4.stat01.com/2/6440/164390029/afacdb/bh-6605-shiny-black-edition-kastryulya-so-steklyannoj-kryshkoj-24sm.jpg'],
         'BH-6616': ['https://i2.stat01.com/2/5527/155261475/afacdb/bh-6616-shiny-black-edition-nabor-posudy-5pr.jpg',
                     'https://i4.stat01.com/2/5527/155261476/afacdb/bh-6616-shiny-black-edition-nabor-posudy-5pr.jpg'],
         'BH-1202': [
             'https://i3.stat01.com/2/2492/124916135/afacdb/sotejnik-s-kryshkoj-32sm-berlinger-haus-bh-1202-forest-line.jpg',
             'https://i3.stat01.com/2/2492/124916136/afacdb/sotejnik-s-kryshkoj-32sm-berlinger-haus-bh-1202-forest-line.jpg'],
         'BH-1204': [
             'https://i4.stat01.com/2/2022/120214993/afacdb/skovoroda-vok-28sm-berlinger-haus-bh-1204-forest-line.jpg',
             'https://i4.stat01.com/2/2022/120214994/afacdb/skovoroda-vok-28sm-berlinger-haus-bh-1204-forest-line.jpg'],
         'BH-1210': [
             'https://i5.stat01.com/2/2747/127461021/afacdb/sotejnik-s-kryshkoj-24sm-berlinger-haus-bh-1210-forest-line.jpg'],
         'BH-1095': [
             'https://i2.stat01.com/1/7110/71090720/afacdb/kastryulya-s-kryshkoj-4-2l-24sm-berlinger-haus-bh-1095-granit-diamond-line.jpg',
             'https://i2.stat01.com/1/7110/71090721/afacdb/kastryulya-s-kryshkoj-4-2l-24sm-berlinger-haus-bh-1095-granit-diamond-line.jpg'],
         'BH-1096': [
             'https://i5.stat01.com/2/2492/124915467/afacdb/kastryulya-s-kryshkoj-5-8l-28sm-berlinger-haus-granit-diamond-line-bh-1096.jpg',
             'https://i5.stat01.com/2/2492/124915468/afacdb/kastryulya-s-kryshkoj-5-8l-28sm-berlinger-haus-granit-diamond-line-bh-1096.jpg'],
         'BH-1107': [
             'https://i2.stat01.com/1/7110/71091063/afacdb/skovoroda-so-sjemnoj-ruchkoj-24sm-berlinger-haus-bh-1107-granit-diamond-line.jpg',
             'https://i1.stat01.com/1/7110/71091062/afacdb/skovoroda-so-sjemnoj-ruchkoj-24sm-berlinger-haus-bh-1107-granit-diamond-line.jpg'],
         'BH-1446': ['https://i1.stat01.com/2/8726/187253331/afacdb/bh-1989-moonlight-edition-tazhin.jpg',
                     'https://i1.stat01.com/2/8726/187253332/afacdb/bh-1989-moonlight-edition-tazhin.jpg',
                     'https://i2.stat01.com/2/8726/187253333/afacdb/bh-1989-moonlight-edition-tazhin.jpg',
                     'https://i1.stat01.com/2/8726/187253334/afacdb/bh-1989-moonlight-edition-tazhin.jpg'],
         'BH-1634N': [
             'https://i2.stat01.com/2/5543/155427355/afacdb/skovoroda-24sm-berlingerhaus-vn-1634n-black-rose.jpg',
             'https://i4.stat01.com/2/2783/127820630/afacdb/skovoroda-24sm-berlingerhaus-vn-1634n-black-rose.jpg'],
         'BH-1645N': [
             'https://i4.stat01.com/2/2022/120215580/afacdb/nabor-posudy-10pr-berlingerhaus-vn-1645n-black-rose.jpg',
             'https://i4.stat01.com/2/5936/159350276/afacdb/nabor-posudy-10pr-berlingerhaus-vn-1645n-black-rose.jpg'],
         'BH-6149': [
             'https://i4.stat01.com/2/3587/135861815/afacdb/bh-6149-black-rose-nabor-posudy-10-pr-berlingerhaus.jpg',
             'https://i4.stat01.com/2/3587/135861816/afacdb/bh-6149-black-rose-nabor-posudy-10-pr-berlingerhaus.jpg'],
         'BH-6154': ['https://i4.stat01.com/2/3587/135861788/afacdb/bh-6154-black-rose-nabor-posudy-10-pr.jpg',
                     'https://i4.stat01.com/2/3587/135861789/afacdb/bh-6154-black-rose-nabor-posudy-10-pr.jpg'],
         'BH-6766': [
             'https://i5.stat01.com/2/5094/150936407/afacdb/sotejnik-s-kryshkoj-28sm-berlinger-haus-vn-1263-burgundy-metallic-line.jpg',
             'https://i5.stat01.com/2/5094/150936407/afacdb/sotejnik-s-kryshkoj-28sm-berlinger-haus-vn-1263-burgundy-metallic-line.jpg'],
         'BH-7423': [
             'https://i1.stat01.com/2/5471/154708304/afacdb/bh-7422-eternal-collection-sotejnik-so-steklyannoj-kryshkoj-24sm.jpg'],
         'BH-6074': ['https://i3.stat01.com/2/8726/187254224/afacdb/bh-7102-purple-eclips-nabor-posudy-4-pr.jpg',
                     'https://i1.stat01.com/2/8726/187253970/afacdb/bh-7102-purple-eclips-nabor-posudy-4-pr.jpg',
                     'https://i2.stat01.com/2/8726/187253971/afacdb/bh-7102-purple-eclips-nabor-posudy-4-pr.jpg',
                     'https://i1.stat01.com/2/8726/187253972/afacdb/bh-7102-purple-eclips-nabor-posudy-4-pr.jpg'],
         'BH-6567': [
             'https://i3.stat01.com/2/5527/155261337/afacdb/bh-6567-primal-gloss-collection-skovoroda-20sm.png'],
         'BH-6569': [
             'https://i2.stat01.com/2/4930/149297180/afacdb/skovoroda-28sm-berlinger-haus-vn-6569-prima-gloss.jpg',
             'https://i1.stat01.com/2/4930/149297181/afacdb/skovoroda-28sm-berlinger-haus-vn-6569-prima-gloss.jpg'],
         'BH-6571': [
             'https://i3.stat01.com/2/5527/155261339/afacdb/bh-6571-primal-gloss-collection-kastryulya-so-steklyannoj-20sm.jpg'],
         'BH-6572': [
             'https://i3.stat01.com/2/5527/155261340/afacdb/bh-6572-primal-gloss-collection-kastryulya-so-steklyannoj-kryshkoj-24-sm.jpg'],
         'BH-6576': ['https://i2.stat01.com/2/5527/155261379/afacdb/bh-6576-primal-gloss-collection-sotejnik-24sm.jpg',
                     'https://i2.stat01.com/2/5527/155261376/afacdb/bh-6576-primal-gloss-collection-sotejnik-24sm.jpg',
                     'https://i2.stat01.com/2/5527/155261375/afacdb/bh-6576-primal-gloss-collection-sotejnik-24sm.jpg',
                     'https://i2.stat01.com/2/5527/155261378/afacdb/bh-6576-primal-gloss-collection-sotejnik-24sm.png'],
         'BH-6577': [
             'https://i2.stat01.com/2/4930/149297485/afacdb/skovoroda-28sm-berlinger-haus-vn-6569-prima-gloss.jpg',
             'https://i1.stat01.com/2/4930/149297486/afacdb/skovoroda-28sm-berlinger-haus-vn-6569-prima-gloss.jpg'],
         'BH-6579': [
             'https://i4.stat01.com/2/6531/165304306/afacdb/skovoroda-blinnaya-25-sm-berlinger-haus-bh-1523n-rosegold-line.jpg',
             'https://i4.stat01.com/2/6531/165304305/afacdb/skovoroda-blinnaya-25-sm-berlinger-haus-bh-1523n-rosegold-line.jpg'],
         'BH-7144': [
             'https://i2.stat01.com/2/8726/187253839/afacdb/bh-7031-aquamarine-metallic-line-nabor-posudy-13-pr.jpg',
             'https://i3.stat01.com/2/8726/187253840/afacdb/bh-7031-aquamarine-metallic-line-nabor-posudy-13-pr.jpg',
             'https://i3.stat01.com/2/8726/187253854/afacdb/bh-7031-aquamarine-metallic-line-nabor-posudy-13-pr.jpg'],
         'BH-9289': [
             'https://i2.stat01.com/2/5393/153929780/afacdb/bh-7217-burgundy-metallic-line-jelektricheskaya-percemolka-1-1.jpg',
             'https://i2.stat01.com/2/5393/153929781/afacdb/bh-7217-burgundy-metallic-line-jelektricheskaya-percemolka-1-1.jpg']}
        # try:
        columns = ['N', 'O', 'P']
        wb = load_workbook(filename=self.read_data_file)
        ws = wb.active

        ws['N8'] = 'Ссылки на фотографии'
        date_now = datetime.datetime.now()
        # for article in self.article_save_imgs:
        for article in self.article_save_imgs:
            # if article == flag:
            #     break
            for i, link in enumerate(self.article_save_imgs[article]):

                for row in ws.iter_cols(min_col=2, max_col=2, min_row=9):
                    for cell in row:
                        # if cell.value == flag:
                        #     break
                        if cell.value.strip().split(' ')[0][3:] in article:
                            # if i == len(self.article_save_imgs[article]) - 1:
                            #     flag = cell.value
                            ws[f'{columns[i]}{cell.row}'] = link

        file_name = f'data_final_{date_now.strftime("%d-%m-%y_%H-%M")}.xlsx'
        wb.save(filename=file_name)
        # shutil.rmtree('./img/')
        print(f'Файл {file_name} сохранён')
        # except Exception as exc:
        #     print(f'Ошибка {exc} в записи итогового файла')
        #     with open('error.txt', 'a', encoding='utf-8') as file:
        #         file.write(f'{datetime.datetime.now().strftime("%d-%m-%y %H:%M")} '
        #                    f'Ошибка {exc} в записи итогового файла, функция - write_final_file()\n')

    def run(self):
        # try:
        # asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        print('Начало работы')
        self.open_token_file()
        self.read_file()
        print('Получаю артикул товаров')
        self.get_article_number()
        print('\rАртикулы получил')
        print('---------------------------\n')
        print('Получаю ссылки на товары')
        # self.get_link_prodicts()
        # asyncio.run(self.get_link_product_run_async())
        print('\nСсылки получены')
        print('---------------------------\n')
        print('Ищу изображения товаров')
        # self.get_link_img()
        # asyncio.run(self.get_link_img_run_async())
        # print('\nИзображения получены')
        # print('---------------------------\n')
        # print('Скачиваю изображения')
        # asyncio.run(self.save_images_run_async())
        # print('\nСкачивание завершено')
        # print('---------------------------\n')
        # print('Измененяю размер изображений')
        # self.resize_img()
        # print('\rРазмеры изменены')
        # print('---------------------------\n')
        # print('Загружаю изображения на фотохостинг')
        # self.sending_to_fotohosting()
        # print('\nЗагрузка завершена')
        # print('---------------------------\n')
        # print('Записываю в итоговый файл')
        self.write_final_file()
        print('Работа завершена')
        print('Для выхода нажмите Enter')
        input()
        print('---------------------------\n')
        # except Exception as exc:
        #     print(f'Произошла ошибка {exc}')
        #     print('Для выхода нажмите Enter')
        #     input()
        #     print('---------------------------\n')


def main():
    p = Parser()
    p.run()


if __name__ == '__main__':
    main()
