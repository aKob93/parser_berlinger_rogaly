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
        self.base_url = 'https://berlingerhaus.ru/'
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
                    #есть ли числа в строке
                    if re.search('\d+', cell.value.strip().split(' ')[0]):
                        self.article_numbers.append(cell.value.strip().split(' ')[0])

            self.article_numbers = list(dict.fromkeys(self.article_numbers))
        except Exception as exc:
            print(f'Ошибка {exc} в чтении табличного документа data.xlsx')
            with open('error.txt', 'a', encoding='utf-8') as file:

                file.write(f'{datetime.datetime.now().strftime("%d-%m-%y %H:%M")} '
                           f'Ошибка {exc} в чтении табличного документа data.xlsm, функция - get_article_number()\n')
            raise IndexError

    async def get_link_product(self, session, article):
        # try:

        retry_options = ExponentialRetry(attempts=5)
        retry_client = RetryClient(raise_for_status=False, retry_options=retry_options, client_session=session,
                                   start_timeout=0.5)
        async with retry_client.get(
                url=f'{self.base_url}search?q={article}&spell=1&where=') as response:
            print(f'{self.base_url}search?q={article}&spell=1&where=')
            if response.ok:

                # sys.stdout.write("\r")
                # sys.stdout.write(f'Получаю ссылку на товар {article}')
                # sys.stdout.flush()

                resp = await response.text()
                soup = BeautifulSoup(resp, features='lxml')
                product_not_found = soup.find('div', class_='catalog_item main_item_wrapper item_wrap')
                print(product_not_found)
                # if bool(product_not_found) is False:
                #     # print(f'Получаю ссылку на товар {article}')
                #     print('True')
                #     link_found = soup.find_all('div', class_='item col-sm-4 col-sms-6 col-smb-12')
                #
                #     print(len(link_found), article)
                #     # links_imgs = soup.find('div', class_='thumblist-box')
                #     # some_links_imgs = links_imgs.find_all('a', class_='thumblisticon')
                #     # link_product = soup.find('div', class_='catalog-item__inner').find('a')
                #     # self.links_products[article] = link_product["href"]
                # else:
                #     print(f'{article} не найдено')

        # except Exception as exc:
        #     print(f'Ошибка {exc} в получении ссылок на товары')
        #     with open('error.txt', 'a', encoding='utf-8') as file:
        #         file.write(f'{datetime.datetime.now().strftime("%d-%m-%y %H:%M")} '
        #                    f'Ошибка {exc} в получении ссылок на товары, функция - get_link_product()\n')

    async def get_link_product_run_async(self):
        connector = aiohttp.TCPConnector(force_close=True)
        async with aiohttp.ClientSession(headers=self.headers, connector=connector) as session:
            tasks = []
            i = 0
            for article in self.article_numbers:
                # i += 1
                # if i == 2:
                #
                #     break
                task = asyncio.create_task(self.get_link_product(session, article))
                tasks.append(task)
                if len(tasks) % 50 == 0:
                    await asyncio.gather(*tasks)
            await asyncio.gather(*tasks)

    async def get_link_img(self, session, link):
        try:

            retry_options = ExponentialRetry(attempts=5)
            retry_client = RetryClient(raise_for_status=False, retry_options=retry_options, client_session=session,
                                       start_timeout=0.5)
            async with retry_client.get(url=f'https://playtoday.ru{self.links_products[link].rstrip()}') as response:
                if response.ok:

                    sys.stdout.write("\r")
                    sys.stdout.write(f'Получаю ссылку на изображение {link}')
                    sys.stdout.flush()

                    resp = await response.text()
                    soup = BeautifulSoup(resp, features='lxml')
                    link_image = soup.find_all('picture', class_='product-gallery__full-img lazy')
                    if bool(link_image) is False:
                        self.article_imgs[link] = ''
                    else:
                        ff = [link.find('source')['srcset'] for link in link_image]
                        if len(ff) >= 3:
                            self.article_imgs[link] = [ff[0], ff[2]]
                        elif len(ff) == 2:
                            self.article_imgs[link] = [ff[0], ff[1]]
                        else:
                            self.article_imgs[link] = [ff[0]]
        except Exception as exc:
            print(f'Ошибка {exc} в получении ссылок на изображения товаров')
            with open('error.txt', 'a', encoding='utf-8') as file:

                file.write(f'{datetime.datetime.now().strftime("%d-%m-%y %H:%M")} '
                           f'Ошибка {exc} в получении ссылок на изображения товаров, функция - get_link_img()\n')

    async def get_link_img_run_async(self):
        connector = aiohttp.TCPConnector(force_close=True)
        async with aiohttp.ClientSession(headers=self.headers, connector=connector) as session:
            tasks = []
            for link in self.links_products:
                task = asyncio.create_task(self.get_link_img(session, link))
                tasks.append(task)
                if len(tasks) % 50 == 0:
                    await asyncio.gather(*tasks)
            await asyncio.gather(*tasks)
        # print(self.article_imgs)

    async def save_images(self, session, urls, name_img):
        try:
            images = []

            sys.stdout.write("\r")
            sys.stdout.write(f'Сохраняю изображение для {name_img}')
            sys.stdout.flush()

            for a, url in enumerate(urls):
                date_now = datetime.datetime.now()
                async with aiofiles.open(f'./img/{name_img}_{date_now.strftime("%M%S%f")}_{a}.jpg', mode='wb') as f:
                    async with session.get(url) as response:
                        images.append(f'./img/{name_img}_{date_now.strftime("%M%S%f")}_{a}.jpg')
                        async for x in response.content.iter_chunked(1024):
                            await f.write(x)

            self.article_imgs[name_img] = images
        except Exception as exc:
            print(f'Ошибка {exc} в сохранении изображений товаров')
            with open('error.txt', 'a', encoding='utf-8') as file:

                file.write(f'{datetime.datetime.now().strftime("%d-%m-%y %H:%M")} '
                           f'Ошибка {exc} в сохранении изображений товаров, функция - save_images()\n')

    async def save_images_run_async(self):
        if not os.path.isdir('./img/'):
            os.mkdir('./img/')
        async with aiohttp.ClientSession() as session:
            tasks = []
            for link in self.article_imgs:
                task = asyncio.create_task(self.save_images(session, urls=self.article_imgs[link], name_img=link))
                tasks.append(task)
                await asyncio.gather(*tasks)

    def resize_img(self):
        try:
            ImageFile.LOAD_TRUNCATED_IMAGES = True
            fixed_height = 426
            for img_file in tqdm(os.listdir('./img/')):
                if img_file[-4:] == '.jpg':
                    img = Image.open(f'./img/{img_file}')
                    height_percent = (fixed_height / float(img.size[1]))
                    width_size = int((float(img.size[0]) * float(height_percent)))
                    new_image = img.resize((width_size, fixed_height))
                    new_image.save(f'./img/{img_file}')
        except Exception as exc:
            print(f'Ошибка {exc} в изменении разрешения изображений')
            with open('error.txt', 'a', encoding='utf-8') as file:
                file.write(f'{datetime.datetime.now().strftime("%d-%m-%y %H:%M")} '
                           f'Ошибка {exc} в изменении разрешения изображений, функция - resize_img()\n')

    def sending_to_fotohosting(self):
        self.active_token = self.token[0]
        self.active_secret_key = self.secret_key[0]
        headers = {
            'Authorization': f'TOKEN {self.active_token}',
        }
        for img_url in self.article_imgs:

            img_short_link = []

            sys.stdout.write("\r")
            sys.stdout.write(f'Загружаю изображение для - {img_url}')
            sys.stdout.flush()

            img_links = self.article_imgs[img_url]

            for img in img_links:

                try:
                    files = {
                        'image': open(img, 'rb'),
                        'secret_key': (None, self.active_secret_key),
                    }
                    response = requests.post('https://api.imageban.ru/v1', headers=headers, files=files)
                    if response.json()['status'] == 200:
                        img_short_link.append(f"[URL=https://imageban.ru][IMG]{response.json()['data']['link']}"
                                              f"[/IMG][/URL]")
                    else:
                        print(f'Не удалось загрузить {img}')
                        continue
                except KeyError:
                    print(f'{img_url} ошибка загрузки изображения - {response.json()["error"]["message"]}\n')
                    with open('error.txt', 'a', encoding='utf-8') as file:
                        file.write(f'{datetime.datetime.now().strftime("%d-%m-%y %H:%M")} '
                                   f'{img} ошибка загрузки изображения, функция - sending_to_fotohosting()\n')
                    if response.json()["error"]["message"] == 'File reception error':
                        continue
                    elif response.json()["error"]["message"] == \
                            'Exceeded the daily limit of uploaded images for your account':
                        print('Переключение на второй аккаунт')

                        self.active_token = self.token[1]
                        self.active_secret_key = self.secret_key[1]

                        files = {
                            'image': open(img, 'rb'),
                            'secret_key': (None, self.active_secret_key),
                        }
                        response = requests.post('https://api.imageban.ru/v1', headers=headers, files=files)
                        if response.json()['status'] == 200:
                            img_short_link.append(f"[URL=https://imageban.ru][IMG]{response.json()['data']['link']}"
                                                  f"[/IMG][/URL]")
                        else:
                            print(f'Не удалось загрузить {img}')
                    continue
                except FileNotFoundError:
                    continue
                self.article_save_imgs[img_url] = img_short_link

    def write_final_file(self):
        try:
            columns = ['AC', 'AD']
            wb = load_workbook(filename=self.read_data_file)
            ws = wb.active

            ws['AC9'] = 'Ссылки на фотографии'
            date_now = datetime.datetime.now()
            for article in self.article_save_imgs:
                # if article == flag:
                #     break
                for i, link in enumerate(self.article_save_imgs[article]):

                    for row in ws.iter_cols(min_col=1, max_col=1, min_row=10):
                        for cell in row:
                            # if cell.value == flag:
                            #     break
                            if cell.value == article:
                                # if i == len(self.article_save_imgs[article]) - 1:
                                #     flag = cell.value
                                ws[f'{columns[i]}{cell.row}'] = link

            file_name = f'data_final_{date_now.strftime("%d-%m-%y_%H-%M")}.xlsx'
            wb.save(filename=file_name)
            shutil.rmtree('./img/')
            print(f'Файл {file_name} сохранён')
        except Exception as exc:
            print(f'Ошибка {exc} в записи итогового файла')
            with open('error.txt', 'a', encoding='utf-8') as file:
                file.write(f'{datetime.datetime.now().strftime("%d-%m-%y %H:%M")} '
                           f'Ошибка {exc} в записи итогового файла, функция - write_final_file()\n')

    def run(self):
        try:
            # asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
            print('Начало работы')
            self.open_token_file()
            self.read_file()
            print('Получаю артикул товаров')
            self.get_article_number()
            print('\rАртикулы получил')
            print('---------------------------\n')
            print('Получаю ссылки на товары')
            asyncio.run(self.get_link_product_run_async())
            print('\nСсылки получены')
            # print('---------------------------\n')
            # print('Ищу изображения товаров')
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
            # self.write_final_file()
            print('Работа завершена')
            print('Для выхода нажмите Enter')
            input()
            print('---------------------------\n')
        except Exception as exc:
            print(f'Произошла ошибка {exc}')
            print('Для выхода нажмите Enter')
            input()
            print('---------------------------\n')


def main():
    p = Parser()
    p.run()


if __name__ == '__main__':
    main()
