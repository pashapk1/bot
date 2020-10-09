import config
import logging
import asyncio
from datetime import datetime

from aiogram import Bot, Dispatcher, executor, types
from sqlighter import SQLighter

from hsenews import hsenews

# задаем уровень логов
logging.basicConfig(level=logging.INFO)

# инициализируем бота
loop = asyncio.get_event_loop()
bot = Bot(token=config.API_TOKEN)
dp = Dispatcher(bot, loop=loop)

# инициализируем соединение с БД
db = SQLighter('db.db')

# инициализируем парсер
hn = hsenews('lastkey.txt')


# Команда активации подписки
@dp.message_handler(commands=['subscribe'])
async def subscribe(message: types.Message):
    if (not db.subscriber_exists(message.from_user.id)):
        # если юзера нет в базе, добавляем его
        db.add_subscriber(message.from_user.id)
    else:
        # если он уже есть, то просто обновляем ему статус подписки
        db.update_subscription(message.from_user.id, True)

    await message.answer(
        "Вы успешно подписались на рассылку!\nЖдите, скоро выйдут новые новости и вы узнаете о них первыми =)")


# Команда отписки
@dp.message_handler(commands=['unsubscribe'])
async def unsubscribe(message: types.Message):
    if (not db.subscriber_exists(message.from_user.id)):
        # если юзера нет в базе, добавляем его с неактивной подпиской (запоминаем)
        db.add_subscriber(message.from_user.id, False)
        await message.answer("Вы итак не подписаны.")
    else:
        # если он уже есть, то просто обновляем ему статус подписки
        db.update_subscription(message.from_user.id, False)
        await message.answer("Вы успешно отписаны от рассылки.")

# проверяем наличие новых новостей и делаем рассылки
async def scheduled(wait_for):
    while True:
        await asyncio.sleep(wait_for)

        # проверяем наличие новых новостей
        new_news = hn.new_news()

        if (new_news):
            # если новости есть, переворачиваем список и итерируем
            new_news.reverse()
            for nn in new_news:
                # парсим инфу о новой новости
                nfo = hn.new_news_info(nn)

                # получаем список подписчиков бота
                subscriptions = db.get_subscriptions()

                # отправляем всем новость
                with open(hn.download_image(nfo['image']), 'rb') as photo:
                    for s in subscriptions:
                        await bot.send_photo(
                            s[1],
                            photo,
                            caption=nfo['title'] + "\n" + "\n" + nfo['excerpt'] + "\n\n" +
                                    nfo['link'],
                            disable_notification=True
                        )

                # обновляем ключ
                hn.update_lastkey(nfo['id'])


# запускаем лонг поллинг
if __name__ == '__main__':
    dp.loop.create_task(scheduled(10)) # пока что оставим 10 секунд (в качестве теста)
    executor.start_polling(dp, skip_updates=True)
